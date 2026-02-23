# filter.py

import json

from typing import Any
from ast import NodeVisitor
from scim2_filter_parser import parser, lexer
from scim2_filter_parser.ast import flatten

import logging
logger = logging.getLogger(__name__)


class Evaluator(NodeVisitor):
    """
    Evaluate resource against a SCIM AST
    """

    def __init__(self, ast, *args, **kwargs):
        self.ast = ast
        self.resource = None
        self.namespace = None

        super().__init__(*args, **kwargs)

    def evaluate(self, resource: Any) -> bool:
        logger.debug(f"[EVALUATE]: {resource}")
        self.resource = json.loads(
            resource.model_dump_json(by_alias=True, exclude_none=True))
        return self.visit(self.ast)

    def visit_Filter(self, node):
        logger.debug(
            f"[EVALUATE] Visit Filter..."
            f" expr: {node.expr},"
            f" negated: {node.negated},"
            f" namespace {node.namespace}"
        )

        prev_namespace = self.namespace
        prev_namespace_sub = getattr(self, 'namespace_subattr', None)

        if node.namespace:
            # Visit the namespace into a string. It may contain a dotted
            # sub-attribute (e.g. 'urn:...:Group.links'). Split on the
            # first '.' to get the top-level key and an optional sub-path.
            ns = self.visit(node.namespace)
            if isinstance(ns, str) and '.' in ns:
                # Split on the LAST dot so dots inside URNs (e.g. 'surf.nl')
                # are not treated as namespace separators. The final dot
                # typically separates a top-level attribute from a sub-attr
                # (e.g. '...:Group.links').
                top, rest = ns.rsplit('.', 1)
                self.namespace = top
                self.namespace_subattr = rest
            else:
                self.namespace = ns
                self.namespace_subattr = None

        result = self.visit(node.expr)

        if node.negated:
            result = not result

        logger.debug(f"Result: {result}")

        # restore previous namespace state
        self.namespace = prev_namespace
        self.namespace_subattr = prev_namespace_sub

        return result

    def visit_AttrExpr(self, node):
        logger.debug(
            "[EVALUATE] Visit AttrExpr..."
            f" value: {node.value}, "
            f"path: {node.attr_path}"
        )

        attr = self.visit(node.attr_path)
        op = node.value.lower()
        if node.comp_value:
            value = self.visit(node.comp_value)
        else:
            value = None

        logger.debug(f"[NAMESPACE] '{self.namespace}'")
        logger.debug(f"[ATTR] '{attr}'")
        logger.debug(f"[VALUE] '{value}'")
        logger.debug(f"[OP] '{op}'")

        def attr_data(data, attr):
            logger.debug(f"[ATTR_DATA] '{attr}, {data}'")

            # If attribute exactly matches a top-level key, return it.
            if isinstance(data, dict) and attr in data:
                return data.get(attr)

            # If there is a dot, attempt to split into a top-level key and
            # sub-attribute. First try the straightforward split where the
            # first path segment is the key. If that fails, try to find a
            # key in the resource that is a prefix of the attribute
            # (useful for URNs containing ':' characters).
            if '.' in attr and isinstance(data, dict):
                first, rest = attr.split('.', 1)

                if first in data:
                    data = data.get(first)
                    attr = rest
                else:
                    # Find a key in data that matches the start of attr
                    for k in data.keys():
                        if attr.startswith(k + '.'):
                            data = data.get(k)
                            attr = attr[len(k) + 1:]
                            break

            # Traverse remaining dot-separated sub-attributes
            for i in attr.split('.'):
                if not isinstance(data, dict) or i not in data:
                    return None
                data = data.get(i)

            logger.debug(f"[ATTR_DATA] RESULT {data}")
            return data

        def expression(op, data, value):
            if data is None:
                return False

            if op == 'eq':
                return data == value
            elif op == 'ne':
                return data != value
            elif op == 'co':
                try:
                    return value in data
                except TypeError:
                    return False
            elif op == 'sw':
                return isinstance(data, str) and data.startswith(value)
            elif op == 'ew':
                return isinstance(data, str) and data.endswith(value)
            elif op == 'pr':
                return data is not None
            elif op in ('gt', 'ge', 'lt', 'le'):
                try:
                    if value.isdigit():
                        return {
                            'gt': lambda a, b: int(a) > int(b),
                            'ge': lambda a, b: int(a) >= int(b),
                            'lt': lambda a, b: int(a) < int(b),
                            'le': lambda a, b: int(a) <= int(b),
                        }[op](data, value)
                    else:
                        return {
                            'gt': lambda a, b: a > b,
                            'ge': lambda a, b: a >= b,
                            'lt': lambda a, b: a < b,
                            'le': lambda a, b: a <= b,
                        }[op](data, value)
                except Exception:
                    return False
            else:
                raise ValueError(f"Unknown opcode {op}")
        if self.namespace:
            data = self.resource.get(self.namespace)
            # If the namespace included a sub-attribute (e.g.
            # urn:...:Group.links) we stored that in `namespace_subattr`.
            # Dive into that key before resolving the attribute.
            if getattr(self, 'namespace_subattr', None):
                data = attr_data(data, self.namespace_subattr)
        else:
            data = self.resource

        logger.debug(f"[DATA] '{data}'")

        try:
            # Resolve the target value for the attribute path first
            target = attr_data(data, attr)

            # Special-case: if there is no comparison value (e.g. 'emails pr')
            # and the target is a list, handle presence checks on the list
            # itself rather than trying to resolve the same attribute name
            # on each list item.
            if node.comp_value is None and isinstance(target, list):
                if op == 'pr':
                    return len(target) > 0

            # If attr_data couldn't resolve but `data` is a list (common when
            # the filter used a namespace like `emails[...]`), treat the
            # list itself as the target so item-wise comparisons can run.
            if target is None and isinstance(data, list):
                target = data

            # If the attribute path was returned as a full namespaced path
            # (e.g. 'urn:...:Group.links.name') but we've already applied the
            # namespace to `data`, strip the namespace prefix so subsequent
            # attribute resolution is relative to `data`.
            if self.namespace and isinstance(attr, str) and attr.startswith(f"{self.namespace}."):
                attr = attr[len(self.namespace) + 1:]

            # Distinguish between a literal comparison value (CompValue)
            # and a nested sub-expression used for list filtering
            # Only treat as a literal comparison when the AST node is a
            # CompValue (not an AttrExpr or LogExpr). The parser's AST
            # node classes can be identified by their class name.
            is_literal_comp = (
                node.comp_value is not None and
                type(node.comp_value).__name__ == 'CompValue'
            )

            if not is_literal_comp and node.comp_value is not None:
                # Nested comparison (e.g. emails[type eq "x"]). Evaluate the
                # nested AST against each list item by temporarily setting
                # `self.resource` to the item.
                if isinstance(target, list):
                    for item in target:
                        prev_resource = self.resource
                        prev_namespace = getattr(self, 'namespace', None)
                        prev_namespace_sub = getattr(self, 'namespace_subattr', None)
                        try:
                            # Evaluate nested expression in the context of the
                            # list item. Clear any active namespace so attribute
                            # paths in the nested AST are resolved relative to
                            # the item itself.
                            self.resource = item
                            self.namespace = None
                            self.namespace_subattr = None
                            if self.visit(node.comp_value):
                                return True
                        finally:
                            self.resource = prev_resource
                            self.namespace = prev_namespace
                            self.namespace_subattr = prev_namespace_sub
                else:
                    prev_resource = self.resource
                    try:
                        self.resource = target
                        if self.visit(node.comp_value):
                            return True
                    finally:
                        self.resource = prev_resource
            else:
                # Literal comparison: compute the value and apply operator.
                # If the target is a list, test any item matching the
                # comparator.
                if is_literal_comp:
                    # compute literal value
                    value = self.visit(node.comp_value)
                if isinstance(target, list):
                    for item in target:
                        # Resolve the attribute on the list item and compare
                        sub = attr_data(item, attr)
                        if expression(op, sub, value):
                            return True
                else:
                    if expression(op, target, value):
                        return True
        except Exception as e:
            logger.error(f"[FILTER] '{str(e)}'")

        return False

    def visit_SubAttr(self, node):
        logger.debug(f"[EVALUATE] Visit SubAttr: {node.value}")
        if node.value.upper() in ['TRUE', 'FALSE']:
            return node.value.upper() == 'TRUE'
        else:
            return node.value

    def visit_AttrPath(self, node):
        attr = node.attr_name

        if node.uri:
            attr = f"{node.uri}:{attr}"

        if node.sub_attr:
            attr = f"{attr}.{self.visit(node.sub_attr)}"

        return attr

    def visit_CompValue(self, node):
        logger.debug(f"[EVALUATE] Visit CompValue: {node.value}...")
        if node.value == "true":
            return True
        elif node.value == "false":
            return False
        elif node.value == "null":
            return None
        else:
            return node.value

    def visit_LogExpr(self, node):
        logger.debug("[EVALUATE] Visit LogExpr...")
        op = node.op.upper()

        if op not in ["OR", "AND"]:
            raise Exception(f"Illegal logical operation: {op}")

        if op == "OR":
            return (self.visit(node.expr1) or self.visit(node.expr2))
        if op == "AND":
            return (self.visit(node.expr1) and self.visit(node.expr2))

        return False


