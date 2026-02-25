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



doc_events = {
    "Sales Order": {
        "on_submit": "production_scheduler.api.auto_create_planning_sheet"
    }
}
