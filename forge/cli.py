"""forge CLI: make / render / check."""
import argparse
import json
import os
import sys

import chevron

from .engine import ScriptEngine, make_backend
from .nlp.corrector import correct
from .nlp.validator import validate


def _cmd_make(args):
    engine = ScriptEngine(make_backend(args.backend))
    request = " ".join(args.request)
    try:
        res = engine.run(request)
    except Exception as e:  # noqa: BLE001 - surface backend faults cleanly
        print("backend error: %s" % e, file=sys.stderr)
        return 2
    print("=== MASTER PROMPT (raw, backend=%s) ===" % res.backend)
    print(res.master_prompt)
    print("\n=== CORRECTED BOOLEAN MUSTACHE ===")
    print(res.corrected)
    print("\n=== CORRECTIONS (%d) ===" % len(res.corrections))
    for c in res.corrections:
        print("- [%s] %s -> %s  (%s)" % (c.kind, c.before, c.after, c.detail))
    print("\n=== VALIDATION ===")
    print("balanced: %s" % ("yes" if res.balanced else "NO"))
    for e in res.errors:
        print("error: %s" % e)
    for label, out in res.renders.items():
        print("--- render[%s] ---" % label)
        print(out)
    if args.out:
        with open(args.out, "w") as f:
            f.write(res.corrected)
        print("\nwrote corrected template to %s" % args.out)
    return 0 if res.balanced else 1


def _cmd_render(args):
    with open(args.template) as f:
        template = f.read()
    if args.correct:
        template, corrections = correct(template)
        for c in corrections:
            print("corrected: %s -> %s" % (c.before, c.after), file=sys.stderr)
    ctx = json.loads(args.context)
    print(chevron.render(template, ctx), end="")
    return 0


def _cmd_check(args):
    with open(args.template) as f:
        template = f.read()
    corrected, corrections = correct(template)
    result = validate(corrected)
    print("corrections: %d" % len(corrections))
    for c in corrections:
        print("- [%s] %s -> %s  (%s)" % (c.kind, c.before, c.after, c.detail))
    print("balanced: %s" % ("yes" if result.balanced else "NO"))
    for e in result.errors:
        print("error: %s" % e)
    if args.in_place:
        with open(args.template, "w") as f:
            f.write(corrected)
        print("rewrote %s" % args.template)
    else:
        print("\n--- corrected template ---")
        print(corrected)
    return 0 if result.balanced else 1


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="forge",
        description="Natural language -> mustache master prompts -> "
                    "boolean mustache blocks.")
    sub = p.add_subparsers(dest="cmd", required=True)

    mk = sub.add_parser("make", help="generate + correct a master prompt")
    mk.add_argument("request", nargs="+", help="natural language request")
    mk.add_argument("--backend", default=os.environ.get("FORGE_BACKEND", "stub"),
                    help="generator backend: stub (default) or gpt-oss")
    mk.add_argument("--out", default=None, help="write corrected template to file")
    mk.set_defaults(fn=_cmd_make)

    rn = sub.add_parser("render", help="render a template against JSON context")
    rn.add_argument("template", help="template file")
    rn.add_argument("--context", default="{}", help="JSON context object")
    rn.add_argument("--correct", action="store_true",
                    help="run boolean correction before rendering")
    rn.set_defaults(fn=_cmd_render)

    ck = sub.add_parser("check", help="lint + boolean-correct a template file")
    ck.add_argument("template", help="template file")
    ck.add_argument("--in-place", action="store_true",
                    help="rewrite the file with corrections applied")
    ck.set_defaults(fn=_cmd_check)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
