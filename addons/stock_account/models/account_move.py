from odoo import fields, models, api
from odoo.tools import float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # OVERRIDE METHODS
    # -------------------------------------------------------------------------

    def _get_lines_onchange_currency(self):
        # OVERRIDE
        return self.line_ids.filtered(lambda l: l.display_type != 'cogs')

    def copy_data(self, default=None):
        # Don't keep anglo-saxon lines when copying a journal entry.
        vals_list = super().copy_data(default=default)

        if not self._context.get('move_reverse_cancel'):
            for vals in vals_list:
                if 'line_ids' in vals:
                    vals['line_ids'] = [line_vals for line_vals in vals['line_ids']
                                             if line_vals[0] != 0 or line_vals[2].get('display_type') != 'cogs']
        return vals_list

    def _post(self, soft=True):
        # OVERRIDE

        # Don't change anything on moves used to cancel another ones.
        if self._context.get('move_reverse_cancel'):
            return super()._post(soft)

        # Create additional COGS lines for customer invoices.
        # self.env['account.move.line'].create(self._stock_account_prepare_anglo_saxon_out_lines_vals())

        # Post entries.
        posted = super()._post(soft)

        # Reconcile COGS lines in case of anglo-saxon accounting with perpetual valuation.
        if not self.env.context.get('skip_cogs_reconciliation'):
            posted._stock_account_anglo_saxon_reconcile_valuation()
        return posted

    def button_draft(self):
        res = super().button_draft()

        # Unlink the COGS lines generated during the 'post' method.
        self.mapped('line_ids').filtered(lambda line: line.display_type == 'cogs').unlink()
        return res

    def button_cancel(self):
        # OVERRIDE
        res = super().button_cancel()

        # Unlink the COGS lines generated during the 'post' method.
        # In most cases it shouldn't be necessary since they should be unlinked with 'button_draft'.
        # However, since it can be called in RPC, better be safe.
        self.mapped('line_ids').filtered(lambda line: line.display_type == 'cogs').unlink()
        return res

    # -------------------------------------------------------------------------
    # COGS METHODS
    # -------------------------------------------------------------------------


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    cogs_origin_id = fields.Many2one(  # technical field used to keep track in the originating line of the anglo-saxon lines
        comodel_name="account.move.line",
        copy=False,
        index="btree_not_null",
    )

    def _compute_account_id(self):
        super()._compute_account_id()
        for line in self:
            if not line.move_id.is_purchase_document():
                continue
            if not line.product_id.is_storable:
                continue
            # Periodic with expense account
            if line.product_id.valuation == 'periodic' and not line.move_id.company_id.anglo_saxon_accounting:
                continue
            fiscal_position = line.move_id.fiscal_position_id
            accounts = line.with_company(line.company_id).product_id.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)

            if line.product_id.valuation == 'real_time' and accounts['stock_valuation']:
                line.account_id = accounts['stock_valuation']
            if line.company_id.anglo_saxon_accounting and accounts['stock_variation']:
                line.account_id = accounts['stock_variation']

    def _eligible_for_cogs(self):
        self.ensure_one()
        return self.product_id.is_storable and self.company_id.anglo_saxon_accounting

    def _get_gross_unit_price(self):
        if self.product_uom_id.is_zero(self.quantity):
            return self.price_unit

        if self.discount != 100:
            if not any(t.price_include for t in self.tax_ids) and self.discount:
                price_unit = self.price_unit * (1 - self.discount / 100)
            else:
                price_unit = self.price_subtotal / self.quantity
        else:
            price_unit = self.price_unit

        return -price_unit if self.move_id.move_type == 'in_refund' else price_unit

    def _get_stock_valuation_layers(self, move):
        valued_moves = self._get_valued_in_moves()
        if move.move_type == 'in_refund':
            valued_moves = valued_moves.filtered(lambda stock_move: stock_move._is_out())
        else:
            valued_moves = valued_moves.filtered(lambda stock_move: stock_move._is_in())
        return valued_moves.stock_valuation_layer_ids

    def _get_valued_in_moves(self):
        return self.env['stock.move']

    def _stock_account_get_anglo_saxon_price_unit(self):
        self.ensure_one()
        if not self.product_id:
            return self.price_unit
        original_line = self.move_id.reversed_entry_id.line_ids.filtered(
            lambda l: l.display_type == 'cogs' and l.product_id == self.product_id and
            l.product_uom_id == self.product_uom_id and l.price_unit >= 0)
        original_line = original_line and original_line[0]
        return original_line.price_unit if original_line \
            else self.product_id.with_company(self.company_id)._stock_account_get_anglo_saxon_price_unit(uom=self.product_uom_id)

    @api.onchange('product_id')
    def _inverse_product_id(self):
        super(AccountMoveLine, self.filtered(lambda l: l.display_type != 'cogs'))._inverse_product_id()

    def _get_exchange_journal(self, company):
        if (
            self and self.move_id.sudo().stock_valuation_layer_ids and
            self.product_id.categ_id.property_valuation == 'real_time'
        ):
            return self.product_id.categ_id.property_stock_journal
        return super()._get_exchange_journal(company)

    def _get_exchange_account(self, company, amount):
        if (
            self and self.move_id.sudo().stock_valuation_layer_ids and
            self.product_id.categ_id.property_valuation == 'real_time'
        ):
            return self.product_id.categ_id.property_stock_valuation_account_id
        return super()._get_exchange_account(company, amount)
