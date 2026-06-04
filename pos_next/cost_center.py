"""Cost center resolution for POS Next (including Veto / Delivery Note billing)."""

from __future__ import annotations

import frappe


def get_item_group_selling_cost_center(item_code: str, company: str) -> str | None:
	"""Return Item Group selling cost center for company, if configured."""
	if not item_code or not company:
		return None

	item_group = frappe.get_cached_value("Item", item_code, "item_group")
	if not item_group:
		return None

	return frappe.db.get_value(
		"Item Default",
		{"parent": item_group, "parenttype": "Item Group", "company": company},
		"selling_cost_center",
	)


def resolve_selling_cost_center(item_code: str, company: str, fallback: str | None = None) -> str | None:
	"""Item Group cost center wins over the provided fallback (POS Profile or DN/Vet)."""
	return get_item_group_selling_cost_center(item_code, company) or fallback


def get_pos_line_cost_center(item_code: str, company: str, pos_profile: str | None = None) -> str | None:
	"""POS cart / SI line added from POS: POS Profile cost center, overridden by Item Group."""
	pos_cc = None
	if pos_profile and company:
		pos_cc = frappe.db.get_value("POS Profile", pos_profile, "cost_center")
	return resolve_selling_cost_center(item_code, company, pos_cc)


def bulk_pos_line_cost_centers(
	item_codes: list[str], company: str, pos_profile: str | None = None
) -> dict[str, str | None]:
	"""Resolve default cost centers for many items (item search / cart add)."""
	if not item_codes or not company:
		return {}

	pos_cc = None
	if pos_profile:
		pos_cc = frappe.db.get_value("POS Profile", pos_profile, "cost_center")

	item_groups = dict(
		frappe.db.sql(
			"""
			SELECT name, item_group
			FROM `tabItem`
			WHERE name IN %s
			""",
			[item_codes],
		)
	)

	group_cc_map = {}
	group_names = {g for g in item_groups.values() if g}
	if group_names:
		for parent, selling_cost_center in frappe.db.sql(
			"""
			SELECT parent, selling_cost_center
			FROM `tabItem Default`
			WHERE parenttype = 'Item Group' AND company = %s AND parent IN %s
			""",
			[company, tuple(group_names)],
		):
			if selling_cost_center:
				group_cc_map[parent] = selling_cost_center

	result = {}
	for item_code in item_codes:
		ig_cc = group_cc_map.get(item_groups.get(item_code))
		result[item_code] = ig_cc or pos_cc
	return result


@frappe.whitelist()
def get_line_cost_center(item_code, pos_profile):
	"""Default cost center for one POS cart line."""
	if not item_code or not pos_profile:
		return None
	company = frappe.db.get_value("POS Profile", pos_profile, "company")
	return get_pos_line_cost_center(item_code, company, pos_profile)


def get_dn_line_cost_center(
	item_code: str,
	company: str,
	dn_row_cost_center: str | None = None,
	dn_header_cost_center: str | None = None,
) -> str | None:
	"""DN / Vet Procedure cart line: DN row (or header) cost center, overridden by Item Group."""
	fallback = dn_row_cost_center or dn_header_cost_center
	return resolve_selling_cost_center(item_code, company, fallback)


# Backward-compatible alias
get_cart_line_cost_center = get_pos_line_cost_center


@frappe.whitelist()
def get_cost_centers(company):
	"""Leaf cost centers for the company (POS cart cost center picker)."""
	if not company:
		return []

	return frappe.get_all(
		"Cost Center",
		filters={"company": company, "is_group": 0, "disabled": 0},
		fields=["name"],
		order_by="name",
	)
