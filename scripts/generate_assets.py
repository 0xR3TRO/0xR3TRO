#!/usr/bin/env python3
"""0xR3TRO Monochrome Profile Generator — Proposal 2: Cybersec Schematic / Blueprint (Dual Dark/Light)."""

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

PALETTES = {
    "dark": {
        "bg": "#0b0b0c",
        "surface": "#121214",
        "elevated": "#19191d",
        "border": "#28282d",
        "hairline": "#1d1d22",
        "grid_dot": "#222228",
        "ink": "#f5f5f6",
        "ink_2": "#c6c6ce",
        "ink_muted": "#82828c",
        "ink_faint": "#50505a",
        "inv_bg": "#f5f5f6",
        "inv_ink": "#0b0b0c",
        "heatmap": ["#151518", "#303038", "#60606c", "#a8a8b4", "#f5f5f6"],
        "heat_stroke": "#222229",
        "bars": ["#f5f5f6", "#bebec8", "#888894", "#585862"],
        "hatch_stroke": "#0b0b0c",
    },
    "light": {
        "bg": "#fdfcfc",
        "surface": "#f6f5f5",
        "elevated": "#eceaea",
        "border": "#d6d3d3",
        "hairline": "#e6e3e3",
        "grid_dot": "#dfdddd",
        "ink": "#171515",
        "ink_2": "#3b3838",
        "ink_muted": "#6c6767",
        "ink_faint": "#9a9595",
        "inv_bg": "#171515",
        "inv_ink": "#fdfcfc",
        "heatmap": ["#efeded", "#cecbcb", "#918c8c", "#4e4a4a", "#171515"],
        "heat_stroke": "#dddada",
        "bars": ["#171515", "#484444", "#767171", "#a39e9e"],
        "hatch_stroke": "#fdfcfc",
    },
}

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

PROGRAMS = [
    ("01", "FOUNDATION PROTOCOL", "Contracts, telemetry & assurance", "0xS3NT1N3L · 0xF0RG3 · PR00FCHAIN · N0CTURN"),
    ("02", "SOC SIGNAL NETWORK", "Signal to case to decision", "S1GNAL-MESH · PR1SM-CASE · 1NT3LGR4PH · N3XUS-C0NS0L3"),
    ("03", "VERIFIABLE INTELLIGENCE", "Citation-bound AI & policy", "V3R1TAS · N0M1N4L · BL4CK-1C3"),
    ("04", "TRUST FABRIC", "Crypto, vault, anchoring & DID", "C1PH3R-VAULT · M3RKLE-LENS · D1D-ATLAS"),
    ("05", "ONCHAIN THREAT SURFACE", "Protocol & ledger security", "CHAIN//FAULT · 0xLEDGER"),
    ("06", "OPERATIONS REFERENCE", "Full-stack ops deployment", "0xC0R3-OPS"),
]

NAV_ITEMS = [
    ("about", "$ open about"),
    ("skills", "$ open skills"),
    ("vision", "$ open vision"),
    ("experience", "$ open exp"),
    ("contact", "$ open contact"),
]

MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"


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
            lang_counts[pl["name"]] = lang_counts.get(pl["name"], 0) + 1
    top_langs = sorted(lang_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]

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


def heat_level(count: int, ramp: list[str]) -> str:
    if count <= 0:
        return ramp[0]
    if count <= 3:
        return ramp[1]
    if count <= 12:
        return ramp[2]
    if count <= 30:
        return ramp[3]
    return ramp[4]


