#!/usr/bin/env python3
"""Build Cloudflare's PDF upload-time manifest from Git history."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "DownloadFile"
manifest = {}

for pdf in sorted(DOWNLOADS.rglob("*")):
    if not pdf.is_file() or pdf.suffix.casefold() != ".pdf":
        continue
    relative = pdf.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ct", "--", relative],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    timestamp = result.stdout.strip()
    if not timestamp:
        raise SystemExit(f"No Git upload history found for {relative}")
    manifest[relative] = int(timestamp)

output = ROOT / "pdf-expiry.json"
output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"Wrote upload timestamps for {len(manifest)} PDFs to {output.name}")
