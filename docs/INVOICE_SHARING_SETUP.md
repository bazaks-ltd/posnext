# Invoice Sharing Setup Guide

## Overview

POS Next now supports native invoice sharing via WhatsApp, SMS, and Email. This guide will help you configure and use the invoice sharing feature.

## Features

- **WhatsApp Sharing**: Send invoices directly via WhatsApp with PDF attachment
- **SMS Sharing**: Send invoice details via SMS with payment link
- **Email Sharing**: Send professional invoice emails with PDF attachment
- **Multi-Channel**: Enable one or all channels based on your needs
- **Template Support**: Customize messages with dynamic placeholders
- **Auto-Fill Contact**: Automatically fills customer contact information
- **Sharing History**: Track all shared invoices

## Configuration

### Step 1: Configure Communication Gateways

#### WhatsApp Gateway Setup

1. Go to **WhatsApp Settings** in ERPNext
2. Configure your WhatsApp Business API or Twilio integration
3. Enable the WhatsApp gateway
4. Test the connection

**Supported Providers:**
- Twilio WhatsApp API
- WhatsApp Business API
- Meta Cloud API

#### SMS Gateway Setup

1. Go to **SMS Settings** in ERPNext
2. Configure your SMS provider:
   - **Twilio**: Most popular, reliable
   - **AWS SNS**: Enterprise-grade
   - **Other providers**: Any HTTP-based SMS gateway
3. Set SMS Gateway URL and credentials
4. Test with a sample SMS

#### Email Setup

Email should already be configured in ERPNext. If not:

1. Go to **Email Account** in ERPNext
2. Configure your SMTP settings
3. Test email sending

### Step 2: Configure POS Profile

1. Go to **POS Profile** in ERPNext
2. Find the **Invoice Sharing Settings** section
3. Configure as needed:

#### Enable WhatsApp Sharing

- ☑️ Check **Enable WhatsApp Sharing**
- **WhatsApp Template** (Optional):
  ```
  Invoice {invoice_name} for {customer_name}
  
  Total: {grand_total}
  Date: {date}
  
  View invoice: {invoice_url}
  
  Thank you for your business!
  ```

#### Enable SMS Sharing

- ☑️ Check **Enable SMS Sharing**
- **SMS Template** (Optional):
  ```
  Invoice {invoice_name} - {customer_name}. Total: {grand_total}. View: {invoice_url}
  ```

#### Enable Email Sharing

- ☑️ Check **Enable Email Sharing**
- **Email Template**: Select or create an Email Template
- **Default Print Format**: Select the print format for PDF attachments

### Step 3: Template Variables

Use these placeholders in your templates:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{invoice_name}` | Invoice number | ACC-SINV-2025-00001 |
| `{customer_name}` | Customer display name | John Doe |
| `{grand_total}` | Total amount with currency | $1,250.00 |
| `{date}` | Invoice date | Jan 15, 2025 |
| `{time}` | Invoice time | 10:30 AM |
| `{company}` | Company name | ABC Corp |
| `{invoice_url}` | Link to view invoice | https://... |
| `{items_summary}` | Brief list of items | Laptop x1, Mouse x2 |
| `{total}` | Subtotal | $1,200.00 |
| `{net_total}` | Net total | $1,200.00 |
| `{outstanding_amount}` | Balance due | $0.00 |

### Step 4: Customer Contact Information

For invoice sharing to work, customers must have contact information:

1. Go to **Customer** in ERPNext
2. Add **Mobile No** (for WhatsApp/SMS)
3. Add **Email ID** (for Email)

Alternatively, contacts are fetched from **Customer Primary Contact**.

## Usage

### After Payment

1. Complete a sale in POS
2. After successful payment, the **Invoice Share Dialog** automatically appears
3. Select channel (WhatsApp, SMS, or Email)
4. Verify/edit contact information
5. Click **Send**

### From Invoice History

1. Click the **printer icon** in POS header
2. Find the invoice in history
3. Click the **Share button** (purple icon)
4. Select channel and send

### From Invoice List

You can also share invoices from the ERPNext backend:
1. Go to **Sales Invoice** list
2. Open any invoice
3. Use the **Share** button in the invoice actions

## Template Examples

### Professional WhatsApp Template

```
🧾 *Invoice {invoice_name}*

