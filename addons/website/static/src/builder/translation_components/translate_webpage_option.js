import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart, useState } from "@odoo/owl";

export class TranslateWebpageOption extends BaseOptionComponent {
    static template = "website.TranslateWebpageOption";
    static props = {
        getTranslationState: Function,
    };

    setup() {
        super.setup();
        this.state = useState({
            language: "",
        });
        this.translationState = useState(this.props.getTranslationState());
        onWillStart(() => {
            this.state.language = this.env.services.website.currentWebsite.metadata.langName;
        });
    }
}
