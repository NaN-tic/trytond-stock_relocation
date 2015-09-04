#This file is part stock_relocation module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool
from trytond.pyson import Eval, Not, Equal, If, In
from trytond.transaction import Transaction

__all__ = ['StockRelocation']

STATES = {
    'readonly': Not(Equal(Eval('state'), 'draft')),
}
DEPENDS = ['state']


class StockRelocation(ModelSQL, ModelView):
    'Stock Relocation'
    __name__ = 'stock.relocation'
    planned_date = fields.Date('Planned Date',
        required=True, states=STATES,
        depends=DEPENDS)
    employee = fields.Many2One('company.employee', 'Employee',
        required=True, states=STATES,
        depends=DEPENDS)
    warehouse = fields.Many2One('stock.location', "Warehouse",
        required=True, states=STATES,
        domain=[('type', '=', 'warehouse')],
        depends=DEPENDS)
    from_location = fields.Many2One('stock.location', 'From Location',
        select=True, required=True, states=STATES, depends=DEPENDS,
        domain=[('type', 'not in', ('warehouse', 'view'))])
    to_location = fields.Many2One('stock.location', 'To Location', select=True,
        required=True, states=STATES, depends=DEPENDS,
        domain=[('type', 'not in', ('warehouse', 'view'))])
    product = fields.Many2One('product.product', 'Product', required=True,
        select=True, states=STATES,
        domain=[('type', '!=', 'service')],
        depends=DEPENDS)
    quantity = fields.Float('Quantity', required=True,
        digits=(16, Eval('unit_digits', 2)), states=STATES,
        depends=['state', 'unit_digits'])
    uom = fields.Many2One('product.uom', 'Uom', required=True, states=STATES,
        depends=DEPENDS)
    unit_digits = fields.Function(fields.Integer('Unit Digits'),
        'on_change_with_unit_digits')
    company = fields.Many2One('company.company', 'Company', required=True,
        states=STATES,
        domain=[
            ('id', If(In('company', Eval('context', {})), '=', '!='),
                Eval('context', {}).get('company', -1)),
            ],
        depends=DEPENDS)
    move = fields.Many2One('stock.move', 'Move', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ], 'State')

    @classmethod
    def __setup__(cls):
        super(StockRelocation, cls).__setup__()
        cls._order.insert(0, ('planned_date', 'DESC'))
        cls._order.insert(1, ('warehouse', 'ASC'))
        cls._order.insert(2, ('from_location', 'ASC'))
        cls._buttons.update({
                'confirm': {
                    'invisible': ~Eval('state').in_(['draft']),
                    },
                })
        cls._error_messages.update({
                'quantity_by_location': (
                    'There are %s of "%s" and you try to relocate %s units.'
                    ),
                })

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_planned_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_employee():
        User = Pool().get('res.user')
        if Transaction().context.get('employee'):
            return Transaction().context['employee']
        else:
            user = User(Transaction().user)
            if user.employee:
                return user.employee.id

    @staticmethod
    def default_warehouse():
        pool = Pool()
        User = pool.get('res.user')
        Location = pool.get('stock.location')

        user = User(Transaction().user)
        if hasattr(user, 'stock_warehouse') and user.stock_warehouse:
            return user.stock_warehouse.id
        else:
            locations = Location.search([('type', '=', 'warehouse')])
            if len(locations) == 1:
                return locations[0].id

    @staticmethod
    def default_to_location():
        Config = Pool().get('stock.configuration')
        config = Config(1)
        return config.to_relocation.id if config.to_relocation else None

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    def update_quantity(self):
        pool = Pool()
        Product = pool.get('product.product')
        Date = pool.get('ir.date')

        today = Date.today()

        if not self.from_location and self.warehouse and self.product.locations:
            for l in self.product.locations:
                if l.warehouse.id == self.warehouse.id:
                    from_location = l.location
                    break
            self.from_location = from_location

        if self.from_location:
            with Transaction().set_context(
                    forecast=False,
                    stock_date_end=today,
                    locations=[self.from_location.id]):
                product = Product(self.product.id)
                self.quantity = product.quantity

    @fields.depends('product', 'warehouse', 'from_location')
    def on_change_product(self):
        res = {}
        res['uom'] = None
        res['from_location'] = None
        res['from_location.rec_name'] = None
        if self.product:
            res['uom'] = self.product.default_uom.id
            res['uom.rec_name'] = self.product.default_uom.rec_name
            res['unit_digits'] = self.product.default_uom.digits
            self.update_quantity()
            if self.from_location:
                res['from_location'] = self.from_location.id
                res['from_location.rec_name'] = self.from_location.rec_name
            res['quantity'] = self.quantity or 0
        return res

    @fields.depends('uom')
    def on_change_with_unit_digits(self, name=None):
        if self.uom:
            return self.uom.digits
        return 2

    @fields.depends('product', 'warehouse', 'from_location')
    def on_change_with_quantity(self, name=None):
        if self.product and self.warehouse and self.from_location:
            self.update_quantity()
            return self.quantity or 0
        return 0

    @classmethod
    def _get_move(cls, relocation):
        pool = Pool()
        Date = pool.get('ir.date')
        Move = pool.get('stock.move')

        move = Move()
        move.product = relocation.product
        for k, v in move.on_change_product().iteritems():
            setattr(move, k, v)
        move.uom = relocation.uom
        move.quantity = relocation.quantity
        move.from_location = relocation.from_location
        move.to_location = relocation.to_location
        move.state = Move.default_state()
        move.effective_date = Date.today()
        move.planned_date = relocation.planned_date
        move.company = relocation.company
        move.origin = relocation
        move.cost_price = relocation.product.cost_price
        move.unit_price = relocation.product.list_price
        return move

    @classmethod
    @ModelView.button
    def confirm(cls, relocations):
        pool = Pool()
        Date = pool.get('ir.date')
        Product = pool.get('product.product')
        Move = pool.get('stock.move')

        today = Date.today()
        location_ids = set()
        products_ids = set()

        for r in relocations:
            location_ids.add(r.from_location.id)
            products_ids.add(r.product.id)
            
        with Transaction().set_context(forecast=False, stock_date_end=today):
            pbl = Product.products_by_location(list(location_ids),
                list(products_ids), grouping=('product',))

        to_create = []
        for r in relocations:
            from_location = r.from_location
            product = r.product

            qty = pbl.get((from_location.id, product.id), 0)
            if qty == 0:
                continue
            del pbl[(from_location.id, product.id)] # remove pbl by key

            if r.quantity > qty:
                cls.raise_user_warning('stock_relocation%s.confirm' % r.id,
                    'quantity_by_location', (
                    qty,
                    product.rec_name,
                    r.quantity,
                    ))
            move = cls._get_move(r)
            to_create.append(move)

        if to_create:
            moves = Move.create([c._save_values for c in to_create])
            Move.do(moves)

            to_write = []
            for move in moves:
                to_write.extend(([move.origin], {
                            'move': move,
                            'state': 'done'
                            }))
            if to_write:
                cls.write(*to_write)
