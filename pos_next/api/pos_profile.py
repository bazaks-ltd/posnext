# -*- coding: utf-8 -*-
# Copyright (c) 2024, POS Next and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt


@frappe.whitelist()
def get_pos_profiles():
	"""Get all POS Profiles accessible by current user"""
	pos_profiles = frappe.db.sql(
		"""
		SELECT DISTINCT p.name, p.company, p.currency, p.warehouse,
			p.selling_price_list, p.write_off_account, p.write_off_cost_center
		FROM `tabPOS Profile` p
		INNER JOIN `tabPOS Profile User` u ON u.parent = p.name
		WHERE p.disabled = 0 AND u.user = %s
		ORDER BY p.name
		""",
		frappe.session.user,
		as_dict=1,
	)

	return pos_profiles


@frappe.whitelist()
def get_pos_profile_data(pos_profile):
	"""Get detailed POS Profile data"""
	if not pos_profile:
		frappe.throw(_("POS Profile is required"))

	# Check if user has access to this POS Profile
	has_access = frappe.db.exists(
		"POS Profile User",
		{"parent": pos_profile, "user": frappe.session.user}
	)

	if not has_access:
		frappe.throw(_("You don't have access to this POS Profile"))

	profile_doc = frappe.get_doc("POS Profile", pos_profile)
	company_doc = frappe.get_doc("Company", profile_doc.company)

	# Get POS Settings for this profile
	pos_settings = get_pos_settings(pos_profile)

	return {
		"pos_profile": profile_doc,
		"company": company_doc,
		"pos_settings": pos_settings,
		"print_settings": {
			"auto_print": profile_doc.get("print_receipt_on_order_complete", 0),
			"print_format": profile_doc.get("print_format"),
			"letter_head": profile_doc.get("letter_head"),
		}
	}


@frappe.whitelist()
def get_pos_settings(pos_profile):
	"""Get POS Settings for a given POS Profile"""
	if not pos_profile:
		return {}

	try:
		# Get POS Settings linked to this POS Profile
		pos_settings = frappe.db.get_value(
			"POS Settings",
			{"pos_profile": pos_profile, "enabled": 1},
			[
				"allow_user_to_edit_additional_discount",
				"allow_user_to_edit_item_discount",
				"use_percentage_discount",
				"max_discount_allowed",
				"disable_rounded_total",
				"allow_credit_sale",
				"allow_return",
				"allow_write_off_change",
				"allow_partial_payment",
				"show_customer_annual_billing",
				"decimal_precision",
				"allow_negative_stock",
				"enable_sales_persons"
			],
			as_dict=True
		)

		# Return settings or defaults if not found
		if not pos_settings:
			return {
				"allow_user_to_edit_additional_discount": 0,
				"allow_user_to_edit_item_discount": 1,
				"use_percentage_discount": 0,
				"max_discount_allowed": 0,
				"disable_rounded_total": 1,
				"allow_credit_sale": 0,
				"allow_return": 0,
				"allow_write_off_change": 0,
				"allow_partial_payment": 0,
				"show_customer_annual_billing": 0,
				"decimal_precision": "2",
				"allow_negative_stock": 0,
				"enable_sales_persons": "Disabled"
			}

		return pos_settings
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Get POS Settings Error")
		return {}


@frappe.whitelist()
def get_payment_methods(pos_profile):
	"""Get available payment methods from POS Profile"""
	try:
		# Validate pos_profile parameter
		if not pos_profile:
			frappe.throw(_("POS Profile is required"))

		payment_methods = frappe.get_list(
			"POS Payment Method",
			filters={"parent": pos_profile},
			fields=["mode_of_payment", "default", "allow_in_returns"],
			order_by="idx",
			ignore_permissions=True
		)

		# Get payment type for each method
		for method in payment_methods:
			payment_type = frappe.db.get_value(
				"Mode of Payment",
				method["mode_of_payment"],
				"type"
			)
			method["type"] = payment_type or "Cash"

		return payment_methods
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Get Payment Methods Error")
		frappe.throw(_("Error fetching payment methods: {0}").format(str(e)))