Dear {customer_name},

Thank you for your purchase!

📦 Items: {items_summary}
💰 Total: *{grand_total}*
📅 Date: {date}

🔗 View full invoice: {invoice_url}

We appreciate your business! 🙏

---
{company}
```

### Short SMS Template

```
Invoice {invoice_name}: {grand_total}. View: {invoice_url} - {company}
```

### Email Template

Create an Email Template in ERPNext:

**Subject:**
```
Invoice {invoice_name} from {company}
```

**Body:**
```html
<p>Dear {customer_name},</p>

<p>Thank you for your purchase. Please find your invoice attached.</p>

<p><strong>Invoice Number:</strong> {invoice_name}</p>
<p><strong>Date:</strong> {date}</p>
<p><strong>Total Amount:</strong> {grand_total}</p>

<p>Items purchased: {items_summary}</p>

<p>You can view your invoice online at: {invoice_url}</p>

<p>If you have any questions, please don't hesitate to contact us.</p>

<p>Best regards,<br>
{company}</p>
```

## Troubleshooting

### WhatsApp Not Working

**Problem**: "WhatsApp gateway is not configured"

**Solution:**
1. Check **WhatsApp Settings** is enabled
2. Verify API credentials are correct
3. Test connection in WhatsApp Settings
4. Check WhatsApp number format includes country code (+1234567890)

### SMS Not Sending

**Problem**: "SMS gateway is not configured"

**Solution:**
1. Go to **SMS Settings**
2. Verify SMS Gateway URL is set
3. Check API credentials
4. Test with a sample SMS
5. Ensure phone numbers include country code

### Email Fails

**Problem**: Email not sending

**Solution:**
1. Check **Email Account** settings
2. Verify SMTP configuration
3. Test email from Email Account
4. Check email address format
5. Verify PDF generation is working

### Contact Information Missing

**Problem**: "No mobile number found for customer"

**Solution:**
1. Edit the **Customer** record
2. Add **Mobile No** and/or **Email ID**
3. Or add contact to **Customer Primary Contact**

### Share Button Not Visible

**Problem**: Share button doesn't appear

**Solution:**
1. Check **POS Profile** has at least one sharing channel enabled
2. Verify custom fields were installed (run `bench migrate`)
3. Clear browser cache
4. Check user has permission to share invoices

## Security & Privacy

- All sharing attempts are logged in **Communication** doctype
- Track delivery status for audit purposes
- Customer contact information is never shared with third parties
- PDF invoices are generated on-demand and not stored permanently
- WhatsApp/SMS use encrypted channels

## Best Practices

1. **Test First**: Test all channels before going live
2. **Keep Templates Short**: SMS has character limits (160 chars)
3. **Professional Tone**: Use appropriate language for your business
4. **Include Company Info**: Always include company name
5. **Provide Invoice Link**: Let customers view invoices online
6. **Check Contact Info**: Verify customer contacts are up-to-date
7. **Monitor Delivery**: Check Communication log for failures

## Costs

- **WhatsApp**: Charged per message by your provider (typically $0.005-0.01/msg)
- **SMS**: Charged per SMS by your provider (typically $0.01-0.05/msg)
- **Email**: Usually free (included with hosting)

## Advanced Configuration

### Custom Print Formats

Create custom print formats in ERPNext:

1. Go to **Print Format**
2. Create new format for **Sales Invoice**
3. Customize layout, add logo, adjust colors
4. Set as **Default Print Format** in POS Profile

### Conditional Templates

Use different templates for different customer groups or invoice amounts:

- Create multiple POS Profiles
- Configure different templates for each
- Assign profiles to different users/terminals

### Batch Sharing

Currently not supported, but coming in future updates:
- Share multiple invoices at once
- Schedule invoice delivery
- Recurring invoice sharing

## Support

For issues or questions:
- **Documentation**: Check POS Next wiki
- **Community**: Discuss in Frappe forum
- **Bug Reports**: GitHub issues

## Updates

Check for updates regularly:
- New gateway integrations
- Enhanced templates
- Additional features

---

**Last Updated**: December 2025  
**Version**: POS Next 1.7.0+

