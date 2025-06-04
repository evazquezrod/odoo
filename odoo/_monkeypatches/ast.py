# ruff: noqa: E402, PLC0415
# ignore import not at top of the file
import ast
import logging
import os
from ast import Call, Constant, Dict, Expression, List, Name, Set, Tuple, UAdd, UnaryOp, USub, expr, parse

_logger = logging.getLogger(__name__)
orig_literal_eval = ast.literal_eval


def expr_eval(node: expr):
    # beautiful but slower then if isinstance :( on python 3.12
    match node:
        case Constant(value=value):
            return value
        case Tuple(elts=elts):
            return tuple(map(expr_eval, elts))
        case List(elts=elts):
            return list(map(expr_eval, elts))
        case Dict(keys=keys, values=values):
            return dict(zip(map(expr_eval, keys), map(expr_eval, values), strict=True))
        case Set(elts=elts):
            return set(map(expr_eval, elts))
        case Call(func=Name(id='set'), args=[], keywords=[]):
            return set()
        # small number operations
        case UnaryOp(op=UAdd(), operand=Constant(value)) if isinstance(value, (int, float, complex)):
            return +value
        case UnaryOp(op=USub(), operand=Constant(value)) if isinstance(value, (int, float, complex)):
            return -value
        # dropping support for complex numbers
    msg = "malformed node or string"
    if lno := getattr(node, 'lineno', None):
        msg += f' on line {lno}'
    raise ValueError(msg + f': {node!r}')


def literal_eval(expr):
    # limit the size of the expression to avoid segmentation faults
    # the default limit is set to 100KiB
    # can be overridden by setting the ODOO_LIMIT_LITEVAL_BUFFER buffer_size_environment variable

    buffer_size = 102400
    buffer_size_env = False # os.getenv("ODOO_LIMIT_LITEVAL_BUFFER")

    if buffer_size_env:
        if buffer_size_env.isdigit():
            buffer_size = int(buffer_size_env)
        else:
            _logger.error("ODOO_LIMIT_LITEVAL_BUFFER has to be an integer, defaulting to 100KiB")

    if isinstance(expr, str):
        if len(expr) > buffer_size:
            raise ValueError("expression can't exceed buffer limit")
        expr = parse(expr.lstrip(" \t"), mode='eval')
    if isinstance(expr, Expression):
        expr = expr.body
    return expr_eval(expr)


def patch_module():
    ast.literal_eval = literal_eval
