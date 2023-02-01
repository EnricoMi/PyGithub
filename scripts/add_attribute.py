#!/usr/bin/env python

############################ Copyrights and license ############################
#                                                                              #
# Copyright 2013 Vincent Jacques <vincent@vincent-jacques.net>                 #
# Copyright 2014 Thialfihar <thi@thialfihar.org>                               #
# Copyright 2014 Vincent Jacques <vincent@vincent-jacques.net>                 #
# Copyright 2016 Peter Buckley <dx-pbuckley@users.noreply.github.com>          #
# Copyright 2018 sfdye <tsfdye@gmail.com>                                      #
# Copyright 2018 bbi-yggy <yossarian@blackbirdinteractive.com>                 #
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

import os.path
import sys

className, attributeName, attributeType = sys.argv[1:4]
if len(sys.argv) > 4:
    attributeClassType = sys.argv[4]
else:
    attributeClassType = ""


types = {
    "string": (
        "string",
        None,
        'self._makeStringAttribute(attributes["' + attributeName + '"])',
    ),
    "int": (
        "integer",
        None,
        'self._makeIntAttribute(attributes["' + attributeName + '"])',
    ),
    "bool": (
        "bool",
        None,
        'self._makeBoolAttribute(attributes["' + attributeName + '"])',
    ),
    "datetime": (
        "datetime.datetime",
        "str",
        'self._makeDatetimeAttribute(attributes["' + attributeName + '"])',
    ),
    "class": (
        ":class:`" + attributeClassType + "`",
        None,
        "self._makeClassAttribute("
        + attributeClassType
        + ', attributes["'
        + attributeName
        + '"])',
    ),
}

attributeDocType, attributeAssertType, attributeValue = types[attributeType]


fileName = os.path.join("github", className + ".py")

with open(fileName) as f:
    lines = list(f)

newLines = []

i = 0

added = False
existed = False
updated = False

isCompletable = True
isProperty = False
while not added:
    line = lines[i].rstrip()
    i += 1
    if line.startswith("class "):
        if "NonCompletableGithubObject" in line:
            isCompletable = False
    elif line == "    @property":
        isProperty = True
    elif line.startswith("    def "):
        attrName = line[8:-7]
        # Properties will be inserted after __repr__, but before any other function.
        if attrName != "__repr__" and (
            attrName == "_identity" or attrName >= attributeName or not isProperty
        ):
            # collect lines existing for this property and those new lines we generate
            # to compare them and detect an update
            newPropLines = []
            existingLines = []

            if attrName == attributeName:
                # consume all existing lines defining this property
                if isProperty:
                    existingLines.append("    @property")
                while line.startswith("    def ") or line.startswith('        '):
                    existingLines.append(line)
                    line = lines[i].rstrip()
                    i += 1
                # also consume the empty line after the definition
                existingLines.append(line)
                line = lines[i].rstrip()
                i += 1

            newPropLines.append("    @property")
            newPropLines.append("    def " + attributeName + "(self):")
            newPropLines.append('        """')
            newPropLines.append("        :type: " + attributeDocType)
            newPropLines.append('        """')
            if isCompletable:
                newPropLines.append(
                    "        self._completeIfNotSet(self._" + attributeName + ")"
                )
            newPropLines.append("        return self._" + attributeName + ".value")
            newPropLines.append("")

            added = True
            existed = len(existingLines) > 0
            updated = existed and existingLines != newPropLines

            newLines.extend(newPropLines)
        if isProperty and not existed:
            newLines.append("    @property")
        isProperty = False
    if not isProperty:
        newLines.append(line)

if updated:
    print(f'Updated {className}.{attributeName}')
elif not existed:
    print(f'Added {className}.{attributeName}')

added = False
existed = False
updated = False

inInit = line.endswith("def _initAttributes(self):")
while not added:
    line = lines[i].rstrip()
    i += 1
    if line == "    def _initAttributes(self):":
        inInit = True
    if inInit:
        if not line or line.endswith(" = github.GithubObject.NotSet"):
            if line:
                attrName = line[14:-29]
            if not line or attrName >= attributeName:
                newLine = "        self._" + attributeName + " = github.GithubObject.NotSet"
                if attrName == attributeName:
                    existed = True
                    updated = line != newLine
                newLines.append(newLine)
                added = True
    if not existed:
        newLines.append(line)

if updated:
    print(f'Updated {className}.{attributeName} in _initAttributes')
elif not existed:
    print(f'Added {className}.{attributeName} to _initAttributes')

added = False
existed = False
updated = False

inUse = False
while not added:
    try:
        line = lines[i].rstrip()
    except IndexError:
        line = ""
    i += 1
    if line == "    def _useAttributes(self, attributes):":
        inUse = True
    if inUse:
        if not line or line.endswith(" in attributes:  # pragma no branch"):
            if line:
                attrName = line[12:-36]
            if not line or attrName >= attributeName:
                # collect lines existing for this property and those new lines we generate
                # to compare them and detect an update
                newUseLines = []
                existingLines = []

                if attrName == attributeName:
                    # consume all existing lines regarding this attribute
                    while line.startswith(f'        if "{attributeName}"') or line.startswith('            '):
                        existingLines.append(line)
                        if i < len(lines):
                            line = lines[i].rstrip()
                        else:
                            line = ""
                        i += 1

                newUseLines.append(
                    '        if "'
                    + attributeName
                    + '" in attributes:  # pragma no branch'
                )
                if attributeAssertType:
                    newUseLines.append(
                        '            assert attributes["'
                        + attributeName
                        + '"] is None or isinstance(attributes["'
                        + attributeName
                        + '"], '
                        + attributeAssertType
                        + '), attributes["'
                        + attributeName
                        + '"]'
                    )
                if existingLines.__len__() == 4:
                    # this line has been reformatted as it is too long for one line
                    attributeValue = attributeValue.replace("(", "(\n                ").replace(")", "\n            )")
                newUseLines.append(
                    "            self._" + attributeName + " = " + attributeValue
                )

                added = True
                existed = len(existingLines) > 0
                updated = existed and existingLines != newUseLines

                newLines.extend(newUseLines)
    newLines.append(line)

if updated:
    print(f'Updated {className}.{attributeName} in _useAttributes')
elif not existed:
    print(f'Added {className}.{attributeName} to _useAttributes')


while i < len(lines):
    line = lines[i].rstrip()
    i += 1
    newLines.append(line)

with open(fileName, "w") as f:
    for line in newLines:
        f.write(line + "\n")
