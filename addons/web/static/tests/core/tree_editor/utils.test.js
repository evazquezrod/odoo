import { describe, expect, test } from "@odoo/hoot";

import { defineModels, getService, makeMockEnv } from "@web/../tests/web_test_helpers";
import {
    Country,
    Partner,
    Player,
    Product,
    Stage,
    Team,
} from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";

import { condition } from "@web/core/tree_editor/condition_tree";
import { useMakeGetConditionDescription, useMakeGetFieldDef } from "@web/core/tree_editor/utils";

describe.current.tags("headless");

defineModels([Partner, Product, Country, Stage, Team, Player]);

test.debug("useMakeGetConditionDescription", async () => {
    await makeMockEnv();
    const makeGetFieldDef = useMakeGetFieldDef(getService("field"));
    const makeGetConditionDescription = await useMakeGetConditionDescription(
        getService("field"),
        getService("name")
    );

    const toTest = [
        {
            tree: condition("id", "in", []),
            description: {
                operatorDescription: "=",
                pathDescription: "0",
                valueDescription: {
                    addParenthesis: false,
                    join: "or",
                    values: [1],
                },
            },
        },
    ];

    for (const { tree, description } of toTest) {
        const getFieldDef = await makeGetFieldDef("partner", tree);
        const getConditionDescription = await makeGetConditionDescription(
            "partner",
            tree,
            getFieldDef
        );
        expect(getConditionDescription(tree)).toEqual(description);
    }
});
