frappe.query_reports["Sales Person Target Variance"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
		},
		{
			"fieldname": "period",
			"label": __("Period"),
			"fieldtype": "Select",
			"options": [
				{ "value": "MTD", "label": __("Month to Date") },
				{ "value": "Month", "label": __("Month") },
				{ "value": "Fiscal Year", "label": __("Fiscal Year") }
			],
			"default": "Fiscal Year",
            "reqd": 1
		},
        {
			"fieldname": "date",
			"label": __("Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
            "depends_on": 'eval:doc.period === "MTD"'
		},
        {
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
            "depends_on": 'eval:doc.period === "Fiscal Year"'
		},
        {
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"options": [
				{ "value": 1, "label": __("Jan") },
				{ "value": 2, "label": __("Feb") },
				{ "value": 3, "label": __("Mar") },
                { "value": 4, "label": __("Apr") },
                { "value": 5, "label": __("May") },
                { "value": 6, "label": __("Jun") },
                { "value": 7, "label": __("Jul") },
                { "value": 8, "label": __("Aug") },
                { "value": 9, "label": __("Sep") },
                { "value": 10, "label": __("Oct") },
                { "value": 11, "label": __("Nov") },
                { "value": 12, "label": __("Dec") },
			],
            "depends_on": 'eval:doc.period === "Month"',
            "default": frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth() + 1
		},
        {
			"fieldname":"year",
			"label": __("Year"),
			"fieldtype": "Select",
            "depends_on": 'eval:doc.period === "Month"',
		},
        {
            "fieldname": "sales_person",
            "label": __("Sales Person"),
			"fieldtype": "Link",
			"options": "Sales Person"
        }
	],
    onload: function() {
		return  frappe.call({
			method: "rajlaxmi_erpnext.rajlaxmi_erpnext.report.sales_person_target_variance.sales_person_target_variance.get_attendance_years",
			callback: function(r) {
				var year_filter = frappe.query_report.get_filter('year');
				year_filter.df.options = r.message;
				year_filter.df.default = r.message.split("\n")[0];
				year_filter.refresh();
				year_filter.set_input(year_filter.df.default);
			}
		});
	},
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname.includes("variance")) {
			if (data[column.fieldname] < 0) {
				value = "<span style='color:red'>" + value + "</span>";
			} else if (data[column.fieldname] > 0) {
				value = "<span style='color:green'>" + value + "</span>";
			}
		}

		return value;
	},
};