import { FormCogMenu } from "@web/views/form/form_cog_menu/form_cog_menu";

export class TaskFormCogMenu extends FormCogMenu {
    async _registryItems() {
        console.log("mmmm",super._registryItems())
        return [];
    }
}
