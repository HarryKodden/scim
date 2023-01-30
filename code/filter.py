# filter.py

import json
import ast

from typing import Any
from scim2_filter_parser import parser, lexer, ast as scim2ast

import logging
logger = logging.getLogger(__name__)


class Evaluator(ast.NodeVisitor):
    """
    Evaluate resource against a SCIM AST
    """

    def __init__(self, resource: Any, *args, **kwargs):
        logger.debug("[EVALUATE] Intializing: {resource}")
        self.resource = json.loads(resource.json())
        super().__init__(*args, **kwargs)

    def evaluate(self, scim_ast) -> bool:
        return self.visit(scim_ast)

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
        q1 = self.visit(node.expr1)
        q2 = self.visit(node.expr2)
        op = node.op.upper()
        if q1 and q2:
            if op == "AND":
                return q1 & q2
            elif op == "OR":
                return q1 | q2
        elif q1:
            return q1
        elif q2:
            return q2
        else:
            return None


class Filter:
    def __init__(self, query: str):
        logger.debug(f"Query: {query}...")

        self.tree = None

        if query:
            try:
                self.tree = parser.SCIMParser().parse(
                    lexer.SCIMLexer().tokenize(query)
                )
                logger.debug(self.tree)

                for depth, node in scim2ast.flatten(self.tree):
                    logger.debug(f"{'    ' * depth} {node}")

            except Exception as e:
                raise Exception(f"Filter is not valid: {str(e)}")

    def match(self, resource: Any) -> bool:
        """ Process filter to see if resource matches filter conditions
        """
        logger.debug(f" Evaulate: {resource}...")

        if self.tree:
            logger.debug("...")
            return Evaluator(resource).evaluate(self.tree)

        return True
