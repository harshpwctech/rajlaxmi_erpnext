import frappe
from frappe.utils.data import get_time, getdate

def before_submit(doc, method=None):
    if doc.status == "Present":
        check_in_time =  get_time(doc.in_time)
        if check_in_time > get_time("10:01:00"):
            doc.status = "Half Day"