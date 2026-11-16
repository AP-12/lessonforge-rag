"""A small, auditable generate-evaluate-revise lesson workflow."""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMORY = ROOT / "memory" / "lessons.jsonl"
MAX_RETRIES = 2

def load_dotenv() -> None:
    """Load simple KEY=VALUE entries from the project .env without overriding shell vars."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if not name or name in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        os.environ[name] = value

load_dotenv()

RUBRIC = """Judge this beginner lesson for an Indian 12th-grade graduate new to AI. Return only JSON: {"pass": boolean, "checks": [{"name": string, "pass": boolean, "evidence": string}], "feedback": [string]}. Every check is pass/fail. Check factual grounding (retrieval provides information for this answer; it does not retrain the model or guarantee truth), plain language with needed terms explained, a worked example with question/evidence/answer, what/why/how coverage, logical flow, and standalone clarity. Cite lesson evidence. Do not fail a correct simple explanation."""

SYSTEM = "You write accurate, self-contained beginner lessons in plain English. Follow every revision instruction. Return only the lesson in Markdown. Avoid claims that retrieved text makes an answer automatically correct."

def call_model(messages: list[dict[str, str]]) -> str:
    key = os.environ.get("LESSONFORGE_API_KEY")
    if not key:
        raise RuntimeError("Set LESSONFORGE_API_KEY before generation/evaluation.")
    base = os.environ.get("LESSONFORGE_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    model = os.environ.get("LESSONFORGE_MODEL", "openai/gpt-oss-120b")
    body = json.dumps({"model": model, "messages": messages, "temperature": 0.3}).encode()
    req = urllib.request.Request(base + "/chat/completions", data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "User-Agent": "LessonForge/1.0 (beginner lesson generator)"})
    for request_attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                data = json.loads(response.read())
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:1000]
            except Exception:
                detail = ""
            if exc.code == 429 and request_attempt == 0:
                retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
                match = re.search(r"try again in ([0-9.]+)s", detail, re.I)
                delay = float(retry_after) if retry_after.replace(".", "", 1).isdigit() else (float(match.group(1)) if match else 6.0)
                time.sleep(min(max(delay, 1.0) + 0.5, 30.0))
                continue
            suffix = f" Provider response: {detail}" if detail else ""
            raise RuntimeError(f"Model request failed with HTTP {exc.code} ({exc.reason}).{suffix}") from exc
        except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Model request failed: {exc}") from exc

def load_memory() -> list[dict]:
    if not MEMORY.exists():
        return []
    records = []
    for line in MEMORY.read_text(encoding="utf-8").splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records

def memory_hints(records: list[dict]) -> str:
    failed = {}
    retired_checks = {"jargon_scan", "evaluator_integrity", "provider_error"}
    for record in records[-30:]:
        for attempt in record.get("attempts", []):
            for check in attempt.get("checks", []):
                if not check.get("pass") and check.get("name") not in retired_checks:
                    failed[check.get("name", "check")] = failed.get(check.get("name", "check"), 0) + 1
    if not failed:
        return ""
    recurring = sorted(failed.items(), key=lambda item: -item[1])[:5]
    return "Recurring quality issues in recent runs; prevent these proactively: " + "; ".join(f"{name} ({count} failures)" for name, count in recurring)

def deterministic_checks(lesson: str) -> list[dict]:
    low = lesson.lower()
    checks = []
    def add(name: str, passed: bool, evidence: str):
        checks.append({"name": name, "pass": bool(passed), "evidence": evidence[:300]})
    has_definition = (
        bool(re.search(r"retrieval[\W_]+augmented[\W_]+generation", low))
        or bool(re.search(r"\brag\b.{0,30}\b(?:is|means|stands for|short for)\b", low, re.S))
        or bool(re.search(r"\b(?:means|stands for|short for)\b.{0,50}\brag\b", low, re.S))
    )
    add("definition", has_definition,
        "Found a clear expansion or definition of RAG." if has_definition else "State what RAG stands for, or define RAG directly (for example, 'RAG is ...').")
    add("why_it_matters", any(x in low for x in ("why use", "why rag", "helps", "can help", "up-to-date", "updated", "because", "latest", "private", "company's", "company documents", "training may not", "not know", "own files")),
        "Look for a stated reason to use RAG.")
    has_search = any(x in low for x in ("retriev", "search", "find"))
    provides_context = "context" in low or bool(re.search(r"(?:give|provide|show|send).{0,60}(?:information|text|details|model)", low, re.S))
    explains_answer = any(x in low for x in ("generat", "write an answer", "create an answer", "model answers"))
    add("process", has_search and provides_context and explains_answer,
        "Explain the search, how found information is given to the AI, and how the AI uses it to answer.")
    add("example", any(x in low for x in ("example", "for example", "imagine")) and "?" in lesson and "answer" in low and ("find" in low or "retriev" in low),
        "A worked example should connect a question to found evidence and an answer.")
    add("limitations", any(x in low for x in ("limit", "wrong", "not guarantee", "may be")),
        "Mention that retrieval does not guarantee a correct answer.")
    false_retraining = bool(re.search(r"(?:retrain|train)\w*.{0,100}(?:every time|permanent|permanently|each question)", low, re.S)) or bool(re.search(r"(?:permanent|permanently).{0,100}(?:remember|knowledge|model)", low, re.S))
    add("no_false_retraining_claim", not false_retraining,
        "The lesson claims retrieval permanently retrains or updates model knowledge." if false_retraining else "No common false permanent-retraining claim detected; semantic evaluator checks facts too.")
    heading_pattern = re.compile(r"^\s*(?:#{1,6}\s*)?(?:\d+[.)]?\s*)?(what|how|example|recap|in summary)\b", re.I | re.M)
    found_headings = {m.group(1).lower() for m in heading_pattern.finditer(lesson)}
    required_headings = {"what", "how", "example"}
    has_recap = bool(found_headings & {"recap", "in summary"})
    missing_headings = sorted(required_headings - found_headings)
    if not has_recap:
        missing_headings.append("recap or in summary")
    add("structure", not missing_headings,
        "Missing lesson sections: " + ", ".join(missing_headings) if missing_headings else "Found What, How, Example, and recap sections.")
    add("length", 250 <= len(lesson.split()) <= 1400, f"Word count: {len(lesson.split())}; target 250–1400.")
    return checks

def parse_json_object(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Evaluator did not return a JSON object")
    result = json.loads(cleaned[start:end + 1])
    if not isinstance(result.get("pass"), bool) or not isinstance(result.get("checks"), list):
        raise ValueError("Evaluator JSON has an invalid schema")
    return result

def evaluate(lesson: str) -> dict:
    hard = deterministic_checks(lesson)
    failed_hard = [check for check in hard if not check["pass"]]
    if failed_hard:
        return {"pass": False, "checks": hard,
                "feedback": [check["evidence"] for check in failed_hard]}
    try:
        semantic = parse_json_object(call_model([
            {"role": "system", "content": "You are a strict but fair lesson evaluator. " + RUBRIC},
            {"role": "user", "content": "Evaluate this lesson:\n\n" + lesson},
        ]))
    except (ValueError, json.JSONDecodeError) as exc:
        semantic = {"pass": False, "checks": [{"name": "evaluator_integrity", "pass": False,
            "evidence": str(exc)}], "feedback": ["Repair model configuration or evaluator output; evaluation failed closed."]}
    all_checks = hard + semantic["checks"]
    passed = all(c.get("pass") is True for c in all_checks) and semantic["pass"] is True
    return {"pass": passed, "checks": all_checks, "feedback": semantic.get("feedback", [])}

def run(topic: str) -> dict:
    history = {"topic": topic, "started_at": datetime.now(timezone.utc).isoformat(), "attempts": []}
    hints = memory_hints(load_memory())
    feedback = ""
    for index in range(MAX_RETRIES + 1):
        prompt = f"Topic: {topic}\nLearner: Indian 12th-grade graduate, beginner, limited English vocabulary. In the opening, clearly explain that RAG means Retrieval-Augmented Generation and describe it in simple words. Explain why it helps when useful information is new or private. Explain each step: retrieve (search for) useful text, give it to the AI as context (information for this answer), then generate (write) an answer. Include a worked question, source text, and answer. Say that retrieval can still find wrong or old information and does not retrain the model. Use headings What, Why, How, Example, Limits, Recap. Avoid advanced tool names, algorithms, and unexplained technical terms."
        if hints:
            prompt += "\n\nMemory guidance: " + hints
        if feedback:
            prompt += "\n\nRevision required based on failed checks:\n" + feedback
        try:
            lesson = call_model([{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}])
            result = evaluate(lesson)
        except RuntimeError as exc:
            history["attempts"].append({"attempt": index + 1, "checks": [{"name": "provider_error", "pass": False, "evidence": str(exc)}], "feedback": [], "pass": False})
            history["status"] = "provider_error"
            history["error"] = str(exc)
            break
        history["attempts"].append({"attempt": index + 1, "checks": result["checks"], "feedback": result["feedback"], "pass": result["pass"]})
        if result["pass"]:
            history["status"] = "passed"
            history["lesson"] = lesson
            break
        failed = [c for c in result["checks"] if c.get("pass") is not True]
        feedback = "\n".join(f"- {c.get('name')}: {c.get('evidence', '')}" for c in failed)
        feedback += "\n" + "\n".join("- " + str(x) for x in result["feedback"])
    else:
        history["status"] = "rejected_after_max_retries"
    MEMORY.parent.mkdir(parents=True, exist_ok=True)
    with MEMORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(history, ensure_ascii=False) + "\n")
    if history["status"] == "passed":
        out = ROOT / "output" / "generated_lesson.md"
        out.write_text(history["lesson"], encoding="utf-8")
        print(f"PASS: lesson written to {out}")
    elif history["status"] == "provider_error":
        print("STOPPED: the model provider failed; see the provider_error in memory/lessons.jsonl")
        print(history["error"])
    else:
        print("REJECTED: maximum retries reached; see memory/lessons.jsonl")
    for attempt in history["attempts"]:
        print(f"Attempt {attempt['attempt']}: {'PASS' if attempt['pass'] else 'FAIL'}")
        for check in attempt["checks"]:
            if not check.get("pass"):
                print(f"  FAIL {check.get('name')}: {check.get('evidence', '')}")
    return history

def demo():
    lesson = (ROOT / "examples" / "demo_lesson.md").read_text(encoding="utf-8")
    checks = deterministic_checks(lesson)
    for check in checks:
        print(f"{'PASS' if check['pass'] else 'FAIL'} {check['name']}: {check['evidence']}")
    print("\nExpected key failure: the lesson falsely says RAG retrains the model. The semantic evaluator also checks factual grounding when run with a configured model.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    elif len(sys.argv) > 2 and sys.argv[1] == "generate":
        run(" ".join(sys.argv[2:]))
    else:
        print('Usage: python src/lessonforge.py demo | generate "topic"')
