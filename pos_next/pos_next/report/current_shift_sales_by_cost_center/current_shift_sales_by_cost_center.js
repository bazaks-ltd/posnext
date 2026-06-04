// Copyright (c) 2026, Bazaks and contributors
// For license information, please see license.txt

frappe.query_reports["Current Shift Sales by Cost Center"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "pos_opening_shift",
			label: __("POS Opening Shift"),
			fieldtype: "Link",
			options: "POS Opening Shift",
			reqd: 1,
			get_query: () => ({
				filters: { status: "Open", docstatus: 1 },
			}),
		},
		{
			fieldname: "pos_profile",
			label: __("POS Profile"),
			fieldtype: "Link",
			options: "POS Profile",
		},
		{
			fieldname: "include_non_pos",
			label: __("Include Non-POS Sales Invoices"),
			fieldtype: "Check",
			default: 0,
		},
	],
	onload(report) {
		frappe.call({
			method: "pos_next.api.shifts.check_opening_shift",
			callback(r) {
				const shift = r.message?.pos_opening_shift;
				if (shift?.name) {
					report.set_filter_value("pos_opening_shift", shift.name);
					if (shift.pos_profile) {
						report.set_filter_value("pos_profile", shift.pos_profile);
					}
					if (shift.company) {
						report.set_filter_value("company", shift.company);
					}
				}
			},
		});
	},
};
