############################ Copyrights and license ############################
#                                                                              #
# Copyright                                                                    #
#                                                                              #
# This file is part of PyGithub.                                               #
# http://pygithub.readthedocs.io/                                              #
#                                                                              #
# PyGithub is free software: you can redistribute it and/or modify it under    #
# the terms of the GNU Lesser General Public License as published by the Free  #
# Software Foundation, either version 3 of the License, or (at your option)    #
# any later version.                                                           #
#                                                                              #
# PyGithub is distributed in the hope that it will be useful, but WITHOUT ANY  #
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS    #
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more #
# details.                                                                     #
#                                                                              #
# You should have received a copy of the GNU Lesser General Public License     #
# along with PyGithub. If not, see <http://www.gnu.org/licenses/>.             #
#                                                                              #
################################################################################

from __future__ import annotations

import argparse
import dataclasses
import difflib
import json
import sys
from json import JSONEncoder
from os import listdir
from os.path import isfile, join
from typing import Sequence, Optional, Any

import libcst as cst
from libcst import SimpleStatementLine, Expr, IndentedBlock, SimpleString, Module


@dataclasses.dataclass(frozen=True)
class Property:
    name: str
    data_type: str | None
    deprecated: bool


class IndexPythonClassesVisitor(cst.CSTVisitor):
    def __init__(self):
        super().__init__()
        self._filename = None
        self._module = None
        self._classes = {}

    def filename(self, filename: str):
        self._filename = filename

    @property
    def classes(self) -> dict[str, Any]:
        return self._classes

    def visit_Module(self, node: "Module") -> Optional[bool]:
        self._module = node

    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
        class_name = node.name.value
        class_docstring = None
        class_schemas = []
        class_bases = [val if isinstance(val, str) else self._module.code_for_node(val)
                       for base in node.bases for val in [base.value.value]]

        # extract class docstring
        try:
            if (isinstance(node.body, IndentedBlock) and
                    isinstance(node.body.body[0], SimpleStatementLine) and
                    isinstance(node.body.body[0].body[0], Expr) and
                    isinstance(node.body.body[0].body[0].value, SimpleString)):
                class_docstring = node.body.body[0].body[0].value.value.strip('"\r\n ')
        except Exception as e:
            print(f"Extracting docstring of class {class_name} failed", e)

        # extract OpenAPI schema
        if class_docstring:
            lines = class_docstring.splitlines()
            for idx, line in enumerate(lines):
                if "The OpenAPI schema can be found at" in line:
                    for schema in lines[idx+1:]:
                        if not schema.strip():
                            break
                        class_schemas.append(schema.strip())

        if class_name in self._classes:
            print(f"Duplicate class definition for {class_name}")

        self._classes[class_name] = {
            "bases": class_bases,
            "docstring": class_docstring,
            "filename": self._filename,
            "schemas": class_schemas
        }
        return False


