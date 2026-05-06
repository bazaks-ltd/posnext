from contextlib import contextmanager

from frappe.utils import cint

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


class POSNextSalesInvoice(SalesInvoice):
	"""Sales Invoice extension for POS carts that also bill Delivery Notes.

	ERPNext treats `update_stock` as a header-level flag and blocks Sales Invoices
	with `update_stock = 1` when any row is linked to a Delivery Note. POS Next can
	have mixed carts: pre-delivered DN rows plus regular store stock rows. For POS
	invoices, we keep stock update enabled but exclude DN-linked rows from stock
	operations because those rows already moved stock through the Delivery Note.
	"""

	def _is_pos_next_mixed_stock_invoice(self):
		return cint(self.get("is_pos")) and cint(self.get("update_stock")) and any(
			row.get("delivery_note") or row.get("dn_detail") for row in self.get("items", [])
		)

	def validate_delivery_note(self):
		if self._is_pos_next_mixed_stock_invoice():
			return
		return super().validate_delivery_note()

	@contextmanager
	def _without_delivery_note_stock_rows(self, table_name="items"):
		if table_name != "items" or not self._is_pos_next_mixed_stock_invoice():
			yield
			return

		original_items = self.get("items")
		stock_items_to_update = [
			row for row in original_items if not (row.get("delivery_note") or row.get("dn_detail"))
		]

		self.set("items", stock_items_to_update)
		try:
			yield
		finally:
			self.set("items", original_items)

	def make_bundle_for_sales_purchase_return(self, table_name=None):
		with self._without_delivery_note_stock_rows(table_name or "items"):
			return super().make_bundle_for_sales_purchase_return(table_name)

	def make_bundle_using_old_serial_batch_fields(self, table_name=None, via_landed_cost_voucher=False):
		with self._without_delivery_note_stock_rows(table_name or "items"):
			return super().make_bundle_using_old_serial_batch_fields(
				table_name, via_landed_cost_voucher=via_landed_cost_voucher
			)

	def validate_standalone_serial_nos_customer(self):
		with self._without_delivery_note_stock_rows("items"):
			return super().validate_standalone_serial_nos_customer()

	def update_stock_reservation_entries(self):
		with self._without_delivery_note_stock_rows("items"):
			return super().update_stock_reservation_entries()

	def update_stock_ledger(self, allow_negative_stock=False):
		with self._without_delivery_note_stock_rows("items"):
			return super().update_stock_ledger(allow_negative_stock=allow_negative_stock)
