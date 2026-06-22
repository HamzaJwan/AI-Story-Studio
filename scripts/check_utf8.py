from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTS = {".md", ".py", ".tsx", ".ts", ".jsx", ".js", ".json", ".yml", ".yaml", ".css", ".html"}

bad_files = []
for path in ROOT.rglob("*"):
    if any(part in {"node_modules", ".git", ".venv", "venv", "dist", "build"} for part in path.parts):
        continue
    if path.is_file() and path.suffix.lower() in EXTS:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            bad_files.append((str(path.relative_to(ROOT)), "not utf-8"))
            continue
        mojibake = sum(1 for ch in text if 0x0080 <= ord(ch) <= 0x00FF)
        if mojibake > 25 and ("Ø" in text or "Ù" in text):
            bad_files.append((str(path.relative_to(ROOT)), f"possible mojibake chars={mojibake}"))

if bad_files:
    print("❌ UTF-8 / Mojibake issues found:")
    for file, reason in bad_files:
        print(f"- {file}: {reason}")
    raise SystemExit(1)

print("✅ UTF-8 check passed")
