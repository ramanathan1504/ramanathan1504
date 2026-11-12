#!/usr/bin/env python3
"""Renders a GitHub-style (dark) contribution panel as SVG.
Usage: contrib_card.py <login> <out.svg>   (env GH_TOKEN required)
       contrib_card.py --mock <out.svg>    (offline test data)"""
import base64, datetime as dt, json, os, random, sys, urllib.request
from html import escape

Q = """query($login:String!){ user(login:$login){
 organizations(first:3){ totalCount nodes{ login avatarUrl(size:40) } }
 contributionsCollection{
  totalCommitContributions totalIssueContributions
  totalPullRequestContributions totalPullRequestReviewContributions
  restrictedContributionsCount
  commitContributionsByRepository(maxRepositories:100){ repository{ nameWithOwner } }
  pullRequestContributionsByRepository(maxRepositories:100){ repository{ nameWithOwner } }
  issueContributionsByRepository(maxRepositories:100){ repository{ nameWithOwner } }
  pullRequestReviewContributionsByRepository(maxRepositories:100){ repository{ nameWithOwner } }
  contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount contributionLevel weekday } } }
 }}}"""

def fetch(login):
    req = urllib.request.Request("https://api.github.com/graphql",
        data=json.dumps({"query": Q, "variables": {"login": login}}).encode(),
        headers={"Authorization": "bearer " + os.environ["GH_TOKEN"], "User-Agent": "contrib-card"})
    d = json.load(urllib.request.urlopen(req))
    if "errors" in d: sys.exit(json.dumps(d["errors"]))
    return d["data"]["user"]

def avatar(url):
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "contrib-card"})).read()
        return "data:image/png;base64," + base64.b64encode(raw).decode()
    except Exception:
        return None

def mock():
    start = dt.date(2025, 11, 9); weeks = []
    lv = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]
    for w in range(53):
        days = []
        for d in range(7):
            day = start + dt.timedelta(w * 7 + d)
            if day > dt.date(2026, 11, 12): break
            days.append({"date": day.isoformat(), "contributionCount": 0, "weekday": d,
                         "contributionLevel": random.choice(lv[:2] * 3 + lv)})
        weeks.append({"contributionDays": days})
    repos = [{"repository": {"nameWithOwner": n}} for n in
             ["apache/commons-secure-xml", "apache/logging-log4j2", "apache/logging-flume"] + [f"x/r{i}" for i in range(215)]]
    return {"organizations": {"totalCount": 5, "nodes": [{"login": "apache", "avatarUrl": ""},
            {"login": "copernik-eu", "avatarUrl": ""}, {"login": "github", "avatarUrl": ""}]},
            "contributionsCollection": {"totalCommitContributions": 450, "totalIssueContributions": 40,
            "totalPullRequestContributions": 300, "totalPullRequestReviewContributions": 210,
            "restrictedContributionsCount": 0, "commitContributionsByRepository": repos,
            "pullRequestContributionsByRepository": [], "issueContributionsByRepository": [],
            "pullRequestReviewContributionsByRepository": [],
            "contributionCalendar": {"totalContributions": 1946, "weeks": weeks}}}

BG, BORDER, FG, MUTED, LINK = "#212830", "#3d444d", "#d1d7e0", "#9198a1", "#478be6"
LEVEL = {"NONE": "#2a313c", "FIRST_QUARTILE": "#1b4721", "SECOND_QUARTILE": "#2b6a30",
         "THIRD_QUARTILE": "#46954a", "FOURTH_QUARTILE": "#6bc46d"}
GREEN = "#57ab5a"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"