def render_activity(m: dict, p: dict) -> str:
    weeks = m["weeks"][-53:]
    w_svg, h_svg = 880, 224
    cell, gap = 12.2, 3.2
    step = cell + gap
    sx, sy = 34, 88

    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    m_lbls = []
    last_m, last_x = None, -100
    for wi, w in enumerate(weeks):
        if not w["contributionDays"]:
            continue
        mon = int(w["contributionDays"][0]["date"][5:7])
        x = sx + wi * step
        if mon != last_m and (x - last_x) >= 34:
            m_lbls.append(f'<text x="{x:.1f}" y="{sy - 9}" class="xs" fill="{p["ink_muted"]}">{months[mon - 1]}</text>')
            last_m, last_x = mon, x

    # Static crisp heatmap — NO wave!
    cells = []
    for wi, w in enumerate(weeks):
        x = sx + wi * step
        for day in w["contributionDays"]:
            y = sy + day["weekday"] * step
            cnt = day["contributionCount"]
            fill = heat_level(cnt, p["heatmap"])
            cells.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="1.5" '
                f'fill="{fill}" stroke="{p["heat_stroke"]}" stroke-width="0.6">'
                f'<title>{escape(day["date"])}: {cnt} contributions</title></rect>'
            )

    # Blueprint 4-cell KPI readout strip on top-right
    kpis = [
        (468, "CONTRIBUTIONS", f'{m["total_contributions"]:,}', True),
        (572, "COMMITS", f'{m["commits"]:,}', False),
        (676, "PULL REQ", f'{m["prs"]}', False),
        (772, "REPOS", f'{m["total_repos"]}', False),
    ]
    kpi_svg = []
    for kx, lbl, val, hi in kpis:
        kpi_svg.append(
            f'<line x1="{kx - 10}" y1="14" x2="{kx - 10}" y2="54" stroke="{p["hairline"]}" stroke-width="1"/>'
            f'<text x="{kx}" y="31" class="kpi" fill="{p["ink"]}">{val}</text>'
            f'<text x="{kx}" y="46" class="micro" fill="{p["ink_muted"]}">{lbl}</text>'
        )

    legend = "".join(
        f'<rect x="{748 + i * 14}" y="203" width="10.5" height="10.5" rx="1.5" fill="{c}" stroke="{p["heat_stroke"]}" stroke-width="0.5"/>'
        for i, c in enumerate(p["heatmap"])
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="100%" role="img" aria-label="0xR3TRO Blueprint Activity Matrix">
  <style>
    text {{ font-family: {MONO}; }}
    .brand {{ font-size: 16px; font-weight: 700; letter-spacing: 1.2px; }}
    .kpi {{ font-size: 15px; font-weight: 700; }}
    .xs {{ font-size: 9px; letter-spacing: 0.4px; }}
    .micro {{ font-size: 8px; letter-spacing: 0.5px; }}
  </style>

  <!-- Double blueprint frame -->
  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="4" fill="{p["bg"]}" stroke="{p["border"]}" stroke-width="1"/>
  <rect x="4.5" y="4.5" width="{w_svg - 9}" height="{h_svg - 9}" rx="2" fill="none" stroke="{p["hairline"]}" stroke-width="0.8"/>

  <!-- Left Title Block -->
  <rect x="18" y="16" width="6" height="34" fill="{p["ink"]}"/>
  <text x="34" y="32" class="brand" fill="{p["ink"]}">0xR3TRO</text>
  <text x="34" y="47" class="micro" fill="{p["ink_muted"]}">SPEC://VERIFIABLE-SYSTEMS · ADVERSARIAL OPS</text>

  <!-- Right KPI Strip -->
  {"".join(kpi_svg)}

  <line x1="14" y1="62" x2="866" y2="62" stroke="{p["border"]}" stroke-width="1"/>

  {"".join(m_lbls)}
  <text x="14" y="{sy + step + 9.5:.1f}" class="micro" fill="{p["ink_faint"]}">M</text>
  <text x="14" y="{sy + 3 * step + 9.5:.1f}" class="micro" fill="{p["ink_faint"]}">W</text>
  <text x="14" y="{sy + 5 * step + 9.5:.1f}" class="micro" fill="{p["ink_faint"]}">F</text>

  <g>{"".join(cells)}</g>

  <text x="34" y="212" class="micro" fill="{p["ink_muted"]}">W00..W52 · {m["active_days_count"]} ACTIVE DAYS · {m["streak"]}D STREAK · AUTO-SYNC</text>
  <text x="740" y="212" text-anchor="end" class="micro" fill="{p["ink_muted"]}">0</text>
  {legend}
  <text x="822" y="212" class="micro" fill="{p["ink_muted"]}">MAX</text>
</svg>
'''


def render_overview(m: dict, p: dict) -> str:
    w_svg, h_svg = 880, 356

    # LEFT PANEL (x=16..444, y=16..340): 3-Tier Defense-in-Depth Circuit Bus Topology
    # Tier 1 (Top): P04 TRUST FABRIC (x=36..212, y=62..106) & P05 ONCHAIN (x=248..424, y=62..106)
    # Tier 2 (Mid Bus): P02 SOC SIGNAL (x=30..158, y=156..204) -- [0xR3TRO CORE] (x=176..284, y=150..210) -- P03 VERIF AI (x=302..430, y=156..204)
    # Tier 3 (Bottom): P01 FOUNDATION (x=36..212, y=252..296) & P06 0xC0R3-OPS (x=248..424, y=252..296)
    circuit_paths = [
        # Top-left TRUST FABRIC -> Core top-left port
        ("M 124 106 V 130 H 206 V 150", 0.0),
        # Top-right ONCHAIN -> Core top-right port
        ("M 336 106 V 130 H 254 V 150", 0.5),
        # Cross-bridge Top-left <-> Top-right
        ("M 212 84 H 248", 1.0),
        # Mid-left SOC SIGNAL <-> Core left
        ("M 158 180 H 176", 0.3),
        # Mid-right VERIF AI <-> Core right
        ("M 302 180 H 284", 0.8),
        # Core bottom-left -> FOUNDATION
        ("M 206 210 V 230 H 124 V 252", 1.2),
        # Core bottom-right -> 0xC0R3-OPS
        ("M 254 210 V 230 H 336 V 252", 1.6),
        # Cross-bridge Bottom-left <-> Bottom-right
        ("M 212 274 H 248", 2.0),
        # Side vertical bypasses TRUST -> SOC -> FOUNDATION and ONCHAIN -> AI -> OPS
        ("M 86 106 V 156", 1.4),
        ("M 86 204 V 252", 1.8),
        ("M 374 106 V 156", 0.6),
        ("M 374 204 V 252", 2.2),
    ]
    traces_svg = []
    for d, delay in circuit_paths:
        traces_svg.append(
            f'<path d="{d}" fill="none" stroke="{p["border"]}" stroke-width="1.3"/>'
            f'<path d="{d}" fill="none" stroke="{p["ink"]}" stroke-width="1.5" '
            f'stroke-dasharray="8 110" class="pulse" style="animation-delay:{delay:.2f}s"/>'
        )

    # Junction nodes along bus
    junctions = [(124, 130), (336, 130), (206, 130), (254, 130), (206, 230), (254, 230), (124, 230), (336, 230)]
    junc_svg = "".join(f'<rect x="{jx - 2.5}" y="{jy - 2.5}" width="5" height="5" fill="{p["ink"]}"/>' for jx, jy in junctions)

    tier_cards = [
        (36, 62, 176, 44, "P04", "TRUST FABRIC", "Vault · Merkle · DID [3m]"),
        (248, 62, 176, 44, "P05", "ONCHAIN SURFACE", "Fault · Ledger [2m]"),
        (30, 158, 128, 44, "P02", "SOC SIGNAL", "Mesh · Case [4m]"),
        (302, 158, 128, 44, "P03", "VERIF. AI", "Search · Lab [3m]"),
        (36, 252, 176, 44, "P01", "FOUNDATION", "Events · Runtime [4m]"),
        (248, 252, 176, 44, "P06", "0xC0R3-OPS", "Reference Deploy [1m]"),
    ]
    cards_svg = []
    for cx, cy, cw, ch, port, name, sub in tier_cards:
        cards_svg.append(f'''
  <g>
    <rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="3" fill="{p["bg"]}" stroke="{p["border"]}" stroke-width="1"/>
    <rect x="{cx}" y="{cy}" width="{cw}" height="2.5" fill="{p["ink"]}" opacity="0.7"/>
    <text x="{cx + 8}" y="{cy + 18}" class="port" fill="{p["ink_muted"]}">{port}</text>
    <text x="{cx + 30}" y="{cy + 18}" class="node" fill="{p["ink"]}">{name}</text>
    <text x="{cx + 8}" y="{cy + 34}" class="micro" fill="{p["ink_muted"]}">{sub}</text>
  </g>''')

    # RIGHT TOP: Axis-Calibrated Monochrome Telemetry Chart
    metrics_rows = [
        ("COMMITS", m["commits"], p["bars"][0]),
        ("PULL REQ", m["prs"], p["bars"][1]),
        ("ISSUES", m["issues"], p["bars"][2]),
        ("NEW REPOS", m["repos_created"], p["bars"][3]),
    ]
    max_m = max(v for _, v, _ in metrics_rows) or 1
    bar_x0, bar_max = 574.0, 232.0
    grid_lines = []
    for pct in (0, 25, 50, 75, 100):
        gx = bar_x0 + bar_max * (pct / 100.0)
        grid_lines.append(
            f'<line x1="{gx:.1f}" y1="54" x2="{gx:.1f}" y2="150" stroke="{p["hairline"]}" stroke-dasharray="2 3" stroke-width="0.9"/>'
            f'<text x="{gx:.1f}" y="162" text-anchor="middle" class="tick" fill="{p["ink_faint"]}">{pct}%</text>'
        )

    bar_rows = []
    for i, (lbl, val, col) in enumerate(metrics_rows):
        ry = 62 + i * 22
        frac = 0.45 * (val / max_m) + 0.55 * (math.log1p(val) / math.log1p(max_m))
        bw = max(10.0, bar_max * frac)
        bar_rows.append(
            f'<text x="476" y="{ry + 10}" class="xs" fill="{p["ink_2"]}">{lbl}</text>'
            f'<rect x="{bar_x0:.1f}" y="{ry}" width="{bar_max:.0f}" height="12" rx="1.5" fill="{p["elevated"]}"/>'
            f'<rect x="{bar_x0:.1f}" y="{ry}" width="{bw:.1f}" height="12" rx="1.5" fill="{col}"/>'
            + (f'<rect x="{bar_x0:.1f}" y="{ry}" width="{bw:.1f}" height="12" rx="1.5" fill="url(#bpHatch)" opacity="0.22"/>' if i % 2 == 1 else "")
            + f'<text x="848" y="{ry + 10}" text-anchor="end" class="val" fill="{p["ink"]}">{val}</text>'
        )

    # RIGHT BOTTOM: Monochrome Tabular Stack Meters (super readable in both light & dark!)
    top_langs = m["top_langs"] or [("Python", 5), ("JavaScript", 5), ("TypeScript", 2)]
    total_l = sum(c for _, c in top_langs) or 1
    lang_rows = []
    for i, (lname, cnt) in enumerate(top_langs):
        ly = 224 + i * 20
        pct = round(100 * cnt / total_l)
        mw = max(8.0, 178.0 * (cnt / total_l))
        shade = p["bars"][min(i, len(p["bars"]) - 1)]
        lang_rows.append(
            f'<text x="476" y="{ly + 8}" class="xs" fill="{p["ink"]}">{escape(lname)}</text>'
            f'<rect x="574" y="{ly}" width="178" height="8" rx="1" fill="{p["elevated"]}"/>'
            f'<rect x="574" y="{ly}" width="{mw:.1f}" height="8" rx="1" fill="{shade}"/>'
            f'<text x="796" y="{ly + 8}" text-anchor="end" class="xs" fill="{p["ink_2"]}">{pct:2d}%</text>'
            f'<text x="848" y="{ly + 8}" text-anchor="end" class="micro" fill="{p["ink_muted"]}">{cnt}r</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="100%" role="img" aria-label="0xR3TRO Defense-in-Depth Circuit Topology and Charts">
  <defs>
    <pattern id="dotGrid" width="14" height="14" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="0.8" fill="{p["grid_dot"]}"/>
    </pattern>
    <pattern id="bpHatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <line x1="0" y1="0" x2="0" y2="5" stroke="{p["hatch_stroke"]}" stroke-width="1.5"/>
    </pattern>
  </defs>
  <style>
    text {{ font-family: {MONO}; }}
    .hdr {{ font-size: 10px; font-weight: 700; letter-spacing: 0.9px; }}
    .port {{ font-size: 8px; font-weight: 700; }}
    .node {{ font-size: 9px; font-weight: 700; letter-spacing: 0.3px; }}
    .core {{ font-size: 11px; font-weight: 700; letter-spacing: 0.8px; }}
    .xs {{ font-size: 9.5px; }}
    .val {{ font-size: 10px; font-weight: 700; }}
    .micro {{ font-size: 8px; letter-spacing: 0.3px; }}
    .tick {{ font-size: 7.5px; }}
    .pulse {{ animation: busPulse 3.4s linear infinite; }}
    @keyframes busPulse {{ 0% {{ stroke-dashoffset: 118; }} 100% {{ stroke-dashoffset: 0; }} }}
  </style>

  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="4" fill="{p["bg"]}" stroke="{p["border"]}" stroke-width="1"/>

  <!-- LEFT: 3-Tier Defense-in-Depth Circuit Bus -->
  <rect x="16" y="16" width="428" height="324" rx="4" fill="{p["surface"]}" stroke="{p["border"]}" stroke-width="1"/>
  <rect x="17" y="44" width="426" height="270" fill="url(#dotGrid)"/>
  <text x="28" y="34" class="hdr" fill="{p["ink"]}">DEFENSE-IN-DEPTH CIRCUIT TOPOLOGY</text>
  <text x="432" y="34" text-anchor="end" class="micro" fill="{p["ink_muted"]}">3-TIER BUS · 6 PORTS</text>
  <line x1="16" y1="44" x2="444" y2="44" stroke="{p["border"]}" stroke-width="1"/>

  <!-- Orthogonal PCB Traces & Junctions -->
  <g>{"".join(traces_svg)}</g>
  <g>{junc_svg}</g>

  <!-- Central Core Bus Block -->
  <rect x="176" y="150" width="108" height="60" rx="3" fill="{p["inv_bg"]}" stroke="{p["ink"]}" stroke-width="1.5"/>
  <rect x="181" y="155" width="98" height="50" rx="1.5" fill="none" stroke="{p["inv_ink"]}" stroke-opacity="0.35" stroke-width="0.8"/>
  <text x="230" y="177" text-anchor="middle" class="core" fill="{p["inv_ink"]}">0xR3TRO</text>
  <text x="230" y="191" text-anchor="middle" class="micro" fill="{p["inv_ink"]}" opacity="0.75">VERIFIABLE CORE</text>

  <!-- 6 Tier Cards -->
  <g>{"".join(cards_svg)}</g>

  <line x1="16" y1="314" x2="444" y2="314" stroke="{p["border"]}" stroke-width="1"/>
  <text x="28" y="331" class="micro" fill="{p["ink_muted"]}">ANONYMITY IS NOT A MASK — IT'S A SHIELD</text>
  <text x="432" y="331" text-anchor="end" class="micro" fill="{p["ink_2"]}">17 MODULES · PRIV</text>

  <!-- RIGHT TOP: Axis-Calibrated Telemetry -->
  <rect x="460" y="16" width="404" height="162" rx="4" fill="{p["surface"]}" stroke="{p["border"]}" stroke-width="1"/>
  <text x="476" y="35" class="hdr" fill="{p["ink"]}">CONTRIBUTION TELEMETRY</text>
  <text x="848" y="35" text-anchor="end" class="val" fill="{p["ink"]}">{m["total_contributions"]:,} TOTAL</text>
  <line x1="460" y1="45" x2="864" y2="45" stroke="{p["border"]}" stroke-width="1"/>
  {"".join(grid_lines)}
  {"".join(bar_rows)}

  <!-- RIGHT BOTTOM: Stack Matrix -->
  <rect x="460" y="190" width="404" height="150" rx="4" fill="{p["surface"]}" stroke="{p["border"]}" stroke-width="1"/>
  <text x="476" y="209" class="hdr" fill="{p["ink"]}">LANGUAGE STACK MATRIX</text>
  <text x="848" y="209" text-anchor="end" class="micro" fill="{p["ink_muted"]}">{m["public_repos"]} PUB · {m["private_repos"]} PRIV</text>
  <line x1="460" y1="217" x2="864" y2="217" stroke="{p["hairline"]}" stroke-width="1"/>
  {"".join(lang_rows)}
  <text x="476" y="331" class="micro" fill="{p["ink_muted"]}">STATUS: <tspan fill="{p["ink"]}">OPERATIONAL</tspan></text>
  <text x="848" y="331" text-anchor="end" class="micro" fill="{p["ink_2"]}">STREAK: {m["streak"]}D · ACTIVE: {m["active_days_count"]}D</text>
</svg>
'''


def render_route_map(p: dict) -> str:
    w_svg, h_svg = 880, 198
    # Git-graph / Railway horizontal release route + 3-stage architecture alignment
    nodes = [
        (56, "01", "PLANNED", "done"),
        (194, "02", "CREATED-PRIV", "active"),
        (356, "03", "BOOTSTRAPPED", "next"),
        (518, "04", "VERTICAL-SLICE", "todo"),
        (680, "05", "VERIFIED", "todo"),
        (824, "06", "PUBLIC-REL", "todo"),
    ]
    rail_svg = [
        f'<line x1="56" y1="62" x2="194" y2="62" stroke="{p["ink"]}" stroke-width="2"/>',
        f'<line x1="194" y1="62" x2="824" y2="62" stroke="{p["border"]}" stroke-dasharray="4 4" stroke-width="1.5"/>',
    ]
    for nx, num, lbl, st in nodes:
        if st == "active":
            rail_svg.append(
                f'<rect x="{nx - 9}" y="53" width="18" height="18" rx="2" fill="{p["inv_bg"]}" stroke="{p["ink"]}" stroke-width="1.5"/>'
                f'<rect x="{nx - 3.5}" y="58.5" width="7" height="7" fill="{p["inv_ink"]}"/>'
                f'<text x="{nx}" y="44" text-anchor="middle" class="badge" fill="{p["ink"]}">[{num}] NOW · 17/17</text>'
                f'<text x="{nx}" y="86" text-anchor="middle" class="badge" fill="{p["ink"]}">{lbl}</text>'
            )
        elif st == "done":
            rail_svg.append(
                f'<circle cx="{nx}" cy="62" r="6" fill="{p["ink"]}"/>'
                f'<text x="{nx}" y="44" text-anchor="middle" class="micro" fill="{p["ink_muted"]}">[{num}]</text>'
                f'<text x="{nx}" y="86" text-anchor="middle" class="micro" fill="{p["ink_2"]}">{lbl}</text>'
            )
        else:
            rail_svg.append(
                f'<circle cx="{nx}" cy="62" r="5.5" fill="{p["bg"]}" stroke="{p["ink_muted"]}" stroke-width="1.3"/>'
                f'<text x="{nx}" y="44" text-anchor="middle" class="micro" fill="{p["ink_faint"]}">[{num}]</text>'
                f'<text x="{nx}" y="86" text-anchor="middle" class="micro" fill="{p["ink_muted"]}">{lbl}</text>'
            )

    flows = [
        (16, "[IN] CRYPTO & ON-CHAIN", "Trust Fabric · Onchain Threat Surface"),
        (308, "[PROC] SIGNAL & EVIDENCE", "SOC Signal Network · Verifiable AI"),
        (600, "[OUT] BOUNDED ACTION", "Foundation Protocol · 0xC0R3-OPS"),
    ]
    flow_boxes = []
    for x, title, sub in flows:
        flow_boxes.append(
            f'<rect x="{x}" y="112" width="264" height="52" rx="3" fill="{p["surface"]}" stroke="{p["border"]}" stroke-width="1"/>'
            f'<text x="{x + 12}" y="133" class="badge" fill="{p["ink"]}">{escape(title)}</text>'
            f'<text x="{x + 12}" y="151" class="micro" fill="{p["ink_muted"]}">{escape(sub)}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="100%" role="img" aria-label="0xR3TRO Lifecycle and Architecture Route Map">
  <style>
    text {{ font-family: {MONO}; }}
    .hdr {{ font-size: 10px; font-weight: 700; letter-spacing: 0.9px; }}
    .badge {{ font-size: 9px; font-weight: 700; letter-spacing: 0.4px; }}
    .micro {{ font-size: 8px; letter-spacing: 0.4px; }}
  </style>

  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="4" fill="{p["bg"]}" stroke="{p["border"]}" stroke-width="1"/>
  <text x="18" y="23" class="hdr" fill="{p["ink"]}">ROUTE MAP // RELEASE LIFECYCLE &amp; EXECUTION FLOW</text>
  <text x="862" y="23" text-anchor="end" class="micro" fill="{p["ink_muted"]}">NEXT GATE: BOOTSTRAPPED</text>

  {"".join(rail_svg)}
  <line x1="16" y1="100" x2="864" y2="100" stroke="{p["hairline"]}" stroke-width="1"/>
  {"".join(flow_boxes)}
  <text x="294" y="142" text-anchor="middle" class="badge" fill="{p["ink_muted"]}">→</text>
  <text x="586" y="142" text-anchor="middle" class="badge" fill="{p["ink_muted"]}">→</text>

  <text x="440" y="185" text-anchor="middle" class="micro" fill="{p["ink_muted"]}">
    AI = TECHNOLOGY LAYER, NOT GOAL  ·  WEB3 = ONLY WHERE IT EARNS TRUST  ·  LINKED AT PUBLIC-RELEASE
  </text>
</svg>
'''


def render_programs(p: dict) -> str:
    # Integrated Schematic Manpage Table (6 rows, zero markdown clash!)
    w_svg, h_svg = 880, 276
    rows = []
    for i, (num, title, scope, mods) in enumerate(PROGRAMS):
        ry = 68 + i * 33
        bg = p["surface"] if i % 2 == 0 else p["bg"]
        rows.append(
            f'<rect x="1" y="{ry - 18}" width="{w_svg - 2}" height="32" fill="{bg}"/>'
            f'<line x1="16" y1="{ry + 14}" x2="864" y2="{ry + 14}" stroke="{p["hairline"]}" stroke-width="0.9"/>'
            f'<text x="24" y="{ry + 2}" class="idx" fill="{p["ink_muted"]}">[{num}]</text>'
            f'<text x="64" y="{ry + 2}" class="title" fill="{p["ink"]}">{escape(title)}</text>'
            f'<text x="256" y="{ry + 2}" class="desc" fill="{p["ink_2"]}">{escape(scope)}</text>'
            f'<text x="488" y="{ry + 2}" class="mods" fill="{p["ink_muted"]}">{escape(mods)}</text>'
            f'<rect x="814" y="{ry - 10}" width="44" height="17" rx="2" fill="{p["elevated"]}" stroke="{p["border"]}" stroke-width="0.8"/>'
            f'<text x="836" y="{ry + 1.5}" text-anchor="middle" class="micro" fill="{p["ink_2"]}">PRIV</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="100%" role="img" aria-label="0xR3TRO Ecosystem Program Matrix">
  <style>
    text {{ font-family: {MONO}; }}
    .hdr {{ font-size: 9.5px; font-weight: 700; letter-spacing: 0.8px; }}
    .idx {{ font-size: 9.5px; font-weight: 700; }}
    .title {{ font-size: 9.8px; font-weight: 700; letter-spacing: 0.3px; }}
    .desc {{ font-size: 9px; }}
    .mods {{ font-size: 8.5px; }}
    .micro {{ font-size: 7.8px; font-weight: 700; letter-spacing: 0.4px; }}
  </style>

  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="4" fill="{p["bg"]}" stroke="{p["border"]}" stroke-width="1"/>
  <rect x="1" y="1" width="{w_svg - 2}" height="46" rx="3" fill="{p["elevated"]}"/>
  <line x1="1" y1="47" x2="{w_svg - 1}" y2="47" stroke="{p["border"]}" stroke-width="1"/>

  <text x="24" y="20" class="hdr" fill="{p["ink"]}">PROGRAM SPECIFICATION INDEX</text>
  <text x="858" y="20" text-anchor="end" class="micro" fill="{p["ink_muted"]}">6 PROGRAMS · 17 MODULES</text>

  <text x="24" y="38" class="micro" fill="{p["ink_muted"]}">ID</text>
  <text x="64" y="38" class="micro" fill="{p["ink_muted"]}">PROGRAM</text>
  <text x="256" y="38" class="micro" fill="{p["ink_muted"]}">SCOPE</text>
  <text x="488" y="38" class="micro" fill="{p["ink_muted"]}">MODULES</text>
  <text x="836" y="38" text-anchor="middle" class="micro" fill="{p["ink_muted"]}">STATE</text>

  {"".join(rows)}
</svg>
'''


def render_nav_button(cmd: str, p: dict) -> str:
    w_svg, h_svg = 166, 36
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w_svg} {h_svg}" width="{w_svg}" height="{h_svg}" role="img" aria-label="{escape(cmd)}">
  <style>
    text {{ font-family: {MONO}; }}
    .cmd {{ font-size: 10px; font-weight: 700; letter-spacing: 0.3px; }}
    .prompt {{ font-size: 10px; font-weight: 700; }}
  </style>
  <rect x="0.5" y="0.5" width="{w_svg - 1}" height="{h_svg - 1}" rx="4" fill="{p["bg"]}" stroke="{p["border"]}" stroke-width="1"/>
  <rect x="3.5" y="3.5" width="{w_svg - 7}" height="{h_svg - 7}" rx="2" fill="{p["surface"]}"/>
  <text x="15" y="21.5" class="prompt" fill="{p["ink_muted"]}">$</text>
  <text x="27" y="21.5" class="cmd" fill="{p["ink"]}">{escape(cmd[2:])}</text>
  <text x="{w_svg - 13}" y="21.5" text-anchor="end" class="prompt" fill="{p["ink_faint"]}">↵</text>
</svg>
'''


def main() -> int:
    user = fetch_stats()
    m = compute_metrics(user)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for mode, pal in PALETTES.items():
        (OUTPUT_DIR / f"activity-{mode}.svg").write_text(render_activity(m, pal), encoding="utf-8")
        (OUTPUT_DIR / f"overview-{mode}.svg").write_text(render_overview(m, pal), encoding="utf-8")
        (OUTPUT_DIR / f"route-{mode}.svg").write_text(render_route_map(pal), encoding="utf-8")
        (OUTPUT_DIR / f"programs-{mode}.svg").write_text(render_programs(pal), encoding="utf-8")
        for key, cmd in NAV_ITEMS:
            (OUTPUT_DIR / f"nav-{key}-{mode}.svg").write_text(render_nav_button(cmd, pal), encoding="utf-8")
    print(f"Generated Mono Proposal 2 (dark+light) in {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
