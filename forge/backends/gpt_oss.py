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

"""GPT-OSS generator backend.

Talks to a GPT-OSS model served either by Ollama (default) or any
OpenAI-compatible server (e.g. llama.cpp's llama-server).

Configuration (env vars):
    GPT_OSS_ENDPOINT  base URL, default http://localhost:11434
    GPT_OSS_MODEL     model name, default gpt-oss:20b
    GPT_OSS_API       "ollama" (default) or "openai"

Hardware note: gpt-oss:20b needs ~12 GB RAM/VRAM even quantized.
A 2-CPU box with ~2 GB free cannot run it locally; point
GPT_OSS_ENDPOINT at a machine that can (or a hosted GPT-OSS endpoint).
"""
import json
import os
import urllib.error
import urllib.request

from ..util import extract_template
from .base import BackendError, PromptBackend


class GptOssBackend(PromptBackend):
    name = "gpt-oss"

    def __init__(self, endpoint=None, model=None, api=None,
                 timeout=180, temperature=0.2):
        self.endpoint = (endpoint or os.environ.get(
            "GPT_OSS_ENDPOINT", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("GPT_OSS_MODEL", "gpt-oss:20b")
        self.api = (api or os.environ.get("GPT_OSS_API", "ollama")).lower()
        self.timeout = timeout
        self.temperature = temperature

    # -- public ---------------------------------------------------------
    def generate(self, system, user):
        try:
            if self.api == "openai":
                content = self._openai_chat(system, user)
            elif self.api == "ollama":
                content = self._ollama_chat(system, user)
            else:
                raise BackendError(f"unknown GPT_OSS_API={self.api!r}; "
                                   "want 'ollama' or 'openai'")
        except BackendError:
            raise
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            raise BackendError(
                f"cannot reach GPT-OSS at {self.endpoint} ({e}). "
                "Start Ollama (`ollama serve`, `ollama pull gpt-oss:20b`) "
                "or set GPT_OSS_ENDPOINT to a reachable host."
            ) from e
        template = extract_template(content)
        if not template:
            raise BackendError("GPT-OSS returned no usable template text")
        return template

    # -- transports -----------------------------------------------------
    def _post(self, path, payload):
        req = urllib.request.Request(
            self.endpoint + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.load(resp)

    def _ollama_chat(self, system, user):
        data = self._post("/api/chat", {
            "model": self.model,
            "stream": False,
            "options": {"temperature": self.temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        })
        return data["message"]["content"]

    def _openai_chat(self, system, user):
        data = self._post("/v1/chat/completions", {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        })
        return data["choices"][0]["message"]["content"]
