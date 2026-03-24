# Copyright (c) 2026, Production Scheduler and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class EquipmentMaintenance(Document):
	"""Equipment Maintenance record for tracking unit maintenance schedules."""
	
	def on_trash(self):
		"""Cascade orders forward when maintenance is deleted."""
		from production_scheduler.api import cascade_orders_after_maintenance_removal
		
		# Trigger cascading to move affected orders to next available date
		result = cascade_orders_after_maintenance_removal(
			unit=self.unit,
			maint_start_date=self.start_date,
			maint_end_date=self.end_date
		)
		
		frappe.msgprint(
			f"✓ Maintenance removed. {result.get('cascaded_count', 0)} orders moved to next available date.",
			indicator='green',
			title="Orders Cascaded"
		)
