#!/usr/bin/env python3
"""Generate Aran Kair's self-contained profile artwork.

Fonts live in this repository. Output SVGs contain no remote requests and use
only animation primitives supported by GitHub.
"""
from __future__ import annotations

import base64
import html
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FONT = ASSETS / "fonts" / "JetBrainsMono-Regular.woff2"
FAMILY = "KairMono,ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

# Handmade mark — no imported logo, no prior brand.
AK_MARK = [
    "    @@@@      @   @   ",
    "   @    @     @  @    ",
    "  @      @    @ @     ",
    "  @@@@@@@@    @@      ",
    "  @      @    @ @     ",
    "  @      @    @  @    ",
    "  @      @    @   @   ",
]


def font_css(text: str) -> str:
    """Embed a local WOFF2, subset when fontTools is available."""
    payload = FONT.read_bytes()
    try:
        from fontTools import subset

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "subset.woff2"
            options = subset.Options()
            options.flavor = "woff2"
            options.layout_features = ["*"]
            font = subset.load_font(str(FONT), options)
            subsetter = subset.Subsetter(options=options)
            subsetter.populate(text="".join(sorted(set(text))))
            subsetter.subset(font)
            subset.save_font(font, str(output_path), options)
            payload = output_path.read_bytes()
    except (ImportError, OSError):
        pass
    encoded = base64.b64encode(payload).decode("ascii")
    return (
        "@font-face{font-family:KairMono;font-style:normal;font-weight:100 800;"
        f"font-display:block;src:url(data:font/woff2;base64,{encoded}) format('woff2')}}"
    )


def shared_style(text: str) -> str:
    return (
        font_css(text)
        + ".ink{fill:#24292f}.muted{fill:#57606a}.faint{fill:#8c959f}"
        ".line{stroke:#d0d7de}.accent{fill:#0e7490}.accent-line{stroke:#0e7490}"
        ".panel{fill:#f6f8fa;stroke:#d0d7de}"
        "@media(prefers-color-scheme:dark){"
        ".ink{fill:#f0f6fc}.muted{fill:#b1bac4}.faint{fill:#6e7681}"
        ".line{stroke:#30363d}.accent{fill:#2dd4bf}.accent-line{stroke:#2dd4bf}"
        ".panel{fill:#161b22;stroke:#30363d}}"
        "@media(prefers-reduced-motion:reduce){.motion{display:none}}"
    )


def build_hero() -> str:
    labels = (
        "ARAN KAIR INDEPENDENT TECHNOLOGIST WORLD XYDEN "
        "LAB GITHUB ORGANIZATION SOFTWARE AI ROBOTICS OPEN SOURCE "
        + "".join(AK_MARK)
    )
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="620" height="360" '
        'viewBox="0 0 620 360" role="img" aria-labelledby="title desc">',
        '<title id="title">Aran Kair — independent technologist</title>',
        '<desc id="desc">Animated monogram with software, AI and robotics signals</desc>',
        f"<style>{shared_style(labels)}</style>",
        '<rect x=".5" y=".5" width="619" height="359" rx="12" class="panel"/>',
        '<path d="M24 55H596M24 305H596" class="line" opacity=".72"/>',
        '<circle cx="35" cy="28" r="3" class="accent"/>',
        '<text x="48" y="32" class="ink" font-family="KairMono" font-size="11" '
        'letter-spacing="1.8">ARAN KAIR / INDEPENDENT TECHNOLOGIST</text>',
        '<text x="596" y="32" text-anchor="end" class="faint" '
        'font-family="KairMono" font-size="9">WORLD</text>',
        '<text x="24" y="74" class="faint" font-family="KairMono" font-size="7" '
        'letter-spacing="1.1">MONOGRAM / AK</text>',
        '<circle cx="118" cy="72" r="2.5" class="accent motion">'
        '<animate attributeName="opacity" values=".2;1;.2" dur="1.4s" '
        'repeatCount="indefinite"/></circle>',
    ]
    x, y, line_height = 28, 108, 18
    for index, line in enumerate(AK_MARK):
        safe = html.escape(line)
        parts.append(
            f'<text x="{x}" y="{y + index * line_height:.1f}" '
            'class="muted" font-family="KairMono" font-size="15" '
            f'xml:space="preserve">{safe}'
            f'<animate attributeName="opacity" values="0;1" '
            f'begin="{0.4 + index * 0.38:.2f}s" dur=".7s" fill="freeze"/></text>'
        )
    parts.extend(
        [
            '<clipPath id="name-reveal"><rect x="28" y="248" width="0" height="28">'
            '<animate attributeName="width" from="0" to="250" begin="3.2s" '
            'dur="1.6s" fill="freeze"/></rect></clipPath>',
            '<text x="28" y="270" clip-path="url(#name-reveal)" class="ink" '
            'font-family="KairMono" font-size="22" font-weight="700" '
            'letter-spacing="3">ARAN KAIR</text>',
            '<g transform="translate(486 178)" opacity="0">',
            '<animate attributeName="opacity" from="0" to="1" begin="4.8s" '
            'dur=".8s" fill="freeze"/>',
            '<ellipse rx="88" ry="59" fill="none" class="line" stroke-dasharray="2 7"/>',
            '<ellipse rx="62" ry="91" fill="none" class="line" '
            'stroke-dasharray="1 8" transform="rotate(31)"/>',
            '<circle r="28" fill="none" class="accent-line" stroke-width="1.2"/>',
            '<circle r="20" class="panel"/>',
            '<text y="-2" text-anchor="middle" class="accent" font-family="KairMono" '
            'font-size="9" font-weight="700">XYDEN</text>',
            '<text y="10" text-anchor="middle" class="faint" font-family="KairMono" '
            'font-size="6">LAB / ORG</text>',
            '<circle r="3.5" class="accent motion"><animateMotion dur="10s" '
            'repeatCount="indefinite" path="M88 0A88 59 0 1 1 -88 0A88 59 0 1 1 88 0"/></circle>',
            '<circle r="2.5" class="muted motion"><animateMotion dur="13s" '
            'repeatCount="indefinite" path="M53 31A62 91 31 1 1 -53 -31A62 91 31 1 1 53 31"/></circle>',
            '<g transform="translate(-92 -45)"><circle r="4" class="accent"/>'
            '<text x="-8" y="-10" text-anchor="end" class="ink" font-family="KairMono" '
            'font-size="8">SOFTWARE</text></g>',
            '<g transform="translate(72 -65)"><circle r="4" class="accent"/>'
            '<text x="-8" y="-10" text-anchor="end" class="ink" font-family="KairMono" '
            'font-size="8">AI</text></g>',
            '<g transform="translate(69 72)"><circle r="4" class="accent"/>'
            '<text x="-8" y="16" text-anchor="end" class="ink" font-family="KairMono" '
            'font-size="8">ROBOTICS</text></g>',
            "</g>",
            '<text x="24" y="330" class="accent" font-family="KairMono" font-size="10">&gt;_</text>',
            '<text x="52" y="330" class="ink" font-family="KairMono" font-size="10">'
            "XYDEN  ·  LAB AND GITHUB ORGANIZATION</text>",
            '<rect x="392" y="319" width="7" height="14" class="accent motion">'
            '<animate attributeName="opacity" values="1;.15;1" dur="1.1s" '
            'repeatCount="indefinite"/></rect>',
            "</svg>",
        ]
    )
    return "".join(parts)


