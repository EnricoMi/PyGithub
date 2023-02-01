#!/usr/bin/env python

############################ Copyrights and license ############################
#                                                                              #
# Copyright 2023 Enrico Minack <github@enrico.minack.dev>                      #
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

import json
import os.path
import subprocess
import sys
from pathlib import Path


add_attribute_py = str(Path(__file__).parent / "add_attribute.py")

schemaFile, className = sys.argv[1:3]
with open(schemaFile) as f:
    schema = json.load(f)

fileName = os.path.join("github", className + ".py")
with open(fileName) as f:
    lines = list(f)


inClass = False
inClassDoc = False
openApiSchema = None

for line in lines:
    if not inClass:
        if line.startswith("class "):
            inClass = True
    else:
        if line.startswith('    """'):
            inClassDoc = not inClassDoc
        if inClassDoc:
            if line.startswith("    OpenAPI schema: "):
                openApiSchema = line[20:].strip()
                break

if not openApiSchema:
    print(f'No OpenAPI schema definition found in {fileName}.')
    sys.exit(1)

print(f"Class {className} has OpenAPI schema {openApiSchema}")

for key in openApiSchema.lstrip("/").split("/"):
    schema = schema.get(key, {})

if not schema:
    print(f'Schema not found schema file {schemaFile}')
    sys.exit(1)

for propName, prop in schema.get('properties', {}).items():
    arrayType = None
    classType = None
    propType = prop.get("type")
    if not propType:
        print(f"Schema does not contain a type for property {propName}")
        sys.exit(1)
    elif propType == "object":
        propType = "class"
        classType = "UNKNOWN"
    elif propType == "array":
        propType = "list"
        arrayType = prop.get("items", {}).get("type")
        if arrayType == "object":
            arrayType = "class"
            classType = "UNKNOWN"

    print(propName)
    print(propType)
    process = subprocess.Popen([sys.executable, add_attribute_py, className, propName, propType] +
                               list(v for v in [arrayType, classType] if v))
    process.wait()

    if process.returncode:
        print(f"Failed to add property {propName}")
        sys.exit(1)

    print()
