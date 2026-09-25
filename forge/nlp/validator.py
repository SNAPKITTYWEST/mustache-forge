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
