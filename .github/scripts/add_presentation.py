#!/usr/bin/env python3
"""Turn a submitted GitHub issue form into an entry in data/conferences.json.

Two modes:
  add    Read the issue form text, check it, and add or update the entry.
  reply  Post the outcome as a comment on the issue, and close it when all went well.
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "conferences.json"
PRESENTATIONS_DIR = ROOT / "presentations"

# Heading text in the issue (lowercase start) mapped to the field it fills.
FIELD_KEYS = [
    ("presentation title", "title"),
    ("conference name", "conference"),
    ("date presented", "date"),
    ("location", "location"),
    ("session type", "type"),
    ("short description", "description"),
    ("html demo", "demo"),
    ("slides file", "slides"),
]

EMPTY_VALUES = {"", "_no response_", "none"}
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"]
FOLDER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._\-]*(/[A-Za-z0-9][A-Za-z0-9._\-]*)*")
FILE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._()\-]*(/[A-Za-z0-9][A-Za-z0-9 ._()\-]*)*")
MAX_LENGTHS = {"title": 200, "conference": 200, "location": 120, "type": 60, "description": 800}


# Section: reading the form

def field_for_heading(heading):
    lowered = heading.strip().lower()
    for prefix, key in FIELD_KEYS:
        if lowered.startswith(prefix):
            return key
    return None


def parse_sections(body):
    """Split the issue text into {field: value}. Each answer sits under a '### Label' heading."""
    raw = {}
    current = None
    lines = []
    for line in body.replace("\r\n", "\n").split("\n"):
        key = field_for_heading(line[4:]) if line.startswith("### ") else None
        if key:
            if current:
                raw[current] = "\n".join(lines)
            current, lines = key, []
        elif current:
            lines.append(line)
    if current:
        raw[current] = "\n".join(lines)

    cleaned = {}
    for key, text in raw.items():
        text = re.sub(r"\s+", " ", text).strip()
        cleaned[key] = "" if text.lower() in EMPTY_VALUES else text
    return cleaned


def parse_date(text):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:80].strip("-") or "presentation"


# Section: links

def check_web_link(value, label):
    if not value.lower().startswith("https://"):
        raise ValueError(f"The {label} web link must start with https://")
    if re.search(r"\s", value):
        raise ValueError(f"The {label} web link cannot contain spaces.")
    return value


def strip_presentations_prefix(path):
    path = path.strip().strip("/")
    if path.lower().startswith("presentations/"):
        path = path[len("presentations/"):]
    return path


def resolve_demo(value, warnings):
    """Return (link, folder). The folder is the demo's own folder when it lives in this repository."""
    if not value:
        return "", ""
    if re.match(r"^https?://", value, re.I):
        return check_web_link(value, "HTML demo"), ""

    path = strip_presentations_prefix(value)
    if not FOLDER_PATTERN.fullmatch(path):
        raise ValueError(
            "The HTML demo should be a folder name such as concept-checks (letters, numbers, "
            "dots, underscores, and hyphens only), or a full web link starting with https://"
        )

    if path.lower().endswith((".html", ".htm")):
        folder = path.rsplit("/", 1)[0] if "/" in path else ""
        if not (PRESENTATIONS_DIR / path).is_file():
            warnings.append(f"I could not find presentations/{path} yet. The demo link will not work until you upload it.")
        return "presentations/" + path, folder

    if not (PRESENTATIONS_DIR / path / "index.html").is_file():
        warnings.append(
            f"I could not find presentations/{path}/index.html yet. "
            "The demo link will not work until you upload that folder."
        )
    return "presentations/" + path + "/", path


def resolve_slides(value, demo_folder, warnings):
    """Return (link, size_in_bytes_or_None) for the slides file."""
    if not value:
        return "", None
    if re.match(r"^https?://", value, re.I):
        return check_web_link(value, "slides file"), None

    path = strip_presentations_prefix(value)
    if "/" not in path and demo_folder:
        path = demo_folder + "/" + path
    if not FILE_PATTERN.fullmatch(path):
        raise ValueError(
            "The slides file should be a file name such as slides.pptx (letters, numbers, spaces, "
            "dots, parentheses, and hyphens only), or a full web link starting with https://"
        )

    link = "presentations/" + urllib.parse.quote(path, safe="/")
    target = PRESENTATIONS_DIR / path
    if target.is_file():
        return link, target.stat().st_size
    warnings.append(f"I could not find presentations/{path} yet. The slides link will not work until you upload it.")
    return link, None


# Section: building the entry

