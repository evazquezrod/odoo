import {
    Condition,
    ConditionTree,
    Connector,
    Expression,
    isTree,
    normalizeValue,
    operate,
} from "./condition_tree";

function splitPath(path) {
    const pathParts = typeof path === "string" ? path.split(".") : [];
    const lastPart = pathParts.pop() || "";
    const initialPath = pathParts.join(".");
    return { initialPath, lastPart };
}

function isSimplePath(path) {
    return typeof path === "string" && !splitPath(path).initialPath;
}

/**
 * @param {Connector} tree
 * @param {string} initialPath
 * @param {boolean} negate
 * @returns {Connector|Condition}
 */
function wrapInAny(tree, initialPath, negate) {
    if (initialPath) {
        tree = Condition.of(initialPath, "any", tree.clone());
    }
    tree.negate = negate;
    return tree;
}

function rewriteNConsecutiveChildren(transformation, N = 2) {
    return (c, options) => {
        const children = [];
        const currentChildren = c.children;
        for (let i = 0; i < currentChildren.length; i++) {
            const NconsecutiveChildren = currentChildren.slice(i, i + N);
            let replacement = null;
            if (NconsecutiveChildren.length === N) {
                replacement = transformation(Connector.of(c.value, NconsecutiveChildren), options);
            }
            if (replacement) {
                children.push(replacement);
                i += N - 1;
            } else {
                children.push(NconsecutiveChildren[0]);
            }
        }
        return { ...c, children };
    };
}

/**
 * @param {Condition} c
 * @param {*} options
 * @returns
 */
function _introduceSetOperator(c, options = {}) {
    const { negate, path, operator, value } = c;
    const fieldType = options.getFieldDef?.(path)?.type;
    if (fieldType && typeof operator === "string" && ["=", "!="].includes(operator)) {
        if (fieldType === "boolean" && value === true) {
            return Condition.of(path, operator === "=" ? "set" : "not set", value, negate);
        } else if (!["many2one", "date", "datetime"].includes(fieldType) && value === false) {
            return Condition.of(path, operator === "=" ? "not set" : "set", value, negate);
        }
    }
}

function introduceSetOperators(tree, options = {}) {
    return operate(_introduceSetOperator, tree, options);
}

function _removeSetOperator(c) {
    const { negate, path, operator, value } = c;
    if (["set", "not set"].includes(operator)) {
        if (value === true) {
            return Condition.of(path, operator === "set" ? "=" : "!=", value, negate);
        }
        return Condition.of(path, operator === "set" ? "!=" : "=", value, negate);
    }
}

function eliminateSetOperators(tree) {
    return operate(_removeSetOperator, tree);
}

function _introduceStartsWithOperator(c, options) {
    const { negate, path, operator, value } = c;
    const fieldType = options.getFieldDef?.(path)?.type;
    if (
        ["char", "text", "html"].includes(fieldType) &&
        operator === "=ilike" &&
        typeof value === "string"
    ) {
        if (value.endsWith("%")) {
            return Condition.of(path, "starts with", value.slice(0, -1), negate);
        }
    }
}

function introduceStartsWithOperators(tree, options) {
    return operate(_introduceStartsWithOperator, tree, options);
}

function _eliminateStartsWithOperator(c) {
    const { negate, path, operator, value } = c;
    if (operator === "starts with") {
        return Condition.of(path, "=ilike", `${value}%`, negate);
    }
}

function eliminateStartsWithOperators(tree) {
    return operate(_eliminateStartsWithOperator, tree);
}

function isSimpleAnd(c) {
    if (
        c.type === "connector" &&
        c.value === "&" &&
        !c.negate &&
        c.children.length === 2 &&
        c.children.every((child) => child instanceof Condition && !child.negate)
    ) {
        return true;
    }
    return false;
}

function isBetween(c) {
    if (isSimpleAnd(c)) {
        const [
            { path: p1, operator: op1, value: value1 },
            { path: p2, operator: op2, value: value2 },
        ] = c.children;
        if (p1 === p2 && op1 === ">=" && op2 === "<=") {
            return { path: p1, value1, value2 };
        }
    }
    return false;
}

function makeBetween(path, value1, value2) {
    return Connector.of("&", [Condition.of(path, ">=", value1), Condition.of(path, "<=", value2)]);
}

function isStrictBetween(c) {
    if (isSimpleAnd(c)) {
        const [
            { path: p1, operator: op1, value: value1 },
            { path: p2, operator: op2, value: value2 },
        ] = c.children;
        if (p1 === p2 && op1 === ">=" && op2 === "<") {
            return { path: p1, value1, value2 };
        }
    }
    return false;
}

function makeStrictBetween(path, value1, value2) {
    return Connector.of("&", [Condition.of(path, ">=", value1), Condition.of(path, "<", value2)]);
}

function boundDate(delta) {
    if (!delta) {
        return Expression.of(`context_today().strftime("%Y-%m-%d")`);
    }
    return Expression.of(`(context_today() + relativedelta(${delta})).strftime('%Y-%m-%d')`);
}

