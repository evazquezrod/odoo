<<<<<<< HEAD
<<<<<<< HEAD
from odoo import api, fields, models, tools
=======
from odoo import _, api, fields, models
>>>>>>> b9e2768527ab88739b0032dafc28c377ab56b006
=======
from odoo import _, api, fields, models
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_es_applicability = fields.Selection(
        selection=[
<<<<<<< HEAD
<<<<<<< HEAD
            ('iva', 'VAT'),
            ('igic', 'IGIC'),
            ('ipsi', 'IPSI'),
            ('other', 'Other'),
        ],
        string="Applicability (Spain)",
        default='iva',
    )

    @api.model
    @tools.ormcache()
    def _l10n_es_edi_verifactu_get_tax_types_map(self):
        """Return dict: l10n_es_applicability -> verifactu tax type"""
        return {
            'iva': '01',
            'ipsi': '02',
            'igic': '03',
            'other': '05',
        }

    @api.model
    @tools.ormcache()
=======
=======
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
            ('01', "VAT"),
            ('02', "IPSI"),
            ('03', "IGIC"),
        ],
        string="Applicability (Spain)",
    )

    @api.model
<<<<<<< HEAD
>>>>>>> b9e2768527ab88739b0032dafc28c377ab56b006
=======
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
    def _l10n_es_edi_verifactu_get_tax_types_name_map(self):
        """Return dict: verifactu tax type -> human readable string
        """
        # We use the applicability selection strings since every applicability is mapped to a single verifactu tax type
<<<<<<< HEAD
<<<<<<< HEAD
=======
        # No applicability is mapped to '05' / "Other"
>>>>>>> b9e2768527ab88739b0032dafc28c377ab56b006
=======
        # No applicability is mapped to '05' / "Other"
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
        applicability_string = dict(self.env['account.tax']._fields['l10n_es_applicability'].get_description(self.env)['selection'])
        return {
            '01': applicability_string['iva'],
            '02': applicability_string['ipsi'],
            '03': applicability_string['igic'],
<<<<<<< HEAD
<<<<<<< HEAD
            '05': applicability_string['other'],
=======
            '05': _("Other"),
>>>>>>> b9e2768527ab88739b0032dafc28c377ab56b006
=======
            '05': _("Other"),
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
        }

    def _l10n_es_edi_verifactu_filter_main_taxes(self):
        return self.filtered(
            lambda tax: tax.l10n_es_type not in ('retencion', 'recargo', 'dua', 'ignore')
                        and tax.l10n_es_applicability
        )

<<<<<<< HEAD
<<<<<<< HEAD
    def _l10n_es_edi_verifactu_get_verifactu_tax_type(self):
        """
        Return the Veri*Factu Tax Type for the "first" main tax in self
=======
=======
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
    def _l10n_es_edi_verifactu_get_tax_type(self):
        """
        Return the Veri*Factu Tax Type for the "first" main tax in self
        Fallback to '05' ("Other")