def build_entry(fields, issue_number):
    errors, warnings = [], []

    for key, label in (("title", "Presentation title"), ("conference", "Conference name"), ("date", "Date presented")):
        if not fields.get(key):
            errors.append(f"{label} is required.")
    for key, limit in MAX_LENGTHS.items():
        if len(fields.get(key, "")) > limit:
            errors.append(f"{key.capitalize()} is limited to {limit} characters.")

    when = None
    if fields.get("date"):
        when = parse_date(fields["date"])
        if when is None:
            errors.append("Date presented must look like 2026-03-12 (year, month, day).")

    demo_link, demo_folder = "", ""
    try:
        demo_link, demo_folder = resolve_demo(fields.get("demo", ""), warnings)
    except ValueError as exc:
        errors.append(str(exc))

    slides_link, slides_size = "", None
    try:
        slides_link, slides_size = resolve_slides(fields.get("slides", ""), demo_folder, warnings)
    except ValueError as exc:
        errors.append(str(exc))

    if errors:
        return None, errors, warnings

    entry = {
        "id": slugify(f"{fields['conference']} {fields['title']} {when.isoformat()}"),
        "issue": issue_number,
        "title": fields["title"],
        "conference": fields["conference"],
        "date": when.isoformat(),
    }
    for key, name in (("location", "location"), ("type", "type"), ("description", "description")):
        if fields.get(key):
            entry[name] = fields[key]
    if demo_link:
        entry["demoUrl"] = demo_link
    if slides_link:
        entry["slidesUrl"] = slides_link
    if slides_size:
        entry["slidesSize"] = slides_size
    if issue_number is None:
        del entry["issue"]
    return entry, errors, warnings


# Section: the data file

def load_entries():
    if not DATA_FILE.exists():
        return []
    data = json.loads(DATA_FILE.read_text(encoding="utf-8") or "[]")
    if isinstance(data, dict):
        data = data.get("presentations", [])
    if not isinstance(data, list):
        raise ValueError("data/conferences.json should hold a list of presentations.")
    return data


def upsert(entries, entry):
    """Update the entry that came from the same issue, or add a new one. Returns 'updated' or 'added'."""
    if entry.get("issue") is not None:
        for index, current in enumerate(entries):
            if current.get("issue") == entry["issue"]:
                entry["id"] = current.get("id", entry["id"])
                entries[index] = entry
                return "updated"

    taken = {current.get("id") for current in entries}
    base, number = entry["id"], 2
    while entry["id"] in taken:
        entry["id"] = f"{base}-{number}"
        number += 1
    entries.append(entry)
    return "added"


def save_entries(entries):
    entries.sort(key=lambda item: item.get("title", "").lower())
    entries.sort(key=lambda item: item.get("date", ""), reverse=True)
    with DATA_FILE.open("w", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


# Section: the two modes

def result_path():
    return Path(os.environ.get("RESULT_FILE") or "result.json")


def write_result(ok, message):
    result_path().write_text(json.dumps({"ok": ok, "message": message}), encoding="utf-8")


def site_address():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner.lower()}.github.io/{name}/"
    return "your landing page"


def run_add():
    number_text = os.environ.get("ISSUE_NUMBER", "")
    number = int(number_text) if number_text.isdigit() else None
    fields = parse_sections(os.environ.get("ISSUE_BODY", ""))

    entry, errors, warnings = build_entry(fields, number)
    if errors:
        message = (
            "I could not add this presentation yet:\n\n"
            + "\n".join(f"- {error}" for error in errors)
            + "\n\nEdit this issue to fix the details. The page will update as soon as you save your edit."
        )
        write_result(False, message)
        print(message)
        return

    entries = load_entries()
    action = upsert(entries, entry)
    save_entries(entries)

    message = (
        f"Presentation {action}: **{entry['title']}** ({entry['conference']}, {entry['date']}).\n\n"
        f"It should appear at {site_address()} within a minute or two."
    )
    if warnings:
        message += "\n\nA few things to check:\n\n" + "\n".join(f"- {warning}" for warning in warnings)
    write_result(True, message)
    print(message)


def github_request(method, path, payload):
    request = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}{path}",
        data=json.dumps(payload).encode("utf-8"),
        method=method,
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "conference-page-helper",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status


def run_reply():
    try:
        result = json.loads(result_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        result = {
            "ok": False,
            "message": "Something went wrong before I could read the form. Open the Actions tab of this repository to see the details.",
        }

    ok = bool(result.get("ok"))
    message = result.get("message", "")
    if ok and os.environ.get("JOB_STATUS", "success") != "success":
        ok = False
        message = (
            "I read the form correctly, but saving the change failed. "
            "Open the Actions tab of this repository to see the details, then edit this issue to try again."
        )

    number = os.environ.get("ISSUE_NUMBER", "")
    if not (os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPOSITORY") and number):
        print(message)
        return

    github_request("POST", f"/issues/{number}/comments", {"body": message})
    if ok:
        github_request("PATCH", f"/issues/{number}", {"state": "closed", "state_reason": "completed"})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "add":
        run_add()
    elif mode == "reply":
        run_reply()
    else:
        print("Usage: add_presentation.py add|reply")
        sys.exit(2)


if __name__ == "__main__":
    main()
