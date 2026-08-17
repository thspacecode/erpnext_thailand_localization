app_name = "erpnext_thailand_localization"
app_title = "ERPNext Thailand Localization"
app_publisher = "SpaceCode Co., Ltd."
app_description = "Thailand localization for ERPNext"
app_email = "p@spacecode.co.th"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# Include js in doctype views
doctype_js = {
	"Journal Entry": "public/js/journal_entry.js",
	"Payment Entry": "public/js/payment_entry.js",
}

# Installation
after_install = "erpnext_thailand_localization.install.after_install"

# Overriding Methods
override_whitelisted_methods = {
	"erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry": "erpnext_thailand_localization.thai_withholding_tax.override_whitelist_method.get_payment_entry.get_payment_entry"
}
override_doctype_dashboards = {
	"Payment Entry": "erpnext_thailand_localization.thai_withholding_tax.payment_entry_dashboard.get_dashboard_data"
}

# Includes in <head>
app_include_js = "/assets/erpnext_thailand_localization/js/pnd_filing.js"

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "erpnext_thailand_localization",
# 		"logo": "/assets/erpnext_thailand_localization/logo.png",
# 		"title": "ERPNext Thailand Localization",
# 		"route": "/erpnext_thailand_localization",
# 		"has_permission": "erpnext_thailand_localization.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/erpnext_thailand_localization/css/erpnext_thailand_localization.css"

# include js, css files in header of web template
# web_include_css = "/assets/erpnext_thailand_localization/css/erpnext_thailand_localization.css"
# web_include_js = "/assets/erpnext_thailand_localization/js/erpnext_thailand_localization.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "erpnext_thailand_localization/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "erpnext_thailand_localization/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "erpnext_thailand_localization.utils.jinja_methods",
# 	"filters": "erpnext_thailand_localization.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "erpnext_thailand_localization.install.before_install"

# Uninstallation
# ------------

# before_uninstall = "erpnext_thailand_localization.uninstall.before_uninstall"
# after_uninstall = "erpnext_thailand_localization.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "erpnext_thailand_localization.utils.before_app_install"
# after_app_install = "erpnext_thailand_localization.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "erpnext_thailand_localization.utils.before_app_uninstall"
# after_app_uninstall = "erpnext_thailand_localization.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "erpnext_thailand_localization.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "erpnext_thailand_localization.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Address": {"validate": "erpnext_thailand_localization.thai_withholding_tax.address.validate_address"}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"erpnext_thailand_localization.tasks.all"
# 	],
# 	"daily": [
# 		"erpnext_thailand_localization.tasks.daily"
# 	],
# 	"hourly": [
# 		"erpnext_thailand_localization.tasks.hourly"
# 	],
# 	"weekly": [
# 		"erpnext_thailand_localization.tasks.weekly"
# 	],
# 	"monthly": [
# 		"erpnext_thailand_localization.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "erpnext_thailand_localization.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "erpnext_thailand_localization.custom.task.CustomTaskMixin"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["erpnext_thailand_localization.utils.before_request"]
# after_request = ["erpnext_thailand_localization.utils.after_request"]

# Job Events
# ----------
# before_job = ["erpnext_thailand_localization.utils.before_job"]
# after_job = ["erpnext_thailand_localization.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"erpnext_thailand_localization.auth.validate"
# ]

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
