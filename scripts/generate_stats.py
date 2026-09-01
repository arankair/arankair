#!/usr/bin/env python3
"""Generate repository-owned GitHub signal graphics.

Uses GitHub GraphQL data at generation time. The resulting SVGs are fully
self-contained and never call a third-party service when viewed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from make_ascii import ASSETS, shared_style

LOGIN = os.environ.get("GITHUB_REPOSITORY_OWNER", "arankair")
TOKEN = os.environ.get("GITHUB_TOKEN")

QUERY = """
query Profile($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    followers { totalCount }
    repositories(
      first: 100
      ownerAffiliations: OWNER
      privacy: PUBLIC
      isFork: false
      orderBy: {field: PUSHED_AT, direction: DESC}
    ) {
      totalCount
      nodes {
        name
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""


def graphql() -> dict:
    if not TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN is required (locally: $env:GITHUB_TOKEN = gh auth token)"
        )
    now = datetime.now(timezone.utc)
    variables = {
        "login": LOGIN,
        "from": (now - timedelta(days=364)).isoformat(),
        "to": now.isoformat(),
    }
    payload = json.dumps({"query": QUERY, "variables": variables}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "arankair-profile-generator",
        },
    )
    result = None
    last_http_error: urllib.error.HTTPError | None = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.load(response)
            break
        except urllib.error.HTTPError as error:
            if error.code not in {502, 503, 504}:
                raise RuntimeError(
                    f"GitHub GraphQL returned HTTP {error.code}"
                ) from error
            last_http_error = error
            if attempt < 4:
                retry_after = error.headers.get("Retry-After")
                delay = min(float(retry_after), 30) if retry_after else 2**attempt
                print(
                    f"GitHub GraphQL returned HTTP {error.code}; "
                    f"retrying in {delay:g}s ({attempt + 1}/4)",
                    file=sys.stderr,
                )
                time.sleep(delay)
        except urllib.error.URLError:
            break

    if result is None:
        # Corporate and older Windows certificate stores can reject GitHub's
        # otherwise-valid chain. The CLI is also a final fallback after all
        # transient HTTP retries have been exhausted.
        try:
            completed = subprocess.run(
                [
                    "gh",
                    "api",
                    "graphql",
                    "-f",
                    f"query={QUERY}",
                    "-F",
                    f"login={variables['login']}",
                    "-F",
                    f"from={variables['from']}",
                    "-F",
                    f"to={variables['to']}",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(completed.stdout)
        except FileNotFoundError as error:
            raise RuntimeError("GitHub request failed and GitHub CLI is unavailable") from error
        except subprocess.CalledProcessError as error:
            detail = error.stderr.strip() or "unknown GitHub CLI error"
            raise RuntimeError(f"GitHub CLI GraphQL request failed: {detail}") from error
        except json.JSONDecodeError as error:
            raise RuntimeError("GitHub CLI returned invalid JSON") from error
        if last_http_error is not None:
            print(
                f"recovered from HTTP {last_http_error.code} via GitHub CLI",
                file=sys.stderr,
            )
    if result.get("errors"):
        messages = "; ".join(error["message"] for error in result["errors"])
        raise RuntimeError(f"GitHub GraphQL: {messages}")
    user = result.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user {LOGIN!r} was not found")
    return user


def contribution_days(user: dict) -> list[dict]:
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [
        day
        for week in weeks
        for day in week["contributionDays"]
        if date.fromisoformat(day["date"]) >= date.today() - timedelta(days=364)
    ]


def streaks(days: list[dict]) -> tuple[int, int]:
    counts = {date.fromisoformat(day["date"]): day["contributionCount"] for day in days}
    cursor = min(date.today(), max(counts, default=date.today()))
    if counts.get(cursor, 0) == 0:
        cursor -= timedelta(days=1)
    current = 0
    while counts.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)

    longest = running = 0
    for day in sorted(counts):
        running = running + 1 if counts[day] > 0 else 0
        longest = max(longest, running)
    return current, longest


def weekly_totals(days: list[dict]) -> list[int]:
    totals: dict[tuple[int, int], int] = defaultdict(int)
    for day in days:
        parsed = date.fromisoformat(day["date"])
        iso = parsed.isocalendar()
        totals[(iso.year, iso.week)] += day["contributionCount"]
    return [totals[key] for key in sorted(totals)][-52:]


def build_stats(user: dict, days: list[dict]) -> str:
    calendar = user["contributionsCollection"]["contributionCalendar"]
    total = calendar["totalContributions"]
    active = sum(day["contributionCount"] > 0 for day in days)
    current, longest = streaks(days)
    repositories = user["repositories"]
    stars = sum(repo["stargazerCount"] for repo in repositories["nodes"])
    followers = user["followers"]["totalCount"]
    values = weekly_totals(days)
    max_value = max(values, default=1)
    x_step = 572 / max(1, len(values) - 1)
    points = " ".join(
        f"{24 + index * x_step:.1f},{154 - value / max_value * 43:.1f}"
        for index, value in enumerate(values)
    )
    text = (
        f"PUBLIC SIGNALS {total} CONTRIBUTIONS {active} ACTIVE DAYS "
        f"{current} CURRENT STREAK {longest} LONGEST STREAK "
        f"{repositories['totalCount']} REPOSITORIES {stars} STARS {followers} FOLLOWERS"
    )
    cards = [
        (str(total), "CONTRIBUTIONS / 365D"),
        (str(active), "ACTIVE DAYS"),
        (f"{current} / {longest}", "CURRENT / LONGEST"),
        (f"{stars} / {followers}", "STARS / FOLLOWERS"),
    ]
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="620" height="176" '
        'viewBox="0 0 620 176" role="img" aria-label="Aran Kair public GitHub signals">',
        f"<style>{shared_style(text)}</style>",
        '<rect x=".5" y=".5" width="619" height="175" rx="10" class="panel"/>',
        '<text x="20" y="26" class="faint" font-family="KairMono" font-size="8" '
        f'letter-spacing="1.4">PUBLIC GITHUB · {days[0]["date"]} — {days[-1]["date"]}</text>',
    ]
    for index, (value, label) in enumerate(cards):
        x = 20 + index * 150
        svg.extend(
            [
                f'<text x="{x}" y="61" class="ink" font-family="KairMono" '
                f'font-size="22" font-weight="700">{value}</text>',
                f'<text x="{x}" y="79" class="muted" font-family="KairMono" '
                f'font-size="7.5">{label}</text>',
            ]
        )
    svg.extend(
        [
            '<path d="M20 96H600" class="line"/>',
            '<text x="20" y="111" class="faint" font-family="KairMono" font-size="7">'
            "CONTRIBUTIONS / WEEK</text>",
            f'<polyline points="{points}" fill="none" class="accent-line" '
            'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
            'pathLength="1" stroke-dasharray="1" stroke-dashoffset="1">'
            '<animate attributeName="stroke-dashoffset" from="1" to="0" begin=".2s" '
            'dur="1.4s" fill="freeze"/></polyline>',
            '<path d="M20 154H600" class="line" opacity=".45"/>',
            "</svg>",
        ]
    )
    return "".join(svg)


def language_data(user: dict) -> list[tuple[str, int, int, str]]:
    byte_totals: Counter[str] = Counter()
    repo_totals: Counter[str] = Counter()
    colors: dict[str, str] = {}
    for repo in user["repositories"]["nodes"]:
        present: set[str] = set()
        for edge in repo["languages"]["edges"]:
            language = edge["node"]["name"]
            byte_totals[language] += edge["size"]
            colors[language] = edge["node"].get("color") or "#8c959f"
            present.add(language)
        repo_totals.update(present)
    return [
        (language, size, repo_totals[language], colors[language])
        for language, size in byte_totals.most_common(7)
    ]


def build_languages(user: dict) -> str:
    languages = language_data(user)
    total_bytes = sum(size for _, size, _, _ in languages) or 1
    max_repos = max((repos for _, _, repos, _ in languages), default=1)
    height = max(150, 64 + len(languages) * 23)
    text = "LANGUAGE SIGNAL " + " ".join(language for language, *_ in languages)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="620" height="{height}" '
        f'viewBox="0 0 620 {height}" role="img" '
        'aria-label="Languages across public repositories">',
        f"<style>{shared_style(text)}</style>",
        f'<rect x=".5" y=".5" width="619" height="{height - 1}" rx="10" class="panel"/>',
        '<text x="20" y="27" class="faint" font-family="KairMono" font-size="8" '
        'letter-spacing="1.3">LANGUAGE SIGNAL · PUBLIC REPOSITORIES</text>',
        '<text x="440" y="27" class="faint" font-family="KairMono" font-size="7">'
        "BYTES</text>",
        '<text x="598" y="27" text-anchor="end" class="faint" '
        'font-family="KairMono" font-size="7">REPO REACH</text>',
    ]
    for index, (name, size, repos, _color) in enumerate(languages):
        y = 51 + index * 23
        byte_width = size / total_bytes * 195
        repo_width = repos / max_repos * 105
        percent = size / total_bytes * 100
        svg.extend(
            [
                f'<text x="20" y="{y + 5}" class="ink" font-family="KairMono" '
                f'font-size="9">{name.upper()}</text>',
                f'<rect x="185" y="{y - 4}" width="195" height="7" rx="3.5" '
                'class="line" opacity=".18"/>',
                f'<rect x="185" y="{y - 4}" width="{byte_width:.1f}" height="7" '
                'rx="3.5" class="accent"/>',
                f'<text x="390" y="{y + 4}" class="muted" font-family="KairMono" '
                f'font-size="7">{percent:4.1f}%</text>',
                f'<path d="M458 {y - 1}H{458 + repo_width:.1f}" class="accent-line" '
                'stroke-width="3" stroke-linecap="round"/>',
                f'<text x="598" y="{y + 4}" text-anchor="end" class="muted" '
                f'font-family="KairMono" font-size="7">{repos} REPOS</text>',
            ]
        )
    svg.append("</svg>")
    return "".join(svg)


