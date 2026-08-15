from typing import TYPE_CHECKING

from erpnext_thailand_localization.types import Json

from .base import DocTypeFactory

if TYPE_CHECKING:
	from frappe.contacts.doctype.address.address import Address


class CompanyAddressFactory(DocTypeFactory["Address"]):
	doctype = "Address"

	@classmethod
	def defaults(cls) -> "Json[Address]":
		return {
			"address_title": "Dunder Mifflin Test",
			"address_type": "Billing",
			"address_line1": "1725 Slough Avenue",
			"city": "Bangkok",
			"state": "Bangkok",
			"pincode": "10100",
			"country": "Thailand",
			"is_your_company_address": 1,
			"links": [{"link_doctype": "Company", "link_name": "Dunder Mifflin"}],
		}
