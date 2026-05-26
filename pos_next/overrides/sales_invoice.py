from contextlib import contextmanager

import frappe
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

	def _delivery_note_linked_rows(self):
		return [
			row
			for row in self.get("items", [])
			if row.get("delivery_note") or row.get("dn_detail")
		]

	def _delivery_note_row_key(self, row):
		return row.get("dn_detail") or row.name

	def _get_delivery_note_row_cost_center(self, row):
		if row.get("cost_center"):
			return row.cost_center
		if row.get("dn_detail"):
			return frappe.db.get_value("Delivery Note Item", row.dn_detail, "cost_center")
		return None

	def _preserve_delivery_note_cost_centers(self):
		dn_rows = self._delivery_note_linked_rows()
		if not dn_rows:
			return None, {}

		all_dn = len(dn_rows) == len(self.get("items", []))
		preserved_header = self.get("cost_center") if all_dn else None
		if all_dn and not preserved_header:
			first_dn = dn_rows[0].get("delivery_note")
			if first_dn:
				preserved_header = frappe.db.get_value("Delivery Note", first_dn, "cost_center")

		preserved_items = {}
		for row in dn_rows:
			cost_center = self._get_delivery_note_row_cost_center(row)
			if cost_center:
				preserved_items[self._delivery_note_row_key(row)] = cost_center

		return preserved_header, preserved_items

	def _restore_delivery_note_cost_centers(self, preserved_header, preserved_items):
		dn_rows = self._delivery_note_linked_rows()
		if not dn_rows:
			return

		if preserved_header:
			self.cost_center = preserved_header

		for row in dn_rows:
			key = self._delivery_note_row_key(row)
			cost_center = preserved_items.get(key) or self._get_delivery_note_row_cost_center(row)
			if cost_center:
				row.cost_center = cost_center

	def set_pos_fields(self, for_validate=False):
		preserved_header, preserved_items = self._preserve_delivery_note_cost_centers()
		super().set_pos_fields(for_validate=for_validate)
		self._restore_delivery_note_cost_centers(preserved_header, preserved_items)

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
