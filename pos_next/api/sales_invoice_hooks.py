# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

"""
Sales Invoice Hooks
Event handlers for Sales Invoice document events
"""

import frappe
from frappe import _


def validate(doc, method=None):
	"""
	Validate hook for Sales Invoice.
	POS Next previously enforced inclusive/exclusive tax based on a POS Settings flag.
	In this deployment we rely on the Taxes & Charges template selected on the POS Profile
	(Accounting section), which already carries the correct `included_in_print_rate` flags.

	Args:
		doc: Sales Invoice document
		method: Hook method name (unused)
	"""
	return


def apply_tax_inclusive(doc):
	"""
	Mark taxes as inclusive based on POS Profile setting.

	This function reads the tax_inclusive setting from POS Settings
	and applies it to all taxes in the invoice (except Actual charge type).

	Args:
		doc: Sales Invoice document
	"""
	# Deprecated: kept for backward compatibility with older versions.
	# Inclusive/exclusive behavior should be controlled via the Taxes & Charges template
	# (POS Profile -> Accounting), not via a separate POS Settings flag.
	return


def before_cancel(doc, method=None):
	"""
	Before Cancel hook for Sales Invoice.
	Cancel any credit redemption journal entries.

	Args:
		doc: Sales Invoice document
		method: Hook method name (unused)
	"""
	try:
		from pos_next.api.credit_sales import cancel_credit_journal_entries
		cancel_credit_journal_entries(doc.name)
	except Exception as e:
		frappe.log_error(
			title="Credit Sale JE Cancellation Error",
			message=f"Invoice: {doc.name}, Error: {str(e)}\n{frappe.get_traceback()}"
		)
		# Don't block invoice cancellation if JE cancellation fails
		frappe.msgprint(
			_("Warning: Some credit journal entries may not have been cancelled. Please check manually."),
			alert=True,
			indicator="orange"
		)
