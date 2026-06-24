"""Smoke test for the Phase 0.x project workspace endpoints.

Exercises the backend over HTTP only (no GPU, no TTS, no fake data):
health -> list -> create -> update -> scenes.json -> export.zip -> delete.
Run with the backend already up (e.g. `docker compose up -d backend`).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://localhost:8810")


def request(method: str, path: str, body: dict | None = None) -> tuple[int, bytes]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        sys.exit(1)


def main() -> None:
    status, body = request("GET", "/health")
    check("GET /health returns 200", status == 200)
    check("health status is ok", json.loads(body)["data"]["status"] == "ok")

    status, body = request("GET", "/api/projects")
    check("GET /api/projects returns 200", status == 200)

    status, body = request(
        "POST",
        "/api/projects",
        {
            "title": "Smoke Test Project",
            "original_story": "قصة اختبار قصيرة.",
            "improved_story": "",
            "scenes": [],
        },
    )
    check("POST /api/projects returns 200", status == 200)
    project = json.loads(body)["data"]
    project_id = project["project_id"]

    status, body = request(
        "PUT",
        f"/api/projects/{project_id}",
        {"title": "Smoke Test Project (updated)"},
    )
    check("PUT /api/projects/{id} returns 200", status == 200)

    status, body = request("GET", f"/api/projects/{project_id}/scenes.json")
    check("GET .../scenes.json returns 200", status == 200)

    status, body = request("GET", f"/api/projects/{project_id}/export.zip")
    check("GET .../export.zip returns 200", status == 200)
    check("export.zip body is non-empty", len(body) > 0)

    status, body = request("DELETE", f"/api/projects/{project_id}")
    check("DELETE /api/projects/{id} returns 200", status == 200)

    print("Smoke test passed.")


if __name__ == "__main__":
    main()
