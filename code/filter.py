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

        if node.namespace:
            self.namespace = self.visit(node.namespace)
            logger.debug(f"[NAMESPACE CHANGE] {self.namespace}")

        result = self.visit(node.expr)

        if node.negated:
            result = ~result

        logger.debug(f"Result: {result}")
        return result

    def visit_AttrExpr(self, node):
        logger.debug(
            "[EVALUATE] Visit AttrExpr..."
            f" value: {node.value}, "
            f"path: {node.attr_path}"
        )

        attr = self.visit(node.attr_path)
        value = self.visit(node.comp_value)
        op = node.value.lower()

        logger.debug(f"[NAMESPACE] '{self.namespace}'")
        logger.debug(f"[ATTR] '{attr}'")
        logger.debug(f"[VALUE] '{value}'")
        logger.debug(f"[OP] '{op}'")

        def expression(op, attribute, value):
            if op == 'eq':
                return attribute == value
            elif op == 'ne':
                return attribute != value
            elif op == 'co':
                return value in attribute
            elif op == 'sw':
                return attribute.startswith(value)
            elif op == 'ew':
                return attribute.endswith(value)
            elif op == 'pr':
                return attribute
            elif op == 'gt':
                return attribute > value
            elif op == 'ge':
                return attribute >= value
            elif op == 'lt':
                return attribute < value
            elif op == 'le':
                return attribute <= value
            else:
                raise ValueError(f"Unknwown opcode {op}")

        if self.namespace:
            data = self.resource.get(self.namespace)
        else:
            data = self.resource

        logger.debug(f"[DATA] '{data}'")

        try:
            if isinstance(data, list):
                for item in data:
                    if expression(op, item.get(attr), value):
                        return True
            else:
                if expression(op, data.get(attr), value):
                    return True
        except Exception as e:
            logger.error(f"[FILTER] '{str(e)}'")

        return False

    def visit_SubAttr(self, node):
        logger.debug(f"[EVALUATE] Visit SubAttr: {node.value}")
        return node.value

    def visit_AttrPath(self, node):
        if node.sub_attr:
            return f"{node.attr_name}.{self.visit(node.sub_attr)}"
        else:
            return node.attr_name

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

        q1 = self.visit(node.expr1)
        if q1 and op == "OR":
            return True
        if not q1 and op == "AND":
            return False

        q2 = self.visit(node.expr2)
        return q2


class Filter:
    def __init__(self, query: str):
        logger.debug(f"Query: {query}...")

        self.ast = None

        if query:
            try:
                self.ast = parser.SCIMParser().parse(
                    lexer.SCIMLexer().tokenize(query)
                )

                for depth, node in flatten(self.ast):
                    logger.debug(f"{'    ' * depth} {node}")

            except Exception as e:
                raise Exception(f"Filter is not valid: {str(e)}")

    def match(self, resource: Any) -> bool:
        """ Process filter to see if resource matches filter conditions
        """
        logger.debug(f" Evaluate: {resource}...")

        if self.ast:
            return Evaluator(self.ast).evaluate(resource)

        return True
