import frappe
from frappe.utils.data import get_time

def before_submit(doc, method=None):
    if doc.status == "Present":
        if doc.in_time:
            check_in_time =  get_time(doc.in_time)
            if check_in_time > get_time("10:00:00"):
                doc.status = "Half Day"
        else:
            frappe.msgprint("Half Day Validation on {0} ignored for {1}".format(doc.attendance_date, doc.employee_name))