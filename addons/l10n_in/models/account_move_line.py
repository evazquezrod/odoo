import re

from odoo import _, api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_in_hsn_code = fields.Char(string="HSN/SAC Code", compute="_compute_l10n_in_hsn_code", store=True, readonly=False, copy=False)
    l10n_in_gstr_section = fields.Selection(
        selection=[
            ("purchase_b2b", "P B2B"),
            ("purchase_b2c", "P B2C"),
            ("purchase_imp_services", "P IMP(service)"),
            ("purchase_imp_goods", "P IMP(goods)"),
            ("purchase_cdnr", "P CDNR"),
            ("purchase_cdnur", "P CDNUR"),
            ("purchase_nil_rated", "P Nil Rated"),
            ("purchase_out_of_scope", "P Out of Scope"),
            ],
        string="GSTR Section",
        compute="_compute_l10n_in_gstr_section",
        store=True,
        index=True,
        readonly=False,
    )

    # withholding related fields
    l10n_in_withhold_tax_amount = fields.Monetary(string="TDS Tax Amount", compute='_compute_l10n_in_withhold_tax_amount')
    l10n_in_tds_tcs_section_id = fields.Many2one(related="account_id.l10n_in_tds_tcs_section_id")

    @api.depends('tax_ids')
    def _compute_l10n_in_withhold_tax_amount(self):
        # Compute the withhold tax amount for the withholding lines
        withholding_lines = self.filtered('move_id.l10n_in_is_withholding')
        (self - withholding_lines).l10n_in_withhold_tax_amount = False
        for line in withholding_lines:
            line.l10n_in_withhold_tax_amount = line.currency_id.round(abs(line.price_total - line.price_subtotal))

    @api.depends('product_id', 'product_id.l10n_in_hsn_code')
    def _compute_l10n_in_hsn_code(self):
        for line in self:
            if line.move_id.country_code == 'IN' and line.parent_state == 'draft':
                line.l10n_in_hsn_code = line.product_id.l10n_in_hsn_code

    def _l10n_in_check_invalid_hsn_code(self):
        self.ensure_one()
        hsn_code = self.env['account.move']._l10n_in_extract_digits(self.l10n_in_hsn_code)
        if not hsn_code:
            return _("HSN code is not set in product line %(name)s", name=self.name)
        elif not re.match(r'^\d{4}$|^\d{6}$|^\d{8}$', hsn_code):
            return _(
                "Invalid HSN Code (%(hsn_code)s) in product line %(product_line)s",
                hsn_code=hsn_code,
                product_line=self.product_id.name or self.name
            )
        return False

    def get_l10n_in_tax_tag_ids(self):

        def get_tag_ids(*refs):
            return [self.env.ref(ref).id for ref in refs]

        return {
            'gst_rc': get_tag_ids(
                'l10n_in.tax_tag_base_sgst_rc', 'l10n_in.tax_tag_sgst_rc',
                'l10n_in.tax_tag_base_cgst_rc', 'l10n_in.tax_tag_cgst_rc',
                'l10n_in.tax_tag_base_igst_rc', 'l10n_in.tax_tag_igst_rc',
                'l10n_in.tax_tag_base_cess_rc', 'l10n_in.tax_tag_cess_rc'
            ),
            'gst': get_tag_ids(
                'l10n_in.tax_tag_base_sgst', 'l10n_in.tax_tag_sgst',
                'l10n_in.tax_tag_base_cgst', 'l10n_in.tax_tag_cgst',
                'l10n_in.tax_tag_base_igst', 'l10n_in.tax_tag_igst',
                'l10n_in.tax_tag_base_cess', 'l10n_in.tax_tag_cess'
            ),
            'nil': get_tag_ids(
                'l10n_in.tax_tag_exempt', 'l10n_in.tax_tag_nil_rated', 'l10n_in.tax_tag_non_gst_supplies'
            ),
            'export': get_tag_ids(
                'l10n_in.tax_tag_base_igst', 'l10n_in.tax_tag_igst',
                'l10n_in.tax_tag_base_cess', 'l10n_in.tax_tag_cess'
            ),
            'igst_lut': get_tag_ids(
                'l10n_in.tax_tag_base_igst_lut', 'l10n_in.tax_tag_zero_rated'
            ),
        }

    @api.depends('move_id.l10n_in_gst_treatment', 'move_id.amount_total', 'move_id.l10n_in_state_id', 'move_id.reversed_entry_id', 'company_id', 'tax_tag_ids')
    def _compute_l10n_in_gstr_section(self):

        def tags_have_categ(tax_tags, categories):
            return  any(tag in tax_tags for category in categories for tag in tax_tags_ids[category])

        def is_move_bill(move):
            return move.is_outbound() and not move.debit_origin_id

        def get_section(line):
            move = line.move_id
            gst_treatment = move.l10n_in_gst_treatment
            tags = line.tax_tag_ids.ids
            is_bill = is_move_bill(move)

            # Nil rated purchases
            if gst_treatment != 'overseas' and tags_have_categ(tags, ['nil']):
                return 'purchase_nil_rated'

            if is_bill:
                # B2B: Registered purchases
                if gst_treatment in ('regular', 'composition', 'uin_holders') and tags_have_categ(tags, ['gst','gst_rc']):
                    return 'purchase_b2b'

                if gst_treatment == 'special_economic_zone' and tags_have_categ(tags, ['export', 'igst_lut']):
                    return 'purchase_b2b'

                # B2C: Unregistered or Consumer sales with gst tags
                if gst_treatment in ('unregistered', 'consumer') and tags_have_categ(tags, 'gst'):
                    return 'purchase_b2c'

                # export service type products purchases
                if line.product_id.type == 'service' and gst_treatment == 'overseas' and tags_have_categ(tags, ['export','igst_lut']):
                    return 'purchase_imp_services'

                # export goods type products purchases
                if line.product_id.type == 'consu' and gst_treatment == 'overseas' and tags_have_categ(tags, ['export','igst_lut']):
                    return 'purchase_imp_goods'

            if not is_bill:
                # credit notes for b2b purchases
                if gst_treatment in ('regular', 'composition', 'uin_holders') and tags_have_categ(tags, ['gst','gst_rc']):
                    return 'purchase_cdnr'

                if gst_treatment  == 'special_economic_zone' and tags_have_categ(tags, ['export', 'igst_lut']):
                    return 'purchase_cdnr'

                if gst_treatment  == 'deemed_export' and tags_have_categ(tags, ['gst']):
                    return 'purchase_cdnr'

                # credit notes for b2c purchases
                if gst_treatment in ('unregistered', 'consumer') and tags_have_categ(tags, ['gst']):
                    return 'purchase_cdnur'

                if gst_treatment == 'overseas' and tags_have_categ(tags, ['export', 'igst_lut']):
                    return 'purchase_cdnur'

             # If none of the above match, default to out of scope
            return 'purchase_out_of_scope'

        indian_moves_purchase_lines = self.filtered(lambda l: l.move_id.country_code == 'IN' and l.move_id.is_purchase_document(include_receipts=True) and l.parent_state == 'posted')
        (self - indian_moves_purchase_lines).l10n_in_gstr_section = False
        if not indian_moves_purchase_lines:
            return
        tax_tags_ids = self.get_l10n_in_tax_tag_ids()
        for move_line in indian_moves_purchase_lines:
            move_line.l10n_in_gstr_section = get_section(move_line)
