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

"""Validator: balance check + trial renders against sample contexts."""
from dataclasses import dataclass, field

import chevron

from .corrector import section_flags
from .lexer import lex


@dataclass
class ValidationResult:
    balanced: bool
    errors: list = field(default_factory=list)
    renders: dict = field(default_factory=dict)


def _sample_contexts(flags):
    return {
        "all_true": {f: True for f in flags},
        "all_false": {f: False for f in flags},
        "empty": {},
    }


def validate(template):
    errors = []
    stack = []
    for tok in lex(template):
        if tok.kind in ("SECTION", "INVERTED"):
            stack.append(tok)
        elif tok.kind == "CLOSE":
            if stack:
                stack.pop()
            else:
                errors.append("stray close %s" % tok.raw)
    for tok in stack:
        errors.append("unclosed section %s" % tok.raw)

    renders = {}
    for label, ctx in _sample_contexts(section_flags(template)).items():
        try:
            renders[label] = chevron.render(template, ctx)
        except Exception as e:  # noqa: BLE001 - report render faults, don't crash
            renders[label] = "RENDER ERROR: %s" % e
            errors.append("render failed for context %s: %s" % (label, e))

    return ValidationResult(balanced=not errors, errors=errors, renders=renders)
