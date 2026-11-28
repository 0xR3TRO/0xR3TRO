#!/usr/bin/env python3
"""Generate animated dark-mode GitHub profile SVG assets for 0xR3TRO (Option 2: Cybernetic Topology & SOC Command)."""

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

LANG_COLORS = {
    "Python": "#38bdf8",
    "JavaScript": "#facc15",
    "TypeScript": "#60a5fa",
    "C#": "#a78bfa",
    "C": "#94a3b8",
    "Shell": "#34d399",
    "HTML": "#fb923c",
    "Rust": "#f97316",
    "Go": "#22d3ee",
}


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

    repos = user["repositories"]["nodes"]
    total_repos = user["repositories"]["totalCount"]
    public_repos = sum(1 for r in repos if not r.get("isPrivate"))
    private_repos = max(total_repos - public_repos, 0)

    lang_counts: dict[str, int] = {}
    for r in repos:
        pl = r.get("primaryLanguage")
        if pl and pl.get("name"):
            name = pl["name"]
            lang_counts[name] = lang_counts.get(name, 0) + 1
    top_langs = sorted(lang_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:6]

    return {
        "weeks": weeks,
        "total_contributions": cal["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "repos_created": cc["totalRepositoryContributions"],
        "total_repos": total_repos,
        "public_repos": public_repos,
        "private_repos": private_repos,
        "active_days_count": len(active_days),
        "streak": streak,
        "top_langs": top_langs,
    }


def cyber_color(count: int) -> tuple[str, int]:
    if count <= 0:
        return "#111926", 0
    if count <= 3:
        return "#0e3a4c", 1
    if count <= 12:
        return "#0d6e6e", 2
    if count <= 30:
        return "#10b981", 3
    return "#38bdf8", 4


def fmt_num(n: int) -> str:
    return f"{n:,}"


def render_activity_pulse(m: dict) -> str:
    weeks = m["weeks"][-53:]
    w_svg, h_svg = 880, 206
    cell = 12.2
    gap = 3.2
    step = cell + gap
    start_x = 32
    start_y = 74

    month_names = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
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
                f'<text x="{x:.1f}" y="{start_y - 10}" class="mono-xs" fill="#64748b">{month_names[mon - 1]}</text>'
            )
            last_month = mon
            last_x = x

    cells = []
    for wi, w in enumerate(weeks):
        x = start_x + wi * step
        delay = (wi * 0.05) % 4.0
        for day in w["contributionDays"]:
            wd = day["weekday"]
            y = start_y + wd * step
            cnt = day["contributionCount"]
            fill, lvl = cyber_color(cnt)
            if lvl == 0:
                cells.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="3" '
                    f'fill="{fill}" stroke="#1b2638" stroke-width="0.6"/>'
                )
            else:
                glow = ' filter="url(#cyanGlow)"' if lvl >= 3 else ""
                cells.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="3" '
                    f'fill="{fill}"{glow} class="pulse-cell" style="animation-delay:{delay:.2f}s">'
                    f'<title>{escape(day["date"])}: {cnt} contributions</title></rect>'
                )

    chips = [
        (434, 118, f'{fmt_num(m["total_contributions"])} CONTR', "#38bdf8", "#0c2233", "#1e4b6b"),
        (560, 114, f'{fmt_num(m["commits"])} COMMITS', "#34d399", "#0b2620", "#175746"),
        (682, 82, f'{m["prs"]} PRs', "#cbd5e1", "#121b28", "#243247"),
        (772, 92, f'{m["total_repos"]} REPOS', "#cbd5e1", "#121b28", "#243247"),
    ]
    chips_svg = "".join(
        f'<rect x="{cx}" y="15" width="{cw}" height="24" rx="12" fill="{bg}" stroke="{bd}" stroke-width="1"/>'
        f'<text x="{cx + cw / 2:.1f}" y="30.5" text-anchor="middle" class="mono-chip" fill="{fg}">{label}</text>'
        for cx, cw, label, fg, bg, bd in chips
    )

    legend = ["#111926", "#0e3a4c", "#0d6e6e", "#10b981", "#38bdf8"]
    legend_svg = "".join(
        f'<rect x="{744 + i * 15}" y="185" width="11" height="11" rx="2.5" fill="{c}" stroke="#1e293b" stroke-width="0.6"/>'
        for i, c in enumerate(legend)
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="100%" role="img" aria-label="0xR3TRO Activity Pulse">
  <defs>
    <filter id="cyanGlow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="2.2" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <linearGradient id="topAccent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="50%" stop-color="#34d399"/>
      <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.1"/>
    </linearGradient>
    <linearGradient id="cyberSweep" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0"/>
      <stop offset="50%" stop-color="#38bdf8" stop-opacity="0.14"/>
      <stop offset="100%" stop-color="#38bdf8" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="matrixClip"><rect x="28" y="70" width="826" height="112" rx="4"/></clipPath>
  </defs>
  <style>
    .mono-brand {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 14px; font-weight: 700; letter-spacing: 0.8px; }}
    .mono-sub {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 11px; letter-spacing: 0.4px; }}
    .mono-chip {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 9.5px; font-weight: 600; letter-spacing: 0.4px; }}
    .mono-xs {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 9px; letter-spacing: 0.6px; }}
    .mono-xxs {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 8.5px; }}
    .beacon {{ animation: beaconPulse 2.2s ease-in-out infinite; }}
    .pulse-cell {{ animation: cellBreath 3.8s ease-in-out infinite; }}
    .sweep {{ animation: sweepX 6.5s linear infinite; }}
    @keyframes beaconPulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.25; }} }}
    @keyframes cellBreath {{ 0%, 100% {{ opacity: 0.84; }} 50% {{ opacity: 1; }} }}
    @keyframes sweepX {{ 0% {{ transform: translateX(-140px); }} 100% {{ transform: translateX(920px); }} }}
  </style>

  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="12" fill="#0b0f14" stroke="#1e293b" stroke-width="1"/>
  <rect x="16" y="1" width="848" height="2" rx="1" fill="url(#topAccent)"/>

  <!-- Header -->
  <circle cx="26" cy="27" r="4.2" fill="#38bdf8" class="beacon"/>
  <circle cx="26" cy="27" r="8" fill="none" stroke="#38bdf8" stroke-opacity="0.3" stroke-width="1" class="beacon"/>
  <text x="42" y="31" class="mono-brand" fill="#f1f5f9">0xR3TRO</text>
  <text x="122" y="31" class="mono-sub" fill="#64748b">// VERIFIABLE SYSTEMS TELEMETRY</text>
  {chips_svg}

  <line x1="16" y1="49" x2="864" y2="49" stroke="#162032" stroke-width="1"/>

  {"".join(month_labels)}
  <text x="10" y="{start_y + step + 9.5:.1f}" class="mono-xxs" fill="#475569">MON</text>
  <text x="10" y="{start_y + 3 * step + 9.5:.1f}" class="mono-xxs" fill="#475569">WED</text>
  <text x="10" y="{start_y + 5 * step + 9.5:.1f}" class="mono-xxs" fill="#475569">FRI</text>

  <g>{"".join(cells)}</g>
  <g clip-path="url(#matrixClip)">
    <rect x="0" y="68" width="130" height="116" fill="url(#cyberSweep)" class="sweep"/>
  </g>

  <text x="32" y="194" class="mono-xxs" fill="#475569">SIGNAL MATRIX · 12-MONTH WINDOW · {m["active_days_count"]} ACTIVE DAYS · {m["streak"]}D STREAK</text>
  <text x="736" y="194" text-anchor="end" class="mono-xxs" fill="#64748b">Low</text>
  {legend_svg}
  <text x="826" y="194" class="mono-xxs" fill="#64748b">High</text>
