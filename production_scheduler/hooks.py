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
    },
    "Planning sheet": {
        "validate": "production_scheduler.api.validate_planning_sheet_duplicates"
    }
}

# Client Scripts
doctype_js = {
    "Planning sheet": "public/js/planning_sheet_custom.js"
}
