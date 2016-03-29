#This file is part stock_relocation module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Configuration']


class Configuration:
    __metaclass__ = PoolMeta
    __name__ = 'stock.configuration'
    to_relocation = fields.Property(fields.Many2One("stock.location",
        "To ReLocation", domain=[('type', 'not in', ('warehouse', 'view'))]))
