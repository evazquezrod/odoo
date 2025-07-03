from __future__ import annotations

import ast
import contextlib
import datetime
import functools
import io
import logging
import re
import typing

from lxml import etree

_logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager


class NoChange(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class InvertUnaryTransformer(ast.NodeTransformer):
    """Inline constant value "-X" which is a unary operator into the constant value."""
    def visit_UnaryOp(self, node: ast.UnaryOp):
        if isinstance(node.op, ast.USub) and isinstance(value := node.operand, ast.Constant):
            value.value = -value.value
            return value
        return node


class UpgradeDomainTransformer(ast.NodeTransformer):
    def __init__(self):
        super().__init__()
        self.log = None
        self._invert_transformer = InvertUnaryTransformer()

    def transform(self, node):
        self.log = None
        node = self._invert_transformer.visit(node)
        result = self.visit(node)
        if self.log:
            raise NoChange(*self.log)
        elif self.log is None:
            raise NoChange()
        return result

    def _cannot_parse(self, node, msg):
        if not self.log:
            self.log = []
        self.log.append(msg + ' ' + ast.unparse(node))
        return node

    def visit_List(self, node: ast.List):
        # same implementation as for tuples
        return self.visit_Tuple(node)

    def visit_Tuple(self, node):
        if len(node.elts) != 3 or not isinstance(node.elts[0], ast.Constant):
            return self.generic_visit(node)
        value_node = node.elts[2]
        if isinstance(value_node, (ast.Tuple, ast.List)):
            value_node.elts = [
                self.visit_Tuple(ast.Tuple([ast.Constant('x'), ast.Constant('='), el])).elts[2]
                for el in value_node.elts
            ]
            return node
        value = self.visit(value_node)
        if isinstance(value, str):
            # remove now
            value = value.removeprefix('now ')
            # remove today (if possible)
            if value.startswith('today ') and re.search(r'=\d+[dmy]|=[a-z]', value):
                value = value.removeprefix('today ')
            # update the operator?
            if '!' in value:
                value = value.replace('!', '')
                operator = node.elts[1].value
                if operator == '>':
                    operator += '='
                elif operator == '<=':
                    operator = operator[:-1]
                else:
                    return self._cannot_parse(node)
                node.elts[1].value = operator
            node.elts[2] = ast.Constant(value)
            if not self.log:
                self.log = []
        return node

    @staticmethod
    def parse_offset_keywords(kws: list[ast.keyword]):
        values = {kw.arg: kw.value.value for kw in kws if isinstance(kw.value, ast.Constant)}
        if len(values) != len(kws):
            return None
        result = ""

        def build(value, suffix, eq=False):
            nonlocal result
            if eq:
                sign = '='
            elif value < 0:
                sign = '-'
                value = -value
            else:
                sign = '+'
            result += f" {sign}{value}{suffix}"

        match values:
            case {'weekday': 0, 'days': days}:
                values.pop('weekday')
                result += ' =monday'
                days -= 1
                if days:
                    values['days'] = days
                else:
                    values.pop('days')

        for name, suffix in (
            ('days', 'd'),
            ('months', 'm'),
            ('years', 'y'),
            ('weeks', 'w'),
            ('hours', 'H'),
            ('minutes', 'M'),
            ('seconds', 'S'),
        ):
            if value := values.pop(name, None):
                build(value, suffix)
        for name, suffix in (
            ('day', 'd'),
            ('month', 'm'),
            ('year', 'y'),
            ('hour', 'H'),
            ('minute', 'M'),
            ('second', 'S'),
        ):
            if value := values.pop(name, None):
                build(value, suffix, eq=True)
        if values:
            # not everything was parsed
            return None
        return result

    def visit_Call(self, node: ast.Call):
        match node.func, node.args, node.keywords:
            case ast.Name(id='context_today'), [], []:
                return "now"
            case ast.Attribute(value=ast.Attribute(value=ast.Name(id='datetime'), attr='datetime'), attr='now'), [], []:
                return "now"
            case ast.Attribute(value=value, attr='to_utc'), [], []:
                value = self.visit(value)
                if isinstance(value, str):
                    return value
            case ast.Attribute(value=value, attr='strftime'), [ast.Constant(value=format)], _:
                value = self.visit(value)
                if isinstance(value, str):
                    if len(format) <= 10:
                        value = value.replace('now', 'today')
                    if '-01' in format:
                        value += ' =1d'
                    return value
            case ast.Name(id='relativedelta'), [], kws:
                value = self.parse_offset_keywords(kws)
                if isinstance(value, str):
                    return value
            case ast.Attribute(value=ast.Name(id='datetime'), attr='timedelta'), [], kws:
                value = self.parse_offset_keywords(kws)
                if isinstance(value, str):
                    return value
            case (ast.Attribute(value=ast.Name(id='datetime'), attr='timedelta'), [const], []) if isinstance(const, ast.Constant):
                value = self.parse_offset_keywords([ast.keyword('days', const)])
                return value
            case ast.Attribute(value=ast.Attribute(value=ast.Name(id='datetime'), attr='datetime'), attr='combine'), [value_node, time_node], []:
                value = self.visit(value_node)
                time_value = self.visit(time_node)
                if isinstance(value, str) and isinstance(time_value, datetime.time):
                    if time_value == datetime.time.min:
                        return value.replace('now', 'today')
                    if (time_value.hour, time_value.minute, time_value.second) == (23, 59, 59):
                        return value.replace('now', 'today') + " +1d!"
            case ast.Attribute(value=ast.Name(id='datetime'), attr='time'), args, []:
                with contextlib.suppress(ValueError):
                    value = datetime.time(*(n.value for n in args))
                    return value

        return self._cannot_parse(node, "call")

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(left, str) and isinstance(right, str):
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                right = right.translate(str.maketrans({'+': '-', '-': '+'}))
                return left + right
            return self._cannot_parse(node, 'binop')
        return node


def upgrade(file_manager: FileManager):
    upgrade_domain = UpgradeDomainTransformer()
    no_whitespace = functools.partial(re.compile(r'\s', re.MULTILINE).sub, '')
    for file in file_manager:
        if not (file.path.parent.name in ('report', 'views') and file.path.suffix == '.xml'):
            continue
        content = file.content
        # tree = etree.fromstring(content)  # does not support declarations
        try:
            tree = etree.parse(io.BytesIO(bytes(content, 'utf-8')))
        except Exception as e:
            _logger.info("Failed to parse the file %s: %s", file.path, e)
            continue
        replacements = {}
        for el in tree.findall('.//filter[@domain]'):
            domain = el.attrib['domain']
            if not domain:
                continue
            try:
                domain_ast = ast.parse(domain, mode='eval')
                domain_ast = upgrade_domain.transform(domain_ast)
                new_domain = ast.unparse(domain_ast)
                replacements[no_whitespace(domain)] = new_domain
            except NoChange:
                pass
            except Exception:  # noqa: BLE001
                # check if contains dynamic part
                level = logging.INFO if re.search(r"%\([a-z0-9\.]+\)[sd]", domain) else logging.WARNING
                _logger.log(level, "Failed to parse the domain %r", domain)
        if not replacements:
            continue

        def replacement(match):
            value = etree.fromstring(f"<x {match[0]} />").attrib["domain"]
            domain = replacements.get(no_whitespace(value))
            if not domain:
                return match[0]
            domain = domain.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            return f"domain={domain!r}"
        content = re.sub(r'domain="(.+?)"', replacement, content, flags=re.MULTILINE | re.DOTALL)
        file.content = content


def test(domain, result=''):
    tree = ast.parse(domain, mode='eval')
    tree = UpgradeDomainTransformer().transform(tree)
    output = ast.unparse(tree)
    _logger.debug("%s", output)
    if result:
        assert output == result, f"Failed to parse {domain!r}; got {output!r} instead of {result!r}"
    else:
        assert output != domain, f"Failed to change {domain!r}"


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    test("[('dt', '>', context_today())]", "[('dt', '>', 'now')]")
    test("[('dt', '>', context_today() - relativedelta(days=3))]", "[('dt', '>', '-3d')]")
    test("[('dt', '>', (context_today() + relativedelta(months=-1)).strftime('%Y-%m-%d'))]", "[('dt', '>', 'today -1m')]")
    test("[('dt', '>=', context_today() - relativedelta(day=1))]", "[('dt', '>=', '=1d')]")
    test("[('dt', '>', (datetime.datetime.combine(context_today() + relativedelta(days=1,weekday=0), datetime.time(0,0,0)).to_utc()))]", "[('dt', '>', '=monday')]")
    test("['|', ('start_date', 'in', [context_today().strftime('%Y-%m-01'), (context_today() - relativedelta(months=1)).strftime('%Y-%m-01')]), '&', '&', ('start_date', '>=', (context_today() - relativedelta(months=5)).strftime('%Y-%m-01')), ('end_date', '<', (context_today() + relativedelta(months=3)).strftime('%Y-%m-01')), ('periodicity', '=', 'trimester')]")
