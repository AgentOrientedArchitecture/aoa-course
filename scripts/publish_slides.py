#!/usr/bin/env python3
"""Publish course slide snapshots from aoa-knowledge into aoa-course.

The knowledge repo remains the source of truth. This script creates cleaned,
Marp-ready markdown copies for the public course repo:

- adds Marp frontmatter
- removes Obsidian/wiki-only source-anchor lines
- removes wiki source footers
- converts any remaining [[wiki-link]] text into plain labels
"""
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT.parent / "aoa-knowledge"
SOURCE_ROOT = KNOWLEDGE_ROOT / "course" / "2026-05-14-oreilly"

DECKS = {
    "01-agentic-inversion": "01-agentic-inversion",
    "02-anatomy-of-aoa": "02-anatomy-of-aoa",
    "03-aoa-in-the-real-world": "03-aoa-in-the-real-world",
    "04-lets-build": "04-lets-build",
}

WIKI_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def main() -> None:
    for source_name, target_name in DECKS.items():
        source = SOURCE_ROOT / source_name / "slides" / "deck.md"
        target = ROOT / "course" / "sessions" / target_name / "slides" / "deck.md"
        if not source.exists():
            raise FileNotFoundError(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(publish_deck(source.read_text(), source_name), encoding="utf-8")
        print(f"published {target.relative_to(ROOT)}")


def publish_deck(text: str, source_name: str) -> str:
    body = strip_frontmatter(text).strip()
    body = clean_body(body)
    title = first_heading(body) or source_name.replace("-", " ").title()
    frontmatter = marp_frontmatter(title)
    return f"{frontmatter}\n\n{body}\n"


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end == -1:
        return text
    return text[end + len("\n---") :]


def clean_body(text: str) -> str:
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Source anchors:"):
            continue
        if stripped.startswith("Source:") or stripped.startswith("Sources:"):
            continue
        if stripped.startswith("Source concept:"):
            continue
        cleaned_lines.append(clean_wiki_links(line))
    return "\n".join(cleaned_lines).strip()


def clean_wiki_links(line: str) -> str:
    def replace(match: re.Match[str]) -> str:
        path = match.group(1)
        alias = match.group(2)
        if alias:
            return alias
        label = path.rsplit("/", 1)[-1]
        return label.replace("-", " ")

    return WIKI_LINK_RE.sub(replace, line)


def first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def marp_frontmatter(title: str) -> str:
    return "\n".join(
        [
            "---",
            "marp: true",
            f'title: "{title}"',
            "theme: default",
            "paginate: true",
            "size: 16:9",
            "footer: Agent-Oriented Architecture - O'Reilly Live Course",
            "---",
        ]
    )


if __name__ == "__main__":
    main()
