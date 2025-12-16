# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WhatsAppMessageTemplates(Document):
	def validate(self):
		# Auto-generate actual_name from template_name if not set
		if not self.actual_name and self.template_name:
			self.actual_name = self.template_name.lower().replace(" ", "_").replace("-", "_")
		
		# Auto-set language_code from language if not set
		if self.language:
			lang_code = frappe.db.get_value("Language", self.language) or "en"
			self.language_code = lang_code.replace("-", "_")

