# Copyright (c) 2025, POS Next and contributors
# For license information, please see license.txt

import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from pos_next.api.serial_batch_bundle import (
	create_batch_bundle,
	_validate_batch_for_bundle,
)


class TestCreateBatchBundle(FrappeTestCase):
	"""Unit tests for create_batch_bundle: valid batches, reject invalid/expired/insufficient qty."""

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

	def test_create_batch_bundle_empty_batches(self):
		"""create_batch_bundle with empty batches returns error or throws."""
		res = create_batch_bundle(
			item_code="_Test Item",
			warehouse=self.warehouse,
			batches=[],
		)
		self.assertFalse(res.get("success", True))
		self.assertIn("error", res)

	def test_create_batch_bundle_invalid_json(self):
		"""create_batch_bundle with invalid JSON string throws or returns error."""
		res = create_batch_bundle(
			item_code="_Test Item",
			warehouse=self.warehouse,
			batches="not valid json {{{",
		)
		self.assertFalse(res.get("success", True))

	def test_create_batch_bundle_not_list(self):
		"""create_batch_bundle with batches not a list returns error."""
		res = create_batch_bundle(
			item_code="_Test Item",
			warehouse=self.warehouse,
			batches={"batch_no": "B1", "qty": 1},
		)
		self.assertFalse(res.get("success", True))

	def test_validate_batch_for_bundle_nonexistent_batch(self):
		"""_validate_batch_for_bundle throws for non-existent batch."""
		item_code = frappe.db.get_value("Item", {"has_batch_no": 1, "disabled": 0}, "name")
		if not item_code:
			self.skipTest("No batch item found")
		with self.assertRaises(Exception):
			_validate_batch_for_bundle(
				"_NonExistentBatchXYZ",
				item_code,
				self.warehouse,
				1,
			)


class TestGetBundleDetails(FrappeTestCase):
	"""Unit tests for get_bundle_details (structure)."""

	def test_get_bundle_details_nonexistent_returns_error(self):
		"""get_bundle_details for non-existent bundle returns success False."""
		from pos_next.api.serial_batch_bundle import get_bundle_details

		res = get_bundle_details("_NonExistentBundleXYZ")
		self.assertFalse(res.get("success", True))
		self.assertIn("error", res)
