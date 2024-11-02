import frappe
from frappe import _
from frappe.query_builder.functions import Count, Extract, Sum
from erpnext.accounts.doctype.monthly_distribution.monthly_distribution import (
    get_periodwise_distribution_data,
)
from erpnext.accounts.report.financial_statements import get_period_list
from erpnext.accounts.utils import get_fiscal_year, getdate, cint, cstr
from frappe.utils.data import get_first_day, get_last_day, date_diff

def execute(filters=None):
    return get_data_column(filters, "Sales Person")

def get_data_column(filters, partner_doctype, with_salary=True):
    data = []
    columns = get_columns(partner_doctype, with_salary)
    rows = get_data(filters, partner_doctype)
    if not rows:
        return columns, data

    for key, value in rows.items():
        value.update({"team": frappe.db.get_value(partner_doctype, {"name": key}, fieldname="department")})
        value.update({"team_lead": frappe.db.get_value(partner_doctype, {"name": key}, fieldname="parent_sales_person")})
        value.update({frappe.scrub(partner_doctype): key})
        if value.get("total_variance") < 0:
            per_day = get_per_day_requirement(filters, value.get("total_variance")*-1)
            value.update({"per_day": per_day})
        data.append(value)

    return columns, data

def get_columns(partner_doctype, with_salary):
    fieldtype, options = "Currency", "currency"

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
            "fieldtype": "Link",
            "options": partner_doctype,
            "width": 150,
        },
        {
            "fieldname": frappe.scrub(partner_doctype),
            "label": _(partner_doctype),
            "fieldtype": "Link",
            "options": partner_doctype,
            "width": 150,
        },
        {
            "fieldname": "experience",
            "label": _("Total Experience"),
            "fieldtype": "Float",
            "default": 0.00,
            "width": 100,
        },
        {
            "fieldname": "customer_acquisition",
            "label": _("Customer Acquisition"),
            "fieldtype": "Int",
            "default": 0,
            "width": 150,
        },
        {
            "fieldname": "total_target",
            "label": _("Total Target"),
            "fieldtype": fieldtype,
            "options": options,
            "width": 150,
        },
        {
            "fieldname": "total_achieved",
            "label": _("Total Achieved"),
            "fieldtype": fieldtype,
            "options": options,
            "width": 150,
        },
        {
            "fieldname": "per_achieved",
            "label": _("% Achieved vs Target"),
            "fieldtype": "Percent",
            "width": 150,
        },
        {
            "fieldname": "total_variance",
            "label": _("Total Variance"),
            "fieldtype": fieldtype,
            "options": options,
            "width": 150,
        },
        {
            "fieldname": "per_day",
            "label": _("Per Day"),
            "fieldtype": fieldtype,
            "options": options,
            "width": 150,
            "default": 0.00,
        }]
    if with_salary:
        columns.extend([
        {
            "fieldname": "salary",
            "label": _("Salary"),
            "fieldtype": fieldtype,
            "options": options,
            "width": 150,
        },
        {
            "fieldname": "per_salary",
            "label": _("% Achieved vs Salary"),
            "fieldtype": "Percent",
            "width": 150,
        }    
    ])

    return columns

def get_data(filters, partner_doctype):
    sales_field = frappe.scrub(partner_doctype)
    sales_users_data = get_parents_data(filters, partner_doctype)
    if not sales_users_data:
        return
    sales_users = []

    for d in sales_users_data:
        if d.parent not in sales_users:
            sales_users.append(d.parent)

    date_field = "posting_date"

    actual_data = get_actual_data(filters, sales_users, date_field, sales_field)

    return prepare_data(
        filters,
        sales_users_data,
        actual_data,
        sales_field,
    )


def prepare_data(
    filters,
    sales_users_data,
    actual_data,
    sales_field,
):
    rows = {}

    target_qty_amt_field = "target_amount"
    qty_or_amount_field = "base_net_amount"

    item_group_parent_child_map = get_item_group_parent_child_map()

    for d in sales_users_data:

        if d.parent not in rows:
            rows.setdefault(d.parent, {"total_target": 0, "total_achieved": 0, "per_achieved": 0, "total_variance": 0, "per_day": 0, "salary": 0, "per_salary": 0})

        details = rows[d.parent]
        
        target_percentage = get_target_percentage(filters, d.distribution_id)
        target_amount = d.get(target_qty_amt_field)*target_percentage/100
        details["total_target"] += target_amount
        for r in actual_data:
            if (
                r.get(sales_field) == d.parent
                and (
                    r.item_group == d.item_group
                    or r.item_group in item_group_parent_child_map.get(d.item_group, [])
                )
            ):
                details["total_achieved"] += r.get(qty_or_amount_field, 0)

        details["total_variance"] = details.get("total_achieved") - details.get("total_target")
        details["per_achieved"] = details.get("total_achieved") / details.get("total_target") * 100

    return rows


def get_item_group_parent_child_map():
    """
    Returns a dict of all item group parents and leaf children associated with them.
    """

    item_groups = frappe.get_all(
        "Item Group", fields=["name", "parent_item_group"], order_by="lft desc, rgt desc"
    )
    item_group_parent_child_map = {}

    for item_group in item_groups:
        children = item_group_parent_child_map.get(item_group.name, [])
        if not children:
            children = [item_group.name]
        item_group_parent_child_map.setdefault(item_group.parent_item_group, []).extend(children)

    return item_group_parent_child_map