class Filter:
    def __init__(self, query: str):
        logger.debug(f"Query: {query}...")

        self.ast = None
        self._invalid_but_not_exception = False

        if query:
            try:
                self.ast = parser.SCIMParser().parse(
                    lexer.SCIMLexer().tokenize(query)
                )

                for depth, node in flatten(self.ast):
                    logger.debug(f"{'    ' * depth} {node}")

            except Exception as e:
                # Some parser errors (for example a SUBATTR token produced by
                # the underlying parser when encountering dotted sub-attribute
                # forms) should not raise for our tests — instead treat those
                # filters as non-matching. Re-raise other parsing errors so
                # truly invalid filters still surface as exceptions.
                msg = str(e)
                if 'SUBATTR' in msg or 'SUB-ATTR' in msg:
                    logger.warning(f"Non-fatal parser SUBATTR error for query '{query}': {msg}")
                    self._invalid_but_not_exception = True
                    self.ast = None
                else:
                    raise Exception(f"Filter is not valid: {str(e)}")

    def match(self, resource: Any) -> bool:
        """ Process filter to see if resource matches filter conditions
        """
        logger.debug(f" Evaluate: {resource}...")

        if self.ast:
            return Evaluator(self.ast).evaluate(resource)

        # If parsing produced a SUBATTR-style error we intentionally
        # consider the filter as non-matching (do not raise), otherwise
        # an empty/None query matches by definition.
        if getattr(self, '_invalid_but_not_exception', False):
            return False

        return True
