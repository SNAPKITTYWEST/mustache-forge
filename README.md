# mustache-forge

A script engine that turns **natural language** into **mustache master prompts**
via GPT-OSS, then NLP-corrects them into **boolean mustache blocks**.

```
natural language
      │
      ▼
┌─────────────┐   system: "Mustache Master" prompt-smith
│  GPT-OSS    │──▶  ```mustache master prompt (raw, often sloppy)
│  generator  │
└─────────────┘
      │
      ▼
┌─────────────┐   {{#if is_admin}} -> {{#is_admin}}
│ NLP         │   {{#unless x}}    -> {{^x}}
│ corrector   │   {{#each items}}  -> {{#items}}
└─────────────┘   unbalanced / stray tags repaired
      │
      ▼
┌─────────────┐   balance check + trial renders
│ validator   │──▶  all_true / all_false / empty contexts
└─────────────┘
```

## Layout

```
forge/
  engine.py            pipeline: run(request) -> EngineResult
  util.py              fenced-block extraction
  backends/
    base.py            PromptBackend interface + BackendError
    gpt_oss.py         GPT-OSS via Ollama (/api/chat) or OpenAI-compatible
                       (/v1/chat/completions, e.g. llama.cpp llama-server)
    stub.py            deterministic offline stand-in (demos/tests only)
  nlp/
    lexer.py           mustache tokenizer
    corrector.py       to_flag() + correct(): boolean-block normalization
    validator.py       balance check + chevron trial renders
  cli.py               forge make / render / check
tests/                 25 checks: corrector, pipeline, backend integration
```

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# offline demo (stub backend stands in for GPT-OSS)
.venv/bin/python -m forge.cli make "Greet the user. If the user is an admin, show the dashboard link."

# lint + boolean-correct an existing template
.venv/bin/python -m forge.cli check template.mustache --in-place

# render a template against JSON context
.venv/bin/python -m forge.cli render template.mustache --context '{"is_admin": true}' --correct
```

## Wiring up the real GPT-OSS generator

```bash
# on a machine with ~16 GB RAM/VRAM (or a hosted endpoint):
ollama serve
ollama pull gpt-oss:20b

export FORGE_BACKEND=gpt-oss
export GPT_OSS_ENDPOINT=http://localhost:11434   # default
export GPT_OSS_MODEL=gpt-oss:20b                 # default
# export GPT_OSS_API=openai                      # for llama-server /v1/chat/completions

.venv/bin/python -m forge.cli make "Your natural language request" --backend gpt-oss
```

Hardware note: `gpt-oss:20b` needs ~12 GB RAM even quantized (Q4). It cannot
run on a 2-CPU box with ~2 GB free — point `GPT_OSS_ENDPOINT` at a host that
can, or at any hosted GPT-OSS-compatible endpoint. The backend code path is
integration-tested against a mock Ollama server (`tests/test_gpt_oss_backend.py`).

## The boolean correction engine

`forge/nlp/corrector.py` is the heart of stage 2. Model output is sloppy;
mustache boolean logic is strict. The corrector:

| sloppy model output | corrected boolean block |
|---|---|
| `{{#if is_admin}}` | `{{#is_admin}}` |
| `{{#when x}}` / `{{#each items}}` | `{{#x}}` / `{{#items}}` |
| `{{#user == true}}` | `{{#user}}` |
| `{{#if not banned}}`, `{{#unless x}}` | `{{^banned}}`, `{{^x}}` |
| `{{^not x}}` (double negation) | `{{#x}}` |
| `{{#a}}…{{/b}}` | `{{#a}}…{{/a}}` (close renamed) |
| unclosed `{{#a}}` | auto-closed at end of scope |
| stray `{{/nope}}` | dropped |

Every fix is reported as a `Correction(kind, before, after, detail)` so the
pipeline is auditable, not magic.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q   # 25 passed
```
