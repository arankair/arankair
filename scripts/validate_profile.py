#!/usr/bin/env python3
"""Validate generated profile graphics and README references."""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def main() -> None:
    errors: list[str] = []
    svg_paths = sorted(ASSETS.glob("*.svg"))
    if not svg_paths:
        errors.append("no generated SVG assets found")

    for path in svg_paths:
        try:
            ElementTree.parse(path)
        except ElementTree.ParseError as error:
            errors.append(f"{path.relative_to(ROOT)}: invalid XML ({error})")
        content = path.read_text(encoding="utf-8")
        runtime_content = content.replace('xmlns="http://www.w3.org/2000/svg"', "")
        if "http://" in runtime_content or "https://" in runtime_content:
            errors.append(f"{path.relative_to(ROOT)}: remote runtime dependency")
        if "<script" in content.lower():
            errors.append(f"{path.relative_to(ROOT)}: scripts are stripped by GitHub")
        if "prefers-color-scheme:dark" not in content:
            errors.append(f"{path.relative_to(ROOT)}: missing dark-mode rules")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    banned = (
        "NovaCoding",
        "novacoding",
        "NovaCheck",
        "novacheck",
        "Roscino",
        "Giovannipaolo",
        "Gianpaolo",
        "Apulia",
        "Puglia",
        "18-year",
        "18 y",
        "biotech",
        "Biotechnology",
        "novacodingg",
        "NovaMono",
        "novabeacon",
    )
    scanned = [readme] + [path.read_text(encoding="utf-8") for path in svg_paths]
    scanned.extend(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "scripts").glob("*.py")
        if path.name != "validate_profile.py"
    )
    for blob in scanned:
        for term in banned:
            if term.lower() in blob.lower():
                errors.append(f"forbidden identity residue: {term}")
                break
    references = re.findall(r'<img[^>]+src="([^"]+)"', readme)
    for reference in references:
        target = ROOT / reference
        if not target.exists():
            errors.append(f"README.md: missing image {reference}")

    if errors:
        print("\n".join(f"ERROR {error}" for error in errors), file=sys.stderr)
        raise SystemExit(1)
    print(
        f"validated {len(svg_paths)} SVGs and "
        f"{len(references)} README image references"
    )


if __name__ == "__main__":
    main()