</svg>
'''


def hex_points(cx: float, cy: float, r: float) -> str:
    pts = []
    for i in range(6):
        ang = math.radians(60 * i - 30)
        pts.append(f"{cx + r * math.cos(ang):.1f},{cy + r * math.sin(ang):.1f}")
    return " ".join(pts)


def render_command_overview(m: dict) -> str:
    w_svg, h_svg = 880, 326

    # Left: 6-Node Security Topology Graph centered at (226, 160)
    cx, cy = 226.0, 158.0
    orbit_rx, orbit_ry = 128.0, 88.0
    nodes = [
        (-90, "FOUNDATION", "4 mods", "#38bdf8"),
        (-28, "SOC SIGNAL", "4 mods", "#34d399"),
        (28, "VERIFIABLE AI", "3 mods", "#38bdf8"),
        (90, "OPS REF", "1 mod", "#34d399"),
        (152, "ONCHAIN", "2 mods", "#38bdf8"),
        (208, "TRUST FABRIC", "3 mods", "#34d399"),
    ]

    links_svg = []
    nodes_svg = []
    for idx, (deg, label, sub, color) in enumerate(nodes):
        ang = math.radians(deg)
        nx = cx + orbit_rx * math.cos(ang)
        ny = cy + orbit_ry * math.sin(ang)
        delay = idx * 0.45

        # Static dim conduit + animated traveling packet line
        links_svg.append(
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#1e293b" stroke-width="1.3"/>'
            f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="{color}" stroke-width="1.8" '
            f'stroke-dasharray="14 140" stroke-linecap="round" class="packet" style="animation-delay:{delay:.2f}s"/>'
        )

        # Node pill card centered at (nx, ny)
        pw, ph = 98, 34
        nodes_svg.append(f'''
  <g>
    <rect x="{nx - pw / 2:.1f}" y="{ny - ph / 2:.1f}" width="{pw}" height="{ph}" rx="7" fill="#0f1724" stroke="{color}" stroke-opacity="0.55" stroke-width="1"/>
    <circle cx="{nx - pw / 2 + 10:.1f}" cy="{ny:.1f}" r="2.6" fill="{color}" class="node-dot" style="animation-delay:{delay:.2f}s"/>
    <text x="{nx + 4:.1f}" y="{ny - 2:.1f}" text-anchor="middle" class="mono-node" fill="#e2e8f0">{label}</text>
    <text x="{nx + 4:.1f}" y="{ny + 10:.1f}" text-anchor="middle" class="mono-micro" fill="#64748b">{sub} · priv</text>
  </g>''')

    # Right Top: Contribution Breakdown Horizontal Bars
    metrics_rows = [
        ("Commits", m["commits"], "#34d399"),
        ("Pull Requests", m["prs"], "#38bdf8"),
        ("Issues & Tracking", m["issues"], "#818cf8"),
        ("Repos Created", m["repos_created"], "#2dd4bf"),
    ]
    max_metric = max(v for _, v, _ in metrics_rows) or 1
    bars_rows_svg = []
    for i, (lbl, val, col) in enumerate(metrics_rows):
        ry = 62 + i * 24
        bar_max = 224.0
        # Use blended linear+log so all bars are readable & honest
        bw = max(12.0, bar_max * (0.45 * (val / max_metric) + 0.55 * (math.log1p(val) / math.log1p(max_metric))))
        bars_rows_svg.append(
            f'<text x="470" y="{ry + 9}" class="mono-xs" fill="#94a3b8">{escape(lbl)}</text>'
            f'<rect x="590" y="{ry}" width="{bar_max:.0f}" height="10" rx="5" fill="#0f1724"/>'
            f'<rect x="590" y="{ry}" width="{bw:.1f}" height="10" rx="5" fill="{col}" class="hbar" style="animation-delay:{i * 0.12:.2f}s"/>'
            f'<text x="846" y="{ry + 9}" text-anchor="end" class="mono-val" fill="#e2e8f0">{val}</text>'
        )

    # Right Bottom: Stacked Language Distribution
    top_langs = m["top_langs"] or [("Python", 5), ("JavaScript", 5), ("TypeScript", 2)]
    total_lang_repos = sum(cnt for _, cnt in top_langs) or 1
    seg_x = 470.0
    seg_total_w = 376.0
    lang_segs = []
    lang_legend = []
    for idx, (lname, cnt) in enumerate(top_langs):
        col = LANG_COLORS.get(lname, "#94a3b8")
        sw = max(8.0, seg_total_w * (cnt / total_lang_repos))
        if idx == len(top_langs) - 1:
            sw = max(4.0, (470.0 + seg_total_w) - seg_x)
        lang_segs.append(f'<rect x="{seg_x:.1f}" y="206" width="{sw:.1f}" height="9" fill="{col}"/>')
        seg_x += sw

        col_idx = idx % 3
        row_idx = idx // 3
        lx = 470 + col_idx * 126
        ly = 235 + row_idx * 22
        pct = round(100 * cnt / total_lang_repos)
        lang_legend.append(
            f'<circle cx="{lx + 4}" cy="{ly - 3.5}" r="3.5" fill="{col}"/>'
            f'<text x="{lx + 14}" y="{ly}" class="mono-xs" fill="#cbd5e1">{escape(lname)} <tspan fill="#64748b">{pct}%</tspan></text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="100%" role="img" aria-label="0xR3TRO Topology and Telemetry Overview">
  <defs>
    <radialGradient id="coreGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.22"/>
      <stop offset="65%" stop-color="#34d399" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="#0b0f14" stop-opacity="0"/>
    </radialGradient>
    <clipPath id="langBarClip"><rect x="470" y="206" width="376" height="9" rx="4.5"/></clipPath>
  </defs>
  <style>
    .mono-hdr {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 10.5px; font-weight: 700; letter-spacing: 0.9px; }}
    .mono-node {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 8.8px; font-weight: 700; letter-spacing: 0.4px; }}
    .mono-core {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 11px; font-weight: 700; letter-spacing: 0.8px; }}
    .mono-xs {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 10px; }}
    .mono-val {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 10.5px; font-weight: 700; }}
    .mono-micro {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 8px; }}
    .packet {{ animation: flow 2.8s linear infinite; }}
    .node-dot {{ animation: pulse 2.4s ease-in-out infinite; }}
    .ring-spin {{ transform-origin: 226px 158px; animation: spin 28s linear infinite; }}
    .hbar {{ transform-box: fill-box; transform-origin: left; animation: growX 0.9s ease-out both; }}
    @keyframes flow {{ 0% {{ stroke-dashoffset: 154; }} 100% {{ stroke-dashoffset: 0; }} }}
    @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.3; }} }}
    @keyframes spin {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
    @keyframes growX {{ from {{ transform: scaleX(0.1); opacity: 0.3; }} to {{ transform: scaleX(1); opacity: 1; }} }}
  </style>

  <!-- Outer Canvas -->
  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="12" fill="#0b0f14" stroke="#1e293b" stroke-width="1"/>

  <!-- LEFT CARD: Cybernetic Topology -->
  <rect x="16" y="16" width="420" height="294" rx="10" fill="#0d131d" stroke="#1e293b" stroke-width="1"/>
  <text x="30" y="36" class="mono-hdr" fill="#38bdf8">ECOSYSTEM TOPOLOGY</text>
  <text x="422" y="36" text-anchor="end" class="mono-micro" fill="#475569">ANONYMITY // SHIELD</text>

  <!-- Radar Rings & Core Aura -->
  <circle cx="226" cy="158" r="118" fill="url(#coreGlow)"/>
  <circle cx="226" cy="158" r="56" fill="none" stroke="#1e293b" stroke-dasharray="3 5" stroke-width="1"/>
  <circle cx="226" cy="158" r="96" fill="none" stroke="#172334" stroke-dasharray="4 6" stroke-width="1" class="ring-spin"/>

  <!-- Animated Signal Links -->
  <g>{"".join(links_svg)}</g>

  <!-- Central 0xR3TRO Hex Core -->
  <polygon points="{hex_points(cx, cy, 34)}" fill="#0b1524" stroke="#38bdf8" stroke-width="1.6"/>
  <polygon points="{hex_points(cx, cy, 27)}" fill="none" stroke="#34d399" stroke-opacity="0.4" stroke-width="0.9"/>
  <text x="{cx}" y="{cy + 3.5}" text-anchor="middle" class="mono-core" fill="#f8fafc">0xR3TRO</text>

  <!-- Orbiting Program Nodes -->
  <g>{"".join(nodes_svg)}</g>

  <text x="226" y="296" text-anchor="middle" class="mono-micro" fill="#64748b">6 PROGRAMS · 17 PRIVATE MODULES · ZERO-TRUST BOUNDARIES</text>

  <!-- RIGHT TOP CARD: Contribution Breakdown -->
  <rect x="452" y="16" width="412" height="148" rx="10" fill="#0d131d" stroke="#1e293b" stroke-width="1"/>
  <text x="470" y="38" class="mono-hdr" fill="#34d399">CONTRIBUTION TELEMETRY</text>
  <text x="846" y="38" text-anchor="end" class="mono-xs" fill="#38bdf8">{fmt_num(m["total_contributions"])} TOTAL</text>
  <line x1="470" y1="48" x2="846" y2="48" stroke="#162032" stroke-width="1"/>
  {"".join(bars_rows_svg)}

  <!-- RIGHT BOTTOM CARD: Languages & Footprint -->
  <rect x="452" y="176" width="412" height="134" rx="10" fill="#0d131d" stroke="#1e293b" stroke-width="1"/>
  <text x="470" y="196" class="mono-hdr" fill="#e2e8f0">CORE STACK &amp; FOOTPRINT</text>
  <text x="846" y="196" text-anchor="end" class="mono-micro" fill="#64748b">{m["public_repos"]} PUB · {m["private_repos"]} PRIV</text>

  <g clip-path="url(#langBarClip)">
    {"".join(lang_segs)}
  </g>
  {"".join(lang_legend)}

  <line x1="470" y1="274" x2="846" y2="274" stroke="#162032" stroke-width="1"/>
  <text x="470" y="294" class="mono-micro" fill="#64748b">STATUS: <tspan fill="#34d399">OPERATIONAL</tspan></text>
  <text x="846" y="294" text-anchor="end" class="mono-micro" fill="#94a3b8">STREAK: <tspan fill="#38bdf8">{m["streak"]}D</tspan> · ACTIVE: {m["active_days_count"]}D</text>
</svg>
'''


