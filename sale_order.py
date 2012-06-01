from osv import fields, osv
from datetime import date

import date_helper
import netsvc

class sale_order(osv.osv):
    _inherit = "sale.order"


    def renew_subscriptions(self, cr, uid, context=None):
        """
        Called by cron
        Renew all the subscriptions with auto-renewal by generating sales order
        """
        today = date.today()

        #We renew all our subscriptions on the 14th
        #TODO SWITCH BACK TO 14
        renewal_day = 1

        if today.day == renewal_day:
            sale_order_object = self.pool.get('sale.order')

            #Gets the id of sales order where there are subscriptions with auto
            # where end_date == end of this month and invoice wasn't generated already
            query = """
                    SELECT DISTINCT(sale_order.id)
                    FROM sale_order, sale_order_line
                    WHERE 
                    sale_order.id = sale_order_line.order_id
                    AND sale_order_line.subscription_start_date IS NOT NULL
                    AND sale_order_line.subscription_end_date = date '%s'
                    AND sale_order.state != 'progress'
                    AND sale_order_line.subscription_renewal IS true
                    """  % date_helper.get_last_day_month(today)

            cr.execute(query);

            sale_order_ids = [x[0] for x in cr.fetchall()]
            
            if sale_order_ids:
                #Gets all the sale orders objects
                sale_orders = sale_order_object.browse(cr, uid, sale_order_ids)
                
                sale_order_line_object = self.pool.get('sale.order.line')

                sale_order_line_ids = sale_order_line_object.search(cr, uid, 
                    ['&',('order_id','in',sale_order_ids), ('subscription_renewal','=',True)])
                sale_order_lines = sale_order_line_object.browse(cr, uid, sale_order_line_ids)

                #now we can invoice and renew these sale orders
                for sale_order in sale_orders:
                    #Getting the lines related to this sale order
                    related_lines = [line for line in sale_order_lines if line.order_id.id == sale_order.id]

                    #need to set the states of order lines to confirmed
                    #otherwise, no invoices will be generated
                    for line in related_lines:
                        prorated_price = self.calculate_prorated_price(line)

                        sale_order_line_object.write(cr, uid, line.id, 
                            {'state' : 'confirmed', 'price_unit' : prorated_price})

                    #First we generate the invoice (calculating pro-rata)
                    #Creates the invoices in a draft state
                    new_invoice_id = self.action_invoice_create(cr, uid, [sale_order.id])

                    if new_invoice_id:
                        #Calling the workflow action opening an invoice
                        wf_service = netsvc.LocalService("workflow")
                        wf_service.trg_validate(uid, 'account.invoice', new_invoice_id, 'invoice_open', cr)

                        invoice_object = self.pool.get('account.invoice')
                        today = date.today()
                        date_due = date_helper.get_last_day_month(today)
                        invoice_object.write(cr, uid, new_invoice_id, {'date_due' : date_due})
                    

                    #Now we're renewing the one we can
                    print 'creating a new sales order'
                    self.create_new_sale_order(cr, uid, sale_order, related_lines)


            else:
                return False

        else:
            return False


    def create_new_sale_order(self, cr, uid, order, lines):
        """
        Gets all the data and create a sale order with subscriptions 
        """

        order_data = {
            'partner_id': order.partner_id.id,
            'partner_invoice_id': order.partner_invoice_id.id,
            'partner_order_id': order.partner_order_id.id,
            'partner_shipping_id': order.partner_shipping_id.id,
            'shop_id': order.shop_id.id,
            'client_order_ref': order.client_order_ref,
            'incoterm': order.incoterm.id,
            'picking_policy': order.picking_policy,
            'order_policy': order.order_policy,
            'pricelist_id': order.pricelist_id.id,
            'project_id': order.project_id.id,
            'note': order.note,
            'invoice_quantity': order.invoice_quantity,
            'payment_term': order.payment_term.id,
            'fiscal_position': order.fiscal_position.id,
            'order_line': [],
            'origin' : order.name,
            'state': 'manual',
            }

        today = date.today()
        subscription_start_date = date_helper.get_first_day_next_month(today)
        subscription_end_date = date_helper.get_last_day_month(subscription_start_date)

        for line in lines:
            line_data = {
                'name': line.name,
                'delay': line.delay,
                'product_id': line.product_id.id,
                'price_unit': line.price_unit,
                'tax_id': line.tax_id,
                'type': line.type,
                'address_allotment_id': line.address_allotment_id.id,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_uom.id,
                'product_uos_qty': line.product_uos_qty,
                'product_uos': line.product_uos.id,
                'product_packaging': line.product_packaging.id,
                'notes': line.notes,
                'discount': line.discount,
                'subscription_end_date': subscription_end_date,
                'subscription_start_date': subscription_start_date,
            }
            order_data['order_line'].append((0, 0, line_data))

        sale_order_object = self.pool.get('sale.order')
        new_order_id = sale_order_object.create(cr, uid, order_data)


    def calculate_prorated_price(self, line):
        """
        Calculate line price using prorata
        """
        start_date = date_helper.convert_to_date(line.subscription_start_date)
        end_date = date_helper.convert_to_date(line.subscription_end_date)
        
        #First case -> same month
        if start_date.month == end_date.month:
            last_day = date_helper.get_last_day_month(end_date)

            #Normal case : 1 to end of month
            if start_date.day == 1 :
                if end_date.day == last_day.day:
                    return line.price_unit
                #TODO : pay less if cancelled < 1 month ?
                else:
                    return line.price_unit
            else:
                #We should never be there
                return line.price_unit

        #Second case -> more than 1 month
        else:
            difference = (end_date - start_date).days
            #If its more than 1 month of difference, we modify the price
            if difference > 31:
                pro_rated_days = difference - 31
                pro_rated_price = line.price_unit / 31
                total = line.price_unit + round(pro_rated_price * pro_rated_days)
                return total
            else:
                return line.price_unit

        return line.price_unit


    def action_wait(self, cr, uid, ids, *args):
        """
        Called when pressing Confirm Order in a sale order
        Add creation of a new sale order automatically to a cron
        """
        super(sale_order, self).action_wait(cr, uid, ids, *args)

        self.renew_subscriptions(cr, uid)

        return True