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

## Architecture and decisions

1. **Generate:** a writer receives the topic, beginner profile, prior improvement notes, and (on retries) specific evaluator failures. It must return only lesson Markdown.
2. **Evaluate:** deterministic hard checks cover required teaching elements, examples, terminology, structure, and bounded length. A separate model evaluator returns a pass/fail decision and evidence for accuracy, simplicity, flow, and coverage. A lesson ships only when both gates pass. Invalid evaluator JSON fails closed.
3. **Revise:** failed checks and evidence are supplied to the writer. There are at most two lesson revisions, then a clear non-shipping result is recorded. A rate-limited API call waits briefly and retries once; provider failures are logged separately from lesson quality failures.
4. **Remember:** each attempt, check, feedback item, and outcome is appended as JSONL. Successful and repeated failure signals become compact prompt hints in later runs. This is inspectable, local, and easy to reset.

The evaluator is deliberately not a single unconstrained “quality score”: hard pass/fail checks are auditable, while model judgment handles semantic qualities that simple string checks cannot reliably measure. The model is not treated as a source of truth; groundedness is judged against basic domain facts embedded in the rubric, and the lesson is kept cautious about changing product details. A human should review content before publication. The two-retry cap prevents runaway cost and guarantees termination.

## Walkthrough outline (15–20 minutes)

1. Show the architecture and rubric in `src/lessonforge.py` (3 min).
2. Run `python src/lessonforge.py demo` and point out the RAG definition error and the failed checks (3 min).
3. Configure a compatible model and generate the topic live; inspect attempts and the rejection log (5–7 min).
4. Open the passing lesson and trace one feedback-driven revision (3–4 min).
5. Explain JSONL memory, retry limit, trade-offs, and human review boundary (2 min).

For a face-visible Loom, record the live run and repo walkthrough. Do not expose the API key on screen.

## Submission readiness

The Markdown lesson is the final document content. To provide a Google Doc link, copy `output/introduction_to_rag.md` into a Google Doc and publish the appropriate sharing access. Push this folder to a GitHub repository and record the Loom walkthrough before entering the three links in the provided form. External publishing and form submission have not been performed from this workspace.