def render_pipeline() -> str:
    w_svg, h_svg = 880, 144
    stages = [
        (16, "01", "CRYPTO & ON-CHAIN", "Identity · Ledger · Provenance", "TRUST FABRIC · ONCHAIN SURFACE", "#38bdf8"),
        (308, "02", "SIGNAL & EVIDENCE", "Correlation · Citation-Bound AI", "SOC SIGNAL · VERIFIABLE AI", "#34d399"),
        (600, "03", "CONTROLLED ACTION", "Policy Runtime · Reference Ops", "FOUNDATION · 0xC0R3-OPS", "#818cf8"),
    ]
    boxes = []
    for x, num, title, desc, sub, col in stages:
        boxes.append(f'''
  <g>
    <rect x="{x}" y="18" width="264" height="86" rx="10" fill="#0d131d" stroke="#1e293b" stroke-width="1"/>
    <rect x="{x}" y="18" width="264" height="3" rx="1.5" fill="{col}" fill-opacity="0.85"/>
    <text x="{x + 16}" y="42" class="mono-num" fill="{col}">[{num}]</text>
    <text x="{x + 48}" y="42" class="mono-title" fill="#f1f5f9">{escape(title)}</text>
    <text x="{x + 16}" y="64" class="sans-desc" fill="#94a3b8">{escape(desc)}</text>
    <text x="{x + 16}" y="88" class="mono-sub" fill="#64748b">{escape(sub)}</text>
  </g>''')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="100%" role="img" aria-label="0xR3TRO Verification Pipeline">
  <style>
    .mono-num {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 10.5px; font-weight: 700; }}
    .mono-title {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 11px; font-weight: 700; letter-spacing: 0.4px; }}
    .sans-desc {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; font-size: 11px; }}
    .mono-sub {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 8.5px; letter-spacing: 0.4px; }}
    .mono-foot {{ font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace; font-size: 9px; letter-spacing: 0.5px; }}
    .arrow-flow {{ animation: dash 1.8s linear infinite; }}
    @keyframes dash {{ to {{ stroke-dashoffset: -18; }} }}
  </style>

  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="12" fill="#0b0f14" stroke="#1e293b" stroke-width="1"/>
  {"".join(boxes)}

  <!-- Animated connectors -->
  <line x1="282" y1="61" x2="306" y2="61" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4 5" class="arrow-flow"/>
  <polygon points="304,57 308,61 304,65" fill="#38bdf8"/>

  <line x1="574" y1="61" x2="598" y2="61" stroke="#34d399" stroke-width="2" stroke-dasharray="4 5" class="arrow-flow"/>
  <polygon points="596,57 600,61 596,65" fill="#34d399"/>

  <!-- Bottom Axiom Strip -->
  <text x="440" y="128" text-anchor="middle" class="mono-foot" fill="#64748b">
    AI = LAYER, NOT GOAL  ·  WEB3 = ONLY WHERE IT EARNS TRUST  ·  EVERY MODULE = MEASURABLE &amp; BOUNDED RISK
  </text>
</svg>
'''


def main() -> int:
    user = fetch_stats()
    m = compute_metrics(user)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "activity-pulse.svg").write_text(render_activity_pulse(m), encoding="utf-8")
    (OUTPUT_DIR / "command-overview.svg").write_text(render_command_overview(m), encoding="utf-8")
    (OUTPUT_DIR / "pipeline.svg").write_text(render_pipeline(), encoding="utf-8")
    print(f"Generated Option 2 assets in {OUTPUT_DIR} ({m['total_contributions']} contributions, {m['commits']} commits)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
