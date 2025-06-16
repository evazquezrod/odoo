from contextlib import contextmanager

from odoo import Command
from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesDispatchingBaseLines(TestTaxCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.currency = cls.env.company.currency_id
        cls.foreign_currency = cls.setup_other_currency('EUR')

    def test_taxes_l10n_be(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        AccountTax = self.env['account.tax']
        tax1 = self.fixed_tax(1, include_base_amount=True)
        tax2 = self.percent_tax(21)
        taxes = tax1 + tax2

        document_params = self.init_document(
            lines=[
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': 10, 'tax_ids': taxes},
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': 10, 'tax_ids': taxes},
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': -12, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=0.5,
        )
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.foreign_currency.id,
            'company_currency_id': self.currency.id,
            'base_amount_currency': 134.32,
            'base_amount': 268.64,
            'tax_amount_currency': 37.89,
            'tax_amount': 75.77,
            'total_amount_currency': 172.21,
            'total_amount': 344.41,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 134.32,
                    'base_amount': 268.64,
                    'tax_amount_currency': 37.89,
                    'tax_amount': 75.77,
                    'tax_groups': [
                        {
                            'id': taxes.tax_group_id.id,
                            'base_amount_currency': 134.32,
                            'base_amount': 268.64,
                            'tax_amount_currency': 37.89,
                            'tax_amount': 75.77,
                            'display_base_amount_currency': 134.32,
                            'display_base_amount': 268.64,
                        },
                    ],
                },
            ],
        }
        document = self.populate_document(document_params)
        base_lines = document['lines']
        tax_totals = AccountTax._get_tax_totals_summary(base_lines, document['currency'], self.env.company)
        self._assert_tax_totals_summary(tax_totals, expected_values)

        # Dispatch the return of product on the others base lines.
        self.assertEqual(len(base_lines), 3)
        base_lines = AccountTax._dispatch_return_of_marchandise_lines(document['lines'], self.env.company)
        AccountTax._squash_return_of_marchandise_lines(base_lines, self.env.company)
        self.assertEqual(len(base_lines), 2)
        self.assertEqual(base_lines[0]['quantity'], 0)
        self.assertEqual(base_lines[1]['quantity'], 8)
        tax_totals = AccountTax._get_tax_totals_summary(base_lines, document['currency'], self.env.company)
        self._assert_tax_totals_summary(tax_totals, expected_values)

        # Global discount 20%.
        discount_base_lines = AccountTax._prepare_global_discount_lines(base_lines, self.env.company, 'percent', 20.0)
        base_lines += discount_base_lines
        AccountTax._add_tax_details_in_base_lines(base_lines, self.env.company)
        AccountTax._round_base_lines_tax_details(base_lines, self.env.company)
        tax_totals = AccountTax._get_tax_totals_summary(base_lines, document['currency'], self.env.company)
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.foreign_currency.id,
            'company_currency_id': self.currency.id,
            'base_amount_currency': 107.45,
            'base_amount': 214.9,
            'tax_amount_currency': 32.25,
            'tax_amount': 64.49,
            'total_amount_currency': 139.7,
            'total_amount': 279.39,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 107.45,
                    'base_amount': 214.9,
                    'tax_amount_currency': 32.25,
                    'tax_amount': 64.49,
                    'tax_groups': [
                        {
                            'id': taxes.tax_group_id.id,
                            'base_amount_currency': 107.45,
                            'base_amount': 214.9,
                            'tax_amount_currency': 32.25,
                            'tax_amount': 64.49,
                            'display_base_amount_currency': 107.45,
                            'display_base_amount': 214.9,
                        },
                    ],
                },
            ],
        }
        self._assert_tax_totals_summary(tax_totals, expected_values)

        # Dispatch the global discount on the others base lines.
        self.assertEqual(len(base_lines), 3)
        base_lines = AccountTax._dispatch_global_discount_lines(base_lines, self.env.company)
        AccountTax._squash_global_discount_lines(base_lines, self.env.company)
        self.assertEqual(len(base_lines), 2)
        self.assertEqual(base_lines[0]['raw_gross_total_excluded_currency'], 0.0)
        self.assertEqual(base_lines[0]['raw_discount_amount_currency'], 0.0)
        self.assertEqual(base_lines[1]['raw_gross_total_excluded_currency'], 134.32)
        self.assertAlmostEqual(base_lines[1]['raw_discount_amount_currency'], 26.873999999999995)
        tax_totals = AccountTax._get_tax_totals_summary(base_lines, document['currency'], self.env.company)
        self._assert_tax_totals_summary(tax_totals, expected_values)