@frappe.whitelist()
def get_taxes(pos_profile):
	"""Get tax configuration for POS cart totals (rates, inclusive flag).

	Uses the POS Profile's **Sales Taxes and Charges** template when set.
	If unset (common), falls back to the **company default** template — the same
	rules as ERPNext ``AccountsController.set_taxes`` on Sales Invoice, so desk
	invoices and POS preview stay aligned.
	"""
	try:
		if not pos_profile:
			return []

		# Get the POS Profile
		profile_doc = frappe.get_cached_doc("POS Profile", pos_profile)
		taxes_and_charges = getattr(profile_doc, "taxes_and_charges", None)
		company = profile_doc.company

		if not taxes_and_charges and company:
			taxes_and_charges = frappe.db.get_value(
				"Sales Taxes and Charges Template",
				{"is_default": 1, "company": company},
				"name",
			)

		if not taxes_and_charges:
			return []

		# Get the tax template
		template_doc = frappe.get_cached_doc("Sales Taxes and Charges Template", taxes_and_charges)

		# Extract tax rows
		taxes = []
		for tax_row in template_doc.taxes:
			taxes.append({
				"account_head": tax_row.account_head,
				"charge_type": tax_row.charge_type,
				"rate": flt(tax_row.rate),
				"description": tax_row.description,
				# 0/1 int so the POS can treat prices as VAT-inclusive like Sales Invoice
				"included_in_print_rate": cint(getattr(tax_row, "included_in_print_rate", 0)),
				"idx": tax_row.idx
			})

		return taxes
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Get Taxes Error")
		# Return empty array instead of throwing - taxes are optional
		return []


@frappe.whitelist()
def get_warehouses(pos_profile):
	"""Get all warehouses for the company in POS Profile"""
	try:
		if not pos_profile:
			return []

		# Get the company from POS Profile
		company = frappe.db.get_value("POS Profile", pos_profile, "company")

		if not company:
			return []

		# Get all active warehouses for the company
		warehouses = frappe.get_list(
			"Warehouse",
			filters={
				"company": company,
				"disabled": 0,
				"is_group": 0
			},
			fields=["name", "warehouse_name"],
			order_by="warehouse_name",
			limit_page_length=0
		)

		# Return warehouses with human-readable names
		return warehouses
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Get Warehouses Error")
		return []


@frappe.whitelist()
def get_default_customer(pos_profile):
	"""Get the default customer configured in POS Profile"""
	try:
		if not pos_profile:
			return {"customer": None}

		# Get the default customer from POS Profile
		default_customer = frappe.db.get_value("POS Profile", pos_profile, "customer")

		if default_customer:
			# Get customer details
			customer_doc = frappe.get_doc("Customer", default_customer)
			return {
				"customer": default_customer,
				"customer_name": customer_doc.customer_name,
				"customer_group": customer_doc.customer_group,
			}

		return {"customer": None}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Get Default Customer Error")
		return {"customer": None}


@frappe.whitelist()
def update_warehouse(pos_profile, warehouse):
	"""Update warehouse in POS Profile"""
	try:
		if not pos_profile:
			frappe.throw(_("POS Profile is required"))

		if not warehouse:
			frappe.throw(_("Warehouse is required"))

		# Check if user has access to this POS Profile
		has_access = frappe.db.exists(
			"POS Profile User",
			{"parent": pos_profile, "user": frappe.session.user}
		)

		if not has_access and not frappe.has_permission("POS Profile", "write"):
			frappe.throw(_("You don't have permission to update this POS Profile"))

		# Get POS Profile to check company
		profile_doc = frappe.get_doc("POS Profile", pos_profile)

		# Validate warehouse exists and is active
		warehouse_doc = frappe.get_doc("Warehouse", warehouse)
		if warehouse_doc.disabled:
			frappe.throw(_("Warehouse {0} is disabled").format(warehouse))

		# Validate warehouse belongs to same company
		if warehouse_doc.company != profile_doc.company:
			frappe.throw(_(
				"Warehouse {0} belongs to {1}, but POS Profile belongs to {2}"
			).format(warehouse, warehouse_doc.company, profile_doc.company))

		# Update the POS Profile
		profile_doc.warehouse = warehouse
		profile_doc.save()

		return {
			"success": True,
			"message": _("Warehouse updated successfully"),
			"warehouse": warehouse
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Update Warehouse Error")
		frappe.throw(_("Error updating warehouse: {0}").format(str(e)))


@frappe.whitelist()
def get_sales_persons(pos_profile=None):
	"""Get all active individual sales persons (not groups) for POS"""
	try:
		filters = {
			"enabled": 1,
			"is_group": 0  # Only get individual sales persons, not group nodes
		}

		# If company is specified via POS Profile, filter by company (if Sales Person has company field)
		if pos_profile:
			company = frappe.db.get_value("POS Profile", pos_profile, "company")
			# Check if Sales Person doctype has a company field
			if frappe.db.has_column("Sales Person", "company") and company:
				filters["company"] = company

		sales_persons = frappe.get_list(
			"Sales Person",
			filters=filters,
			fields=["name", "sales_person_name", "commission_rate", "employee"],
			order_by="sales_person_name",
			limit_page_length=0
		)

		return sales_persons
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Get Sales Persons Error")
		return []
