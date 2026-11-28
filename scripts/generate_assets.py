#!/usr/bin/env python3
"""Generate animated dark-mode GitHub profile SVG assets for 0xR3TRO (Option 1: SOC Telemetry & Shield)."""

from __future__ import annotations

import datetime as dt
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
    peak_day = max(days, key=lambda d: d["contributionCount"]) if days else {"contributionCount": 0, "date": ""}

    # Current streak (allowing today to be 0 if day just started)
    streak = 0
    idx = len(days) - 1
    if idx >= 0 and days[idx]["contributionCount"] == 0:
        idx -= 1
    while idx >= 0 and days[idx]["contributionCount"] > 0:
        streak += 1
        idx -= 1

    repos = user["repositories"]["nodes"]
    total_repos = user["repositories"]["totalCount"]
    public_repos = sum(1 for r in repos if not r.get("isPrivate"))
    private_repos = max(total_repos - public_repos, 0)

    commits = cc["totalCommitContributions"]
    restricted = cc.get("restrictedContributionsCount", 0)
    total_contributions = cal["totalContributions"]
    prs = cc["totalPullRequestContributions"]
    issues = cc["totalIssueContributions"]

    # Recent 12 active sessions for bar chart
    recent_sessions = active_days[-12:]

    return {
        "weeks": weeks,
        "days": days,
        "total_contributions": total_contributions,
        "commits": commits,
        "restricted": restricted,
        "prs": prs,
        "issues": issues,
        "total_repos": total_repos,
        "public_repos": public_repos,
        "private_repos": private_repos,
        "active_days_count": len(active_days),
        "streak": streak,
        "peak_count": peak_day["contributionCount"],
        "peak_date": peak_day["date"],
        "recent_sessions": recent_sessions,
    }


def level_color(count: int) -> tuple[str, int]:
    if count <= 0:
        return "#161b22", 0
    if count <= 3:
        return "#0e4429", 1
    if count <= 12:
        return "#006d32", 2
    if count <= 30:
        return "#26a641", 3
    return "#39d353", 4


def fmt_num(n: int) -> str:
    return f"{n:,}"


