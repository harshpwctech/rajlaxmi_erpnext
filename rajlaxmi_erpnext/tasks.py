import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, time_diff_in_hours
from hrms.hr.doctype.shift_assignment.shift_assignment import (
	get_actual_start_end_datetime_of_shift,
)
from frappe.desk.query_report import build_xlsx_data
from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday
from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee
from frappe.utils.xlsxutils import make_xlsx

def hourly():
    notify_not_checked_in_employees()
    notify_not_checked_out_employees()

def daily():
    update_last_sync()
    # send_reports()

def update_last_sync():
    shift_list = frappe.get_all("Shift Type", filters={"enable_auto_attendance": "1"}, pluck="name")
    for shift in shift_list:
        frappe.db.set_value("Shift Type", shift, "last_sync_of_checkin", get_datetime(), update_modified=False)

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
            ["Leave Application", "status", "=", "Approved"],
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
        if shift_timings and should_mark_attendance(e, now):
            if now >= shift_timings.start_datetime and time_diff_in_hours(now, shift_timings.start_datetime) <= 1:
                parent_doc = frappe.get_doc("Employee", e)
                args = parent_doc.as_dict()
                message = frappe.render_template(email_template.response, args)
                subject = frappe.render_template(email_template.subject, args)
                leave_approver = None
                if parent_doc.leave_approver:
                    leave_approver =  frappe.db.get_value("User", parent_doc.leave_approver, "email")
                notify(
                        {
                            # for post in messages
                            "message": message,
                            "message_to": parent_doc.prefered_email,
                            # for email
                            "subject": subject,
                            "cc": leave_approver
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
    not_checked_out_employees = [e.employee for e in frappe.get_all(
        "Employee Checkin",
        filters=[
            ["Employee Checkin", "employee", "not in", employee_checkouts+leave_employee_ids],
            ["Employee Checkin","time","Timespan","today"],
            ["Employee Checkin","log_type","=","IN"]
        ],
        fields=["employee"]
    )]

    email_template = frappe.get_doc("Email Template", "Employees Not Checked Out")
    for e in not_checked_out_employees:
        now = get_datetime()
        shift_timings = get_actual_start_end_datetime_of_shift(
			e, now, True
		)
        if shift_timings:
            if now >= shift_timings.end_datetime and time_diff_in_hours(now, shift_timings.end_datetime) <= 1:
                parent_doc = frappe.get_doc("Employee", e)
                args = parent_doc.as_dict()
                leave_approver = None
                if parent_doc.leave_approver:
                    leave_approver =  frappe.db.get_value("User", parent_doc.leave_approver, "email")
                message = frappe.render_template(email_template.response, args)
                subject = frappe.render_template(email_template.subject, args)
                notify(
                        {
                            # for post in messages
                            "message": message,
                            "message_to": parent_doc.prefered_email,
                            # for email
                            "subject": subject,
                            "cc": leave_approver
                        }
                    )
   
def should_mark_attendance(employee: str, attendance_date: str) -> bool:
    """Determines whether attendance should be marked on holidays or not"""
    holiday_list = get_holiday_list_for_employee(employee, False)
    if is_holiday(holiday_list, attendance_date):
        return False
    return True

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
            cc=args.cc,
            attachments=args.get("attachments", None)
        )
        frappe.msgprint(_("Email sent to {0}").format(contact))
    except frappe.OutgoingEmailError:
        pass


# def send_reports():
#     to_team = ["Sales Team Target Variance"]
#     to_management = ["Sales Person Target Variance"]
#     for m in to_management:
#         data = get_report_content(m)
#         if not data:
#             return
#         if isinstance(data, list):
#             attachments = [{"fname": m, "fcontent": data}]
#         frappe.sendmail(
# 			recipients=self.email_to.split(),
# 			subject=m,
# 			message=message,
# 			attachments=attachments
# 		)
#     return

# def get_report_content(report_name):
#     report = frappe.get_doc("Report", report_name)
#     if report_name == "Sales Person Target Variance":
#         filters = {
#             "company": "",

#         }
#     columns, data = report.get_data(
#         limit= 500,
#         filters=frappe.parse_json(filters) if filters else {},
#         as_dict=True,
#         ignore_prepared_report=True,
#         are_default_filters=False,
#     )
#     columns.insert(0, frappe._dict(fieldname="idx", label="", width="30px"))
#     for i in range(len(data)):
#         data[i]["idx"] = i + 1
#     if len(data) == 0:
#         return None
#     report_data = frappe._dict()
#     report_data["columns"] = columns
#     report_data["result"] = data

#     xlsx_data, column_widths = build_xlsx_data(report_data, [], 1, ignore_visible_idx=True)
#     xlsx_file = make_xlsx(xlsx_data, report_name, column_widths=column_widths)
#     return xlsx_file.getvalue()
