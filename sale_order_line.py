from osv import fields, osv

from datetime import date
from dateutil import parser

import date_helper

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    _columns =  {
        'subscription': fields.related('product_id', 'subscription', 
            type='boolean', string='Subscription'),
        'subscription_start_date':fields.date('Subscription Beginning Date', 
            readonly=True, states={'draft': [('readonly', False)]}),
        'subscription_end_date':fields.date('Subscription Ending Date', 
            readonly=True, states={'draft': [('readonly', False)]}),
        'subscription_renewal':fields.boolean('Auto-renewal'),
    }


    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, 
            fiscal_position=False, flag=False, context=None):
        """
        Called when selecting a product in the sale order line popup
        """
        
        result_dict = super(sale_order_line, self).product_id_change(cr, uid, 
            ids,pricelist, product, qty,uom, qty_uos, uos, name, partner_id,
            lang, update_tax, date_order, packaging, fiscal_position, flag, context)

        if product:
            product = self.pool.get('product.product').browse(cr, uid, product)

            #If it's a subscription, returns today date as start date
            #and start date + duration for end date
            if product.subscription:
                today = date.today()

                #If we're after the 14, the end date should be the last day of the next month
                if today.day > 14:
                    end_date = date_helper.get_last_day_next_month(today)
                else:
                    end_date = date_helper.get_last_day_month(today)

                print end_date

                result_dict['value'].update({
                    'subscription': 1,
                    'subscription_start_date': str(today.strftime("%Y-%m-%d")),
                    'subscription_end_date': str(end_date.strftime("%Y-%m-%d")),
                    'subscription_renewal': True
                    })

            else:
                #Cleaning the data, if we select a normal product after a subscription
                #we don't have the related subscriptions data
               result_dict['value'].update({
                    'subscription': 0,
                    'subscription_start_date': "",
                    'subscription_end_date': "",
                    'subscription_renewal': False
                    }) 

        return result_dict


    def onchange_start_date(self, cr, uid, ids, subscription_start_date):
        """
        Automatically set the subscription end date to the end of the month
        of subscription_start_date
        """
        values = {}
        today = date.today()

        parsed_start_date = date_helper.convert_to_date(subscription_start_date)

        #remove this test
        if subscription_start_date:
            #new_end_date = date_helper.get_last_day_month(parsed_start_date)

            if parsed_start_date.day > 14:
                new_end_date = date_helper.get_last_day_next_month(today)
            else:
                new_end_date = date_helper.get_last_day_month(today)

            values['subscription_end_date'] = str(new_end_date.strftime("%Y-%m-%d"))

        return {'value': values}
