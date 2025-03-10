import { registry } from "@web/core/registry";

export function goBack(env, action) {
    return env.services.action.restore();
}

registry.category("actions").add("go_back", goBack);
