"""Shared helpers for mustache-forge."""
import re

FENCE_RE = re.compile(r"```(?:mustache|hbs|handlebars)?\s*\n(.*?)```", re.S)


def extract_template(text):
    """Pull the mustache template out of model output.

    Prefers a fenced ```mustache block; falls back to the whole text.
    """
    m = FENCE_RE.search(text or "")
    if m:
        return m.group(1).strip()
    return (text or "").strip()
