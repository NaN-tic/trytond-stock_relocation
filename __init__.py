#This file is part stock_relocation module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.pool import Pool
from .configuration import *
from .move import *
from .stock_relocation import *

def register():
    Pool.register(
        Configuration,
        Move,
        StockRelocation,
        module='stock_relocation', type_='model')
