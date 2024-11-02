from rajlaxmi_erpnext.report.sales_person_target_variance.sales_person_target_variance import get_data_column

def execute(filters=None):
    return get_data_column(filters, "Sales Person", False)