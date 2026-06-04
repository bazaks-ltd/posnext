# Copyright (c) 2026, Bazaks and contributors
# For license information, please see license.txt

import frappe
from frappe.desk.query_report import run
from frappe.utils import today


POS_REPORTS = (
	"Daily Sales by Cost Center",
	"Current Shift Sales by Cost Center",
)


@frappe.whitelist()
def run_pos_report(report_name, filters=None):
	"""Run a POS Next sales report for the POS UI."""
	if report_name not in POS_REPORTS:
		frappe.throw(frappe._("Report {0} is not available").format(report_name))

	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	filters = frappe._dict(filters or {})

	return run(report_name, filters)


@frappe.whitelist()
def get_default_report_filters(report_name, company=None, pos_profile=None):
	"""Default filters for POS report dialogs."""
	if report_name not in POS_REPORTS:
		frappe.throw(frappe._("Report {0} is not available").format(report_name))

	company = company or frappe.defaults.get_user_default("Company")
	filters = {
		"company": company,
		"pos_profile": pos_profile,
		"include_non_pos": 0,
	}

	if report_name == "Daily Sales by Cost Center":
		filters["from_date"] = today()
		filters["to_date"] = today()
	elif report_name == "Current Shift Sales by Cost Center":
		from pos_next.api.shifts import check_opening_shift

		shift_data = check_opening_shift()
		shift = shift_data.get("pos_opening_shift") if shift_data else None
		if shift:
			filters["pos_opening_shift"] = shift.name
			filters["pos_profile"] = filters.get("pos_profile") or shift.pos_profile
			filters["company"] = shift.company or company
		else:
			filters["pos_opening_shift"] = None

	return filters
