"""Pipeline tests: NL -> master prompt -> boolean correction -> validation."""
from forge.backends.stub import StubBackend
from forge.engine import ScriptEngine


def _run(request):
    return ScriptEngine(StubBackend()).run(request)


def test_admin_dashboard_pipeline():
    res = _run("Greet the user. If the user is an admin, show the dashboard link.")
    assert res.backend == "stub"
    assert res.balanced, res.errors
    assert "{{#is_admin}}" in res.corrected or "{{#the_user_is_an_admin}}" in res.corrected
    assert len(res.corrections) > 0  # stub is sloppy on purpose
    assert "dashboard" in res.renders["all_true"].lower()
    assert "dashboard" not in res.renders["all_false"].lower()


def test_loop_pipeline():
    res = _run("List all orders. For each order show the total.")
    assert res.balanced, res.errors
    assert "{{#each" not in res.corrected  # `each` is rewritten away


def test_unless_pipeline():
    res = _run("Show the signup button unless the user is logged in.")
    assert res.balanced, res.errors
    assert "{{^" in res.corrected  # negation became an inverted block


def test_greeting_renders_name():
    res = _run("Greet the user by name.")
    assert res.balanced, res.errors
    assert "Hello" in res.renders["all_true"]


def test_result_shape():
    res = _run("Show a message.")
    assert res.master_prompt
    assert res.corrected
    assert isinstance(res.corrections, list)
    assert set(res.renders) == {"all_true", "all_false", "empty"}
