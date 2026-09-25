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

"""Script engine: natural language -> GPT-OSS master prompt ->
NLP boolean-mustache correction -> validation.
"""
import os
from dataclasses import dataclass, field

from .backends.base import PromptBackend
from .backends.gpt_oss import GptOssBackend
from .backends.stub import StubBackend
from .nlp.corrector import correct
from .nlp.validator import validate
from .util import extract_template

MASTER_SYSTEM_PROMPT = """\
You are the Mustache Master, an expert prompt-smith that converts natural
language requests into mustache templates.

Rules:
- Interpolation: {{variable}} for values, {{{html}}} for unescaped HTML.
- Boolean conditionals: {{#flag}}...{{/flag}} renders the block when flag is
  truthy; {{^flag}}...{{/flag}} renders it when flag is falsy.
- Lists: {{#items}}...{{.}}...{{/items}} iterates; {{name}} inside refers to
  each item's fields.
- Partials: {{>partial_name}} to include reusable blocks.
- Section names must be snake_case boolean flags or list names. Never write
  `{{#if ...}}`, `{{#each ...}}`, or natural-language conditions inside tags.
- Output ONLY the template inside a single ```mustache fenced block, no
  explanations, no prose outside the fence.\
"""


@dataclass
class EngineResult:
    request: str
    backend: str
    master_prompt: str          # raw template from the generator
    corrected: str              # boolean-normalized template
    corrections: list = field(default_factory=list)
    balanced: bool = False
    errors: list = field(default_factory=list)
    renders: dict = field(default_factory=dict)


def make_backend(name=None):
    name = (name or os.environ.get("FORGE_BACKEND", "stub")).lower()
    if name in ("gpt-oss", "gpt_oss", "gptoss"):
        return GptOssBackend()
    if name == "stub":
        return StubBackend()
    raise ValueError("unknown backend %r (want 'gpt-oss' or 'stub')" % name)


class ScriptEngine:
    """Runs the full NL -> master prompt -> boolean correction pipeline."""

    def __init__(self, backend=None):
        self.backend = backend or make_backend()
        if not isinstance(self.backend, PromptBackend):
            raise TypeError("backend must be a PromptBackend")

    def run(self, request):
        user_msg = (
            "Convert the following natural language request into a "
            "mustache master prompt template.\n\n"
            "Natural language request:\n%s\n\n"
            "Output only the template inside a ```mustache fenced block."
            % request
        )
        raw = self.backend.generate(MASTER_SYSTEM_PROMPT, user_msg)
        master = extract_template(raw)
        corrected, corrections = correct(master)
        result = validate(corrected)
        return EngineResult(
            request=request,
            backend=self.backend.name,
            master_prompt=master,
            corrected=corrected,
            corrections=corrections,
            balanced=result.balanced,
            errors=result.errors,
            renders=result.renders,
        )
