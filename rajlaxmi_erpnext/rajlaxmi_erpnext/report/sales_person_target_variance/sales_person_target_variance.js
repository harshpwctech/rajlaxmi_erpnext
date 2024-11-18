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
			"default": "MTD",
            "reqd": 1
		},
        {
			"fieldname": "date",
			"label": __("Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
		},
        {
			"fieldname": "based_on",
			"label": __("Based On"),
			"fieldtype": "Select",
			"options": [
				{ "value": "Sales Person", "label": __("Sales Person") },
                { "value": "Item Group", "label": __("Item Group") },
                { "value": "Item", "label": __("Item") }
			],
			"default": "Sales Person",
		},
        {
            "fieldname": "sales_person",
            "label": __("Sales Person"),
			"fieldtype": "Link",
			"options": "Sales Person"
        },
        {
            "fieldname": "team_lead",
            "label": __("Team Lead"),
			"fieldtype": "Link",
			"options": "Sales Person",
            get_query: () => {
				return {
					filters: {
						is_group: 1,
					},
				};
			},

        }
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname.includes("variance")) {
			if (data[column.fieldname] < 0) {
				value = "<span style='color:red'>" + value + "</span>";
			} else if (data[column.fieldname] > 0) {
				value = "<span style='color:green'>" + value + "</span>";
			}
		};
		if (data && data.bold) {
			value = value.bold();
		}

		return value;
	},
};