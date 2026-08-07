import csv
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

import frappe

ChangeType = Literal["created", "updated", "skipped"]
Report = dict[ChangeType, dict[str, list[str]]]


class BaseImporter(ABC):
	data_csv_path: Path | None = None

	def __init__(self):
		self.report: Report = {
			"created": {},
			"updated": {},
			"skipped": {},
		}

	def record_change(self, change_type: ChangeType, doctype: str, name: str):
		self.report[change_type].setdefault(doctype, []).append(name)

	def merge_report(self, report: Report) -> Report:
		for change_type in ("created", "updated", "skipped"):
			for doctype, names in report[change_type].items():
				self.report[change_type].setdefault(doctype, []).extend(names)
		return self.report

	def csv_loader(self, filename: str, csv_replacements: dict[str, str] | None = None) -> Report:
		"""Create or update DocType records from a CSV file.

		File naming convention:
		- Name the file exactly after the parent DocType, including spaces and capitalization.
		- Pass the filename without the ``.csv`` extension. For example,
		  ``csv_loader("Example Parent")`` loads ``Example Parent.csv`` and imports the
		  ``Example Parent`` DocType.

		File path:
		The loader reads ``<data_csv_path>/<filename>.csv``. ``BaseImporter`` does not
		provide a default path, so subclasses must override ``data_csv_path`` with a
		``pathlib.Path``. For example::

		        class SetupInitialData(BaseImporter):
		            data_csv_path = Path(__file__).parent / "data_csv"

		CSV replacements:
		Pass replacements when loading a CSV to resolve environment-specific values::

		        importer.csv_loader(
		            "Example Parent",
		            csv_replacements={"company": "Example Company"},
		        )

		Replacement keys are automatically enclosed as ``{{ key }}``. Every occurrence
		of a placeholder in parent and child values is replaced before type casting and
		document lookup.

		Column naming convention:
		- Parent columns use Frappe fieldnames, not field labels (for example,
		  ``company_name`` rather than ``Company Name``).
		- Include ``name`` unless the DocType uses ``field:<fieldname>`` for autoname;
		  in that case, include the autoname field instead.
		- Child-table columns use ``[<parent_table_fieldname>]<child_fieldname>``.
		  For example, ``[items]item_code`` refers to the ``item_code`` field in the
		  child table stored in the parent's ``items`` field.
		- Empty cells are ignored. A row with any populated parent column starts a new
		  parent record; rows containing only child-table values continue the current
		  parent record.

		For example, ``Example Parent.csv`` can import two parent records and three
		child rows::

			name,company,[items]item_code,[items]qty
			BUNDLE-001,ACME,ITEM-001,2
			,,ITEM-002,1
			BUNDLE-002,ACME,ITEM-003,4

		The second CSV row above has empty parent columns, so ``ITEM-002`` is appended
		to the ``items`` table of ``BUNDLE-001``. ``BUNDLE-002`` starts a new parent
		record. Keep all columns for one child row on the same CSV row.

		The method returns the importer's cumulative created, updated, and skipped
		report.
		"""
		if self.data_csv_path is None:
			raise ValueError("data_csv_path must be configured")

		file_path = self.data_csv_path / f"{filename}.csv"
		doctype = filename
		int_types = {"Int", "Check"}
		float_types = {"Float", "Currency", "Percent", "Duration"}

		def build_casters(dt):
			casters = {}
			for field in frappe.get_meta(dt).fields:
				if field.fieldtype in int_types:
					casters[field.fieldname] = int
				elif field.fieldtype in float_types:
					casters[field.fieldname] = float
			return casters

		def cast(casters, fieldname, value):
			caster = casters.get(fieldname)
			return caster(value) if caster else value

		def prepare_csv_value(value: str | None) -> str | None:
			if value is None:
				return None
			for key, replacement in (csv_replacements or {}).items():
				value = value.replace(f"{{{{ {key} }}}}", replacement)
			return value

		def values_match(actual, expected):
			if not isinstance(expected, list):
				return actual == expected
			if len(actual or []) != len(expected):
				return False
			return all(
				all(actual_row.get(fieldname) == value for fieldname, value in expected_row.items())
				for actual_row, expected_row in zip(actual, expected, strict=True)
			)

		def get_record_name(values):
			if values.get("name"):
				return values["name"]
			autoname = parent_meta.autoname or ""
			if autoname.startswith("field:"):
				return values[autoname.removeprefix("field:")]
			raise ValueError(f"{doctype} CSV rows must include a name")

		child_column = re.compile(r"^\[(\w+)\](.+)$")
		parent_meta = frappe.get_meta(doctype)
		parent_casters = build_casters(doctype)
		child_casters = {
			field.fieldname: build_casters(field.options)
			for field in parent_meta.fields
			if field.fieldtype in ("Table", "Table MultiSelect") and field.options
		}
		records = []
		current = None

		with file_path.open(encoding="utf-8", newline="") as csv_file:
			for row in csv.DictReader(csv_file):
				row = {column: prepare_csv_value(value) for column, value in row.items()}
				scalar = {
					column: cast(parent_casters, column, value)
					for column, value in row.items()
					if column and not child_column.match(column) and value
				}
				child_data = {}
				for column, value in row.items():
					match = column and child_column.match(column)
					if match and value:
						table, child_field = match.group(1), match.group(2)
						child_data.setdefault(table, {})[child_field] = cast(
							child_casters.get(table, {}), child_field, value
						)

				if scalar:
					if current is not None:
						records.append(current)
					current = scalar

				if current is not None:
					for table, child_row in child_data.items():
						current.setdefault(table, []).append(child_row)

		if current is not None:
			records.append(current)

		for expected_values in records:
			name = get_record_name(expected_values)
			if not frappe.db.exists(doctype, name):
				doc = frappe.get_doc({"doctype": doctype, **expected_values})
				if expected_values.get("name"):
					doc.flags.name_set = True
				for child in doc.get_all_children():
					if child.name:
						child.flags.name_set = True
				doc.insert()
				self.record_change("created", doctype, doc.name)
				continue

			doc = frappe.get_doc(doctype, name)
			changed_values = {
				fieldname: value
				for fieldname, value in expected_values.items()
				if not values_match(doc.get(fieldname), value)
			}
			if changed_values:
				doc.update(changed_values)
				doc.save()
				self.record_change("updated", doctype, name)
			else:
				self.record_change("skipped", doctype, name)

		return self.report

	@abstractmethod
	def make(self) -> Report:
		return self.report
