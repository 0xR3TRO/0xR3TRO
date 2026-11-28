#!/usr/bin/env python3
"""Generate animated dark-mode GitHub profile SVG assets for 0xR3TRO (Option 3: Swiss Terminal & Executive Minimal)."""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = os.environ.get("GH_USERNAME", "0xR3TRO")
OUTPUT_DIR = Path(os.environ.get("ASSETS_DIR", "assets"))

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    name
    repositories(first: 100, ownerAffiliations: OWNER) {
      totalCount
      nodes {
        name
        isPrivate
        stargazerCount
        primaryLanguage { name color }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
            weekday
            color
          }
        }
      }
    }
  }
}
"""


def fetch_stats() -> dict:
    local_json = os.environ.get("LOCAL_STATS_JSON")
    if local_json and Path(local_json).exists():
        raw = json.loads(Path(local_json).read_text(encoding="utf-8"))
        return raw["data"].get("viewer") or raw["data"].get("user")

    token = os.environ.get("GH_STATS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("Missing GH_STATS_TOKEN or GITHUB_TOKEN")

    use_viewer = bool(os.environ.get("GH_STATS_TOKEN"))
    query = GRAPHQL_QUERY.replace("user(login: $login)", "viewer") if use_viewer else GRAPHQL_QUERY
    payload = {"query": query} if use_viewer else {"query": query, "variables": {"login": USERNAME}}

    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "0xR3TRO-profile-generator",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")
    return data["data"].get("viewer") or data["data"].get("user")


def compute_metrics(user: dict) -> dict:
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    active_days = [d for d in days if d["contributionCount"] > 0]

    streak = 0
    idx = len(days) - 1
    if idx >= 0 and days[idx]["contributionCount"] == 0:
        idx -= 1
    while idx >= 0 and days[idx]["contributionCount"] > 0:
        streak += 1
        idx -= 1

    # Weekday distribution Mon..Sun (GitHub weekday: 0=Sun, 1=Mon..6=Sat)
    raw_wd = {i: 0 for i in range(7)}
    for d in days:
        raw_wd[d["weekday"]] += d["contributionCount"]
    weekdays = [
        ("MON", raw_wd[1]),
        ("TUE", raw_wd[2]),
        ("WED", raw_wd[3]),
        ("THU", raw_wd[4]),
        ("FRI", raw_wd[5]),
        ("SAT", raw_wd[6]),
        ("SUN", raw_wd[0]),
    ]

    repos = user["repositories"]["nodes"]
    total_repos = user["repositories"]["totalCount"]
    public_repos = sum(1 for r in repos if not r.get("isPrivate"))
    private_repos = max(total_repos - public_repos, 0)

    return {
        "weeks": weeks,
        "total_contributions": cal["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "total_repos": total_repos,
        "public_repos": public_repos,
        "private_repos": private_repos,
        "active_days_count": len(active_days),
        "streak": streak,
        "weekdays": weekdays,
    }


def swiss_color(count: int) -> tuple[str, int]:
    if count <= 0:
        return "#161b22", 0
    if count <= 3:
        return "#144620", 1
    if count <= 12:
        return "#1f6f33", 2
    if count <= 30:
        return "#2ea043", 3
    return "#3fb950", 4


def fmt_num(n: int) -> str:
    return f"{n:,}"


def render_header_matrix(m: dict) -> str:
    weeks = m["weeks"][-53:]
    w_svg, h_svg = 880, 232
    cell = 12.2
    gap = 3.2
    step = cell + gap
    start_x = 32
    start_y = 102

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_labels = []
    last_month = None
    last_x = -100
    for wi, w in enumerate(weeks):
        if not w["contributionDays"]:
            continue
        mon = int(w["contributionDays"][0]["date"][5:7])
        x = start_x + wi * step
        if mon != last_month and (x - last_x) >= 34:
            month_labels.append(
                f'<text x="{x:.1f}" y="{start_y - 9}" class="mono-xs" fill="#6e7681">{month_names[mon - 1]}</text>'
            )
            last_month = mon
            last_x = x

    cells = []
    for wi, w in enumerate(weeks):
        x = start_x + wi * step
        delay = (wi * 0.045) % 4.0
        for day in w["contributionDays"]:
            wd = day["weekday"]
            y = start_y + wd * step
            cnt = day["contributionCount"]
            fill, lvl = swiss_color(cnt)
            cls = "act" if lvl > 0 else "idle"
            cells.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="2" '
                f'fill="{fill}" class="{cls}" style="animation-delay:{delay:.2f}s">'
                f'<title>{escape(day["date"])}: {cnt} contributions</title></rect>'
            )

    legend = ["#161b22", "#144620", "#1f6f33", "#2ea043", "#3fb950"]
    legend_svg = "".join(
        f'<rect x="{748 + i * 15}" y="213" width="10.5" height="10.5" rx="2" fill="{c}"/>'
        for i, c in enumerate(legend)
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="100%" role="img" aria-label="0xR3TRO Header and Contribution Matrix">
  <style>
    .wordmark {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 23px; font-weight: 700; letter-spacing: 0.6px; }}
    .tagline {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 12px; }}
    .stat-big {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 22px; font-weight: 700; }}
    .mono-xs {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 9.5px; }}
    .mono-xxs {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 8.5px; }}
    .cursor {{ animation: blink 1.15s step-end infinite; }}
    .act {{ animation: softPulse 4.2s ease-in-out infinite; }}
    .idle {{ opacity: 0.92; }}
    @keyframes blink {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}
    @keyframes softPulse {{ 0%, 100% {{ opacity: 0.85; }} 50% {{ opacity: 1; }} }}
  </style>

  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="10" fill="#0d1117" stroke="#21262d" stroke-width="1"/>

  <!-- Typographic Masthead -->
  <text x="32" y="40" class="wordmark" fill="#e6edf3">0xR3TRO</text>
  <rect x="132" y="38" width="10" height="2.5" fill="#3fb950" class="cursor"/>
  <text x="32" y="60" class="tagline" fill="#8b949e">Verifiable systems for adversarial digital environments.</text>

  <!-- Right Stat Readout -->
  <text x="720" y="39" text-anchor="end" class="stat-big" fill="#3fb950">{fmt_num(m["total_contributions"])}</text>
  <text x="720" y="55" text-anchor="end" class="mono-xxs" fill="#8b949e">CONTRIBUTIONS / 12M</text>

  <line x1="740" y1="22" x2="740" y2="58" stroke="#21262d" stroke-width="1"/>

  <text x="848" y="39" text-anchor="end" class="stat-big" fill="#e6edf3">{fmt_num(m["commits"])}</text>
  <text x="848" y="55" text-anchor="end" class="mono-xxs" fill="#8b949e">COMMITS</text>

  <!-- Hairline Divider -->
  <line x1="24" y1="74" x2="856" y2="74" stroke="#21262d" stroke-width="1"/>

  <!-- Month & Day Labels -->
  {"".join(month_labels)}
  <text x="12" y="{start_y + step + 9.5:.1f}" class="mono-xxs" fill="#484f58">M</text>
  <text x="12" y="{start_y + 3 * step + 9.5:.1f}" class="mono-xxs" fill="#484f58">W</text>
  <text x="12" y="{start_y + 5 * step + 9.5:.1f}" class="mono-xxs" fill="#484f58">F</text>

  <!-- Grid -->
  <g>{"".join(cells)}</g>

  <!-- Footer -->
  <text x="32" y="221" class="mono-xxs" fill="#6e7681">contribution activity · auto-synced via GitHub Actions</text>
  <text x="740" y="221" text-anchor="end" class="mono-xxs" fill="#6e7681">Less</text>
  {legend_svg}
  <text x="828" y="221" class="mono-xxs" fill="#6e7681">More</text>
</svg>
'''


def render_metrics_bento(m: dict) -> str:
    w_svg, h_svg = 880, 294

    # Weekly rhythm 7-bar chart
    weekdays = m["weekdays"]
    max_wd = max(v for _, v in weekdays) or 1
    log_max = math.log1p(max_wd)

    chart_x = 480
    chart_base_y = 250
    max_h = 68.0
    col_step = 52.0
    bar_w = 26.0

    wd_bars = []
    for i, (day_lbl, cnt) in enumerate(weekdays):
        frac = math.log1p(cnt) / log_max if log_max > 0 else 0.15
        bh = max(8.0, frac * max_h)
        bx = chart_x + i * col_step
        by = chart_base_y - bh
        is_peak = cnt == max_wd
        fill = "#3fb950" if is_peak else "#30363d"
        val_col = "#3fb950" if is_peak else "#8b949e"
        wd_bars.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" rx="4" fill="{fill}" '
            f'class="wbar" style="animation-delay:{i * 0.08:.2f}s"/>'
            f'<text x="{bx + bar_w / 2:.1f}" y="{by - 6:.1f}" text-anchor="middle" class="mono-xxs" fill="{val_col}">{cnt}</text>'
            f'<text x="{bx + bar_w / 2:.1f}" y="{chart_base_y + 15}" text-anchor="middle" class="mono-xxs" fill="#6e7681">{day_lbl}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="100%" role="img" aria-label="0xR3TRO Terminal Profile and Metrics">
  <style>
    .mono-win {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 10px; }}
    .mono-code {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 11px; }}
    .mono-kpi {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 24px; font-weight: 700; }}
    .mono-lbl {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 9px; font-weight: 600; letter-spacing: 0.7px; }}
    .mono-xs {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 10px; }}
    .mono-xxs {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 8.8px; }}
    .line-in {{ animation: fadeSlide 0.6s ease-out both; }}
    .cursor {{ animation: blink 1.1s step-end infinite; }}
    .wbar {{ transform-box: fill-box; transform-origin: bottom; animation: barUp 0.8s ease-out both; }}
    @keyframes fadeSlide {{ from {{ opacity: 0; transform: translateY(3px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    @keyframes blink {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}
    @keyframes barUp {{ from {{ transform: scaleY(0.12); opacity: 0.3; }} to {{ transform: scaleY(1); opacity: 1; }} }}
  </style>

  <!-- Outer Frame -->
  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="10" fill="#0d1117" stroke="#21262d" stroke-width="1"/>

  <!-- LEFT PANEL: Minimalist Unix Terminal (Replaces Profile Photo) -->
  <rect x="16" y="16" width="432" height="262" rx="9" fill="#090d12" stroke="#21262d" stroke-width="1"/>
  <!-- Window Header Bar -->
  <path d="M16 25 A9 9 0 0 1 25 16 H439 A9 9 0 0 1 448 25 V42 H16 Z" fill="#161b22"/>
  <line x1="16" y1="42" x2="448" y2="42" stroke="#21262d" stroke-width="1"/>
  <circle cx="32" cy="29" r="4" fill="#30363d"/>
  <circle cx="46" cy="29" r="4" fill="#30363d"/>
  <circle cx="60" cy="29" r="4" fill="#30363d"/>
  <text x="232" y="32.5" text-anchor="middle" class="mono-win" fill="#8b949e">0xR3TRO@ops — profile.toml</text>

  <!-- Terminal Output -->
  <g class="mono-code">
    <text x="32" y="66" class="line-in" style="animation-delay:0.05s"><tspan fill="#3fb950">$</tspan><tspan fill="#e6edf3"> cat profile.toml</tspan></text>

    <text x="32" y="92" class="line-in" style="animation-delay:0.15s"><tspan fill="#8b949e">handle    = </tspan><tspan fill="#e6edf3">"0xR3TRO"</tspan></text>
    <text x="32" y="114" class="line-in" style="animation-delay:0.25s"><tspan fill="#8b949e">stance    = </tspan><tspan fill="#3fb950">"Anonymity is not a mask, it's a shield."</tspan></text>
    <text x="32" y="136" class="line-in" style="animation-delay:0.35s"><tspan fill="#8b949e">domains   = </tspan><tspan fill="#e6edf3">["Security", "Web3", "AI", "Platform"]</tspan></text>
    <text x="32" y="158" class="line-in" style="animation-delay:0.45s"><tspan fill="#8b949e">ecosystem = </tspan><tspan fill="#e6edf3">"6 programs / 17 private modules"</tspan></text>
    <text x="32" y="180" class="line-in" style="animation-delay:0.55s"><tspan fill="#8b949e">principle = </tspan><tspan fill="#c9d1d9">"measurable effect · bounded risk"</tspan></text>

    <line x1="32" y1="198" x2="432" y2="198" stroke="#1b222c" stroke-width="1"/>

    <text x="32" y="222" class="line-in" style="animation-delay:0.65s"><tspan fill="#3fb950">$</tspan><tspan fill="#e6edf3"> verify --integrity</tspan></text>
    <text x="32" y="246" class="line-in" style="animation-delay:0.75s"><tspan fill="#3fb950">✓</tspan><tspan fill="#8b949e"> provenance valid · </tspan><tspan fill="#e6edf3">17/17 modules tracked</tspan></text>
    <rect x="316" y="236" width="7" height="12" rx="1" fill="#3fb950" class="cursor"/>
  </g>

  <!-- RIGHT PANEL: Minimalist KPI Row -->
  <rect x="464" y="16" width="126" height="72" rx="9" fill="#12171e" stroke="#21262d" stroke-width="1"/>
  <text x="478" y="50" class="mono-kpi" fill="#3fb950">{fmt_num(m["total_contributions"])}</text>
  <text x="478" y="72" class="mono-lbl" fill="#8b949e">12M ACTIVITY</text>

  <rect x="601" y="16" width="126" height="72" rx="9" fill="#12171e" stroke="#21262d" stroke-width="1"/>
  <text x="615" y="50" class="mono-kpi" fill="#e6edf3">{fmt_num(m["commits"])}</text>
  <text x="615" y="72" class="mono-lbl" fill="#8b949e">COMMITS</text>

  <rect x="738" y="16" width="126" height="72" rx="9" fill="#12171e" stroke="#21262d" stroke-width="1"/>
  <text x="752" y="50" class="mono-kpi" fill="#e6edf3">{m["total_repos"]}</text>
  <text x="752" y="72" class="mono-lbl" fill="#8b949e">REPOS ({m["public_repos"]}/{m["private_repos"]})</text>

  <!-- Inline Secondary Strip -->
  <rect x="464" y="98" width="400" height="32" rx="8" fill="#12171e" stroke="#21262d" stroke-width="1"/>
  <text x="664" y="117.5" text-anchor="middle" class="mono-xs" fill="#8b949e">
    <tspan fill="#e6edf3">{m["prs"]}</tspan> PRs  ·  <tspan fill="#e6edf3">{m["issues"]}</tspan> Issues  ·  <tspan fill="#e6edf3">{m["active_days_count"]}</tspan> Active Days  ·  <tspan fill="#3fb950">{m["streak"]}d Streak</tspan>
  </text>

  <!-- Weekly Rhythm Bar Chart -->
  <rect x="464" y="140" width="400" height="138" rx="9" fill="#12171e" stroke="#21262d" stroke-width="1"/>
  <text x="480" y="160" class="mono-lbl" fill="#c9d1d9">WEEKLY RHYTHM</text>
  <text x="848" y="160" text-anchor="end" class="mono-xxs" fill="#6e7681">MON – SUN · LOG SCALE</text>
  <line x1="480" y1="250" x2="848" y2="250" stroke="#21262d" stroke-width="1"/>
  {"".join(wd_bars)}
</svg>
'''


def render_ecosystem_matrix() -> str:
    w_svg, h_svg = 880, 290

    stages = [
        ("Planned", False),
        ("Created-private", True),
        ("Bootstrapped", False),
        ("Vertical-slice", False),
        ("Internal-verified", False),
        ("Public-release", False),
        ("Maintained", False),
    ]
    stage_svg = []
    sx = 48.0
    for i, (name, active) in enumerate(stages):
        sw = len(name) * 6.0 + 22
        if active:
            stage_svg.append(
                f'<rect x="{sx:.1f}" y="38" width="{sw:.1f}" height="24" rx="12" fill="#0f2419" stroke="#3fb950" stroke-width="1.1"/>'
                f'<circle cx="{sx + 10:.1f}" cy="50" r="3" fill="#3fb950"/>'
                f'<text x="{sx + sw / 2 + 4:.1f}" y="53.5" text-anchor="middle" class="mono-stage-act" fill="#3fb950">{name}</text>'
            )
        else:
            stage_svg.append(
                f'<rect x="{sx:.1f}" y="38" width="{sw:.1f}" height="24" rx="12" fill="#12171e" stroke="#21262d" stroke-width="1"/>'
                f'<text x="{sx + sw / 2:.1f}" y="53.5" text-anchor="middle" class="mono-stage" fill="#6e7681">{name}</text>'
            )
        if i < len(stages) - 1:
            ax = sx + sw + 3
            stage_svg.append(f'<line x1="{ax:.1f}" y1="50" x2="{ax + 10:.1f}" y2="50" stroke="#30363d" stroke-width="1"/>')
        sx += sw + 16

    programs = [
        ("01", "FOUNDATION PROTOCOL", "Contracts, telemetry, automation runtime & assurance", "0xS3NT1N3L · 0xF0RG3 · PR00FCHAIN · N0CTURN"),
        ("02", "SOC SIGNAL NETWORK", "End-to-end signal correlation to case & decision", "S1GNAL-MESH · PR1SM-CASE · 1NT3LGR4PH · N3XUS-C0NS0L3"),
        ("03", "VERIFIABLE INTELLIGENCE", "Citation-bound AI search, policy & red-team regression", "V3R1TAS · N0M1N4L · BL4CK-1C3"),
        ("04", "TRUST FABRIC", "Cryptography, sealed evidence, anchoring & DID", "C1PH3R-VAULT · M3RKLE-LENS · D1D-ATLAS"),
        ("05", "ONCHAIN THREAT SURFACE", "Protocol security workbench & ledger intelligence", "CHAIN//FAULT · 0xLEDGER"),
        ("06", "OPERATIONS REFERENCE", "Reference deployment validating the full ecosystem", "0xC0R3-OPS"),
    ]

    rows_svg = []
    for idx, (num, title, desc, mods) in enumerate(programs):
        col = idx % 2
        row = idx // 2
        px = 24 + col * 424
        py = 96 + row * 62
        rows_svg.append(f'''
  <g>
    <text x="{px}" y="{py + 12}" class="mono-num" fill="#3fb950">{num}</text>
    <text x="{px + 24}" y="{py + 12}" class="mono-title" fill="#e6edf3">{escape(title)}</text>
    <text x="{px + 24}" y="{py + 29}" class="sans-desc" fill="#8b949e">{escape(desc)}</text>
    <text x="{px + 24}" y="{py + 45}" class="mono-mods" fill="#6e7681">{escape(mods)}</text>
  </g>''')
        if row < 2:
            rows_svg.append(f'<line x1="{px}" y1="{py + 54}" x2="{px + 404}" y2="{py + 54}" stroke="#1b222c" stroke-width="1"/>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="100%" role="img" aria-label="0xR3TRO Ecosystem Lifecycle and Programs">
  <style>
    .mono-hdr {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 10px; font-weight: 600; letter-spacing: 0.8px; }}
    .mono-stage {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 9px; }}
    .mono-stage-act {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 9px; font-weight: 700; }}
    .mono-num {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 10px; font-weight: 700; }}
    .mono-title {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 11px; font-weight: 700; letter-spacing: 0.4px; }}
    .sans-desc {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 11px; }}
    .mono-mods {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 9px; }}
  </style>

  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="10" fill="#0d1117" stroke="#21262d" stroke-width="1"/>

  <text x="24" y="25" class="mono-hdr" fill="#8b949e">MODULE LIFECYCLE · <tspan fill="#e6edf3">LINKED ONLY AT PUBLIC-RELEASE</tspan></text>
  <text x="856" y="25" text-anchor="end" class="mono-hdr" fill="#3fb950">17 / 17 CREATED-PRIVATE</text>

  <!-- Lifecycle Pipeline -->
  {"".join(stage_svg)}

  <line x1="24" y1="78" x2="856" y2="78" stroke="#21262d" stroke-width="1"/>
  <!-- Vertical Divider between 2 columns -->
  <line x1="438" y1="92" x2="438" y2="274" stroke="#1b222c" stroke-width="1"/>

  <!-- 6 Programs Index -->
  {"".join(rows_svg)}
</svg>
'''


def main() -> int:
    user = fetch_stats()
    m = compute_metrics(user)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "header-matrix.svg").write_text(render_header_matrix(m), encoding="utf-8")
    (OUTPUT_DIR / "metrics-bento.svg").write_text(render_metrics_bento(m), encoding="utf-8")
    (OUTPUT_DIR / "ecosystem-matrix.svg").write_text(render_ecosystem_matrix(), encoding="utf-8")
    print(f"Generated Option 3 assets in {OUTPUT_DIR} ({m['total_contributions']} contributions, {m['commits']} commits)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