def get_actual_data(filters, sales_users_or_territory_data, date_field, sales_field):
    start_date, end_date = get_start_date_end_date(filters)
    parent_doc = frappe.qb.DocType("Sales Invoice")
    child_doc = frappe.qb.DocType("Sales Invoice Item")

    query = frappe.qb.from_(parent_doc).inner_join(child_doc).on(child_doc.parent == parent_doc.name)

    if sales_field == "sales_person":
        sales_team = frappe.qb.DocType("Sales Team")
        net_amount = sales_team.custom_contribution_to_margin
        sales_field_col = sales_team[sales_field]

        query = query.inner_join(sales_team).on(sales_team.parent == parent_doc.name)
    else:
        net_amount = parent_doc.custom_net_amount_eligible_for_commission
        sales_field_col = parent_doc[sales_field]

    query = query.select(
        child_doc.item_group,
        parent_doc[date_field],
        (net_amount).as_("base_net_amount"),
        sales_field_col,
    ).where(
        #For testing
        (parent_doc.docstatus == 0)
        & (parent_doc[date_field].between(start_date, end_date))
        & (sales_field_col.isin(sales_users_or_territory_data))
    )

    return query.run(as_dict=True)


def get_parents_data(filters, partner_doctype):
    filters_dict = {"parenttype": partner_doctype}
    if filters.get(frappe.scrub(partner_doctype)):
        filters_dict["parent"] = filters.get(frappe.scrub(partner_doctype))
    
    if filters.get("team_lead"):
        filters_dict["parent_sales_person"] = filters.get("team_lead")
        
    target_qty_amt_field = "target_amount"
    
    start_date, end_date = get_start_date_end_date(filters)

    fiscal_year =  get_fiscal_year(start_date)
    filters_dict["fiscal_year"] = fiscal_year[0]

    return frappe.get_all(
        "Target Detail",
        filters=filters_dict,
        fields=["parent", "item_group", target_qty_amt_field, "fiscal_year", "distribution_id"],
    )

def get_start_date_end_date(filters):
    if filters.get("period") == "Fiscal Year":
        fiscal_year = get_fiscal_year(fiscal_year=filters.get("fiscal_year"), as_dict=1)
        return fiscal_year.year_start_date, fiscal_year.year_end_date
    elif filters.get("period") == "MTD":
        end_date = filters.get("date")
        start_date = get_first_day(end_date)
        return start_date, end_date
    elif filters.get("period") == "Month":
        start_date = getdate("{1}-{0}-01".format(filters.get("month"), filters.get("year")))
        end_date = get_last_day(start_date)
        return start_date, end_date

def get_target_percentage(filters, distribution_id):
    doc = frappe.get_doc("Monthly Distribution", distribution_id)
    if filters.get("period") == "Fiscal Year":
        return 100.00
    elif filters.get("period") == "MTD":
        date = getdate(filters.get("date"))
        month = date.strftime("%B").title()
        start_date = get_first_day(date)
        end_date = get_last_day(start_date)
        total_days_of_month = date_diff(end_date, start_date)
        mtd_days = date_diff(date, start_date)
        total_percent = 0
        for d in doc.percentages:
            if d.month == month:
                total_percent += d.percentage_allocation
        return total_percent*mtd_days/total_days_of_month
    elif filters.get("period") == "Month":
        start_date = getdate("{1}-{0}-01".format(filters.get("month"), filters.get("year")))
        month = start_date.strftime("%B").title()
        for d in doc.percentages:
            if d.month == month:
                return d.percentage_allocation

def get_per_day_requirement(filters, total_variance):
    today = getdate()
    if filters.get("period") == "Fiscal Year":
        fiscal_year = get_fiscal_year(fiscal_year=filters.get("fiscal_year"), as_dict=1)
        balance_days =  date_diff(fiscal_year.year_end_date, today)
        if balance_days > 0:
            return total_variance/balance_days
    elif filters.get("period") == "MTD":
        start_date = getdate(filters.get("date"))
        end_date = get_last_day(start_date)
        balance_days =  date_diff(end_date, today)
        if balance_days > 0:
            return total_variance/balance_days
    elif filters.get("period") == "Month":
        start_date = getdate("{1}-{0}-01".format(filters.get("month"), filters.get("year")))
        end_date = get_last_day(start_date)
        balance_days =  date_diff(end_date, today)
        if balance_days > 0:
            return total_variance/balance_days
    
    return 0.00

    

@frappe.whitelist()
def get_attendance_years() -> str:
    """Returns all the years for which attendance records exist"""
    sals_invoice = frappe.qb.DocType("Sales Invoice")
    year_list = (
        frappe.qb.from_(sals_invoice)
        .select(Extract("year", sals_invoice.posting_date).as_("year"))
        .distinct()
    ).run(as_dict=True)

    if year_list:
        year_list.sort(key=lambda d: d.year, reverse=True)
    else:
        year_list = [frappe._dict({"year": getdate().year})]

    return "\n".join(cstr(entry.year) for entry in year_list)