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
