from erpnext_thailand_localization.data.test_data.bootstrap_test_data import BootStrapTestData
from erpnext_thailand_localization.tests.testsuite import ERPNextThaiTestSuite

# Importing test utilities bootstraps the shared records, following erpnext.tests.utils.
boot_strap_test_data = BootStrapTestData()
boot_strap_test_data.make()
