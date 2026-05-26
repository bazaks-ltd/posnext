// Copyright (c) 2026, Bazaks and contributors
// For license information, please see license.txt

frappe.query_reports["Daily Sales by Cost Center"] = {
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
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
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
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
			events: {
				onCheckRow: function (data) {
					if (!data || !frappe.query_report.chart) return;
					const row_name = data[2]?.content;
					if (!row_name || row_name.startsWith("—")) return;

					const raw_data = frappe.query_report.chart.data;
					const new_datasets = raw_data.datasets || [];
					const slice_at = 3;
					const element_found = new_datasets.some((element, index, array) => {
						if (element.name === row_name) {
							array.splice(index, 1);
							return true;
						}
						return false;
					});

					if (!element_found) {
						new_datasets.push({
							name: row_name,
							values: data.slice(slice_at, data.length - 1).map((column) => {
								const value = column.content;
								return typeof value === "number" ? value : flt(value);
							}),
						});
					}

					const new_data = {
						labels: raw_data.labels,
						datasets: new_datasets,
					};
					const new_options = Object.assign({}, frappe.query_report.chart_options, {
						data: new_data,
					});
					frappe.query_report.render_chart(new_options);
					frappe.query_report.raw_chart_data = new_data;
				},
			},
		});
	},
};
