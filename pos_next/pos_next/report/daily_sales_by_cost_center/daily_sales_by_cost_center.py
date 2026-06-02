# Copyright (c) 2026, Bazaks and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _, scrub
from frappe.utils import add_days, cint, flt, formatdate, getdate


def execute(filters=None):
	return DailySalesByCostCenter(filters).run()


class DailySalesByCostCenter:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.from_date = getdate(self.filters.from_date)
		self.to_date = getdate(self.filters.to_date)
		if self.from_date > self.to_date:
			frappe.throw(_("From Date cannot be after To Date"))

		self.company = self.filters.company
		self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
		self.currency_precision = frappe.get_cached_value("Currency", self.currency, "fraction") or 2
		self.daily_periods = []
		self.columns = []
		self.data = []
		self.chart = None
		self.sales_section_rows = []

	def run(self):
		self._build_daily_periods()
		self._build_columns()
		self._build_data()
		self._build_chart()
		return self.columns, self.data, None, self.chart, None, 0

	def _build_daily_periods(self):
		current = self.from_date
		while current <= self.to_date:
			label = formatdate(current)
			self.daily_periods.append((label, scrub(f"d_{current.isoformat()}"), current))
			current = add_days(current, 1)

	def _build_columns(self):
		self.columns = [
			{
				"label": _("Cost Center / Mode of Payment"),
				"fieldname": "entity",
				"fieldtype": "Data",
				"width": 220,
			}
		]
		for label, fieldname, _day in self.daily_periods:
			self.columns.append(
				{
					"label": label,
					"fieldname": fieldname,
					"fieldtype": "Currency",
					"options": self.currency,
					"width": 120,
				}
			)
		self.columns.append(
			{
				"label": _("Total"),
				"fieldname": "total",
				"fieldtype": "Currency",
				"options": self.currency,
				"width": 120,
			}
		)

	def _invoice_conditions(self):
		conditions = [
			"si.docstatus = 1",
			"si.company = %(company)s",
			"si.posting_date BETWEEN %(from_date)s AND %(to_date)s",
			"IFNULL(si.is_opening, 'No') = 'No'",
		]
		if not cint(self.filters.include_non_pos):
			conditions.append("si.is_pos = 1")
		if self.filters.pos_profile:
			conditions.append("si.pos_profile = %(pos_profile)s")
		return " AND ".join(conditions)

	def _get_sales_by_cost_center(self):
		return frappe.db.sql(
			f"""
			SELECT
				COALESCE(
					NULLIF(igd.selling_cost_center, ''),
					NULLIF(sii.cost_center, ''),
					NULLIF(si.cost_center, ''),
					%(not_set)s
				) AS entity,
				si.posting_date,
				SUM(sii.base_net_amount) AS amount
			FROM `tabSales Invoice` si
			INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
			LEFT JOIN `tabItem Default` igd
				ON igd.parent = sii.item_group
				AND igd.parenttype = 'Item Group'
				AND igd.company = si.company
			WHERE {self._invoice_conditions()}
			GROUP BY entity, si.posting_date
			ORDER BY entity, si.posting_date
			""",
			self._query_params(),
			as_dict=True,
		)

	def _cost_center_share_sql(self, amount_expr):
		"""Allocate an invoice-level amount to item lines by net amount share."""
		return f"""
			CASE
				WHEN IFNULL(si.base_net_total, 0) = 0 THEN 0
				ELSE (sii.base_net_amount / si.base_net_total) * ({amount_expr})
			END
		"""

	def _get_tax_by_cost_center(self):
		tax_expr = self._cost_center_share_sql("stc.base_tax_amount_after_discount_amount")
		return frappe.db.sql(
			f"""
			SELECT
				COALESCE(
					NULLIF(igd.selling_cost_center, ''),
					NULLIF(sii.cost_center, ''),
					NULLIF(si.cost_center, ''),
					%(not_set)s
				) AS entity,
				si.posting_date,
				SUM({tax_expr}) AS amount
			FROM `tabSales Invoice` si
			INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
			LEFT JOIN `tabItem Default` igd
				ON igd.parent = sii.item_group
				AND igd.parenttype = 'Item Group'
				AND igd.company = si.company
			INNER JOIN `tabSales Taxes and Charges` stc
				ON stc.parent = si.name
				AND stc.parenttype = 'Sales Invoice'
				AND stc.docstatus = 1
			INNER JOIN `tabAccount` acc ON acc.name = stc.account_head
			WHERE {self._invoice_conditions()}
				AND acc.account_type = 'Tax'
				AND stc.account_head NOT IN (
					SELECT DISTINCT sii2.income_account
					FROM `tabSales Invoice Item` sii2
					WHERE sii2.parent = si.name AND IFNULL(sii2.income_account, '') != ''
				)
			GROUP BY entity, si.posting_date
			ORDER BY entity, si.posting_date
			""",
			self._query_params(),
			as_dict=True,
		)

	def _get_total_sales_by_cost_center(self, net_entries, tax_entries):
		combined = defaultdict(float)

		for entry in net_entries:
			combined[(entry.entity, getdate(entry.posting_date))] += flt(entry.amount)

		for entry in tax_entries:
			combined[(entry.entity, getdate(entry.posting_date))] += flt(entry.amount)

		return [
			frappe._dict({"entity": entity, "posting_date": posting_date, "amount": amount})
			for (entity, posting_date), amount in sorted(
				combined.items(), key=lambda row: ((row[0][0] or "").lower(), row[0][1])
			)
		]

	def _get_payments_by_mode(self):
		return frappe.db.sql(
			f"""
			SELECT
				sip.mode_of_payment AS entity,
				si.posting_date,
				SUM(sip.base_amount) AS amount
			FROM `tabSales Invoice` si
			INNER JOIN `tabSales Invoice Payment` sip ON sip.parent = si.name
			WHERE {self._invoice_conditions()}
			GROUP BY sip.mode_of_payment, si.posting_date
			ORDER BY sip.mode_of_payment, si.posting_date
			""",
			self._query_params(),
			as_dict=True,
		)

	def _query_params(self):
		return {
			"company": self.company,
			"from_date": self.from_date,
			"to_date": self.to_date,
			"pos_profile": self.filters.pos_profile,
			"not_set": _("Not Set"),
		}

	def _build_data(self):
		self.data = []
		net_entries = self._get_sales_by_cost_center()
		tax_entries = self._get_tax_by_cost_center()
		self._append_section(_("Net Sales by Cost Center"), net_entries)
		self._append_section(_("Tax by Cost Center"), tax_entries)
		self._append_section(
			_("Total Sales by Cost Center (Incl. Tax)"),
			self._get_total_sales_by_cost_center(net_entries, tax_entries),
			store_chart_rows=True,
		)
		self._append_section(_("Payments by Mode of Payment"), self._get_payments_by_mode())

	def _append_section(self, title, entries, store_chart_rows=False):
		self.data.append(self._section_row(title))
		section_rows = self._build_matrix_rows(entries)
		if store_chart_rows:
			self.sales_section_rows = section_rows
		self.data.extend(section_rows)
		if section_rows:
			self.data.append(self._total_row(section_rows))
		self.data.append({})

	def _section_row(self, title):
		return {"entity": f"— {title} —", "indent": 0, "is_section": 1}

	def _build_matrix_rows(self, entries):
		matrix = defaultdict(lambda: defaultdict(float))
		entities = set()

		for entry in entries:
			entity = entry.entity or _("Not Set")
			entities.add(entity)
			matrix[entity][getdate(entry.posting_date)] += flt(entry.amount, self.currency_precision)

		rows = []
		for entity in sorted(entities, key=lambda value: (value or "").lower()):
			row = {"entity": entity}
			total = 0
			for _label, fieldname, day in self.daily_periods:
				value = flt(matrix[entity].get(day, 0), self.currency_precision)
				row[fieldname] = value
				total += value
			row["total"] = flt(total, self.currency_precision)
			if total:
				rows.append(row)
		return rows

	def _total_row(self, section_rows):
		row = {"entity": _("Total"), "bold": 1}
		for _label, fieldname, _day in self.daily_periods:
			row[fieldname] = flt(
				sum(flt(section_row.get(fieldname, 0), self.currency_precision) for section_row in section_rows),
				self.currency_precision,
			)
		row["total"] = flt(
			sum(flt(section_row.get("total", 0), self.currency_precision) for section_row in section_rows),
			self.currency_precision,
		)
		return row

	def _build_chart(self):
		if not self.daily_periods or not self.sales_section_rows:
			self.chart = None
			return

		labels = [label for label, _fieldname, _day in self.daily_periods]
		datasets = []
		for row in self.sales_section_rows[:10]:
			datasets.append(
				{
					"name": row.get("entity"),
					"values": [flt(row.get(fieldname, 0)) for _label, fieldname, _day in self.daily_periods],
				}
			)

		self.chart = {
			"data": {"labels": labels, "datasets": datasets},
			"type": "line",
			"fieldtype": "Currency",
		}
