#This file is part stock_relocation module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
from trytond.model import Workflow, ModelView, fields
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond import backend

__all__ = ['Move']
__metaclass__ = PoolMeta


class Move:
    __name__ = 'stock.move'

    @classmethod
    def _get_origin(cls):
        models = super(Move, cls)._get_origin()
        models.append('stock.relocation')
        return models