class ApplySchemaTransformer(cst.CSTTransformer):
    def __init__(self, class_name: str, properties: dict[str, (str | None, bool)], deprecate: bool):
        super().__init__()
        self.visit_class_name = []
        self.class_name = class_name
        self.properties = sorted([Property(name=k, data_type=v[0], deprecated=v[1]) for k, v in properties.items()], key=lambda p: p.name)
        self.all_properties = self.properties.copy()
        self.deprecate = deprecate

    @property
    def current_class_name(self) -> str:
        return ".".join(self.visit_class_name)

    @property
    def current_property(self) -> Property | None:
        if not self.properties:
            return None
        return self.properties[0]

    @staticmethod
    def contains_decorator(seq: Sequence[cst.Decorator], decorator_name: str):
        return any(d.decorator.value == decorator_name for d in seq if isinstance(d.decorator, cst.Name))

    @classmethod
    def is_github_object_property(cls, func_def: cst.FunctionDef):
        return cls.contains_decorator(func_def.decorators, "property")

    @staticmethod
    def deprecate_function(node: cst.FunctionDef) -> cst.FunctionDef:
        decorators = list(node.decorators)
        decorators.append(cst.Decorator(decorator=cst.Name(value="deprecated")))
        return node.with_changes(decorators=decorators)

    def visit_ClassDef(self, node: cst.ClassDef):
        self.visit_class_name.append(node.name.value)

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef):
        self.visit_class_name.pop()
        return updated_node

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef):
        if self.current_class_name != self.class_name:
            return updated_node
        if updated_node.name.value.startswith("__") and updated_node.name.value.endswith("__"):
            return updated_node
        if updated_node.name.value == "_initAttributes":
            return self.update_init_attrs(updated_node)

        if updated_node.name.value == "_useAttributes":
            return self.update_use_attrs(updated_node)

        nodes = []
        updated_node_is_github_object_property = self.is_github_object_property(updated_node)

        while self.current_property and (updated_node_is_github_object_property and self.current_property.name < updated_node.name.value or not updated_node_is_github_object_property):
            prop = self.properties.pop(0)
            node = self.create_property_function(prop.name, prop.data_type, prop.deprecated)
            nodes.append(cst.EmptyLine(indent=False))
            nodes.append(node)

        if updated_node_is_github_object_property:
            if not self.current_property or updated_node.name.value != self.current_property.name or self.current_property.deprecated:
                nodes.append(self.deprecate_function(updated_node) if self.deprecate else updated_node)
            else:
                nodes.append(updated_node)
            if self.current_property and updated_node.name.value == self.current_property.name:
                self.properties.pop(0)
        else:
            nodes.append(updated_node)

        return cst.FlattenSentinel(nodes=nodes)

    @staticmethod
    def create_property_function(name: str, data_type: str | None, deprecated: bool) -> cst.FunctionDef:
        return cst.FunctionDef(
            decorators=[cst.Decorator(decorator=cst.Name(value="property"))],
            name=cst.Name(value=name),
            params=cst.Parameters(params=[cst.Param(cst.Name("self"))]),
            returns=cst.Annotation(annotation=cst.Name(value=data_type)) if data_type else None,
            body=cst.IndentedBlock(body=[
                cst.SimpleStatementLine(body=[
                    cst.Expr(cst.SimpleString(f'"""\n        :type: {data_type}\n        """'))
                ]),
                cst.SimpleStatementLine(body=[
                    cst.Expr(cst.Call(
                        func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value="_completeIfNotSet")),
                        args=[cst.Arg(cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value=f"_{name}")))]
                    ))
                ]),
                cst.SimpleStatementLine(body=[cst.Return(cst.Attribute(value=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value=f"_{name}")), attr=cst.Name(value="value")))])
            ])
        )

    @staticmethod
    def create_type(data_type: str) -> cst.BaseExpression:
        if data_type and "[" in data_type:
            base = data_type[:data_type.find("[")]
            index = data_type[data_type.find("[")+1:data_type.find("]")]
            return cst.Subscript(cst.Name(base), slice=[cst.SubscriptElement(cst.Index(cst.Name(index)))])
        return cst.Name(data_type or "None")

    @classmethod
    def create_init_attr(cls, prop: Property) -> cst.SimpleStatementLine:
        return cst.SimpleStatementLine([cst.AnnAssign(
            target=cst.Attribute(value=cst.Name("self"), attr=cst.Name(f"_{prop.name}")),
            annotation=cst.Annotation(annotation=cst.Subscript(
                value=cst.Name("Attribute"),
                slice=[cst.SubscriptElement(slice=cst.Index(cls.create_type(prop.data_type)))]
            )),
            value=cst.Name("NotSet")
        )])

    @staticmethod
    def make_attribute(prop: Property) -> cst.Call:
        attr = cst.Subscript(
            value=cst.Name("attributes"),
            slice=[cst.SubscriptElement(slice=cst.Index(cst.SimpleString(f'"{prop.name}"')))]
        )
        if prop.data_type == "bool":
            func_name = "_makeBoolAttribute"
            args = [cst.Arg(attr)]
        elif prop.data_type == "int":
            func_name = "_makeIntAttribute"
            args = [cst.Arg(attr)]
        elif prop.data_type == "list[int]":
            func_name = "_makeListOfIntAttribute"
            args = [cst.Arg(attr)]
        elif prop.data_type == "list[str]":
            func_name = "_makeListOfStringAttribute"
            args = [cst.Arg(attr)]
        elif prop.data_type == "str":
            func_name = "_makeStringAttribute"
            args = [cst.Arg(attr)]
        else:
            func_name = "_makeClassAttribute"
            args = [cst.Arg(cst.Name(prop.data_type or "None")), cst.Arg(attr)]
        return cst.Call(func=cst.Attribute(cst.Name("self"), cst.Name(func_name)), args=args)

    @classmethod
    def create_use_attr(cls, prop: Property) -> cst.BaseStatement:
        return cst.If(
                test=cst.Comparison(
                    left=cst.SimpleString(f'"{prop.name}"'),
                    comparisons=[cst.ComparisonTarget(operator=cst.In(), comparator=cst.Name("attributes"))]
                ),
                body=cst.IndentedBlock([
                    cst.SimpleStatementLine([
                        cst.Assign(
                            targets=[cst.AssignTarget(cst.Attribute(cst.Name("self"), cst.Name(f'_{prop.name}')))],
                            value=cls.make_attribute(prop)
                        )
                    ])
                ])
            )

    def update_init_attrs(self, func: cst.FunctionDef) -> cst.FunctionDef:
        # adds only missing attributes, does not update existing ones
        statements = func.body.body
        new_statements = [self.create_init_attr(p) for p in self.all_properties]
        updated_statements = []

        for statement in statements:
            while new_statements and new_statements[0].body[0].target.attr.value < statement.body[0].target.attr.value:
                updated_statements.append(new_statements.pop(0))
            if new_statements and new_statements[0].body[0].target.attr.value == statement.body[0].target.attr.value:
                    updated_statements.append(statement)
                    new_statements.pop(0)
            else:
                updated_statements.append(statement)

        return func.with_changes(body=func.body.with_changes(body=updated_statements))

    def update_use_attrs(self, func: cst.FunctionDef) -> cst.FunctionDef:
        # adds only missing attributes, does not update existing ones
        statements = func.body.body
        new_statements = [self.create_use_attr(p) for p in self.all_properties]
        updated_statements = []

        for statement in statements:
            while new_statements and new_statements[0].test.left.value < statement.test.left.value:
                updated_statements.append(new_statements.pop(0))
            if new_statements and new_statements[0].test.left.value == statement.test.left.value:
                updated_statements.append(statement)
                new_statements.pop(0)
            else:
                updated_statements.append(statement)

        return func.with_changes(body=func.body.with_changes(body=updated_statements))


