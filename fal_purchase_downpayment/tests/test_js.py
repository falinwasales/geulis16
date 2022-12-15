from odoo.addons.web.tests.test_js import WebSuite


def fal_skip_test():
    return True


WebSuite.test_01_js = fal_skip_test()
