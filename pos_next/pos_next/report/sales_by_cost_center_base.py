# Copyright (c) 2026, Bazaks and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt


class SalesByCostCenterReport:
	"""Summary sales report: cost center (net / tax / grand) and modes of payment."""

	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.company = self.filters.company
		self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
		self.currency_precision = self._currency_precision()
		self.columns = []
		self.data = []
		self.chart = None

	def run(self):
		self._build_columns()
		self._build_data()
		self._build_chart()
		return self.columns, self.data, None, self.chart, None, 0

	def _build_columns(self):
		self.columns = [
			{
				"label": _("Cost Center / Mode of Payment"),
				"fieldname": "entity",
				"fieldtype": "Data",
				"width": 240,
			},
			{
				"label": _("Amount"),
				"fieldname": "amount",
				"fieldtype": "Currency",
				"options": self.currency,
				"width": 120,
			},
			{
				"label": _("Tax"),
				"fieldname": "tax",
				"fieldtype": "Currency",
				"options": self.currency,
				"width": 120,
			},
			{
				"label": _("Grand Total"),
				"fieldname": "grand_total",
				"fieldtype": "Currency",
				"options": self.currency,
				"width": 120,
			},
		]

	def _invoice_conditions(self):
		conditions = [
			"si.docstatus = 1",
			"si.company = %(company)s",
			"IFNULL(si.is_opening, 'No') = 'No'",
		]
		if not cint(self.filters.include_non_pos):
			conditions.append("si.is_pos = 1")
		if self.filters.pos_profile:
			conditions.append("si.pos_profile = %(pos_profile)s")
		self._extend_invoice_conditions(conditions)
		return " AND ".join(conditions)

	def _extend_invoice_conditions(self, conditions):
		"""Override in subclasses for date range or opening shift."""

	def _query_params(self):
		return {
			"company": self.company,
			"pos_profile": self.filters.pos_profile,
			"not_set": _("Not Set"),
		}

	def _cost_center_expr(self):
		return """
			COALESCE(
				NULLIF(igd.selling_cost_center, ''),
				NULLIF(sii.cost_center, ''),
				NULLIF(si.cost_center, ''),
				%(not_set)s
			)
		"""

	def _currency_precision(self):
		"""Decimal places for currency (Currency.fraction is a label, not precision)."""
		fraction_units = frappe.get_cached_value("Currency", self.currency, "fraction_units")
		if fraction_units:
			return max(0, len(str(cint(fraction_units))) - 1)
		return cint(frappe.db.get_default("currency_precision")) or 2

	def _round_currency(self, value):
		return flt(value, self.currency_precision)

	def _cost_center_share_sql(self, amount_expr):
		return f"""
			CASE
				WHEN IFNULL(si.base_total, 0) = 0 THEN 0
				ELSE (sii.base_amount / si.base_total) * ({amount_expr})
			END
		"""

	def _get_amount_by_cost_center(self):
		return frappe.db.sql(
			f"""
			SELECT
				{self._cost_center_expr()} AS entity,
				SUM(sii.base_amount) AS amount
			FROM `tabSales Invoice` si
			INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
			LEFT JOIN `tabItem Default` igd
				ON igd.parent = sii.item_group
				AND igd.parenttype = 'Item Group'
				AND igd.company = si.company
			WHERE {self._invoice_conditions()}
			GROUP BY entity
			ORDER BY entity
			""",
			self._query_params(),
			as_dict=True,
		)

	def _get_tax_by_cost_center(self):
		tax_expr = self._cost_center_share_sql("stc.base_tax_amount_after_discount_amount")
		rows = frappe.db.sql(
			f"""
			SELECT
				{self._cost_center_expr()} AS entity,
				SUM({tax_expr}) AS tax
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
			GROUP BY entity
			ORDER BY entity
			""",
			self._query_params(),
			as_dict=True,
		)
		return {row.entity: flt(row.tax) for row in rows}

	def _get_grand_by_cost_center(self):
		"""Allocate invoice grand total by line amount share (matches SI grand_total / payments)."""
		grand_expr = self._cost_center_share_sql("si.base_grand_total")
		rows = frappe.db.sql(
			f"""
			SELECT
				{self._cost_center_expr()} AS entity,
				SUM({grand_expr}) AS grand_total
			FROM `tabSales Invoice` si
			INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
			LEFT JOIN `tabItem Default` igd
				ON igd.parent = sii.item_group
				AND igd.parenttype = 'Item Group'
				AND igd.company = si.company
			WHERE {self._invoice_conditions()}
			GROUP BY entity
			ORDER BY entity
			""",
			self._query_params(),
			as_dict=True,
		)
		return {row.entity: flt(row.grand_total) for row in rows}

	def _get_payments_by_mode(self):
		return frappe.db.sql(
			f"""
			SELECT
				IFNULL(sip.mode_of_payment, %(not_set)s) AS entity,
				SUM(sip.base_amount) AS grand_total
			FROM `tabSales Invoice` si
			INNER JOIN `tabSales Invoice Payment` sip ON sip.parent = si.name
			WHERE {self._invoice_conditions()}
			GROUP BY sip.mode_of_payment
			ORDER BY sip.mode_of_payment
			""",
			self._query_params(),
			as_dict=True,
		)

	def _merge_cost_center_rows(self, amount_rows, tax_by_entity, grand_by_entity):
		entities = set()
		amount_by_entity = {}
		for row in amount_rows:
			entity = row.entity or _("Not Set")
			entities.add(entity)
			amount_by_entity[entity] = flt(row.amount)
		entities.update(tax_by_entity.keys())
		entities.update(grand_by_entity.keys())

		rows = []
		for entity in sorted(entities, key=lambda value: (value or "").lower()):
			amount = self._round_currency(amount_by_entity.get(entity, 0))
			tax = self._round_currency(tax_by_entity.get(entity, 0))
			grand_total = self._round_currency(grand_by_entity.get(entity, 0))
			if amount or tax or grand_total:
				rows.append(
					{
						"entity": entity,
						"amount": amount,
						"tax": tax,
						"grand_total": grand_total,
					}
				)
		return rows

	def _build_data(self):
		self.data = []
		amount_rows = self._get_amount_by_cost_center()
		tax_by_entity = self._get_tax_by_cost_center()
		grand_by_entity = self._get_grand_by_cost_center()
		cost_center_rows = self._merge_cost_center_rows(amount_rows, tax_by_entity, grand_by_entity)

		self._append_section(_("Sales by Cost Center"), cost_center_rows, store_chart_rows=True)
		payment_rows = [
			{
				"entity": row.entity or _("Not Set"),
				"amount": None,
				"tax": None,
				"grand_total": self._round_currency(row.grand_total),
			}
			for row in self._get_payments_by_mode()
			if flt(row.grand_total)
		]
		self._append_section(_("Modes of Payment"), payment_rows)

	def _append_section(self, title, rows, store_chart_rows=False):
		self.data.append(self._section_row(title))
		if store_chart_rows:
			self._chart_rows = rows
		self.data.extend(rows)
		if rows:
			self.data.append(self._total_row(rows, payment_section=title == _("Modes of Payment")))
		self.data.append({})

	def _section_row(self, title):
		return {"entity": f"— {title} —", "is_section": 1}

	def _total_row(self, rows, payment_section=False):
		row = {"entity": _("Total"), "bold": 1}
		if payment_section:
			row["grand_total"] = self._round_currency(
				sum(self._round_currency(r.get("grand_total", 0)) for r in rows)
			)
		else:
			row["amount"] = self._round_currency(
				sum(self._round_currency(r.get("amount", 0)) for r in rows)
			)
			row["tax"] = self._round_currency(sum(self._round_currency(r.get("tax", 0)) for r in rows))
			row["grand_total"] = self._round_currency(
				sum(self._round_currency(r.get("grand_total", 0)) for r in rows)
			)
		return row

	def _build_chart(self):
		chart_rows = getattr(self, "_chart_rows", None)
		if not chart_rows:
			self.chart = None
			return

		labels = [row["entity"] for row in chart_rows[:12]]
		values = [flt(row.get("grand_total", 0)) for row in chart_rows[:12]]
		self.chart = {
			"data": {
				"labels": labels,
				"datasets": [{"name": _("Grand Total"), "values": values}],
			},
			"type": "bar",
			"fieldtype": "Currency",
		}


