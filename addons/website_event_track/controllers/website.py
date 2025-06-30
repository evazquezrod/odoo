from odoo.addons.website.controllers.main import Website


class WebsiteEventTrack(Website):
    def _get_robots_directives(self):
        config = super()._get_robots_directives()

        disallow_patterns = [
            '/event/*/track?*tags=*',
        ]

        config.setdefault('*', {}).setdefault('disallow', []).extend(disallow_patterns)

        return config
