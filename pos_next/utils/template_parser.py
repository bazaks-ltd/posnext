# -*- coding: utf-8 -*-
# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

"""
Template Parser - Parse invoice templates with dynamic placeholders
"""

import frappe
from frappe import _
from frappe.utils import get_url, fmt_money, formatdate, get_time_str
import io


def parse_invoice_template(template_string, invoice_doc):
    """
    Parse template string with invoice data placeholders.
    
    Supported placeholders:
        {invoice_name} - Invoice number
        {customer_name} - Customer display name
        {grand_total} - Invoice total with currency
        {date} - Invoice date
        {time} - Invoice time
        {company} - Company name
        {invoice_url} - Link to view invoice online
        {items_summary} - Brief list of items
        
    Args:
        template_string: Template text with placeholders
        invoice_doc: Sales Invoice document
        
    Returns:
        str: Parsed template with replaced placeholders
    """
    if not template_string:
        return ""
    
    try:
        # Get invoice data
        invoice_data = invoice_doc.as_dict()
        
        # Build replacement map
        replacements = {
            "{invoice_name}": invoice_doc.name,
            "{customer_name}": invoice_doc.customer_name or invoice_doc.customer,
            "{grand_total}": fmt_money(
                invoice_doc.grand_total,
                currency=invoice_doc.currency
            ),
            "{date}": formatdate(invoice_doc.posting_date),
            "{time}": get_time_str(invoice_doc.posting_time) if invoice_doc.posting_time else "",
            "{company}": invoice_doc.company,
            "{invoice_url}": get_invoice_url(invoice_doc.name),
            "{items_summary}": _get_items_summary(invoice_doc),
            "{total}": fmt_money(
                invoice_doc.total,
                currency=invoice_doc.currency
            ),
            "{net_total}": fmt_money(
                invoice_doc.net_total,
                currency=invoice_doc.currency
            ),
            "{outstanding_amount}": fmt_money(
                invoice_doc.outstanding_amount,
                currency=invoice_doc.currency
            ),
        }
        
        # Replace placeholders
        parsed_template = template_string
        for placeholder, value in replacements.items():
            parsed_template = parsed_template.replace(placeholder, str(value))
        
        return parsed_template
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Template Parsing Error")
        # Return original template if parsing fails
        return template_string


def get_invoice_url(invoice_name):
    """
    Generate shareable URL for invoice.
    
    Args:
        invoice_name: Sales Invoice name
        
    Returns:
        str: Full URL to view invoice
    """
    try:
        site_url = get_url()
        # Generate link to print view
        invoice_url = f"{site_url}/app/sales-invoice/{invoice_name}"
        return invoice_url
    except Exception:
        return ""


def render_invoice_pdf(invoice_name, print_format=None):
    """
    Render invoice as PDF for attachment.
    
    Args:
        invoice_name: Sales Invoice name
        print_format: Optional print format name
        
    Returns:
        dict: File dict with 'fname' and 'fcontent' keys
    """
    try:
        # Get default print format if not specified
        if not print_format:
            print_format = frappe.db.get_single_value("Print Settings", "pdf_page_size")
            if not print_format:
                print_format = "Standard"
        
        # Use frappe.get_print to generate PDF
        pdf_content = frappe.get_print(
            "Sales Invoice",
            invoice_name,
            print_format=print_format,
            as_pdf=True
        )
        
        # Create file dict
        file_dict = {
            "fname": f"{invoice_name}.pdf",
            "fcontent": pdf_content
        }
        
        return file_dict
        
    except Exception as e:
        frappe.log_error(f"PDF generation error for {invoice_name}: {str(e)}")
        raise


def _get_items_summary(invoice_doc, max_items=3):
    """
    Get brief summary of invoice items.
    
    Args:
        invoice_doc: Sales Invoice document
        max_items: Maximum number of items to show
        
    Returns:
        str: Items summary text
    """
    try:
        items = invoice_doc.items
        if not items:
            return ""
        
        item_names = []
        for idx, item in enumerate(items):
            if idx >= max_items:
                break
            item_names.append(f"{item.item_name} x{int(item.qty)}")
        
        summary = ", ".join(item_names)
        
        # Add "and X more" if there are more items
        if len(items) > max_items:
            remaining = len(items) - max_items
            summary += f" {_('and')} {remaining} {_('more')}"
        
        return summary
        
    except Exception:
        return ""

