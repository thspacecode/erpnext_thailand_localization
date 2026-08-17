from typing import TYPE_CHECKING

from erpnext_thailand_localization.types import Json

from .base import DocTypeFactory

if TYPE_CHECKING:
	from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry


class PaymentEntryFactory(DocTypeFactory["PaymentEntry"]):
	doctype = "Payment Entry"

	@classmethod
	def defaults(cls) -> "Json[PaymentEntry]":
		return {
			"company": "Dunder Mifflin",
			"payment_type": "Receive",
			"paid_from_account_currency": "THB",
			"paid_to_account_currency": "THB",
			"source_exchange_rate": 1,
			"target_exchange_rate": 1,
			"paid_amount": 1000,
			"received_amount": 1000,
		}
