import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, time_diff_in_hours
from hrms.hr.doctype.shift_assignment.shift_assignment import (
	get_actual_start_end_datetime_of_shift,
)

def hourly():
    notify_not_checked_in_employees()
    notify_not_checked_out_employees()


def notify_not_checked_in_employees():
    employee_checkins = [ec.employee for ec in frappe.get_all(
        "Employee Checkin",
        filters=[
                ["Employee Checkin","time","Timespan","today"],
                ["Employee Checkin","log_type","=","IN"]
        ], 
        fields=["employee"]
    )]
    leave_employee_ids = [la.employee for la in frappe.get_all(
        "Leave Application",
        filters=[
            ["Leave Application", "from_date", "<=", getdate()],
            ["Leave Application", "to_date", ">=", getdate()],
            ["Leave Application", "status", "=", "Approved"]
            ["Leave Application", "docstatus", "=", "1"]
        ],
        fields=["employee"]
    )]
    not_checked_in_employees = [e.name for e in frappe.get_all(
        "Employee",
        filters=[
            ["Employee", "name", "not in", employee_checkins+leave_employee_ids],
            ["Employee", "user_id", "is", "set"],
            ["Employee", "status", "=", "Active"],
        ],
        fields=["name"]
    )]

    email_template = frappe.get_doc("Email Template", "Employees Not Checked In")
    for e in not_checked_in_employees:
        now = get_datetime()
        shift_timings = get_actual_start_end_datetime_of_shift(
			e, now, True
		)
        if now >= shift_timings.actual_start and now <= shift_timings.actual_end:
            parent_doc = frappe.get_doc("Employee", e)
            args = parent_doc.as_dict()
            managers = []
            if time_diff_in_hours(now, shift_timings.actual_start) < 2 or time_diff_in_hours(shift_timings.actual_end, now) < 2:
                if parent_doc.reports_to:
                    if frappe.db.get_value("Employee", parent_doc.reports_to, "prefered_email"):
                        managers.append(frappe.db.get_value("Employee", parent_doc.reports_to, "prefered_email"))
                    if time_diff_in_hours(shift_timings.actual_end, now) < 2:
                        if frappe.db.get_value("Employee", parent_doc.reports_to, "reports_to"):
                            super_manager = frappe.db.get_value("Employee", parent_doc.reports_to, "reports_to")
                            managers.append(frappe.db.get_value("Employee", super_manager, "prefered_email"))
            
            message = frappe.render_template(email_template.response, args)
            notify(
                    {
                        # for post in messages
                        "message": message,
                        "message_to": parent_doc.prefered_email,
                        # for email
                        "subject": email_template.subject,
                        "cc": managers
                    }
                )

def notify_not_checked_out_employees():
    employee_checkouts = [ec.employee for ec in frappe.get_all(
        "Employee Checkin",
        filters=[
                ["Employee Checkin","time","Timespan","today"],
                ["Employee Checkin","log_type","=","OUT"]
        ], 
        fields=["employee"]
    )]
    leave_employee_ids = [la.employee for la in frappe.get_all(
        "Leave Application",
        filters=[
            ["Leave Application", "from_date", "<=", getdate()],
            ["Leave Application", "to_date", ">=", getdate()],
            ["Leave Application", "status", "=", "Approved"],
            ["Leave Application", "docstatus", "=", "1"]
        ],
        fields=["employee"]
    )]
    not_checked_out_employees = [e.name for e in frappe.get_all(
        "Employee",
        filters=[
            ["Employee", "name", "not in", employee_checkouts+leave_employee_ids],
            ["Employee", "user_id", "is", "set"],
            ["Employee", "status", "=", "Active"],
        ],
        fields=["name"]
    )]

    email_template = frappe.get_doc("Email Template", "Employees Not Checked Out")
    for e in not_checked_out_employees:
        now = get_datetime()
        shift_timings = get_actual_start_end_datetime_of_shift(
			e, now, True
		)
        if time_diff_in_hours(now, shift_timings.actual_end) > 1:
            parent_doc = frappe.get_doc("Employee", e)
            args = parent_doc.as_dict()
            managers = []
            if time_diff_in_hours(now, shift_timings.actual_end) > 2:
                if parent_doc.reports_to:
                    if frappe.db.get_value("Employee", parent_doc.reports_to, "prefered_email"):
                        managers.append(frappe.db.get_value("Employee", parent_doc.reports_to, "prefered_email"))
                    if time_diff_in_hours(shift_timings.actual_end, now) > 4:
                        if frappe.db.get_value("Employee", parent_doc.reports_to, "reports_to"):
                            super_manager = frappe.db.get_value("Employee", parent_doc.reports_to, "reports_to")
                            managers.append(frappe.db.get_value("Employee", super_manager, "prefered_email"))
            
            message = frappe.render_template(email_template.response, args)
            notify(
                    {
                        # for post in messages
                        "message": message,
                        "message_to": parent_doc.prefered_email,
                        # for email
                        "subject": email_template.subject,
                        "cc": managers
                    }
                )
   
def notify(args):
    args = frappe._dict(args)
    # args -> message, message_to, subject
    contact = args.message_to
    if not isinstance(contact, list):
        if not args.notify == "employee":
            contact = frappe.get_doc("User", contact).email or contact
    try:
        frappe.sendmail(
            recipients=contact,
            subject=args.subject,
            message=args.message,
            cc=args.cc
        )
        frappe.msgprint(_("Email sent to {0}").format(contact))
    except frappe.OutgoingEmailError:
        pass