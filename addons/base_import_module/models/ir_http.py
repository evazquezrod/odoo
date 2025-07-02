# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import logging

from odoo import api, models
from odoo.tools import ormcache
from odoo.tools.translate import CodeTranslations, get_base_langs, JAVASCRIPT_TRANSLATION_COMMENT

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @api.model
    @ormcache('module', 'lang')
    def _get_imported_module_trasnlations_for_webclient(self, module, lang):
        if not lang:
            lang = self.env.context.get("lang") or 'en_US'
        IrAttachment = self.env['ir.attachment']

        def filter_func(row):
            return row.get('value') and JAVASCRIPT_TRANSLATION_COMMENT in row['comments']

        translations = {}
        for lang_ in get_base_langs(lang):
            attachment = IrAttachment.sudo().search([
                    ('name', '=', f"{module}_{lang_}.po"),
                    ('url', '=', f"/{module}/i18n/{lang_}.po"),
                    ('type', '=', 'binary'),
                ], limit=1)
            if attachment.raw:
                try:
                    with io.BytesIO(attachment.raw) as fileobj:
                        fileobj.name = attachment.name
                        webclient_translations = CodeTranslations._read_code_translations_file(fileobj, filter_func)
                        translations.update(webclient_translations)
                except Exception:  # noqa: BLE001
                    _logger.warning('module %s: failed to load translation attachment %s for language %s', module, attachment.name, lang)

        return {
            'messages': tuple({
                'id': src,
                'string': value,
            } for src, value in translations.items())
        }

    @api.model
    def get_translations_for_webclient(self, modules, lang):
        all_imported_modules = self.env['ir.module.module']._get_imported_module_names()
        if not modules:
            non_imported_modules = []
            imported_modules = all_imported_modules
        else:
            non_imported_modules = [m for m in modules if m not in all_imported_modules] or ['__dummy__']
            imported_modules = [m for m in modules if m in all_imported_modules]

        translations_per_module, lang_params = super().get_translations_for_webclient(non_imported_modules, lang)
        for module in imported_modules:
            translations_per_module[module] = self._get_imported_module_trasnlations_for_webclient(module, lang)
        return translations_per_module, lang_params
