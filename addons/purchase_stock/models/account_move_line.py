# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.float_utils import float_is_zero
from collections import defaultdict


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_valued_in_moves(self):
        self.ensure_one()
        return self.purchase_line_id.move_ids.filtered(lambda m: m.is_in)

    def _get_out_and_not_invoiced_qty(self, in_moves):
        self.ensure_one()
        if not in_moves:
            return 0
        aml_qty = self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
        invoiced_qty = sum(line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id)
                           for line in self.purchase_line_id.invoice_lines - self)
        layers = in_moves.stock_valuation_layer_ids
        layers_qty = sum(layers.mapped('quantity'))
        out_qty = layers_qty - sum(layers.mapped('remaining_qty'))
        total_out_and_not_invoiced_qty = max(0, out_qty - invoiced_qty)
        out_and_not_invoiced_qty = min(aml_qty, total_out_and_not_invoiced_qty)
        return self.product_id.uom_id._compute_quantity(out_and_not_invoiced_qty, self.product_uom_id)

    def _get_price_unit_val_dif_and_relevant_qty(self):
        self.ensure_one()
        # Retrieve stock valuation moves.
        valuation_stock_moves = self.env['stock.move'].search([
            ('purchase_line_id', '=', self.purchase_line_id.id),
            ('state', '=', 'done'),
            ('product_qty', '!=', 0.0),
        ]) if self.purchase_line_id else self.env['stock.move']

        if self.product_id.cost_method != 'standard' and self.purchase_line_id:
            if self.move_type == 'in_refund':
                valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_out())
            else:
                valuation_stock_moves = valuation_stock_moves.filtered(lambda stock_move: stock_move._is_in())

            if not valuation_stock_moves:
                return 0, 0

            valuation_price_unit_total, valuation_total_qty = valuation_stock_moves._get_valuation_price_and_qty(self, self.move_id.currency_id)
            valuation_price_unit = valuation_price_unit_total / valuation_total_qty
            valuation_price_unit = self.product_id.uom_id._compute_price(valuation_price_unit, self.product_uom_id)
        else:
            # Valuation_price unit is always expressed in invoice currency, so that it can always be computed with the good rate
            price_unit = self.product_id.uom_id._compute_price(self.product_id.standard_price, self.product_uom_id)
            price_unit = -price_unit if self.move_id.move_type == 'in_refund' else price_unit
            valuation_date = (valuation_stock_moves and max(valuation_stock_moves.mapped('date'))) or self.date
            valuation_price_unit = self.company_currency_id._convert(
                price_unit, self.currency_id,
                self.company_id, valuation_date, round=False
            )

        price_unit = self._get_gross_unit_price()

        price_unit_val_dif = price_unit - valuation_price_unit
        # If there are some valued moves, we only consider their quantity already used
        if self.product_id.cost_method == 'standard':
            relevant_qty = self.quantity
        else:
            relevant_qty = self._get_out_and_not_invoiced_qty(valuation_stock_moves)

        return price_unit_val_dif, relevant_qty
