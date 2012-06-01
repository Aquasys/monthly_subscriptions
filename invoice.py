from osv import fields, osv, orm
from datetime import date
import date_helper

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    def send_mail(self, cr, uid, context=None):
        today = date.today()

        #We send the invoices the 15
        #TODO SWITCH BACK TO 15
        renewal_day = 30
        
        if today.day == renewal_day:
            #we only want the invoice with subscriptions where date due = end of this month
            query = """
                    SELECT DISTINCT(account_invoice.id) 
                    FROM account_invoice, account_invoice_line, product_product
                    WHERE account_invoice.id = account_invoice_line.invoice_id
                    AND account_invoice_line.name = product_product.name_template
                    AND product_product.subscription is True
                    AND account_invoice.date_due = date '%s';
                    """  % date_helper.get_last_day_month(today)

            cr.execute(query)
            invoice_ids = [x[0] for x in cr.fetchall()]
        	
            if invoice_ids:
                invoice_object = self.pool.get('account.invoice')
                invoices = invoice_object.browse(cr, uid, invoice_ids)
                for invoice in invoices:
                    invoice.edi_export_and_email(template_ext_id='account.email_template_edi_invoice', context=context)
    
    
    def button_reset_taxes(self, cr, uid, ids, context=None):
        super(account_invoice, self).button_reset_taxes(cr, uid, ids, context)

        self.send_mail(cr, uid, context)

        return True
    