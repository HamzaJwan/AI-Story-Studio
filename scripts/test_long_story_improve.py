"""Regression test for the manual-QA long-story improve fix (2026-06-25) and
the long-sentence-without-punctuation hardening fix (2026-06-26):

/api/story/improve must not misreport a slow request (long story, near the
model's context/time budget) as the generic "service unreachable" message,
and must split long stories into ordered chunks instead of sending one
oversized prompt that tends to time out -- including a pathological case
where the text has no `.!?؟` punctuation at all (e.g. one giant run-on
sentence), which previously caused `_split_long_paragraph()` to silently
truncate text instead of chunking it.

Hits the live backend over HTTP for the integration checks. The pure local
chunking-correctness check (`split_text_into_chunks`) additionally imports
`backend/app/story_engine/engine.py` directly -- this is a dependency-free
pure function (no I/O, no Ollama call), so this is the one script in this
repo that imports backend code instead of staying HTTP-only, specifically to
prove zero text loss byte-for-byte, which a live Ollama round-trip cannot
prove (the model is free to paraphrase/shorten).

NEVER prints story or improved-text content, only structural facts (character
counts, chunk_count, HTTP status, errors_count), per the manual-QA transcript
rule.

Requires the backend to be up. If Ollama itself is not reachable, the
integration checks verify the failure path returns a real connection error
(HTTP 200 envelope with a non-empty errors list) instead of raising an
unhandled exception, then skip the success-path (chunking) assertions.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://localhost:8810")

SHORT_STORY = (
    "كان يا ما كان، في قديم الزمان، راوٍ يحمل فانوساً قديماً يحكي للأطفال "
    "قصصاً عن الشجاعة والأمل في قريته الصغيرة."
)

_FILLER_PARAGRAPH = (
    "في ليلة من ليالي الشتاء الباردة، جلس الأطفال حول النار يستمعون إلى حكايات "
    "الراوي العجوز الذي كان يحمل فانوساً يضيء له الطريق بين القرى البعيدة.\n\n"
)

# One giant run-on "sentence" -- no periods/commas/newlines anywhere, the
# pathological case for the sentence-boundary splitter's fallback path.
_NO_PUNCTUATION_WORD = "كلمة"


def request(method: str, path: str, body: dict | None = None, timeout: int = 30) -> tuple[int, dict]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        sys.exit(1)


def build_long_story(chunk_chars: int) -> str:
    """Deterministic filler text sized to ~1.3x the chunk threshold -- enough
    to force at least 2 chunks, without being needlessly large (keeps the
    real Ollama verification call count low)."""
    target_len = int(chunk_chars * 1.3)
    parts: list[str] = []
    total = 0
    while total <= target_len:
        parts.append(_FILLER_PARAGRAPH)
        total += len(_FILLER_PARAGRAPH)
    return "".join(parts).strip()


def check_no_punctuation_chunking_is_lossless(chunk_chars: int) -> None:
    """Pure local check: a long run-on sentence with zero `.!?؟` punctuation
    must be split into chunks whose concatenation exactly reproduces the
    original text -- no character dropped, no truncation."""
    from app.story_engine.engine import split_text_into_chunks  # local import, see module docstring

    text = ((_NO_PUNCTUATION_WORD + " ") * 3000).strip()
    chunks = split_text_into_chunks(text, chunk_chars)
    reassembled = "".join(chunks)
    check("no-punctuation text: at least 2 chunks produced", len(chunks) > 1)
    check("no-punctuation text: every chunk respects the max_chars limit", all(len(c) <= chunk_chars for c in chunks))
    check("no-punctuation text: reassembled length matches original exactly (zero text loss)", len(reassembled) == len(text))
    check("no-punctuation text: reassembled content matches original exactly", reassembled == text)
    print(f"[INFO] no_punctuation_original_len={len(text)} chunk_count={len(chunks)} reassembled_len={len(reassembled)}")


def main() -> None:
    status, config_body = request("GET", "/api/config")
    check("GET /api/config returns 200", status == 200)
    chunk_chars = int(config_body.get("data", {}).get("long_story_chunk_chars") or 6000)
    print(f"[INFO] long_story_chunk_chars={chunk_chars}")

    check_no_punctuation_chunking_is_lossless(chunk_chars)

    status, health_body = request("GET", "/api/ai/ollama/health")
    ollama_ok = bool(health_body.get("data", {}).get("ok"))
    print(f"[INFO] ollama_health_status={status} ollama_ok={ollama_ok}")

    if not ollama_ok:
        status, body = request(
            "POST",
            "/api/story/improve",
            {"story_text": SHORT_STORY, "tone": "هادئ", "language": "ar"},
            timeout=30,
        )
        errors_count = len(body.get("errors", []))
        check("HTTP status is 200 (envelope, not an unhandled exception)", status == 200)
        check("Ollama-unavailable case returns a real error (errors_count > 0)", errors_count > 0)
        print(f"[INFO] http_status={status} errors_count={errors_count}")
        print("[SKIP] Ollama not reachable from this host -- cannot verify the success-path chunking behavior in this run.")
        return

    # 1) Short story stays a single request (no unnecessary chunking).
    status, body = request(
        "POST",
        "/api/story/improve",
        {"story_text": SHORT_STORY, "tone": "هادئ", "language": "ar"},
        timeout=240,
    )
    errors_count = len(body.get("errors", []))
    improved_len = len((body.get("data") or {}).get("improved_text") or "")
    chunk_count = (body.get("meta") or {}).get("chunk_count")
    check("short story: HTTP 200", status == 200)
    check("short story: no errors", errors_count == 0)
    check("short story: improved_text non-empty", improved_len > 0)
    check("short story: chunk_count == 1", chunk_count == 1)
    print(
        f"[INFO] short_story_chars={len(SHORT_STORY)} improved_chars={improved_len} "
        f"chunk_count={chunk_count} errors_count={errors_count}"
    )

    # 2) Long story must be chunked and must not fail with the misleading
    #    "connection" message that previously masked timeouts.
    long_story = build_long_story(chunk_chars)
    status, body = request(
        "POST",
        "/api/story/improve",
        {"story_text": long_story, "tone": "هادئ", "language": "ar"},
        timeout=600,
    )
    errors_count = len(body.get("errors", []))
    improved_len = len((body.get("data") or {}).get("improved_text") or "")
    chunk_count = (body.get("meta") or {}).get("chunk_count")
    check("long story: HTTP 200", status == 200)
    check("long story: no errors", errors_count == 0)
    check("long story: improved_text non-empty", improved_len > 0)
    check(
        "long story: chunk_count > 1 (sent as ordered chunks, not one oversized prompt)",
        bool(chunk_count) and chunk_count > 1,
    )
    print(
        f"[INFO] long_story_chars={len(long_story)} improved_chars={improved_len} "
        f"chunk_count={chunk_count} errors_count={errors_count}"
    )

    print("Long story improve test passed.")


if __name__ == "__main__":
    main()
