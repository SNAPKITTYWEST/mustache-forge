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
