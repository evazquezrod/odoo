from odoo import Command

from odoo.addons.l10n_es_edi_verifactu.tests.common import TestL10nEsEdiVerifactuCommon
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


class TestL10nEsEdiVerifactuPosCommon(TestL10nEsEdiVerifactuCommon, TestPoSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
<<<<<<< HEAD
<<<<<<< HEAD
        cls.config = cls.basic_config
=======
        cls.config = cls.main_pos_config
>>>>>>> b9e2768527ab88739b0032dafc28c377ab56b006
=======
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c

        cls.product = cls.env['product.product'].create({
            'name': 'verifactu_pos_product',
            'default_code': "product_verifactu",
            'lst_price': 100.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [Command.set(cls.tax21_goods.ids)],
            'company_id': cls.company.id,
            'available_in_pos': True,
        })
