# -*- coding: utf-8 -*-
# Copyright (c) 2024, POS Next and contributors

"""Letter head helpers for POS printing (online and offline cache)."""

from __future__ import unicode_literals

import frappe


def get_letter_head_for_print(letter_head_name=None, doc=None):
	"""Return rendered letter head content and footer for printing.

	Args:
		letter_head_name: Letter Head document name from POS Profile (optional).
		doc: Optional document (e.g. Company) for Jinja context in letter head.
	"""
	if letter_head_name:
		lh = frappe.db.get_value(
			"Letter Head",
			letter_head_name,
			["content", "footer", "header_script", "footer_script"],
			as_dict=True,
		)
	else:
		lh = frappe.db.get_value(
			"Letter Head",
			{"is_default": 1, "disabled": 0},
			["content", "footer", "header_script", "footer_script"],
			as_dict=True,
		)

	if not lh:
		return {"content": "", "footer": ""}

	context = {"doc": doc.as_dict() if doc and hasattr(doc, "as_dict") else (doc or {})}
	content = _render_letter_head_part(lh.content, context, lh.header_script)
	footer = _render_letter_head_part(lh.footer, context, lh.footer_script)
	return {"content": content or "", "footer": footer or ""}


def _render_letter_head_part(template, context, script=None):
	if not template:
		return ""
	rendered = frappe.utils.jinja.render_template(template, context)
	if script:
		rendered += f"\n<script>\n{script}\n</script>"
	return rendered
