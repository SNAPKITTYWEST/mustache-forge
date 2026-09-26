# SPDX-License-Identifier: AGPL-3.0-or-later
#
# mustache-forge
# Copyright (C) 2026 SnapKitty Collective
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Mustache lexer: turns template text into a token stream.

Token kinds:
    TEXT       literal text between tags
    VAR        {{name}}
    UNESCAPED  {{{name}}} or {{& name}}
    SECTION    {{#name}}
    INVERTED   {{^name}}
    CLOSE      {{/name}}
    PARTIAL    {{>name}}
    COMMENT    {{! ...}}
"""
import re
from dataclasses import dataclass

TAG_RE = re.compile(r"""
      \{\{\{\s*(?P<triple>.*?)\s*\}\}\}          # triple mustache {{{x}}}
    | \{\{\s*(?P<sig>[#^/>=!&]?)\s*(?P<body>.*?)\s*\}\}   # {{sig name}}
""", re.X | re.S)

_SIG_KIND = {
    "": "VAR",
    "#": "SECTION",
    "^": "INVERTED",
    "/": "CLOSE",
    ">": "PARTIAL",
    "!": "COMMENT",
    "&": "UNESCAPED",
    "=": "SET_DELIM",
}


@dataclass
class Token:
    kind: str
    name: str
    raw: str
    pos: int


def lex(template):
    tokens = []
    pos = 0
    for m in TAG_RE.finditer(template or ""):
        if m.start() > pos:
            tokens.append(Token("TEXT", "", template[pos:m.start()], pos))
        if m.group("triple") is not None:
            tokens.append(Token("UNESCAPED", m.group("triple").strip(),
                                m.group(0), m.start()))
        else:
            sig, body = m.group("sig"), m.group("body").strip()
            tokens.append(Token(_SIG_KIND.get(sig, "VAR"), body,
                                m.group(0), m.start()))
        pos = m.end()
    if pos < len(template or ""):
        tokens.append(Token("TEXT", "", template[pos:], pos))
    return tokens