def build_projects() -> str:
    projects = [
        ("01", "VSARENA", "EMBODIED AI", "BROWSER ARENA · VLA · PUBLIC ELO"),
        ("02", "BEACON", "PLANETARY DATA", "JPL CAD · JPL SENTRY · ESA NEOCC"),
        ("03", "NOVACHECK", "AI SECURITY", "GHOST PACKAGES · SARIF · LOCAL-FIRST"),
    ]
    all_text = " ".join(" ".join(item) for item in projects)
    height = 8 + len(projects) * 76
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="620" height="{height}" '
        f'viewBox="0 0 620 {height}" role="img" '
        'aria-label="Selected systems by Aran Kair">',
        f"<style>{shared_style(all_text)}</style>",
    ]
    for index, (number, name, domain, detail) in enumerate(projects):
        y = index * 76 + 1
        p.extend(
            [
                f'<rect x=".5" y="{y}" width="619" height="67" rx="8" class="panel"/>',
                f'<text x="20" y="{y + 27}" class="accent" font-family="KairMono" '
                f'font-size="12">{number}</text>',
                f'<path d="M54 {y + 13}V{y + 54}" class="line"/>',
                f'<text x="72" y="{y + 27}" class="ink" font-family="KairMono" '
                f'font-size="15" font-weight="700">{name}</text>',
                f'<text x="72" y="{y + 47}" class="muted" font-family="KairMono" '
                f'font-size="9">{detail}</text>',
                f'<text x="598" y="{y + 27}" text-anchor="end" class="faint" '
                f'font-family="KairMono" font-size="8">{domain}</text>',
                f'<circle cx="588" cy="{y + 48}" r="3" class="accent">'
                f'<animate attributeName="opacity" values=".25;1;.25" '
                f'begin="{index * .4}s" dur="2.4s" repeatCount="indefinite"/></circle>',
                f'<path d="M560 {y + 48}H582" class="accent-line" '
                'stroke-dasharray="2 3"/>',
            ]
        )
    p.append("</svg>")
    return "".join(p)


def build_heading(label: str) -> str:
    safe = html.escape(label.upper())
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="620" height="34" '
        'viewBox="0 0 620 34">'
        f"<style>{shared_style(safe)}</style>"
        '<circle cx="5" cy="17" r="3" class="accent"/>'
        f'<text x="18" y="21" class="ink" font-family="KairMono" font-size="11" '
        f'letter-spacing="1.5">{safe}</text>'
        f'<path d="M{max(115, 34 + len(label) * 8)} 17H620" class="line"/>'
        "</svg>"
    )


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "hero.svg").write_text(build_hero(), encoding="utf-8")
    (ASSETS / "projects.svg").write_text(build_projects(), encoding="utf-8")
    for slug, label in (
        ("about", "Manifesto"),
        ("shipping", "Currently shipping"),
        ("signals", "Public signals"),
        ("contact", "Open channel"),
    ):
        (ASSETS / f"section-{slug}.svg").write_text(
            build_heading(label), encoding="utf-8"
        )
    print("generated hero, project cards, and section headings")


if __name__ == "__main__":
    main()
