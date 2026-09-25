"""Deterministic offline stand-in for GPT-OSS.

Emits plausible, deliberately sloppy mustache (unbalanced tags, `if`
prefixes, `each` loops, stray closes) so the NLP correction engine has
real work to do in demos and tests. Never used when a real backend is
configured; clearly labeled wherever it appears.
"""
import re

from ..util import extract_template
from .base import PromptBackend


def _slug(text):
    text = re.sub(r"\s+", "_", text.strip().lower())
    text = re.sub(r"[^a-z0-9_.]", "", text)
    return re.sub(r"_+", "_", text).strip("_.") or "value"


class StubBackend(PromptBackend):
    name = "stub"

    def generate(self, system, user):
        m = re.search(r"natural language request:\s*(.*)", user, re.S | re.I)
        req = m.group(1).strip() if m else user.strip()
        body = self._draft(req)
        raw = ("Here is your mustache master prompt:\n\n"
               "```mustache\n" + body + "\n```\n")
        return extract_template(raw)

    def _draft(self, req):
        parts = []
        # loops -> sloppy {{#each x}}...{{/each}} (mustache has no `each`)
        for m in re.finditer(r"(?:for each|list all|show all)\s+(\w+)", req, re.I):
            item = m.group(1).lower()
            parts.append("{{#each %s}}\n- {{.}}\n{{/each}}" % item)
        # conditionals -> sloppy {{#if ...}} with natural-language insides
        for m in re.finditer(r"\bif\s+(.+?)(?=[,.;]|$)", req, re.I):
            cond = m.group(1).strip()
            im = re.search(r"(?:show|include|display|render)\s+"
                           r"(?:the\s+|a\s+)?(.+?)(?=[,.;]|$)", req, re.I)
            inner = im.group(1).strip() if im else "details"
            parts.append("{{#if %s}}\n  %s: {{%s}}\n{{/if}}"
                         % (cond, inner.capitalize(), _slug(inner)))
        # negations -> sloppy {{#if not ...}}
        for m in re.finditer(r"\bunless\s+(.+?)(?=[,.;]|$)", req, re.I):
            cond = m.group(1).strip()
            parts.append("{{#if not %s}}\n  hidden\n{{/if}}" % cond)
        if re.search(r"\bgreet|hello|welcome\b", req, re.I):
            parts.insert(0, "Hello, {{name}}!")
        if not parts:
            parts.append("{{message}}")
        # leave one tag unclosed on purpose, like a sloppy model would
        parts.append("{{#footer}}\n  {{tagline}}")
        return "\n".join(parts)
