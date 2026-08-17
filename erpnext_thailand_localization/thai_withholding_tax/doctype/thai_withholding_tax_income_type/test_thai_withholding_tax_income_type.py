# Copyright (c) 2026, SpaceCode Co., Ltd. and Contributors
# See license.txt

import json

import frappe

from erpnext_thailand_localization.tests.utils import ERPNextThaiTestSuite

# On ERPNextThaiTestSuite, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = ["Account"]


class IntegrationTestThaiWithholdingTaxIncomeType(ERPNextThaiTestSuite):
	"""
	Integration tests for ThaiWithholdingTaxIncomeType.
	Use this class for testing interactions between multiple components.
	"""

	pass
