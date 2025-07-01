from odoo import api, models


class StockValuationReport(models.AbstractModel):
    _name = 'stock_account.stock.valuation.report'
    _description = 'Stock Valuation'

    @api.model
    def get_report_values(self):
        report_values = {
            'data': self._get_report_data(),
            'context': self._get_report_context(),
        }
        return report_values

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = []
        doc = self._get_report_data()
        docs.append(self._include_pdf_specifics(doc, data))
        report_values = {
            'doc_ids': docids,
            'doc_model': 'mrp.production',
            'docs': docs,
        }
        return report_values

    def _get_report_context(self):
        # TODO: set default warehouse ? Default category ?
        return {}

    def _get_report_data(self, product_category=False, warehouse=False):
        stock_initial = 3000 # TODO: to compute correctly.
        inventory_valuation_data = self._compute_inventory_valuation(product_category)
        accounting_stock_valuation = inventory_valuation_data['total']

        # # - Goods Delivered Not Invoiced: total of delivered SO not invoiced yet:
        # #   - An entry by SO;
        # #   - TOTAL
        # data['delivered_not_invoiced'] = {
        #     'lines': [
        #         {'name': "SO00051", 'value': 1000},
        #         {'name': "SO00065", 'value': 2000},
        #     ],
        #     'total': 3000,
        # }
        # # - Work In Progress: total of the ongoing MO:
        # #   - An entry by MO;
        # #   - TOTAL
        # data['work_in_progress'] = {
        #     'lines': [
        #         {'name': "MO00051", 'value': 500},
        #     ],
        #     'total': 500,
        # }

        # - Accounting Stock Valuation
        # accounting_stock_valuation = data['inventory_valuation']['total'] + data['delivered_not_invoiced']['total'] + data['work_in_progress']['total']
        accounting_stock_valuation = inventory_valuation_data['total']

        data = {
            'currency_id': self.env.company.currency_id.id,
            'accounting_stock_valuation': accounting_stock_valuation,
            'inventory_valuation': inventory_valuation_data,
            'stock_initial': stock_initial,
            'stock_variation': accounting_stock_valuation - stock_initial,
        }
        return data

    def _compute_inventory_valuation(self, product_category):
        """ Compute inventory valuation, product by product."""
        domain = []
        if product_category:
            domain = [('categ_id', '=', product_category.id)]
        products = self.env['product.product'].search(domain)
        valuation_lines = []
        total = 0
        for product in products:
            if not product.total_value:
                continue
            valuation_lines.append({
                'id': product.id,
                'display_name': product.display_name,
                'name': product.name,
                'total_value': product.total_value
            })
            total += product.total_value
        return {
            'lines': valuation_lines,
            'total': total,
        }