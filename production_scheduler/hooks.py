# Revert: Restoring stable version of Production Scheduler
app_name = "production_scheduler"
app_title = "Production Scheduler"
app_publisher = "Admin"
app_description = "Production Scheduler App"
app_email = "admin@example.com"
app_license = "mit"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/production_scheduler/css/production_scheduler.css"
app_include_js = "production_scheduler.bundle.js"


# Document hooks are owned by production_entry when both apps are installed
# (scheduler_hooks + scheduler_api) to avoid double execution. Sales Order
# on_submit creates Planning sheets only via production_entry.
# Color Chart / board UIs call production_scheduler.api.* for whitelisted methods.
doc_events = {}
