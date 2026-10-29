#!/usr/bin/env python3
"""Build a Pages artifact without deleting any PDFs from the repository.
PDF age is based on the latest Git commit that changed each file.
"""
from __future__ import annotations
import argparse
import html
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote


def latest_change(path: Path, repository: Path) -> datetime:
    relative_path = path.relative_to(repository).as_posix()
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ct", "--", relative_path],
        cwd=repository, check=True, capture_output=True, text=True
    )
    timestamp = result.stdout.strip()
    if not timestamp:
        raise RuntimeError(f"No Git history found for {relative_path}")
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)


def write_index(site: Path, source: Path, pdfs: list[tuple[Path, datetime]]) -> None:
    items = []
    for path, changed_at in pdfs:
        relative = quote(path.relative_to(source).as_posix(), safe="/")
        name = html.escape(path.name)
        updated = changed_at.strftime("%Y-%m-%d UTC")
        items.append(f"<li><a href=\"{relative}\">{name}</a> <small>Updated {updated}</small></li>")
    body = "".join(items) if items else "<li>No current PDF files are available.</li>"
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Available PDFs</title>
<style>body{{max-width:54rem;margin:3rem auto;padding:0 1.25rem;font:1rem/1.6 system-ui,sans-serif;color:#17202a}}ul{{padding:0;list-style:none}}li{{padding:.8rem 0;border-bottom:1px solid #d9e0e7}}small{{color:#596773;margin-left:1rem}}</style></head>
<body><main><h1>Available PDF files</h1><p>Files expire 365 days after their latest update. Expired files are omitted from this site and show its 404 page. Repository copies are retained.</p><ul>{body}</ul></main></body></html>
"""
    (site / "DownloadFile" / "index.html").write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--output", type=Path, default=Path("_site"))
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days must be a positive integer")

    repository = Path(__file__).resolve().parents[1]
    source = repository / "DownloadFile"
    if not source.is_dir():
        raise SystemExit("DownloadFile directory was not found")
    output = args.output if args.output.is_absolute() else repository / args.output
    if output == repository or output in repository.parents or output == source or source in output.parents:
        raise SystemExit("Output must not replace the repository or source PDF directory")
    if output.exists():
        shutil.rmtree(output)

    site_downloads = output / "DownloadFile"
    site_downloads.mkdir(parents=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    active: list[tuple[Path, datetime]] = []
    expired_count = 0
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        destination = site_downloads / path.relative_to(source)
        if path.suffix.casefold() == ".pdf":
            changed_at = latest_change(path, repository)
            if changed_at < cutoff:
                expired_count += 1
                continue
            active.append((path, changed_at))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

    custom_404 = repository / "404.html"
    if not custom_404.is_file():
        raise SystemExit("404.html must exist at the repository root")
    shutil.copy2(custom_404, output / "404.html")
    write_index(output, source, active)
    (output / "index.html").write_text(
        "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><title>PDF downloads</title>"
        "<h1>PDF downloads</h1><a href=\"DownloadFile/\">Browse available PDF files</a></html>\n",
        encoding="utf-8"
    )
    print(f"Published {len(active)} active PDFs; omitted {expired_count} expired PDFs.")


if __name__ == "__main__":
    main()
