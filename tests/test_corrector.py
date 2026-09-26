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

"""Unit tests for the NLP boolean-mustache correction engine."""
from forge.nlp.corrector import correct, section_flags, to_flag


def test_if_prefix_stripped():
    out, cor = correct("{{#if is_admin}}X{{/if}}")
    assert out == "{{#is_admin}}X{{/is_admin}}"
    assert any(c.kind == "normalize" for c in cor)


def test_negation_becomes_inverted():
    out, _ = correct("{{#if not banned}}X{{/if}}")
    assert out == "{{^banned}}X{{/banned}}"


def test_unless_becomes_inverted():
    out, _ = correct("{{#unless guest}}X{{/unless}}")
    assert out == "{{^guest}}X{{/guest}}"


def test_equality_true_collapses():
    out, _ = correct("{{#user == true}}X{{/user}}")
    assert out == "{{#user}}X{{/user}}"


def test_equality_false_inverts():
    out, _ = correct("{{#active is false}}X{{/active}}")
    assert out == "{{^active}}X{{/active}}"


def test_each_loop_rewritten():
    out, _ = correct("{{#each items}}{{.}}{{/each}}")
    assert out == "{{#items}}{{.}}{{/items}}"


def test_double_negation_resolves():
    out, _ = correct("{{^not banned}}X{{/not banned}}")
    assert out == "{{#banned}}X{{/banned}}"


def test_unclosed_section_auto_closed():
    out, cor = correct("{{#admin}}panel")
    assert out == "{{#admin}}panel{{/admin}}"
    assert any(c.kind == "auto_close" for c in cor)


def test_stray_close_dropped():
    out, cor = correct("hello {{/nope}} world")
    assert out == "hello  world"
    assert any(c.kind == "drop_stray" for c in cor)


def test_mismatched_close_renamed():
    out, cor = correct("{{#admin}}X{{/user}}")
    assert out == "{{#admin}}X{{/admin}}"
    assert any(c.kind == "close_fix" for c in cor)


def test_generic_close_matches_top():
    out, _ = correct("{{#if is_admin}}X{{/if}}")
    assert out == "{{#is_admin}}X{{/is_admin}}"


def test_nested_sections_survive():
    src = "{{#user}}{{#is_admin}}A{{/is_admin}}{{^is_admin}}B{{/is_admin}}{{/user}}"
    out, cor = correct(src)
    assert out == src
    assert cor == []


def test_intervening_auto_close():
    out, cor = correct("{{#a}}{{#b}}x{{/a}}")
    assert out == "{{#a}}{{#b}}x{{/b}}{{/a}}"
    assert any(c.kind == "auto_close" for c in cor)


def test_natural_language_flag_slug():
    out, _ = correct("{{#if the user is an admin}}X{{/if}}")
    assert "{{#the_user_is_an_admin}}" in out


def test_dotted_names_preserved():
    out, _ = correct("{{#user.is_admin}}X{{/user.is_admin}}")
    assert out == "{{#user.is_admin}}X{{/user.is_admin}}"


def test_to_flag_table():
    assert to_flag("if is_admin") == ("is_admin", False)
    assert to_flag("unless x") == ("x", True)
    assert to_flag("if not y") == ("y", True)
    assert to_flag("each items") == ("items", False)
    assert to_flag("active == false") == ("active", True)
    assert to_flag("Admin Panel") == ("admin_panel", False)


def test_section_flags():
    assert section_flags("{{#a}}x{{/a}}{{^b}}y{{/b}}{{name}}") == ["a", "b"]
