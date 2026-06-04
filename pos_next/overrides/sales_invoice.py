from contextlib import contextmanager

import frappe
from frappe.utils import cint, flt

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

from pos_next.cost_center import get_dn_line_cost_center, get_pos_line_cost_center


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
		dn_row_cc = row.get("cost_center")
		if not dn_row_cc and row.get("dn_detail"):
			dn_row_cc = frappe.db.get_value("Delivery Note Item", row.dn_detail, "cost_center")

		dn_header_cc = None
		if row.get("delivery_note"):
			dn_header_cc = frappe.db.get_value("Delivery Note", row.delivery_note, "cost_center")

		return get_dn_line_cost_center(
			row.item_code, self.company, dn_row_cc, dn_header_cc
		)

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

	def _pos_allows_cost_center_edit(self):
		if not self.pos_profile:
			return False
		return cint(
			frappe.db.get_value(
				"POS Profile", self.pos_profile, "custom_allow_edit_item_cost_center"
			)
		)

	def _cart_cost_center_row_key(self, row):
		return row.get("dn_detail") or row.get("name") or f"{row.idx}-{row.item_code}"

	def _preserve_cart_cost_centers(self):
		if not self._pos_allows_cost_center_edit():
			return {}

		return {
			self._cart_cost_center_row_key(row): row.get("cost_center")
			for row in self.get("items", [])
		}

	def _restore_cart_cost_centers(self, preserved):
		if not preserved:
			return

		for row in self.get("items", []):
			key = self._cart_cost_center_row_key(row)
			if key in preserved:
				row.cost_center = preserved[key]

	def _apply_cart_cost_centers_from_payload(self, items_payload):
		"""Apply cost centers sent from the POS cart (authoritative when edit is enabled)."""
		if not items_payload or not self._pos_allows_cost_center_edit():
			return

		payload_rows = [item for item in items_payload if isinstance(item, dict)]
		invoice_rows = list(self.get("items", []))

		if len(payload_rows) == len(invoice_rows):
			for row, payload in zip(invoice_rows, payload_rows):
				row.cost_center = payload.get("cost_center")
			return

		by_dn_detail = {
			item["dn_detail"]: item.get("cost_center")
			for item in payload_rows
			if item.get("dn_detail")
		}
		for row in invoice_rows:
			if row.get("dn_detail") and row.dn_detail in by_dn_detail:
				row.cost_center = by_dn_detail[row.dn_detail]
				continue

			for payload in payload_rows:
				if payload.get("dn_detail"):
					continue
				if payload.get("item_code") != row.item_code:
					continue
				if abs(flt(payload.get("qty")) - flt(row.qty)) >= 0.0001:
					continue
				row.cost_center = payload.get("cost_center")
				break

	def _apply_resolved_cost_centers(self):
		"""Apply POS / DN defaults and Item Group overrides (when cart edit is disabled)."""
		if not self.company:
			return

		for row in self.get("items", []):
			if not row.get("item_code"):
				continue

			if row.get("delivery_note") or row.get("dn_detail"):
				row.cost_center = self._get_delivery_note_row_cost_center(row)
			else:
				row.cost_center = get_pos_line_cost_center(
					row.item_code, self.company, self.pos_profile
				)

	def set_pos_fields(self, for_validate=False):
		cart_preserved = self._preserve_cart_cost_centers()

		if self._pos_allows_cost_center_edit():
			super().set_pos_fields(for_validate=for_validate)
			self._restore_cart_cost_centers(cart_preserved)
			return

		preserved_header, preserved_items = self._preserve_delivery_note_cost_centers()
		super().set_pos_fields(for_validate=for_validate)
		self._restore_delivery_note_cost_centers(preserved_header, preserved_items)
		self._apply_resolved_cost_centers()

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
