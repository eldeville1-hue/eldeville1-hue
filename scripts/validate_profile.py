#!/usr/bin/env python3
"""Validate local image references, section anchors and SVG assets in the profile README."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

IMAGE_RE = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"', re.I)
MARKDOWN_LINK_RE = re.compile(r'\[[^]]+\]\(([^)]+)\)')
HTML_ANCHOR_RE = re.compile(r'<a\b[^>]*\bhref="([^"]+)"', re.I)
HEADING_RE = re.compile(r'^#{1,6}\s+(.+)$', re.M)


def local_file(target: str) -> Path | None:
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or target.startswith("#"):
        return None
    resolved = (ROOT / unquote(parsed.path)).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"Reference escapes repository: {target}")
    return resolved


def heading_anchor(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\[[^]]+\]\(([^)]+)\)', '', text)
    text = text.lower()
    text = re.sub(r'[^\w\- ]', '', text, flags=re.UNICODE)
    return text.replace(" ", "-")


def validate(readme: str) -> list[str]:
    errors: list[str] = []
    image_urls = IMAGE_RE.findall(readme)
    if not image_urls:
        errors.append("README has no local project images")

    for url in image_urls:
        try:
            path = local_file(url)
            if path is None:
                continue
            if not path.is_file():
                errors.append(f"Missing image: {url}")
                continue
            if path.suffix.lower() == ".svg":
                try:
                    element = ET.parse(path).getroot()
                    if element.tag != "{http://www.w3.org/2000/svg}svg":
                        errors.append(f"SVG root is invalid: {url}")
                    if not element.attrib.get("viewBox"):
                        errors.append(f"SVG missing viewBox: {url}")
                except ET.ParseError as exc:
                    errors.append(f"SVG parse error in {url}: {exc}")
        except ValueError as exc:
            errors.append(str(exc))

    anchors = {heading_anchor(h) for h in HEADING_RE.findall(readme)}
    refs = MARKDOWN_LINK_RE.findall(readme) + HTML_ANCHOR_RE.findall(readme)
    for url in refs:
        if url.startswith("#"):
            if unquote(url[1:]).lower() not in anchors:
                errors.append(f"Invalid section anchor: {url}")
        else:
            try:
                path = local_file(url)
                if path is not None and not path.exists():
                    errors.append(f"Missing local link: {url}")
            except ValueError as exc:
                errors.append(str(exc))
    return errors


def main() -> int:
    failures = validate(README.read_text(encoding="utf-8"))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("PASS: README local images, SVG parsing and section references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
