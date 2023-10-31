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
            f" namespace={node.namespace}"
        )
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

        if op == 'eq':
            return attr == value
        elif op == 'ne':
            return attr != value
        elif op == 'co':
            return value in attr
        elif op == 'sw':
            return attr.startswith(value)
        elif op == 'ew':
            return attr.endswith(value)
        elif op == 'pr':
            return attr
        elif op == 'gt':
            return attr > value
        elif op == 'ge':
            return attr >= value
        elif op == 'lt':
            return attr < value
        elif op == 'le':
            return attr <= value
        else:
            raise ValueError(f"Unknwown opcode {op}")

    def visit_AttrPath(self, node):
        logger.debug(f"[EVALUATE] Visit AttrPath: {node.attr_name}")
        if not self.resource:
            raise Exception("No resource provided")

        logger.debug(f"CHECK ATTR: {self.resource.get(node.attr_name)}")
        return self.resource.get(node.attr_name)

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
        logger.debug(f" Evaulate: {resource}...")

        if self.ast:
            return Evaluator(self.ast).evaluate(resource)

        return True