<<<<<<< HEAD
>>>>>>> b9e2768527ab88739b0032dafc28c377ab56b006
=======
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
        Note: Currently we only support one Veri*Factu Tax Type for the whole invoice.
        """

        main_taxes = self._l10n_es_edi_verifactu_filter_main_taxes()
<<<<<<< HEAD
<<<<<<< HEAD
        # Main taxes always have a `l10n_es_applicability`
        if not main_taxes:
            return False
        verifactu_tax_type_map = self.env['account.tax']._l10n_es_edi_verifactu_get_tax_types_map()
        return verifactu_tax_type_map.get(main_taxes[0].l10n_es_applicability, False)
=======
=======
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
        if not main_taxes:
            return '05'
        # We fall back to 'Other' tax type in case the field is not set
        return main_taxes[0].l10n_es_applicability or '05'
<<<<<<< HEAD
>>>>>>> b9e2768527ab88739b0032dafc28c377ab56b006
=======
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c

    def _l10n_es_edi_verifactu_get_suggested_clave_regimen(self, special_regime, forced_verifactu_tax_type=None):
        """
        Return a suggested Clave Regimen for the taxes in `self` to be used for the Veri*Factu document.
        Note: Currently we only support one Clave Regimen for a whole Veri*Factu document.
        """
        taxes = self
        if forced_verifactu_tax_type:
            # Remove main taxes with different a Veri*Factu tax type
            taxes = self - self._l10n_es_edi_verifactu_filter_main_taxes().filtered(
<<<<<<< HEAD
<<<<<<< HEAD
                lambda tax: tax._l10n_es_edi_verifactu_get_verifactu_tax_type == forced_verifactu_tax_type
            )

        verifactu_tax_type = forced_verifactu_tax_type or taxes._l10n_es_edi_verifactu_get_verifactu_tax_type()
=======
=======
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
                lambda tax: tax._l10n_es_edi_verifactu_get_tax_type() == forced_verifactu_tax_type
            )

        verifactu_tax_type = forced_verifactu_tax_type or taxes._l10n_es_edi_verifactu_get_tax_type()
<<<<<<< HEAD
>>>>>>> b9e2768527ab88739b0032dafc28c377ab56b006
=======
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
        if not verifactu_tax_type:
            return False

        VAT = verifactu_tax_type == '01'
        IGIC = verifactu_tax_type == '03'
        if not (VAT or IGIC):
            return False

        recargo_taxes = taxes.filtered(lambda tax: tax.l10n_es_type == 'recargo')
        oss_tag = self.env.ref('l10n_eu_oss.tag_oss', raise_if_not_found=False)

        regimen_key = None
<<<<<<< HEAD
<<<<<<< HEAD
        if VAT and special_regime == 'simplified' and self.l10n_es_is_simplified:
            # simplified
            regimen_key = '20_iva'
        elif VAT and special_regime == 'reagyp':
            # REAGYP
            regimen_key = '19_iva'
        elif VAT and recargo_taxes:
            # recargo
            regimen_key = '18_iva'
        elif VAT and oss_tag and oss_tag in taxes.repartition_line_ids.tag_ids:
=======
        if VAT and oss_tag and oss_tag.id in taxes.repartition_line_ids.tag_ids.ids:
>>>>>>> b9e2768527ab88739b0032dafc28c377ab56b006
=======
        if VAT and oss_tag and oss_tag.id in taxes.repartition_line_ids.tag_ids.ids:
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
            # oss
            regimen_key = '17_iva'
        elif taxes.filtered(lambda tax: tax.l10n_es_type == 'exento' and tax.l10n_es_exempt_reason == 'E2'):
            # export
            regimen_key = '02'
<<<<<<< HEAD
<<<<<<< HEAD
=======
=======
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
        elif VAT and recargo_taxes:
            # recargo
            regimen_key = '18_iva'
        elif VAT and special_regime == 'simplified':
            # simplified
            regimen_key = '20_iva'
        elif VAT and special_regime == 'reagyp':
            # REAGYP
            regimen_key = '19_iva'
<<<<<<< HEAD
>>>>>>> b9e2768527ab88739b0032dafc28c377ab56b006
=======
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
        else:
            regimen_key = '01'

        return regimen_key

    @api.model
    def _l10n_es_edi_verifactu_get_tax_details_functions(self, company):
        def full_filter_invl_to_apply(line):
            return any(t != 'ignore' for t in line.tax_ids.flatten_taxes_hierarchy().mapped('l10n_es_type'))

<<<<<<< HEAD
<<<<<<< HEAD
        verifactu_tax_type_map = self._l10n_es_edi_verifactu_get_tax_types_map()

=======
>>>>>>> b9e2768527ab88739b0032dafc28c377ab56b006
=======
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
        def grouping_key_generator(base_line, tax_values):
            tax = tax_values['tax_repartition_line'].tax_id

            l10n_es_exempt_reason = tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False

            # Sujeto taxes with different recargo taxes are kept separate for the output
            # Note: In `_check_record_values` we assert that there is only a single (main tax, recargo tax) pair
            recargo_taxes = self.env['account.tax']
            if tax.l10n_es_type in self.env['account.tax']._l10n_es_get_sujeto_tax_types():
                recargo_taxes = base_line['taxes'].filtered(lambda t: t.l10n_es_type == 'recargo')

            grouping_key = {
                'amount': tax.amount,
                'recargo_taxes': recargo_taxes,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
                'l10n_es_exempt_reason': l10n_es_exempt_reason,
                'l10n_es_type': tax.l10n_es_type,
<<<<<<< HEAD
<<<<<<< HEAD
                'verifactu_tax_type': verifactu_tax_type_map.get(tax.l10n_es_applicability),
=======
                'verifactu_tax_type': tax._l10n_es_edi_verifactu_get_tax_type(),
>>>>>>> b9e2768527ab88739b0032dafc28c377ab56b006
=======
                'verifactu_tax_type': tax._l10n_es_edi_verifactu_get_tax_type(),
>>>>>>> cdd38b7973e8950b4cebf96aa4d0ca15122f1e0c
                'is_main_tax': bool(tax._l10n_es_edi_verifactu_filter_main_taxes()),
            }
            return grouping_key

        def filter_to_apply(base_line, tax_values):
            return (tax_values['tax_repartition_line'].factor_percent > 0.0
                    and tax_values['tax_repartition_line'].tax_id.amount != -100.0
                    and tax_values['tax_repartition_line'].tax_id.l10n_es_type not in ('ignore', 'retencion'))

        return {
            'full_filter_invl_to_apply': full_filter_invl_to_apply,
            'grouping_key_generator': grouping_key_generator,
            'filter_to_apply': filter_to_apply,
        }
