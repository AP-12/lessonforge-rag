# LessonForge: a self-evaluating lesson generator

LessonForge generates a beginner lesson, scores it against explicit pass/fail checks, and revises it using the failed checks as feedback. The loop is bounded to two revisions. The submitted topic is **Introduction to RAG**.

## What is included

- `src/lessonforge.py` — generator, evaluator, retry controller, and durable run log.
- `output/introduction_to_rag.md` — a reviewed, standalone lesson suitable as the document deliverable.
- `memory/lessons.jsonl` — accumulated run history and reusable failure patterns. The file starts empty; each run appends a record.
- `examples/demo_lesson.md` — deliberately flawed lesson used to show evaluator behavior.
- `examples/demo_evaluation.json` — expected demo rejection and explanation.

## Run it

Requires Python 3.10+ and no third-party packages. The built-in `demo` command runs the evaluator against the deliberate error without an API key:

```sh
python src/lessonforge.py demo
```

For generation with the configured Groq endpoint and model, add your Groq API key to `.env`, then run:

```sh
# Copy .env.example to .env, then edit .env and set LESSONFORGE_API_KEY.
python src/lessonforge.py generate "Introduction to RAG"
```

The project reads simple `KEY=VALUE` lines from `.env` without any extra package. Shell environment variables take priority over values in `.env`. The defaults are `https://api.groq.com/openai/v1` and `openai/gpt-oss-120b`. You can override them with `LESSONFORGE_BASE_URL` and `LESSONFORGE_MODEL`. `.env` is ignored by Git; never commit or share it. The endpoint is expected to implement `POST {BASE_URL}/chat/completions` with a standard `choices[0].message.content` response. API calls use Python's standard library. Generated output and an audit record are written to `output/` and `memory/`.