function boundDatetime(delta) {
    if (!delta) {
        return Expression.of(
            `datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
        );
    }
    return Expression.of(
        `datetime.datetime.combine(context_today() + relativedelta(${delta}), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")`
    );
}

const DELTAS = {
    today: ["", "days = 1"],
    "last 7 days": ["days = -7", ""],
    "last 30 days": ["days = -30", ""],
    "month to date": ["day = 1", "days = 1"],
    "last month": ["day = 1, months = -1", "day = 1"],
    "year to date": ["day = 1, month = 1", "days = 1"],
    "last 12 months": ["day = 1, months = -12", "day = 1"],
};

function _introduceInRangeOperator(c, options) {
    const res1 = isStrictBetween(c);
    if (res1) {
        // @ts-ignore
        const { path, value1, value2 } = res1;
        const fieldType = options.getFieldDef?.(path)?.type;
        if (["date", "datetime"].includes(fieldType) && isSimplePath(path)) {
            const toBound = fieldType === "date" ? boundDate : boundDatetime;
            for (const valueType in DELTAS) {
                const [leftBound, rightBound] = DELTAS[valueType].map(toBound);
                if (value1._expr === leftBound._expr && value2._expr === rightBound._expr) {
                    return Condition.of(path, "in range", [fieldType, valueType, false, false]);
                }
            }
        }
    }
    const res2 = isBetween(c);
    if (res2) {
        // @ts-ignore
        const { path, value1, value2 } = res2;
        const fieldType = options.getFieldDef?.(path)?.type;
        if (["date", "datetime"].includes(fieldType) && isSimplePath(path)) {
            return Condition.of(path, "in range", [
                fieldType,
                "custom range",
                // @ts-ignore
                ...normalizeValue([value1, value2]),
            ]);
        }
    }
}

function introduceInRangeOperators(tree, options) {
    return operate(
        rewriteNConsecutiveChildren(_introduceInRangeOperator),
        tree,
        options,
        "connector"
    );
}

function _eliminateInRangeOperator(c) {
    const { negate, path, operator, value } = c;
    // @ts-ignore
    if (operator !== "in range") {
        return;
    }
    const { initialPath, lastPart } = splitPath(path);
    const [fieldType, valueType, value1, value2] = value;
    let tree;
    if (valueType === "custom range") {
        tree = makeBetween(lastPart, value1, value2);
    } else {
        const toBound = fieldType === "date" ? boundDate : boundDatetime;
        const [leftBound, rightBound] = DELTAS[valueType].map(toBound);
        tree = makeStrictBetween(lastPart, leftBound, rightBound);
    }
    return wrapInAny(tree, initialPath, negate);
}

function eliminateInRangeOperators(tree) {
    return operate(_eliminateInRangeOperator, tree);
}

function _introduceBetweenOperator(c, options) {
    const res = isBetween(c);
    if (!res) {
        return;
    }
    // @ts-ignore
    const { path, value1, value2 } = res;
    const fieldType = options.getFieldDef?.(path)?.type;
    if (["integer", "float", "monetary"].includes(fieldType) && isSimplePath(path)) {
        return Condition.of(path, "between", normalizeValue([value1, value2]));
    }
}

function introduceBetweenOperators(tree, options = {}) {
    return operate(
        rewriteNConsecutiveChildren(_introduceBetweenOperator),
        tree,
        options,
        "connector"
    );
}

function _eliminateBetweenOperator(c) {
    const { negate, path, operator, value } = c;
    // @ts-ignore
    if (operator !== "between") {
        return;
    }
    const { initialPath, lastPart } = splitPath(path);
    return wrapInAny(makeBetween(lastPart, value[0], value[1]), initialPath, negate);
}

function eliminateBetweenOperators(tree) {
    return operate(_eliminateBetweenOperator, tree);
}

function _eliminateAnyOperator(c) {
    const { path, operator, value, negate } = c;
    if (
        operator === "any" &&
        isTree(value) &&
        value instanceof Condition &&
        typeof path === "string" &&
        typeof value.path === "string" &&
        !negate &&
        !value.negate &&
        ["between", "in range"].includes(value.operator)
    ) {
        return Condition.of(`${path}.${value.path}`, value.operator, value.value);
    }
}

function eliminateAnyOperators(tree) {
    return operate(_eliminateAnyOperator, tree);
}

function applyTransformations(transformations, transformed, ...fixedParams) {
    for (let i = transformations.length - 1; i >= 0; i--) {
        const fn = transformations[i];
        transformed = fn(transformed, ...fixedParams);
    }
    return transformed;
}

export function introduceVirtualOperators(tree, options) {
    return applyTransformations(
        [
            eliminateAnyOperators,
            introduceSetOperators,
            introduceStartsWithOperators,
            introduceBetweenOperators,
            introduceInRangeOperators,
        ],
        tree,
        options
    );
}

export function eliminateVirtualOperators(tree) {
    return applyTransformations(
        [
            eliminateInRangeOperators,
            eliminateBetweenOperators,
            eliminateStartsWithOperators,
            eliminateSetOperators,
        ],
        tree
    );
}

export function areEquivalentTrees(tree, otherTree) {
    const simplifiedTree = eliminateVirtualOperators(tree);
    const otherSimplifiedTree = eliminateVirtualOperators(otherTree);
    return simplifiedTree.equals(otherSimplifiedTree);
}
