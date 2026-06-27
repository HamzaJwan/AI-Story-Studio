"""Optional small REAL Ollama smoke test for the streaming/auto-mood job
endpoint -- not run automatically as part of the main validation suite
(requires a reachable Ollama). Hamza will test the full 8986-char story
himself manually; this only proves the new job-based path (streaming +
auto-mood analysis + tone resolution) works end-to-end on one small synthetic
story (3200-4000 chars) without spending a long real run.

Never prints the story text, prompt, or improved output -- only structural
facts, per the manual-QA no-content-in-logs rule.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8810"

_FILLER = (
    "في صباح هادئ، جلس الراوي يستذكر تفاصيل رحلته الطويلة بين المدن القديمة والحديثة. "
)


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


def build_story(target_len: int) -> str:
    parts: list[str] = []
    total = 0
    while total < target_len:
        parts.append(_FILLER)
        total += len(_FILLER)
    return "".join(parts)[:target_len]


def main() -> None:
    status, health = request("GET", "/api/ai/ollama/health")
    if status != 200 or not health.get("data", {}).get("ok"):
        print("[SKIP] Ollama not reachable from this host -- cannot run the real smoke test.")
        return

    story = build_story(3600)
    started = time.monotonic()
    status, body = request(
        "POST",
        "/api/projects/smoke-test/story/improve/jobs",
        {"story_text": story, "tone": "تلقائي", "title": "اختبار دخان"},
        timeout=30,
    )
    if status != 200:
        print(f"input_chars={len(story)} resolved_tone=N/A chunk_count=N/A elapsed_seconds=N/A done_reason=N/A success=False")
        return
    job_id = body["data"]["job_id"]

    final_job = None
    while time.monotonic() - started < 240:
        status, body = request("GET", f"/api/jobs/{job_id}")
        job = body.get("data", {})
        if job.get("status") in ("done", "failed", "cancelled"):
            final_job = job
            break
        time.sleep(2)

    elapsed_seconds = round(time.monotonic() - started, 1)
    if final_job is None:
        print(f"input_chars={len(story)} resolved_tone=N/A chunk_count=N/A elapsed_seconds={elapsed_seconds} done_reason=N/A success=False (poll timed out)")
        return

    summary = final_job.get("result_summary") or {}
    success = final_job.get("status") == "done"
    print(
        f"input_chars={len(story)} "
        f"resolved_tone={summary.get('resolved_tone')} "
        f"chunk_count={summary.get('chunk_count')} "
        f"elapsed_seconds={elapsed_seconds} "
        f"done_reason=N/A(non-streaming-field-not-surfaced-to-job-summary) "
        f"success={success}"
    )


if __name__ == "__main__":
    main()
