import frappe
from frappe import _
from frappe.utils import getdate, get_datetime
from hrms.hr.doctype.shift_assignment.shift_assignment import (
	get_actual_start_end_datetime_of_shift,
)

def hourly():
    notify_not_checked_in_employees()


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

    email_template = frappe.get_doc("Email Template", "Employees not Checked In")
    for e in not_checked_in_employees:
        now = get_datetime()
        shift_timings = get_actual_start_end_datetime_of_shift(
			e, now, True
		)
        if now >= shift_timings.actual_start and now <= shift_timings.actual_end:
            parent_doc = frappe.get_doc("Employee", e)
            args = parent_doc.as_dict()
            reporting_manager = None
            if parent_doc.reports_to:
                reporting_manager = frappe.db.get_value("Employee", parent_doc.reports_to, "prefered_email")
            message = frappe.render_template(email_template.response, args)
            notify(
                    {
                        # for post in messages
                        "message": message,
                        "message_to": parent_doc.prefered_email,
                        # for email
                        "subject": email_template.subject,
                        "cc": reporting_manager
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