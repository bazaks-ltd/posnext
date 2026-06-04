# Copyright (c) 2026, Bazaks and contributors
# For license information, please see license.txt

from pos_next.pos_next.report.sales_by_cost_center_base import CurrentShiftSalesByCostCenterReport


def execute(filters=None):
	return CurrentShiftSalesByCostCenterReport(filters).run()