def render(u, use_avatars=True):
    c = u["contributionsCollection"]; cal = c["contributionCalendar"]
    W, PAD = 900, 16; o = []
    t = lambda x, y, s, size=12, fill=FG, anchor="start", weight=400: o.append(
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>')
    t(0, 22, f'{cal["totalContributions"]:,} contributions in the last year', 16)
    # main box
    BOX_Y = 36
    # heatmap
    CELL, GAP = 12, 3; STEP = CELL + GAP
    HX, HY = PAD + 32, BOX_Y + 40
    last_month, last_label = None, -9
    for wi, wk in enumerate(cal["weeks"]):
        for d in wk["contributionDays"]:
            x, y = HX + wi * STEP, HY + d["weekday"] * STEP
            o.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{LEVEL[d["contributionLevel"]]}"/>')
        first = dt.date.fromisoformat(wk["contributionDays"][0]["date"])
        if first.month != last_month:
            if wi - last_label >= 3 and wi <= len(cal["weeks"]) - 2:
                t(HX + wi * STEP, HY - 8, first.strftime("%b"), 12); last_label = wi
            last_month = first.month
    for wd, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        t(PAD, HY + wd * STEP + 9, name, 12)
    LY = HY + 7 * STEP + 22
    t(HX, LY, "Learn how we count contributions", 12, MUTED)
    lx = HX + 53 * STEP - 5 * STEP - 34
    t(lx - 6, LY, "Less", 12, MUTED, "end")
    for i, k in enumerate(LEVEL):
        o.append(f'<rect x="{lx + i * STEP}" y="{LY - 10}" width="{CELL}" height="{CELL}" rx="2" fill="{LEVEL[k]}"/>')
    t(lx + 5 * STEP + 4, LY, "More", 12, MUTED)
    SEP = LY + 16
    o.append(f'<line x1="0" y1="{SEP}" x2="{W}" y2="{SEP}" stroke="{BORDER}"/>')
    # org chips
    cx, cy = PAD, SEP + 16
    orgs = u["organizations"]["nodes"]
    for org in orgs:
        label = "@" + org["login"]; w = 42 + len(label) * 8.2
        o.append(f'<rect x="{cx}" y="{cy}" width="{w}" height="30" rx="6" fill="none" stroke="{BORDER}"/>')
        src = avatar(org["avatarUrl"]) if use_avatars and org["avatarUrl"] else None
        if src:
            o.append(f'<clipPath id="c{org["login"]}"><rect x="{cx+6}" y="{cy+5}" width="20" height="20" rx="4"/></clipPath>'
                     f'<image href="{src}" x="{cx+6}" y="{cy+5}" width="20" height="20" clip-path="url(#c{org["login"]})"/>')
        else:
            o.append(f'<rect x="{cx+6}" y="{cy+5}" width="20" height="20" rx="4" fill="#30363d"/>')
        t(cx + 32, cy + 20, escape(label), 13, FG, weight=600); cx += w + 8
    if u["organizations"]["totalCount"] > len(orgs):
        o.append(f'<rect x="{cx}" y="{cy}" width="60" height="30" rx="6" fill="none" stroke="{BORDER}"/>')
        t(cx + 30, cy + 20, "More", 13, MUTED, "middle")
    # activity overview (left)
    AY = cy + 64
    t(PAD, AY, "Activity overview", 15)
    seen = []
    for key in ("commitContributionsByRepository", "pullRequestContributionsByRepository",
                "issueContributionsByRepository", "pullRequestReviewContributionsByRepository"):
        for r in c[key]:
            n = r["repository"]["nameWithOwner"]
            if n not in seen: seen.append(n)
    top, rest = seen[:3], max(len(seen) - 3, 0)
    lines, cur = [], "Contributed to "
    parts = [(n, True) for n in top]
    y = AY + 34
    o.append(f'<g font-size="13">')
    o.append(f'<path d="M{PAD} {y-11}h10v12h-10z" fill="none" stroke="{MUTED}"/>')
    tx = PAD + 20
    o.append(f'<text x="{tx}" y="{y}" fill="{FG}">Contributed to <tspan fill="{LINK}">{escape(top[0]) if top else ""}</tspan></text>')
    if len(top) > 1:
        y += 20; o.append(f'<text x="{tx}" y="{y}" fill="{FG}">, <tspan fill="{LINK}">{escape(top[1])}</tspan>{"," if len(top) > 2 else ""}</text>')
    if len(top) > 2:
        y += 20; o.append(f'<text x="{tx}" y="{y}" fill="{LINK}">{escape(top[2])}</text>')
    if rest:
        y += 20; o.append(f'<text x="{tx}" y="{y}" fill="{FG}">and {rest} other repositories</text>')
    o.append('</g>')
    # divider
    MID = W * 0.46
    o.append(f'<line x1="{MID}" y1="{AY - 16}" x2="{MID}" y2="{AY + 220}" stroke="{BORDER}"/>')
    # radar (right)
    vals = {"commits": c["totalCommitContributions"], "prs": c["totalPullRequestContributions"],
            "issues": c["totalIssueContributions"], "reviews": c["totalPullRequestReviewContributions"]}
    tot = sum(vals.values()) or 1
    pct = {k: round(v * 100 / tot) for k, v in vals.items()}
    RX, RY, R = MID + (W - MID) / 2, AY + 108, 80
    mx = max(pct.values()) or 1
    f = lambda k: R * pct[k] / mx
    pts = [(RX, RY - f("reviews")), (RX + f("issues"), RY), (RX, RY + f("prs")), (RX - f("commits"), RY)]
    o.append(f'<line x1="{RX - R}" y1="{RY}" x2="{RX + R}" y2="{RY}" stroke="{GREEN}" stroke-width="2"/>')
    o.append(f'<line x1="{RX}" y1="{RY - R}" x2="{RX}" y2="{RY + R}" stroke="{GREEN}" stroke-width="2"/>')
    o.append('<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) +
             f'" fill="{GREEN}" fill-opacity="0.55" stroke="{GREEN}" stroke-width="2"/>')
    for x, y in pts:
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{BG}" stroke="{GREEN}" stroke-width="2"/>')
    t(RX, RY - R - 24, f'{pct["reviews"]}%', 12, MUTED, "middle"); t(RX, RY - R - 8, "Code review", 12, MUTED, "middle")
    t(RX, RY + R + 18, f'{pct["prs"]}%', 12, MUTED, "middle"); t(RX, RY + R + 34, "Pull requests", 12, MUTED, "middle")
    t(RX - R - 40, RY - 4, f'{pct["commits"]}%', 12, MUTED, "middle"); t(RX - R - 40, RY + 12, "Commits", 12, MUTED, "middle")
    t(RX + R + 36, RY - 4, f'{pct["issues"]}%', 12, MUTED, "middle"); t(RX + R + 36, RY + 12, "Issues", 12, MUTED, "middle")
    H = RY + R + 56
    body = "\n".join(o)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W + 2}" height="{H + 2}" viewBox="-1 -1 {W + 2} {H + 2}" font-family="{FONT}">'
            f'<rect x="-1" y="-1" width="{W + 2}" height="{H + 2}" fill="{BG}"/>'
            f'<rect x="0" y="{BOX_Y}" width="{W}" height="{H - BOX_Y}" rx="6" fill="none" stroke="{BORDER}"/>'
            f'{body}</svg>')

if __name__ == "__main__":
    if sys.argv[1] == "--mock":
        random.seed(4); svg = render(mock(), use_avatars=False)
    else:
        svg = render(fetch(sys.argv[1]))
    os.makedirs(os.path.dirname(sys.argv[2]) or ".", exist_ok=True)
    open(sys.argv[2], "w", encoding="utf-8").write(svg)