def build_year(days: list[dict]) -> str:
    symbols = {"NONE": "·", "FIRST_QUARTILE": ":", "SECOND_QUARTILE": "+", "THIRD_QUARTILE": "#", "FOURTH_QUARTILE": "@"}
    text = "THE LAST 365 DAYS " + "".join(symbols.values())
    start_x, start_y, step_x, step_y = 112, 41, 9.1, 12
    by_week: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for day in days:
        parsed = date.fromisoformat(day["date"])
        iso = parsed.isocalendar()
        by_week[(iso.year, iso.week)].append(day)
    weeks = [by_week[key] for key in sorted(by_week)][-53:]
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="620" height="145" '
        'viewBox="0 0 620 145" role="img" aria-label="The last year of public contributions">',
        f"<style>{shared_style(text)}</style>",
        '<rect x=".5" y=".5" width="619" height="144" rx="10" class="panel"/>',
        '<text x="20" y="25" class="faint" font-family="KairMono" font-size="8" '
        'letter-spacing="1.3">THE LAST 365 DAYS · ONE CHARACTER PER DAY</text>',
    ]
    for week_index, week in enumerate(weeks):
        for day in week:
            weekday = date.fromisoformat(day["date"]).weekday()
            symbol = symbols[day["contributionLevel"]]
            css_class = "accent" if day["contributionCount"] else "faint"
            svg.append(
                f'<text x="{start_x + week_index * step_x:.1f}" '
                f'y="{start_y + weekday * step_y:.1f}" class="{css_class}" '
                f'font-family="KairMono" font-size="10">{symbol}</text>'
            )
    for weekday, label in ((0, "MON"), (2, "WED"), (4, "FRI"), (6, "SUN")):
        svg.append(
            f'<text x="20" y="{start_y + weekday * step_y:.1f}" class="faint" '
            f'font-family="KairMono" font-size="7">{label}</text>'
        )
    svg.extend(
        [
            '<text x="20" y="130" class="faint" font-family="KairMono" font-size="7">'
            "QUIET  ·  :  +  #  @  LOUD</text>",
            "</svg>",
        ]
    )
    return "".join(svg)


def main() -> None:
    user = graphql()
    days = contribution_days(user)
    if not days:
        raise RuntimeError("GitHub returned an empty contribution calendar")
    ASSETS.mkdir(exist_ok=True)
    outputs = {
        "stats.svg": build_stats(user, days),
        "languages.svg": build_languages(user),
        "year.svg": build_year(days),
    }
    changed = []
    for name, content in outputs.items():
        path = ASSETS / name
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
            changed.append(name)
    print("updated " + ", ".join(changed) if changed else "statistics already current")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
