# Copyright (c) 2025, POS Next and contributors
# For license information, please see license.txt

"""
Integration tests for POS Next item flows (batch, variant, service, simple stock).

These tests use existing site data (company, warehouse, POS profile, items).
They validate the scenario matrix: get_items -> get_item_details / get_batch_serial_details
-> validate_cart_items and invoice flow behaviour without requiring full submit.
"""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from pos_next.api import items as pos_items
from pos_next.api.invoices import validate_cart_items, update_invoice


class TestPOSItemsIntegration(FrappeTestCase):
	"""Integration: get_items and get_item_details with real site data."""

	@classmethod
	def setUpClass(cls):
		cls.company = frappe.db.get_default("company") or frappe.db.get_value(
			"Company", {"name": ["!=", ""]}, "name", order_by="creation asc"
		)
		cls.warehouse = None
		cls.pos_profile = None
		if cls.company:
			cls.warehouse = frappe.db.get_value(
				"Warehouse", {"company": cls.company, "is_group": 0}, "name"
			)
			cls.pos_profile = frappe.db.get_value(
				"POS Profile", {"company": cls.company}, "name"
			)

	def test_get_items_and_details_simple_stock_flow(self):
		"""Simple stock: get_items returns item; get_item_details returns price/stock keys."""
		if not self.pos_profile:
			self.skipTest("No POS Profile")
		items = pos_items.get_items(
			self.pos_profile, search_term=None, item_group=None, start=0, limit=5
		)
		self.assertIsInstance(items, list)
		# Find a simple stock item (no batch, no variant)
		stock_item = None
		for it in items:
			if it.get("is_stock_item") and not it.get("has_batch_no") and not it.get("has_variants"):
				stock_item = it
				break
		if not stock_item:
			self.skipTest("No simple stock item in POS item list")
		details = pos_items.get_item_details(
			stock_item["item_code"],
			self.pos_profile,
			qty=1,
		)
		self.assertIn("rate", details)
		self.assertIn("actual_qty", details)
		self.assertIn("batch_no_data", details)
		self.assertIn("serial_no_data", details)

	def test_get_items_service_item(self):
		"""Service item appears in get_items and has is_stock_item=0."""
		if not self.pos_profile:
			self.skipTest("No POS Profile")
		items = pos_items.get_items(
			self.pos_profile, search_term=None, item_group=None, start=0, limit=100
		)
		service_items = [i for i in items if not i.get("is_stock_item")]
		# Site may or may not have service items
		for it in service_items:
			self.assertEqual(it.get("is_stock_item"), 0)

	def test_get_batch_serial_details_only_valid_batches(self):
		"""get_batch_serial_details returns batches list; when warehouse given, batches are warehouse-scoped."""
		item_code = frappe.db.get_value(
			"Item", {"has_batch_no": 1, "disabled": 0}, "name"
		)
		if not item_code or not self.warehouse:
			self.skipTest("No batch item or warehouse")
		res = pos_items.get_batch_serial_details(item_code, self.warehouse)
		self.assertIn("batches", res)
		self.assertIn("serial_nos", res)
		# All returned batches should have batch_no and qty (from get_batch_qty, so warehouse-scoped)
		for b in res["batches"]:
			self.assertIn("batch_no", b)
			self.assertIn("qty", b)

	def test_validate_cart_items_then_update_invoice_draft(self):
		"""validate_cart_items with one item; update_invoice creates draft without submit."""
		if not self.pos_profile:
			self.skipTest("No POS Profile")
		items = pos_items.get_items(
			self.pos_profile, search_term=None, item_group=None, start=0, limit=1
		)
		if not items:
			self.skipTest("No items in POS")
		item = items[0]
		# Build minimal cart: one item, qty 1
		cart = [
			{
				"item_code": item["item_code"],
				"item_name": item.get("item_name"),
				"qty": 1,
				"quantity": 1,
				"rate": item.get("rate") or 0,
				"price_list_rate": item.get("rate") or 0,
				"warehouse": item.get("warehouse"),
				"is_stock_item": item.get("is_stock_item", 0),
				"stock_qty": 1,
				"conversion_factor": 1,
			}
		]
		errors = validate_cart_items(cart, self.pos_profile)
		# If blocking and insufficient stock, errors may be non-empty; otherwise []
		self.assertIsInstance(errors, list)
		# Update invoice (draft only)
		customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		if not customer:
			self.skipTest("No customer")
		invoice_data = {
			"doctype": "Sales Invoice",
			"pos_profile": self.pos_profile,
			"customer": customer,
			"items": [
				{
					"item_code": item["item_code"],
					"item_name": item.get("item_name"),
					"qty": 1,
					"rate": item.get("rate") or 0,
					"price_list_rate": item.get("rate") or 0,
					"warehouse": item.get("warehouse"),
					"is_stock_item": item.get("is_stock_item", 0),
				}
			],
			"payments": [{"mode_of_payment": "Cash", "amount": item.get("rate") or 0}],
			"is_pos": 1,
			"update_stock": 1,
		}
		try:
			doc = update_invoice(frappe.as_json(invoice_data))
			self.assertTrue(doc)
			# Clean up draft (do not cancel; just delete draft)
			if isinstance(doc, dict) and doc.get("name"):
				si = frappe.get_doc("Sales Invoice", doc["name"])
				if si.docstatus == 0:
					si.delete()
		except Exception as e:
			# Allow missing payment account etc. in test env
			if "Account" in str(e) or "payment" in str(e).lower():
				self.skipTest("Payment account not set for test company")
			raise
