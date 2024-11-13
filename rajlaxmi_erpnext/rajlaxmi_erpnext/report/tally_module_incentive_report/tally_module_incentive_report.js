// Copyright (c) 2024, pwctech technologies private limited and contributors
// For license information, please see license.txt

frappe.query_reports["Tally Module Incentive Report"] = {
	"filters": [
		{
			"fieldname": "date",
			"label": __("MTD"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "based_on_invoice",
			"label": __("Show Sales Invoice"),
			"fieldtype": "Check",
			"default": 0
		},

	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.bold) {
			value = value.bold();
		}
		return value;
	},
};
