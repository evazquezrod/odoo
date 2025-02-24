import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { simpleTags } from "@web/core/utils/html";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("point_of_sale_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            isActive: ["community"],
            trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
            content: _t("Ready to launch your %(b_open)spoint of sale%(b_close)s?", simpleTags),
            tooltipPosition: "right",
            run: "click",
        },
        {
            isActive: ["enterprise"],
            trigger: '.o_app[data-menu-xmlid="point_of_sale.menu_point_root"]',
            content: _t("Ready to launch your %(b_open)spoint of sale%(b_close)s?", simpleTags),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_pos_kanban",
            tooltipPosition: "bottom",
            run: "click",
        },
    ],
});