def render_heatmap(m: dict) -> str:
    weeks = m["weeks"][-53:]
    w_svg, h_svg = 880, 196
    cell = 12.2
    gap = 3.2
    step = cell + gap
    start_x = 32
    start_y = 66

    # Month markers
    month_names = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    month_labels = []
    last_month = None
    last_x = -100
    for wi, w in enumerate(weeks):
        if not w["contributionDays"]:
            continue
        first_date = w["contributionDays"][0]["date"]
        mon = int(first_date[5:7])
        x = start_x + wi * step
        if mon != last_month and (x - last_x) >= 34:
            month_labels.append(
                f'<text x="{x:.1f}" y="{start_y - 10}" class="mono-xs" fill="#6e7681">{month_names[mon - 1]}</text>'
            )
            last_month = mon
            last_x = x

    cells_svg = []
    for wi, w in enumerate(weeks):
        x = start_x + wi * step
        delay = (wi * 0.055) % 4.5
        for day in w["contributionDays"]:
            wd = day["weekday"]
            y = start_y + wd * step
            cnt = day["contributionCount"]
            fill, lvl = level_color(cnt)
            if lvl == 0:
                cells_svg.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="2.5" '
                    f'fill="{fill}" stroke="#21262d" stroke-width="0.6" class="c0" style="animation-delay:{delay:.2f}s"/>'
                )
            else:
                cls = f"c{lvl}"
                glow = ' filter="url(#greenGlow)"' if lvl >= 3 else ""
                cells_svg.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="2.5" '
                    f'fill="{fill}"{glow} class="{cls}" style="animation-delay:{delay:.2f}s">'
                    f'<title>{escape(day["date"])}: {cnt} contributions</title></rect>'
                )

    day_labels = [
        (1, "MON"),
        (3, "WED"),
        (5, "FRI"),
    ]
    day_svg = "".join(
        f'<text x="10" y="{start_y + wd * step + 9.5:.1f}" class="mono-xxs" fill="#484f58">{lbl}</text>'
        for wd, lbl in day_labels
    )

    legend_colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
    legend_rects = "".join(
        f'<rect x="{744 + i * 15}" y="176" width="11" height="11" rx="2" fill="{c}" stroke="#21262d" stroke-width="0.5"/>'
        for i, c in enumerate(legend_colors)
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="100%" role="img" aria-label="0xR3TRO Contribution Matrix">
  <defs>
    <filter id="greenGlow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="2.2" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <linearGradient id="scanLine" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#39d353" stop-opacity="0"/>
      <stop offset="50%" stop-color="#39d353" stop-opacity="0.14"/>
      <stop offset="100%" stop-color="#39d353" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="gridClip">
      <rect x="28" y="62" width="826" height="112" rx="4"/>
    </clipPath>
  </defs>
  <style>
    .mono-title {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 13px; letter-spacing: 0.4px; }}
    .mono-num {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 14px; font-weight: 700; }}
    .mono-xs {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 9.5px; letter-spacing: 0.6px; }}
    .mono-xxs {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 8.5px; letter-spacing: 0.4px; }}
    .c0 {{ animation: baseWave 6s ease-in-out infinite; }}
    .c1, .c2 {{ animation: midPulse 4.5s ease-in-out infinite; }}
    .c3, .c4 {{ animation: hiPulse 3.6s ease-in-out infinite; }}
    .live-dot {{ animation: blink 2s ease-in-out infinite; }}
    .cursor {{ animation: blink 1.1s step-end infinite; }}
    .scanner {{ animation: sweep 7s linear infinite; }}
    @keyframes baseWave {{
      0%, 100% {{ fill: #161b22; }}
      12% {{ fill: #1b242d; }}
      24% {{ fill: #161b22; }}
    }}
    @keyframes midPulse {{
      0%, 100% {{ opacity: 0.85; }}
      50% {{ opacity: 1; }}
    }}
    @keyframes hiPulse {{
      0%, 100% {{ opacity: 0.88; }}
      50% {{ opacity: 1; }}
    }}
    @keyframes blink {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.25; }}
    }}
    @keyframes sweep {{
      0% {{ transform: translateX(-140px); }}
      100% {{ transform: translateX(920px); }}
    }}
  </style>

  <!-- Outer Frame -->
  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="10" fill="#0d1117" stroke="#21262d" stroke-width="1"/>

  <!-- Header Bar -->
  <circle cx="24" cy="27" r="4" fill="#39d353" class="live-dot"/>
  <text x="38" y="31" class="mono-title" fill="#8b949e">contributions // <tspan class="mono-num" fill="#e6edf3">{fmt_num(m["total_contributions"])}</tspan> total</text>

  <!-- Commit Pill -->
  <rect x="286" y="16" width="118" height="22" rx="11" fill="#0f2419" stroke="#1f5132" stroke-width="1"/>
  <text x="345" y="31" text-anchor="middle" class="mono-xs" fill="#39d353">{fmt_num(m["commits"])} COMMITS</text>

  <!-- Streak Pill -->
  <rect x="412" y="16" width="96" height="22" rx="11" fill="#161b22" stroke="#30363d" stroke-width="1"/>
  <text x="460" y="31" text-anchor="middle" class="mono-xs" fill="#c9d1d9">{m["streak"]}D STREAK</text>

  <!-- Right Label -->
  <text x="844" y="31" text-anchor="end" class="mono-xs" fill="#6e7681">last 12 months · 0xR3TRO</text>
  <rect x="850" y="21" width="6" height="12" rx="1" fill="#39d353" class="cursor"/>

  <!-- Month & Day Labels -->
  {"".join(month_labels)}
  {day_svg}

  <!-- Heatmap Grid -->
  <g>
    {"".join(cells_svg)}
  </g>

  <!-- Subtle Phosphor Radar Sweep -->
  <g clip-path="url(#gridClip)">
    <rect x="0" y="60" width="120" height="116" fill="url(#scanLine)" class="scanner"/>
  </g>

  <!-- Footer -->
  <text x="32" y="185" class="mono-xxs" fill="#484f58">TELEMETRY://GITHUB.GRAPHQL · AUTO-SYNC DAILY</text>
  <text x="736" y="185" text-anchor="end" class="mono-xxs" fill="#6e7681">Less</text>
  {legend_rects}
  <text x="826" y="185" class="mono-xxs" fill="#6e7681">More</text>
</svg>
'''


def build_shield_dots() -> str:
    """Build a crisp halftone dot-matrix cryptographic shield with inner lock/hex emblem."""
    cols = 29
    rows = 19
    cx0 = (cols - 1) / 2.0
    start_x = 82.8
    start_y = 58
    dx = 9.8
    dy = 9.6

    out = []
    for r in range(rows):
        ny = r / (rows - 1)  # 0 at top, 1 at bottom
        delay = r * 0.08
        for c in range(cols):
            nx = (c - cx0) / (cols / 2.0)  # -1..1
            ax = abs(nx)

            # Shield outer half-width at vertical coordinate ny
            if ny < 0.08:
                max_w = 0.0
            elif ny < 0.16:
                # Top crown curve
                max_w = 0.72 * math.sqrt((ny - 0.07) / 0.10)
            elif ny < 0.56:
                # Upper shield sides
                max_w = 0.72 - 0.06 * ((ny - 0.16) / 0.40)
            elif ny <= 0.94:
                # Taper to shield tip
                t = (ny - 0.56) / 0.38
                max_w = 0.66 * (1.0 - t ** 1.35)
            else:
                max_w = 0.0

            x = start_x + c * dx
            y = start_y + r * dy

            inside = max_w > 0.04 and ax <= max_w
            if not inside:
                # Faint ambient matrix dot
                if (r + c) % 2 == 0:
                    out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.1" fill="#161b22"/>')
                continue

            # Distance from outer border
            edge_dist = max_w - ax
            is_outer_rim = edge_dist < 0.11 or (0.08 <= ny <= 0.17) or (ny > 0.87)

            # Inner cryptographic diamond / keyhole emblem
            dy_c = (ny - 0.48) * 1.45
            dx_c = ax * 1.15
            diamond = dx_c + abs(dy_c)

            if is_outer_rim:
                color = "#39d353"
                rad = 3.0
                cls = "dot-rim"
            elif 0.24 <= diamond <= 0.34:
                color = "#e6edf3"
                rad = 2.9
                cls = "dot-core"
            elif diamond < 0.15:
                color = "#39d353"
                rad = 3.1
                cls = "dot-core"
            elif abs(ny - 0.48) < 0.055 and ax < 0.50:
                color = "#26a641"
                rad = 2.4
                cls = "dot-mid"
            else:
                # Shaded inner shield body (left lighter, right darker for 3D depth)
                if nx < 0:
                    color = "#1b7f37" if (r + c) % 2 == 0 else "#0e4429"
                    rad = 2.3 if (r + c) % 2 == 0 else 1.8
                else:
                    color = "#0e4429" if (r + c) % 2 == 0 else "#132a1e"
                    rad = 2.0 if (r + c) % 2 == 0 else 1.5
                cls = "dot-body"

            out.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{color}" class="{cls}" '
                f'style="animation-delay:{delay:.2f}s"/>'
            )
    return "\n    ".join(out)


def render_telemetry(m: dict) -> str:
    w_svg, h_svg = 880, 318
    shield_dots = build_shield_dots()

    # Build 12-bar recent active sessions chart
    sessions = m["recent_sessions"]
    if not sessions:
        sessions = [{"date": "2026-11-27", "contributionCount": 1}]
    max_val = max(s["contributionCount"] for s in sessions) or 1
    log_max = math.log1p(max_val)

    chart_x = 460
    chart_base_y = 282
    chart_max_h = 54
    n_bars = len(sessions)
    avail_w = 384
    bar_step = avail_w / max(n_bars, 1)
    bar_w = min(20, bar_step * 0.62)

    bars_svg = []
    for i, s in enumerate(sessions):
        cnt = s["contributionCount"]
        frac = math.log1p(cnt) / log_max if log_max > 0 else 0.2
        bh = max(7.0, frac * chart_max_h)
        bx = chart_x + i * bar_step + (bar_step - bar_w) / 2
        by = chart_base_y - bh
        is_peak = cnt == max_val
        fill = "#39d353" if is_peak else ("#26a641" if cnt >= 12 else "#006d32")
        delay = i * 0.07
        short_date = s["date"][5:].replace("-", "/")
        bars_svg.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" rx="3" fill="{fill}" '
            f'class="bar" style="animation-delay:{delay:.2f}s">'
            f'<title>{escape(s["date"])}: {cnt} contributions</title></rect>'
        )
        # Value above top 3 or alternating bars
        if is_peak or i in (0, n_bars - 1, n_bars - 2):
            bars_svg.append(
                f'<text x="{bx + bar_w / 2:.1f}" y="{by - 4:.1f}" text-anchor="middle" class="mono-xxs" '
                f'fill="{"#39d353" if is_peak else "#8b949e"}">{cnt}</text>'
            )
        if i % 3 == 0 or i == n_bars - 1:
            bars_svg.append(
                f'<text x="{bx + bar_w / 2:.1f}" y="{chart_base_y + 13}" text-anchor="middle" class="mono-xxs" fill="#484f58">{short_date}</text>'
            )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="100%" role="img" aria-label="0xR3TRO Telemetry and Shield">
  <defs>
    <radialGradient id="shieldAura" cx="50%" cy="48%" r="50%">
      <stop offset="0%" stop-color="#39d353" stop-opacity="0.14"/>
      <stop offset="100%" stop-color="#0d1117" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="vScan" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#39d353" stop-opacity="0"/>
      <stop offset="50%" stop-color="#39d353" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="#39d353" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="shieldClip">
      <rect x="17" y="43" width="406" height="258" rx="9"/>
    </clipPath>
  </defs>
  <style>
    .mono-hdr {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 12px; letter-spacing: 0.5px; }}
    .mono-kpi {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 27px; font-weight: 700; letter-spacing: -0.5px; }}
    .mono-lbl {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 10px; font-weight: 600; letter-spacing: 0.8px; }}
    .mono-sub {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 10px; }}
    .mono-xxs {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 8.5px; }}
    .dot-rim {{ animation: rimGlow 3.2s ease-in-out infinite; }}
    .dot-core {{ animation: coreGlow 2.6s ease-in-out infinite; }}
    .dot-mid {{ animation: midFade 4s ease-in-out infinite; }}
    .dot-body {{ animation: midFade 4.5s ease-in-out infinite; }}
    .v-scanner {{ animation: vSweep 5.5s linear infinite; }}
    .bar {{ transform-box: fill-box; transform-origin: bottom; animation: barRise 0.9s ease-out both; }}
    @keyframes rimGlow {{
      0%, 100% {{ opacity: 0.72; }}
      50% {{ opacity: 1; }}
    }}
    @keyframes coreGlow {{
      0%, 100% {{ opacity: 0.82; }}
      50% {{ opacity: 1; }}
    }}
    @keyframes midFade {{
      0%, 100% {{ opacity: 0.65; }}
      50% {{ opacity: 0.95; }}
    }}
    @keyframes vSweep {{
      0% {{ transform: translateY(-45px); }}
      100% {{ transform: translateY(275px); }}
    }}
    @keyframes barRise {{
      0% {{ transform: scaleY(0.15); opacity: 0.3; }}
      100% {{ transform: scaleY(1); opacity: 1; }}
    }}
  </style>

  <!-- Outer Frame -->
  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="10" fill="#0d1117" stroke="#21262d" stroke-width="1"/>

  <!-- Section Header -->
  <text x="20" y="27" class="mono-hdr" fill="#8b949e">telemetry // <tspan fill="#e6edf3">shield &amp; metrics</tspan></text>
  <text x="860" y="27" text-anchor="end" class="mono-sub" fill="#484f58">MODE: ANONYMOUS · VERIFIED</text>

  <!-- LEFT PANEL: Halftone Cryptographic Shield (Replaces Profile Photo) -->
  <rect x="16" y="42" width="408" height="260" rx="10" fill="#0b0f14" stroke="#21262d" stroke-width="1"/>
  <ellipse cx="220" cy="152" rx="145" ry="105" fill="url(#shieldAura)"/>

  <!-- Corner brackets inside shield panel -->
  <path d="M28 58 V50 H36 M412 58 V50 H404 M28 286 V294 H36 M412 286 V294 H404" fill="none" stroke="#30363d" stroke-width="1.2"/>
  <text x="34" y="64" class="mono-xxs" fill="#484f58">SIGIL://0xR3TRO</text>
  <text x="406" y="64" text-anchor="end" class="mono-xxs" fill="#39d353">● ACTIVE</text>

  <!-- Dot-Matrix Shield -->
  <g>
    {shield_dots}
  </g>

  <!-- Vertical Scanline inside Shield Card -->
  <g clip-path="url(#shieldClip)">
    <rect x="17" y="43" width="406" height="36" fill="url(#vScan)" class="v-scanner"/>
  </g>

  <!-- Shield Caption -->
  <text x="220" y="268" text-anchor="middle" class="mono-lbl" fill="#e6edf3" letter-spacing="2.2">0xR3TRO</text>
  <text x="220" y="285" text-anchor="middle" class="mono-xxs" fill="#6e7681">ANONYMITY IS NOT A MASK — IT'S A SHIELD</text>

  <!-- RIGHT COLUMN: 2x2 Bento KPI Grid -->
  <!-- Card 1: Total Contributions -->
  <rect x="440" y="42" width="204" height="72" rx="9" fill="#121820" stroke="#21262d" stroke-width="1"/>
  <rect x="440" y="54" width="3" height="48" rx="1.5" fill="#39d353"/>
  <text x="456" y="75" class="mono-kpi" fill="#39d353">{fmt_num(m["total_contributions"])}</text>
  <text x="456" y="93" class="mono-lbl" fill="#c9d1d9">CONTRIBUTIONS</text>
  <text x="456" y="106" class="mono-xxs" fill="#6e7681">rolling 12-month window</text>

  <!-- Card 2: Commits & PRs -->
  <rect x="656" y="42" width="208" height="72" rx="9" fill="#121820" stroke="#21262d" stroke-width="1"/>
  <rect x="656" y="54" width="3" height="48" rx="1.5" fill="#26a641"/>
  <text x="672" y="75" class="mono-kpi" fill="#e6edf3">{fmt_num(m["commits"])}</text>
  <text x="672" y="93" class="mono-lbl" fill="#c9d1d9">COMMITS</text>
  <text x="672" y="106" class="mono-xxs" fill="#6e7681">{m["prs"]} PRs · {m["issues"]} issues</text>

  <!-- Card 3: Repositories -->
  <rect x="440" y="124" width="204" height="72" rx="9" fill="#121820" stroke="#21262d" stroke-width="1"/>
  <text x="456" y="157" class="mono-kpi" fill="#e6edf3">{m["total_repos"]}</text>
  <text x="456" y="175" class="mono-lbl" fill="#c9d1d9">REPOSITORIES</text>
  <text x="456" y="188" class="mono-xxs" fill="#6e7681">{m["public_repos"]} public · {m["private_repos"]} private</text>

  <!-- Card 4: Active Streak -->
  <rect x="656" y="124" width="208" height="72" rx="9" fill="#121820" stroke="#21262d" stroke-width="1"/>
  <text x="672" y="157" class="mono-kpi" fill="#39d353">{m["streak"]}d</text>
  <text x="672" y="175" class="mono-lbl" fill="#c9d1d9">CURRENT STREAK</text>
  <text x="672" y="188" class="mono-xxs" fill="#6e7681">{m["active_days_count"]} active days · peak {m["peak_count"]}</text>

  <!-- Bottom Activity Bar Chart Card -->
  <rect x="440" y="206" width="424" height="96" rx="9" fill="#121820" stroke="#21262d" stroke-width="1"/>
  <text x="456" y="223" class="mono-xxs" fill="#8b949e">RECENT ACTIVE SESSIONS (LOG SCALE)</text>
  <text x="848" y="223" text-anchor="end" class="mono-xxs" fill="#39d353">PEAK: {m["peak_count"]}/DAY</text>
  <line x1="456" y1="282" x2="848" y2="282" stroke="#21262d" stroke-width="1"/>
  {"".join(bars_svg)}
</svg>
'''


def render_programs() -> str:
    w_svg, h_svg = 880, 294
    programs = [
        ("01", "FOUNDATION PROTOCOL", "Event contracts, telemetry & runtime", ["0xS3NT1N3L", "0xF0RG3", "PR00FCHAIN", "N0CTURN"]),
        ("02", "SOC SIGNAL NETWORK", "Signal to case to operator decision", ["S1GNAL-MESH", "PR1SM-CASE", "1NT3LGR4PH", "N3XUS-C0NS0L3"]),
        ("03", "VERIFIABLE INTELLIGENCE", "Provable AI search & policy engine", ["V3R1TAS", "N0M1N4L", "BL4CK-1C3"]),
        ("04", "TRUST FABRIC", "Cryptography, identity & anchoring", ["C1PH3R-VAULT", "M3RKLE-LENS", "D1D-ATLAS"]),
        ("05", "ONCHAIN THREAT SURFACE", "Adversarial protocol & ledger ops", ["CHAIN//FAULT", "0xLEDGER"]),
        ("06", "OPERATIONS REFERENCE", "End-to-end reference deployment", ["0xC0R3-OPS"]),
    ]

    cards = []
    card_w, card_h = 274, 108
    gap_x, gap_y = 13, 14
    for idx, (num, title, desc, mods) in enumerate(programs):
        col = idx % 3
        row = idx // 3
        cx = 16 + col * (card_w + gap_x)
        cy = 48 + row * (card_h + gap_y)

        # Render compact module pills in up to 2 rows inside the card
        pills = []
        px = cx + 14
        py = cy + 62
        for mod in mods:
            pw = len(mod) * 5.7 + 12
            if px + pw > cx + card_w - 10:
                px = cx + 14
                py += 20
            pills.append(
                f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="16" rx="4" fill="#0d1117" stroke="#26303c" stroke-width="0.8"/>'
                f'<text x="{px + pw / 2:.1f}" y="{py + 11.2:.1f}" text-anchor="middle" class="mono-pill" fill="#8b949e">{escape(mod)}</text>'
            )
            px += pw + 5

        cards.append(f'''
  <g>
    <rect x="{cx}" y="{cy}" width="{card_w}" height="{card_h}" rx="9" fill="#121820" stroke="#21262d" stroke-width="1"/>
    <rect x="{cx}" y="{cy + 14}" width="3" height="24" rx="1.5" fill="#39d353"/>
    <text x="{cx + 14}" y="{cy + 24}" class="mono-num-idx" fill="#39d353">{num}</text>
    <text x="{cx + 34}" y="{cy + 24}" class="mono-card-title" fill="#e6edf3">{escape(title)}</text>
    <text x="{cx + 14}" y="{cy + 43}" class="sans-desc" fill="#8b949e">{escape(desc)}</text>
    {"".join(pills)}
  </g>''')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="100%" role="img" aria-label="0xR3TRO 6 Programs Architecture">
  <style>
    .mono-hdr {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 12px; letter-spacing: 0.5px; }}
    .mono-num-idx {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 10px; font-weight: 700; }}
    .mono-card-title {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 11px; font-weight: 700; letter-spacing: 0.4px; }}
    .sans-desc {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 10.5px; }}
    .mono-pill {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 8.5px; }}
    .mono-xxs {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 9px; }}
  </style>

  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="10" fill="#0d1117" stroke="#21262d" stroke-width="1"/>

  <text x="20" y="29" class="mono-hdr" fill="#8b949e">ecosystem // <tspan fill="#e6edf3">6 programs · 17 modules</tspan></text>
  <rect x="676" y="14" width="188" height="22" rx="11" fill="#0f2419" stroke="#1f5132" stroke-width="1"/>
  <text x="770" y="28.5" text-anchor="middle" class="mono-xxs" fill="#39d353">STATE: 17 CREATED-PRIVATE</text>

  {"".join(cards)}
</svg>
'''


def main() -> int:
    user = fetch_stats()
    m = compute_metrics(user)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "heatmap.svg").write_text(render_heatmap(m), encoding="utf-8")
    (OUTPUT_DIR / "telemetry.svg").write_text(render_telemetry(m), encoding="utf-8")
    (OUTPUT_DIR / "programs.svg").write_text(render_programs(), encoding="utf-8")
    print(f"Generated Option 1 assets in {OUTPUT_DIR} ({m['total_contributions']} contributions, {m['commits']} commits)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
