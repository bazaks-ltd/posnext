# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt


@frappe.whitelist()
def list_delivery_notes_for_billing(customer, company, txt=None, limit=50):
	"""
	List submitted Delivery Notes with remaining qty to bill, for the POS customer/company.
	Mirrors Sales Invoice → Get Items From → Delivery Note filters.
	"""
	txt = txt or ""
	limit = min(cint(flt(limit) or 50), 100)

	filters = {"docstatus": 1, "company": company, "is_return": 0}
	if customer:
		filters["customer"] = customer

	from erpnext.controllers.queries import get_delivery_notes_to_be_billed

	return get_delivery_notes_to_be_billed(
		"Delivery Note",
		txt,
		"name",
		0,
		limit,
		filters,
		as_dict=1,
	)


@frappe.whitelist()
def get_cart_items_from_delivery_note(delivery_note, pos_profile=None):
	"""
	Build pending Sales Invoice lines from a Delivery Note (same mapping as desk SI),
	returned as dicts for the POS cart. Preserves dn_detail / delivery_note / SO links.
	"""
	from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

	if not frappe.db.exists("Delivery Note", delivery_note):
		frappe.throw(_("Delivery Note {0} not found").format(delivery_note))

	dn = frappe.get_doc("Delivery Note", delivery_note)
	dn_items_by_name = {row.name: row for row in dn.items}

	if pos_profile:
		pp_company = frappe.db.get_value("POS Profile", pos_profile, "company")
		if pp_company and dn.company and dn.company != pp_company:
			frappe.throw(
				_("Delivery Note belongs to company {0}; POS profile is for {1}").format(
					dn.company, pp_company
				)
			)

	si = make_sales_invoice(delivery_note)

	out = []
	for row in si.items:
		d = row.as_dict()
		item_code = d.get("item_code")
		dn_row = dn_items_by_name.get(d.get("dn_detail"))
		item_meta = (
			frappe.db.get_value(
				"Item",
				item_code,
				["has_serial_no", "has_batch_no", "is_stock_item", "image"],
				as_dict=True,
			)
			or {}
		)

		qty = flt(d.get("qty"))
		# Keep DN pricing authoritative: use mapped SI qty/links, but preserve the
		# original Delivery Note row rate/price list/discount values.
		if dn_row:
			rate = flt(dn_row.get("rate") or 0)
			plr = flt(dn_row.get("price_list_rate") or dn_row.get("rate") or 0)
			discount_percentage = flt(dn_row.get("discount_percentage") or 0)
			discount_amount = flt(dn_row.get("discount_amount") or 0)
		else:
			rate = flt(d.get("rate") or 0)
			plr = flt(d.get("price_list_rate") or d.get("rate") or 0)
			discount_percentage = flt(d.get("discount_percentage") or 0)
			discount_amount = flt(d.get("discount_amount") or 0)

		out.append(
			{
				"item_code": item_code,
				"item_name": d.get("item_name"),
				"rate": rate,
				"price_list_rate": plr if plr else rate,
				"quantity": qty,
				"uom": d.get("uom"),
				"stock_uom": d.get("stock_uom"),
				"conversion_factor": flt(d.get("conversion_factor") or 1),
				"warehouse": d.get("warehouse"),
				"batch_no": d.get("batch_no"),
				"serial_no": d.get("serial_no"),
				"serial_and_batch_bundle": d.get("serial_and_batch_bundle"),
				"dn_detail": d.get("dn_detail"),
				"delivery_note": d.get("delivery_note"),
				"sales_order": d.get("sales_order"),
				"so_detail": d.get("so_detail"),
				"discount_percentage": discount_percentage,
				"discount_amount": discount_amount,
				"has_serial_no": cint(item_meta.get("has_serial_no") or 0),
				"has_batch_no": cint(item_meta.get("has_batch_no") or 0),
				"is_stock_item": 0 if item_meta.get("is_stock_item") == 0 else 1,
				"image": item_meta.get("image"),
			}
		)

	return {"items": out, "delivery_note": delivery_note, "customer": dn.customer}
