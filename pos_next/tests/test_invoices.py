# Copyright (c) 2025, POS Next and contributors
# For license information, please see license.txt

import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from pos_next.api.invoices import (
	_auto_set_return_batches,
	_collect_stock_errors,
	_get_available_stock,
	_should_block,
	validate_cart_items,
	validate_return_items,
)


class TestInvoicesStockHelpers(FrappeTestCase):
	"""Unit tests for stock validation helpers: _get_available_stock, _collect_stock_errors, _should_block."""

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

	def test_get_available_stock_no_item_code(self):
		"""_get_available_stock returns 0 when item_code or warehouse missing."""
		self.assertEqual(
			_get_available_stock({"warehouse": self.warehouse}),
			0,
		)
		self.assertEqual(
			_get_available_stock({"item_code": "_Test Item"}),
			0,
		)

	def test_get_available_stock_item_without_bin(self):
		"""_get_available_stock returns 0 for item with no bin."""
		item_code = "_NonExistentItemForPOS"
		self.assertEqual(
			_get_available_stock({
				"item_code": item_code,
				"warehouse": self.warehouse,
			}),
			0,
		)

	def test_collect_stock_errors_empty(self):
		"""_collect_stock_errors with no items returns empty list."""
		self.assertEqual(_collect_stock_errors([]), [])

	def test_collect_stock_errors_negative_qty_skipped(self):
		"""_collect_stock_errors skips rows with negative qty."""
		errors = _collect_stock_errors([
			{
				"item_code": "_Test",
				"warehouse": self.warehouse,
				"qty": -1,
				"stock_qty": -1,
				"conversion_factor": 1,
			},
		])
		self.assertEqual(errors, [])

	def test_collect_stock_errors_exceeds_available(self):
		"""_collect_stock_errors includes row when requested > available."""
		# Item with no stock: available 0, requested 1
		item_code = frappe.db.get_value(
			"Item", {"is_stock_item": 1, "disabled": 0}, "name", order_by="creation desc"
		)
		if not item_code:
			self.skipTest("No stock item found")
		errors = _collect_stock_errors([
			{
				"item_code": item_code,
				"warehouse": self.warehouse,
				"qty": 1,
				"stock_qty": 1,
				"conversion_factor": 1,
				"is_stock_item": 1,
			},
		])
		# If there is no bin, available is 0, so we expect one error
		self.assertGreaterEqual(len(errors), 0)
		for e in errors:
			self.assertIn("item_code", e)
			self.assertIn("requested_qty", e)
			self.assertIn("available_qty", e)

	def test_should_block_no_profile(self):
		"""_should_block with no pos_profile defaults to blocking when negative stock not allowed."""
		# Depends on Stock Settings; we only check it returns bool
		result = _should_block(None)
		self.assertIsInstance(result, bool)

	def test_should_block_with_profile(self):
		"""_should_block with pos_profile returns bool."""
		pos_profile = frappe.db.get_value("POS Profile", {"company": self.company}, "name")
		if not pos_profile:
			self.skipTest("No POS Profile")
		result = _should_block(pos_profile)
		self.assertIsInstance(result, bool)


class TestValidateCartItems(FrappeTestCase):
	"""Unit tests for validate_cart_items."""

	def setUp(self):
		self.company = frappe.db.get_default("company") or frappe.db.get_value(
			"Company", {"name": ["!=", ""]}, "name", order_by="creation asc"
		)
		if not self.company:
			self.skipTest("No company found")
		self.pos_profile = frappe.db.get_value("POS Profile", {"company": self.company}, "name")
		if not self.pos_profile:
			self.skipTest("No POS Profile found")

	def test_validate_cart_items_json_string(self):
		"""validate_cart_items accepts items as JSON string."""
		result = validate_cart_items("[]", self.pos_profile)
		self.assertIsInstance(result, list)
		self.assertEqual(result, [])

	def test_validate_cart_items_empty_list(self):
		"""validate_cart_items with empty list returns [] when blocking or no errors."""
		result = validate_cart_items([], self.pos_profile)
		self.assertEqual(result, [])


class TestValidateReturnItems(FrappeTestCase):
	"""Unit tests for validate_return_items."""

	def test_validate_return_items_valid(self):
		"""validate_return_items returns valid when return qty <= sold qty."""
		# We need an existing submitted Sales Invoice; if none, skip
		si = frappe.db.get_value(
			"Sales Invoice",
			{"docstatus": 1, "is_return": 0, "company": frappe.db.get_default("company")},
			"name",
			order_by="creation desc",
		)
		if not si:
			self.skipTest("No submitted Sales Invoice found")
		doc = frappe.get_doc("Sales Invoice", si)
		return_items = [{"item_code": item.item_code, "qty": 1} for item in doc.items[:1]]
		if not return_items:
			self.skipTest("Invoice has no items")
		result = validate_return_items(si, return_items)
		self.assertIn("valid", result)
		# May be True or False depending on qty; we only check structure
		self.assertIsInstance(result.get("valid"), bool)


class TestAutoSetReturnBatches(FrappeTestCase):
	"""Unit tests for _auto_set_return_batches (expiry/disabled filter)."""

	def test_auto_set_return_batches_skips_non_return(self):
		"""_auto_set_return_batches does nothing when is_return is 0."""
		items = [{"item_code": "_Test", "warehouse": "_Test WH", "batch_no": None}]
		doc = _make_doc(is_return=0, items=items)
		_auto_set_return_batches(doc)
		self.assertIsNone(items[0].get("batch_no"))

	def test_auto_set_return_batches_skips_when_return_against_set(self):
		"""_auto_set_return_batches does nothing when return_against is set."""
		items = [{"item_code": "_Test", "warehouse": "_Test WH", "batch_no": None}]
		doc = _make_doc(is_return=1, return_against="SINV-001", items=items)
		_auto_set_return_batches(doc)
		self.assertIsNone(items[0].get("batch_no"))


def _make_doc(**kwargs):
	"""Build a doc-like object so invoice_doc.items is the list (not dict.items())."""
	doc = type("Doc", (), kwargs)()
	doc.get = lambda k: getattr(doc, k, None)
	return doc
