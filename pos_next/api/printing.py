# -*- coding: utf-8 -*-
# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

"""Server-side printer discovery (CUPS). Browser printing still uses the OS print dialog."""

from __future__ import unicode_literals

import re

import frappe


@frappe.whitelist()
def get_system_printers():
	"""
	List printers from CUPS when `lpstat` is available on the app server.

	The web app cannot send jobs directly to a named printer; this list is for
	selecting a default in POS settings (reference / future integrations). Actual
	printing uses the browser print dialog and the OS default or user choice.
	"""
	import shutil
	import subprocess

	if not shutil.which("lpstat"):
		return []

	try:
		completed = subprocess.run(
			["lpstat", "-p"],
			capture_output=True,
			text=True,
			timeout=8,
			check=False,
		)
	except Exception:
		return []

	out = completed.stdout or ""
	printers = []
	seen = set()
	for line in out.splitlines():
		line = line.strip()
		match = re.match(r"^printer\s+(\S+)\s+is\s+", line, re.I)
		if not match:
			continue
		name = match.group(1)
		if name not in seen:
			seen.add(name)
			printers.append({"name": name, "label": name})

	return printers
