# Copyright (c) 2025, POS Next and contributors
# For license information, please see license.txt

import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, nowdate

from pos_next.api import items as pos_items


class TestPOSItems(FrappeTestCase):
	"""Unit tests for pos_next.api.items (get_item_detail, get_batch_serial_details, get_stock_availability)."""

	def setUp(self):
		self.company = frappe.db.get_default("company") or frappe.db.get_value(
			"Company", {"name": ["!=", ""]}, "name", order_by="creation asc"
		)
		if not self.company:
			self.skipTest("No company found")
		self.warehouse = frappe.db.get_value(
			"Warehouse", {"company": self.company, "is_group": 0}, "name"
		)
		if not self.warehouse:
			self.skipTest("No warehouse found")

	def test_get_stock_availability_no_warehouse(self):
		"""get_stock_availability with no warehouse returns 0."""
		self.assertEqual(pos_items.get_stock_availability("_NonExistent", None), 0.0)

	def test_get_stock_availability_unknown_item(self):
		"""get_stock_availability for item with no bin returns 0."""
		qty = pos_items.get_stock_availability("_NonExistentItem", self.warehouse)
		self.assertEqual(flt(qty), 0.0)

	def test_get_item_detail_returns_batch_no_data_and_serial_no_data(self):
		"""get_item_detail returns batch_no_data and serial_no_data keys."""
		item = {
			"item_code": "_Test Item",
			"has_batch_no": 0,
			"has_serial_no": 0,
			"is_stock_item": 1,
			"qty": 1,
		}
		if not frappe.db.exists("Item", "_Test Item"):
			self.skipTest("_Test Item not found")
		res = pos_items.get_item_detail(
			item,
			warehouse=self.warehouse,
			company=self.company,
		)
		self.assertIn("batch_no_data", res)
		self.assertIn("serial_no_data", res)
		self.assertIsInstance(res["batch_no_data"], list)
		self.assertIsInstance(res["serial_no_data"], list)

	def test_get_batch_serial_details_no_warehouse_batch_item(self):
		"""get_batch_serial_details with warehouse None for batch item returns empty batches."""
		# Use an item that has has_batch_no; if none, skip
		item_code = frappe.db.get_value(
			"Item", {"has_batch_no": 1, "disabled": 0}, "name"
		)
		if not item_code:
			self.skipTest("No batch item found")
		res = pos_items.get_batch_serial_details(item_code, None)
		self.assertEqual(res.get("batches"), [])

	def test_get_batch_serial_details_warehouse_scope(self):
		"""get_batch_serial_details accepts warehouse and returns structure with batches/serial_nos."""
		item_code = frappe.db.get_value(
			"Item", {"disabled": 0, "is_sales_item": 1}, "name", order_by="creation desc"
		)
		if not item_code:
			self.skipTest("No item found")
		res = pos_items.get_batch_serial_details(item_code, self.warehouse)
		self.assertIn("item_code", res)
		self.assertIn("has_batch_no", res)
		self.assertIn("has_serial_no", res)
		self.assertIn("batches", res)
		self.assertIn("serial_nos", res)
		self.assertIsInstance(res["batches"], list)
		self.assertIsInstance(res["serial_nos"], list)
		for b in res["batches"]:
			self.assertIn("batch_no", b)
			self.assertIn("qty", b)
			# Batches must be warehouse-scoped (from get_batch_qty), not global batch_qty

	def test_get_batch_serial_details_json_input_warehouse(self):
		"""get_batch_serial_details with string item_code and warehouse returns dict."""
		item_code = frappe.db.get_value(
			"Item", {"disabled": 0, "is_sales_item": 1}, "name", order_by="creation desc"
		)
		if not item_code:
			self.skipTest("No item found")
		res = pos_items.get_batch_serial_details(item_code, self.warehouse)
		self.assertEqual(res["item_code"], item_code)


class TestPOSGetItems(FrappeTestCase):
	"""Unit tests for get_items (template vs variant, service, stock)."""

	def setUp(self):
		self.company = frappe.db.get_default("company") or frappe.db.get_value(
			"Company", {"name": ["!=", ""]}, "name", order_by="creation asc"
		)
		if not self.company:
			self.skipTest("No company found")
		self.pos_profile = frappe.db.get_value(
			"POS Profile", {"company": self.company}, "name"
		)
		if not self.pos_profile:
			self.skipTest("No POS Profile found")

	def test_get_items_returns_list(self):
		"""get_items returns a list of items."""
		items = pos_items.get_items(
			self.pos_profile,
			search_term=None,
			item_group=None,
			start=0,
			limit=5,
		)
		self.assertIsInstance(items, list)

	def test_get_items_filters_disabled(self):
		"""get_items does not return disabled items (filter disabled=0 in base)."""
		items = pos_items.get_items(
			self.pos_profile,
			search_term=None,
			item_group=None,
			start=0,
			limit=100,
		)
		# All returned items should be from Item with disabled=0 (enforced in query)
		for item in items:
			self.assertTrue(
				item.get("disabled") == 0 or "disabled" not in item,
				"get_items should not return disabled items",
			)
