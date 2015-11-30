# This file is part of the stock_relocation module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class StockRelocationTestCase(ModuleTestCase):
    'Test Stock Relocation module'
    module = 'stock_relocation'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        StockRelocationTestCase))
    return suite
