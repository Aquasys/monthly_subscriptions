from osv import fields, osv

class product_product(osv.osv):
    _inherit = "product.product"

    _columns =  {
        'subscription':fields.boolean('Subscription'),
        #'subscription_duration': fields.integer('Subscription Duration', help='Subscription duration'),
        #'subscription_duration_unit': fields.selection((('day','Day'), ('month','Month'), ('year','Year')), 'Subscription Unit', 
        #    help='Unit for the subscription duration'),
    }


    def onchange_subscription(self, cr, uid, ids, subscription):
        values = {}
        if subscription:
            values['type'] = 'service'
            #values['subscription_duration_unit'] = 'day'
        return {'value': values}