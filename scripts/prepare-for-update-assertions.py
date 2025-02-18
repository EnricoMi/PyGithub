import argparse
import difflib
import sys
from typing import Union

import libcst as cst
from libcst import SimpleWhitespace, TrailingWhitespace


class SingleLineStatementTransformer(cst.CSTTransformer):
    def __init__(self, function: str):
        super().__init__()
        self.function = function
        self.in_function = False

    def visit_FunctionDef(self, node: cst.FunctionDef):
        if node.name.value == self.function:
            self.in_function = True

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef):
        self.in_function = False
        return updated_node

    def leave_SimpleStatementLine(self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine):
        if self.in_function:
            return updated_node.with_changes(
                leading_lines=(), trailing_whitespace=TrailingWhitespace(whitespace=SimpleWhitespace(""))
            )
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.BaseExpression:
        if self.in_function:
            return updated_node.with_changes(
                whitespace_after_func=SimpleWhitespace(""), whitespace_before_args=SimpleWhitespace("")
            )
        return updated_node

    def leave_Arg(
        self, original_node: cst.Arg, updated_node: cst.Arg
    ) -> Union[cst.Arg, cst.FlattenSentinel[cst.Arg], cst.RemovalSentinel]:
        if self.in_function:
            return updated_node.with_changes(
                whitespace_after_star=SimpleWhitespace(""), whitespace_after_arg=SimpleWhitespace("")
            )
        return updated_node

    def leave_LeftCurlyBrace(
        self, original_node: cst.LeftCurlyBrace, updated_node: cst.LeftCurlyBrace
    ) -> cst.LeftCurlyBrace:
        if self.in_function:
            return updated_node.with_changes(whitespace_after=SimpleWhitespace(""))
        return updated_node

    def leave_RightCurlyBrace(
        self, original_node: cst.RightCurlyBrace, updated_node: cst.RightCurlyBrace
    ) -> cst.RightCurlyBrace:
        if self.in_function:
            return updated_node.with_changes(whitespace_before=SimpleWhitespace(""))
        return updated_node

    def leave_Comma(self, original_node: cst.Comma, updated_node: cst.Comma) -> Union[cst.Comma, cst.MaybeSentinel]:
        if self.in_function:
            return updated_node.with_changes(
                whitespace_before=SimpleWhitespace(""), whitespace_after=SimpleWhitespace(" ")
            )
        return updated_node


def main(filename: str, function: str, dry_run: bool) -> bool:
    with open(filename) as r:
        code = "".join(r.readlines())

    tree = cst.parse_module(code)
    transformer = SingleLineStatementTransformer(function)
    tree_updated = tree.visit(transformer)

    if dry_run:
        diff = "".join(difflib.unified_diff(code.splitlines(1), tree_updated.code.splitlines(1)))
        if diff:
            print(f"Diff of {filename}:")
            print(diff)
            print()
            return True
    else:
        if not tree_updated.deep_equals(tree):
            with open(filename, "w") as w:
                w.write(tree_updated.code)
            return True

    return False


def parse_args():
    args_parser = argparse.ArgumentParser(
        description="Removes newlines from all statements in a specific function of one test file"
    )
    args_parser.add_argument("filename", help="Path of test file")
    args_parser.add_argument("function", help="Name of the test function")
    args_parser.add_argument(
        "--dry-run", default=False, action="store_true", help="Show prospect changes and do not modify the file"
    )
    args_parser.add_argument(
        "--exit-code", default=False, action="store_true", help="Indicate changes via non-zero exit code"
    )

    if len(sys.argv) == 1:
        args_parser.print_help()
        sys.exit(1)
    return args_parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    changed = main(args.filename, args.function, args.dry_run)
    if args.exit_code and changed:
        sys.exit(1)
