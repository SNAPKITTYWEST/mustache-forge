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

"""NLP correction engine: rewrites sloppy model output into canonical
boolean mustache blocks.

What it fixes:
  * `{{#if is_admin}}` / `{{#when x}}`      -> `{{#is_admin}}`
  * `{{#each items}}`                       -> `{{#items}}` (mustache iterates
                                               on the list name itself)
  * `{{#user == true}}`, `{{#x is true}}`    -> `{{#user}}`, `{{#x}}`
  * `{{#if not banned}}`, `{{#unless x}}`    -> `{{^banned}}`, `{{^x}}`
  * `{{^not x}}` (double negation)          -> `{{#x}}`
  * generic closes `{{#if x}}...{{/if}}`     -> `{{#x}}...{{/x}}`
  * mismatched closes `{{#a}}...{{/b}}`      -> close renamed to `{{/a}}`
  * unclosed sections                       -> auto-closed at end of scope
  * stray closes with no opener              -> dropped
  * section names                            -> snake_case boolean flags
"""
import re
from dataclasses import dataclass

from .lexer import lex

_IF_RE = re.compile(r"^(?:if|when)\s+(.*?)$", re.S)
_UNLESS_RE = re.compile(r"^unless\s+(.*?)$", re.S)
_NOT_RE = re.compile(r"^(?:if\s+)?not\s+(.*?)$", re.S)
_EACH_RE = re.compile(r"^each\s+(.*?)$", re.S)
_EQ_TRUE_RE = re.compile(r"^(.*?)\s*(?:==|is)\s*true\s*\??$", re.S)
_EQ_FALSE_RE = re.compile(r"^(.*?)\s*(?:==|is)\s*false\s*\??$", re.S)

# close-tag names that carry no flag of their own: they close the top block
_GENERIC_CLOSE = {"if", "when", "each", "flag"}


@dataclass
class Correction:
    kind: str      # normalize | invert | close_fix | auto_close | drop_stray
    before: str
    after: str
    detail: str


def to_flag(raw):
    """Map a sloppy section expression to (flag_name, inverted)."""
    name = (raw or "").strip()
    inverted = False

    m = _UNLESS_RE.match(name) or _NOT_RE.match(name)
    if m:
        inverted, name = True, m.group(1)
    else:
        m = _IF_RE.match(name) or _EACH_RE.match(name)
        if m:
            name = m.group(1)

    m = _EQ_TRUE_RE.match(name)
    if m:
        name = m.group(1)
    else:
        m = _EQ_FALSE_RE.match(name)
        if m:
            inverted, name = True, m.group(1)

    name = name.strip().rstrip("?")
    name = re.sub(r"\s+", "_", name.lower())
    name = re.sub(r"[^a-z0-9_.]", "", name)
    name = re.sub(r"_+", "_", name).strip("_.")
    return (name or "flag"), inverted


def _tag(kind, name):
    sig = {"SECTION": "#", "INVERTED": "^", "CLOSE": "/"}[kind]
    return "{{%s%s}}" % (sig, name)


def correct(template):
    """Return (corrected_template, [Correction, ...])."""
    tokens = lex(template)
    corrections = []
    out = []
    stack = []  # list of (flag, kind)

    for tok in tokens:
        if tok.kind in ("SECTION", "INVERTED"):
            flag, inverted = to_flag(tok.name)
            # XOR: section+inverted-meaning -> INVERTED; inverted+inverted -> SECTION
            new_kind = "INVERTED" if (inverted != (tok.kind == "INVERTED")) \
                else "SECTION"
            new_raw = _tag(new_kind, flag)
            if tok.raw != new_raw:
                corrections.append(Correction(
                    "invert" if new_kind != tok.kind else "normalize",
                    tok.raw, new_raw,
                    "boolean block %s -> %s" % (tok.raw, new_raw)))
            out.append(new_raw)
            stack.append((flag, new_kind))

        elif tok.kind == "CLOSE":
            flag, _ = to_flag(tok.name)
            idx = next((i for i in range(len(stack) - 1, -1, -1)
                        if stack[i][0] == flag), None)
            if idx is None and flag in _GENERIC_CLOSE and stack:
                idx = len(stack) - 1  # {{/if}} / {{/each}} closes top block
            if idx is None and len(stack) == 1:
                idx = 0  # one open block + one foreign close: rename it
            if idx is None:
                corrections.append(Correction(
                    "drop_stray", tok.raw, "",
                    "stray close %s has no opener; dropped" % tok.raw))
                continue
            while len(stack) - 1 > idx:  # auto-close intervening sections
                f, _ = stack.pop()
                close_raw = _tag("CLOSE", f)
                corrections.append(Correction(
                    "auto_close", "", close_raw,
                    "auto-closed unclosed section {{#%s}}" % f))
                out.append(close_raw)
            matched_flag, _ = stack.pop()
            new_raw = _tag("CLOSE", matched_flag)
            if tok.raw != new_raw:
                corrections.append(Correction(
                    "close_fix", tok.raw, new_raw,
                    "close renamed to match opener"))
            out.append(new_raw)

        else:
            out.append(tok.raw)

    while stack:  # auto-close anything left open at end of template
        flag, _ = stack.pop()
        close_raw = _tag("CLOSE", flag)
        corrections.append(Correction(
            "auto_close", "", close_raw,
            "auto-closed unclosed section {{#%s}} at end of template" % flag))
        out.append(close_raw)

    return "".join(out), corrections


def section_flags(template):
    """All boolean flag names used by section/inverted blocks."""
    flags = []
    for tok in lex(template):
        if tok.kind in ("SECTION", "INVERTED"):
            flag, _ = to_flag(tok.name)
            if flag not in flags:
                flags.append(flag)
    return flags