class DailySalesByCostCenterReport(SalesByCostCenterReport):
	def __init__(self, filters=None):
		from frappe.utils import getdate

		super().__init__(filters)
		self.from_date = getdate(self.filters.from_date)
		self.to_date = getdate(self.filters.to_date)
		if self.from_date > self.to_date:
			frappe.throw(_("From Date cannot be after To Date"))

	def _extend_invoice_conditions(self, conditions):
		conditions.append("si.posting_date BETWEEN %(from_date)s AND %(to_date)s")

	def _query_params(self):
		params = super()._query_params()
		params.update({"from_date": self.from_date, "to_date": self.to_date})
		return params


class CurrentShiftSalesByCostCenterReport(SalesByCostCenterReport):
	def _extend_invoice_conditions(self, conditions):
		if not self.filters.pos_opening_shift:
			frappe.throw(_("POS Opening Shift is required"))
		if frappe.db.has_column("Sales Invoice", "posa_pos_opening_shift"):
			conditions.append("si.posa_pos_opening_shift = %(pos_opening_shift)s")
		else:
			frappe.throw(_("POS Opening Shift field is not available on Sales Invoice"))

	def _query_params(self):
		params = super()._query_params()
		params["pos_opening_shift"] = self.filters.pos_opening_shift
		return params
