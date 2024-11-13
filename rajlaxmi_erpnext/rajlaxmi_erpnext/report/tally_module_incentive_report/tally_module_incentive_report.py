# Copyright (c) 2024, pwctech technologies private limited and contributors
# For license information, please see license.txt

import frappe
import copy
from frappe import _
from frappe.utils.data import get_first_day

def execute(filters=None):
	data = []
	base_price = 9000
	sku = "Tally Module"
	columns = get_columns(filters)
	rows = get_data(filters, base_price, sku)
	if not rows:
		return columns, data
	for sales_person, details in rows.items():
		value = {"sales_person": sales_person}
		value.update({"team": frappe.db.get_value("Sales Person", {"name": sales_person}, fieldname="department")})
		value.update({"team_lead": frappe.db.get_value("Sales Person", {"name": sales_person}, fieldname="parent_sales_person")})
		value["qty"] = 0
		value["gross_amount"] = 0
		value["margin_amount"] = 0
		for i in details:
			if filters.get("based_on_invoice"):
				value.update(i)
				data.append(copy.deepcopy(value))
			else:
				value["qty"] += i["qty"]
				value["gross_amount"] += i["gross_amount"]
				value["margin_amount"] += i["margin_amount"]
		
		if filters.get("based_on_invoice"):
			value.update({"sales_invoice": "Total","bold": 1})
			value.update({"qty": sum(i["qty"] for i in details),"bold": 1})
			value.update({"gross_amount": sum(i["gross_amount"] for i in details),"bold": 1})
			value.update({"margin_amount": sum(i["margin_amount"] for i in details),"bold": 1})
		
		incentive = calculate_incentive(value["qty"], value["margin_amount"])
		value.update({"incentive": incentive, "bold": 1 if filters.get("based_on_invoice") else 0})
		data.append(value)

	return columns, data

def get_columns(filters):
	columns = [
		{
			"fieldname": "team",
			"label": _("Team"),
			"fieldtype": "Link",
			"options": "Department",
			"width": 150,
		},
		{
			"fieldname": "team_lead",
			"label": _("Team Lead"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "sales_person",
			"label": _("Sales Person"),
			"fieldtype": "Data",
			"width": 150,
		}]
	if filters.get("based_on_invoice"):
		columns.append(
			{
				"fieldname": "sales_invoice",
				"label": _("Sales Invoice"),
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"width": 150,
        	}
		)
	
	columns.extend([
		{
			"fieldname": "qty",
			"label": _("MTD Quantity"),
			"fieldtype": "Int",
			"default": 0.00,
			"width": 100,
		},
		{
			"fieldname": "gross_amount",
			"label": _("MTD Gross Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"default": 0.00,
			"width": 100,
		},
		{
			"fieldname": "margin_amount",
			"label": _("MTD Margin Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"default": 0.00,
			"width": 100,
		},
		{
			"fieldname": "incentive",
			"label": _("MTD Incentive"),
			"fieldtype": "Currency",
			"options": "currency",
			"default": 0.00,
			"width": 100,
		}
	])
	return columns

def get_data(filters, base_price, sku):
	start_date, end_date = get_start_date_end_date(filters)
	date_field = "posting_date"
	parent_doc = frappe.qb.DocType("Sales Invoice")
	child_doc = frappe.qb.DocType("Sales Invoice Item")
	sales_team = frappe.qb.DocType("Sales Team")
	query = frappe.qb.from_(parent_doc).inner_join(child_doc).on(child_doc.parent == parent_doc.name)
	query = query.inner_join(sales_team).on(sales_team.parent == parent_doc.name)
	sales_field_col = sales_team["sales_person"]
	contribution = sales_team.allocated_percentage
	query = query.select(
		parent_doc.name.as_("sales_invoice"),
		child_doc.qty,
		child_doc.rate,
		sales_field_col,
		contribution,
	).where(
		#For testing
		(parent_doc.docstatus == 0)
		& (child_doc.item_code == sku)
		& (child_doc.rate > base_price)
		& (parent_doc[date_field].between(start_date, end_date))
	)
	inv_data = query.run(as_dict=True)

	return prepare_data(inv_data, base_price)

def get_start_date_end_date(filters):
	end_date = filters.get("date")
	start_date = get_first_day(end_date)
	return start_date, end_date


def prepare_data(inv_data, base_price):
	rows = {}
	for i in inv_data:
		if i.sales_person not in rows:
			rows.setdefault(i.sales_person, [])
		details = rows[i.sales_person]
		invoice_details = {
			"sales_invoice": i.sales_invoice,
			"qty": i.qty,
			"gross_amount": i.rate*i.allocated_percentage/100,
			"margin_amount": (i.rate-base_price)*i.allocated_percentage/100
		}
		details.append(invoice_details)
	
	return rows

def calculate_incentive(qty, margin_amount):
	if qty < 3:
		return margin_amount*.1
	elif 3 <= qty < 5:
		return margin_amount*.2
	else:
		return margin_amount*.3
