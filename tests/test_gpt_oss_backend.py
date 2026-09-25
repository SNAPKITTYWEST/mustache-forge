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

"""Integration tests for the GPT-OSS backend against a mock server."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from forge.backends.base import BackendError
from forge.backends.gpt_oss import GptOssBackend

OLLAMA_BODY = {
    "message": {"content": "```mustache\n{{#is_admin}}hi{{/is_admin}}\n```"}
}
OPENAI_BODY = {
    "choices": [{"message": {"content": "```mustache\n{{name}}\n```"}}]
}


def _mock_server(body):
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            payload = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_ollama_backend_extracts_fenced_block():
    srv = _mock_server(OLLAMA_BODY)
    try:
        b = GptOssBackend(endpoint="http://127.0.0.1:%d" % srv.server_port,
                          model="gpt-oss:20b", api="ollama")
        assert b.generate("sys", "user") == "{{#is_admin}}hi{{/is_admin}}"
    finally:
        srv.shutdown()


def test_openai_compat_backend():
    srv = _mock_server(OPENAI_BODY)
    try:
        b = GptOssBackend(endpoint="http://127.0.0.1:%d" % srv.server_port,
                          model="gpt-oss:20b", api="openai")
        assert b.generate("sys", "user") == "{{name}}"
    finally:
        srv.shutdown()


def test_unreachable_endpoint_raises_backend_error():
    b = GptOssBackend(endpoint="http://127.0.0.1:1", api="ollama", timeout=2)
    with pytest.raises(BackendError):
        b.generate("sys", "user")