class JsonSerializer(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(sorted(obj))
        return super().default(obj)


class OpenApi:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.subcommand = args.subcommand
        self.dry_run = args.dry_run
        self.index = OpenApi.read_index(args.index_filename) if 'index_filename' in args else {}
        self.schema_to_class = self.index.get("indices", {}).get("schema_to_classes", {})
        self.schema_to_class['default'] = "GithubObject"

    @staticmethod
    def read_index(filename: str) -> dict[str, Any]:
        with open(filename, 'r') as r:
            return json.load(r)

    def as_python_type(self, data_type: str | None, format: str | None) -> str | None:
        if data_type is None:
            return None

        data_types = {
            "array": "list",
            "boolean": "bool",
            "integer": "int",
            "object": self.schema_to_class,
            "string": {
                None: "str",
                "date-time": "datetime",
                "uri": "str",
            },
        }

        if data_type not in data_types:
            raise ValueError(f"Unsupported data type: {data_type}")

        maybe_with_format = data_types.get(data_type)

        if isinstance(maybe_with_format, str):
            if data_type == "array":
                return f"{maybe_with_format}[{self.as_python_type(format, None)}]"
            return maybe_with_format

        if 'default' not in maybe_with_format and format not in maybe_with_format:
            raise ValueError(f"Unsupported data type format: {format}")

        return maybe_with_format.get(format, maybe_with_format.get('default'))

    def apply(self, spec_file: str, schema_name: str, class_name: str, filename: str | None, dry_run: bool):
        print(f"Using spec {spec_file} for {schema_name} {class_name}")
        with open(spec_file, 'r') as r:
            spec = json.load(r)

        schemas = spec.get('components', {}).get('schemas', {})
        schema = schemas.get(schema_name, {})
        properties = {k: (self.as_python_type(v.get("type") or "object", v.get("format") or v.get("$ref", "").strip("# ") or v.get("items", {}).get("type") or v.get("items", {}).get("$ref")), v.get("deprecated", False)) for k, v in schema.get("properties", {}).items()}
        print(schema)
        print(properties)

        if filename is None:
            filename = f"github/{class_name}.py"
        with open(filename, "r") as r:
            code = "".join(r.readlines())

        tree = cst.parse_module(code)
        tree_updated = tree.visit(ApplySchemaTransformer(class_name, properties, deprecate=False))

        if dry_run:
            diff = difflib.unified_diff(code.splitlines(1), tree_updated.code.splitlines(1))
            print("Diff:")
            print("".join(diff))
        else:
            if not tree_updated.deep_equals(tree):
                with open(filename, "w") as w:
                    w.write(tree_updated.code)


    def extend_inheritance(self, classes: dict[str, Any]) -> bool:
        extended_classes = {}
        updated = False

        for name, cls in classes.items():
            orig_inheritance = cls.get("inheritance", set()).union(set(cls.get("bases", [])))
            inheritance = orig_inheritance.union(ancestor
                                                 for base in cls.get("bases", [])
                                                 for ancestor in classes.get(base, {}).get("inheritance", []))
            cls["inheritance"] = inheritance
            extended_classes[name] = cls
            updated = updated or inheritance != orig_inheritance

        return updated

    def index(self, github_path: str, index_filename: str):
        files = [f for f in listdir(github_path) if isfile(join(github_path, f)) and f.endswith(".py")]
        print(f"Indexing {len(files)} Python files")

        visitor = IndexPythonClassesVisitor()
        for file in files:
            filename = join(github_path, file)
            with open(filename, "r") as r:
                code = "".join(r.readlines())

            visitor.filename(filename)
            tree = cst.parse_module(code)
            tree.visit(visitor)

        # construct inheritance list
        classes = visitor.classes
        while self.extend_inheritance(classes):
            pass

        # construct schema-to-class index
        schema_to_classes = {}
        for name, cls in classes.items():
            for schema in cls.get("schemas"):
                if schema in schema_to_classes:
                    print(f"Multiple classes for schema found: {name} and {schema_to_classes[schema]}")
                schema_to_classes[schema] = name
        print(schema_to_classes)

        print(f"Indexed {len(classes)} classes")
        print(f"Indexed {len([cls for cls in classes.values() if cls.get('schema')])} schemas")

        data = {
            "sources": github_path,
            "classes": classes,
            "indices": {
                "schema_to_classes": schema_to_classes,
            }
        }

        with open(index_filename, "w") as w:
            json.dump(data, w, indent=2, sort_keys=True, ensure_ascii=False, cls=JsonSerializer)

    @staticmethod
    def parse_args():
        args_parser = argparse.ArgumentParser(description="Applies OpenAPI spec to GithubObject classes")
        args_parser.add_argument("--index-filename", help="filename of the index file")
        args_parser.add_argument("--dry-run", default=False, action="store_true", help="show prospect changes and do not modify any files")

        subparsers = args_parser.add_subparsers(dest="subcommand")
        apply_parser = subparsers.add_parser("apply")
        apply_parser.add_argument("spec", help="Github API OpenAPI spec file")
        apply_parser.add_argument("schema_name", help="Name of schema under /components/schemas/")
        apply_parser.add_argument("class_name", help="Python class name")
        apply_parser.add_argument("filename", nargs="?", help="Python file")

        index_parser = subparsers.add_parser("index")
        index_parser.add_argument("github_path", help="Path to Github Python files")
        index_parser.add_argument("index_filename", help="Path of index file")

        if len(sys.argv) == 1:
            args_parser.print_help()
            sys.exit(1)
        return args_parser.parse_args()

    def main(self):
        if self.args.subcommand == "apply":
            self.apply(self.args.spec, self.args.schema_name, self.args.class_name, self.args.filename, self.args.dry_run)
        elif args.subcommand == "index":
            self.index(self.args.github_path, self.args.index_filename)
        else:
            raise RuntimeError("Subcommand not implemented " + args.subcommand)


if __name__ == "__main__":
    args = OpenApi.parse_args()
    OpenApi(args).main()
