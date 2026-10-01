"""GitHub profile README: GitHub-native content (activity, languages, repos) in the landing aesthetic.

Run:  python build_readme.py           -> fetches live data, writes assets/r/*.svg + README.md
      python build_readme.py --cached  -> reuses src/gh.json (no network)
Data comes from the GitHub GraphQL API (token from GH_TOKEN / GITHUB_TOKEN, or `gh auth token`).
"""
import datetime as dt
import html
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from build_profile import THEMES, Svg, esc, hero, panel, para, pill, wrap, button

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent if HERE.name == "scripts" else HERE
OUT = ROOT / "assets" / "r"
CACHE = HERE / ".cache" / "gh.json"
LOGIN = "Masega360"

# Curated cards: GitHub descriptions are mixed-language, these read better on the profile.
REPOS = [
    ("VecFin", "Net worth in one place: Go backend aggregating wallets, banks and crypto brokers, with an AI assistant.", None),
    ("ai-gateway", "Load balancer for a fleet of Ollama nodes: queue, health checks, retries, OpenAI-compatible API.", None),
    ("the-stalker", "Real-time person analytics: ESP32 cameras over MQTT, Rekognition / YOLOv8, relay control.", None),
    ("golf-sim-vision", "Golf ball tracking at 120 fps for an indoor simulator: ball speed and launch angle.", None),
    ("KorusLedger", "Event-driven personal finance backend. Kotlin, Spring Boot, Clean Architecture.", None),
    ("gripper", "Modular 3D-printable holders with a web configurator that exports ready-to-print STL.", None),
]

NOW = [
    ("building", "Anima", "a multi-agent system where every action passes a risk gate"),
    ("learning", "Rust & C", "going closer to the metal"),
    ("ask me about", "backends & agents", "event-driven design, LLM serving, agents with guardrails"),
    ("looking for", "part-time / async", "backend or applied-AI roles · UTC-3"),
]

LANDING = {
    "dark": dict(THEMES["dark"], bg="#12141C", panel="#1A1D27", panel2="#1F2330", line="#2A2E3A", line2="#353A49",
                 text="#E4E6EB", muted="#8B8FA3", faint="#565B6C", acc="#E8A33D", acc_ink="#191307",
                 teal="#6EE7B7", teal_bg="#1B2B27", acc_bg="#2A2316", pipes="#353A49"),
    "light": dict(THEMES["light"], bg="#F6F4EF", panel="#FFFFFF", panel2="#F1EEE7", line="#E2DED4", line2="#D3CEC2",
                  text="#1A1C24", muted="#5F6373", faint="#9A9DA8", acc="#B8740F", acc_ink="#FFFFFF",
                  teal="#0E8F63", teal_bg="#E3F3EC", acc_bg="#F6EBD9", pipes="#D3CEC2"),
}

QUERY = """query{ viewer{
  login createdAt followers{totalCount}
  repositories(ownerAffiliations:[OWNER, ORGANIZATION_MEMBER, COLLABORATOR], first:100, orderBy:{field:PUSHED_AT, direction:DESC}){
    totalCount nodes{ name isFork isPrivate owner{login} pushedAt
      languages(first:15){ edges{ size node{name color} } } } }
  contributionsCollection{ totalCommitContributions totalPullRequestContributions
    totalPullRequestReviewContributions totalIssueContributions restrictedContributionsCount
    contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } } }
}}"""


# ----------------------------------------------------------------------------- data

def token():
    for k in ("PROFILE_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(k):
            return os.environ[k]
    return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY}).encode(),
        headers={"Authorization": f"bearer {token()}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(body["errors"])
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(body), encoding="utf-8")
    return body


def load(cached):
    body = json.loads(CACHE.read_text(encoding="utf-8")) if cached and CACHE.exists() else fetch()
    d = body["data"]
    return d.get("user") or d.get("viewer")


def streaks(days):
    cur = best = run = 0
    for day in days:
        run = run + 1 if day["contributionCount"] > 0 else 0
        best = max(best, run)
    # current streak: count back from today (today may still be empty)
    for i, day in enumerate(reversed(days)):
        if day["contributionCount"] > 0:
            cur += 1
        elif i > 0:
            break
    return cur, best


def languages(user, top=7, skip=("HTML", "CSS", "EJS", "Dockerfile", "Shell", "Makefile", "Batchfile")):
    agg = {}
    for r in user["repositories"]["nodes"]:
        if r["isFork"]:
            continue
        for e in r["languages"]["edges"]:
            if e["node"]["name"] in skip:
                continue
            agg[e["node"]["name"]] = agg.get(e["node"]["name"], 0) + e["size"]
    total = sum(agg.values()) or 1
    items = sorted(agg.items(), key=lambda x: -x[1])
    head = [(n, v / total) for n, v in items[:top]]
    rest = sum(v for _, v in items[top:]) / total
    if rest > 0:
        head.append(("Other", rest))
    return head


def ago(iso, now):
    d = (now - dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    if d < 1:
        return "today"
    if d < 31:
        return f"{d}d ago"
    if d < 365:
        return f"{d // 30}mo ago"
    return f"{d // 365}y ago"


# ----------------------------------------------------------------------------- cards

def section_label(s, x, y, num, text):
    c = s.c
    s.t(x, y, f'<tspan fill="{c["faint"]}">{num}</tspan>  {esc(text)}', "JB", 12, c["acc"], ls=0.6)


def now_card(c):
    w, h = 1000, 196
    s = Svg(c, w, h, "Now: " + "; ".join(f"{k}: {t} — {d}" for k, t, d in NOW))
    panel(s, 0, 0, w, h, 10)
    section_label(s, 24, 34, "01", "now")
    colw = (w - 48) / 4
    for i, (k, title, desc) in enumerate(NOW):
        x = 24 + i * colw
        if i:
            s.add(f'<line x1="{x - 12:.0f}" y1="58" x2="{x - 12:.0f}" y2="{h - 22}" stroke="{c["line"]}"/>')
        s.t(x, 74, k.upper(), "JB", 10.5, c["faint"], ls=0.8)
        s.t(x, 104, esc(title), "SG", 21, c["teal"] if i == 3 else c["text"])
        para(s, x, 132, desc, colw - 28, 13.5, "IN", c["muted"], 1.45)
    return s.render()


def activity_card(c, user, now):
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    weeks = cal["weeks"]
    days = [d for wk in weeks for d in wk["contributionDays"]]
    cur, best = streaks(days)
    w = 1000
    cell, gap = 14, 3.6
    gx, gy = 52, 172
    h = gy + 7 * (cell + gap) + 64
    s = Svg(c, w, h, f"{cal['totalContributions']} contributions in the last year: "
                     f"{cc['totalCommitContributions']} commits, {cc['totalPullRequestContributions']} pull requests, "
                     f"{cc['totalPullRequestReviewContributions']} reviews. Longest streak {best} days.")
    panel(s, 0, 0, w, h, 10)
    section_label(s, 24, 34, "01", "activity · last 12 months")
    stats = [
        (f"{cal['totalContributions']:,}", "contributions"),
        (str(cc["totalCommitContributions"]), "commits"),
        (str(cc["totalPullRequestContributions"]), "pull requests"),
        (str(cc["totalPullRequestReviewContributions"]), "reviews"),
        (str(cc["totalIssueContributions"]), "issues"),
        (f"{best}d", "longest streak"),
    ]
    sw = (w - 48) / len(stats)
    for i, (v, lab) in enumerate(stats):
        x = 24 + i * sw
        s.t(x, 92, esc(v), "SGB", 38, c["acc"] if i == 0 else c["text"], ls=-1.2)
        s.t(x, 118, esc(lab), "JB", 11.5, c["muted"])
    # heatmap
    mx = max((d["contributionCount"] for d in days), default=1) or 1
    levels = [c["panel2"]]
    ops = [0.28, 0.5, 0.75, 1.0]
    s.add(f'<line x1="24" y1="142" x2="{w-24}" y2="142" stroke="{c["line"]}"/>')
    last_month, last_wi = None, -9
    for wi, wk in enumerate(weeks):
        x = gx + wi * (cell + gap)
        for d in wk["contributionDays"]:
            wd = dt.date.fromisoformat(d["date"]).isoweekday() % 7  # Sunday = 0
            y = gy + wd * (cell + gap)
            n = d["contributionCount"]
            if n == 0:
                s.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="3" fill="{c["panel2"]}" stroke="{c["line"]}" stroke-width=".6"/>')
            else:
                lvl = min(3, int((n / mx) ** 0.6 * 4))
                col = c["teal"] if lvl == 3 else c["acc"]
                s.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="3" fill="{col}" fill-opacity="{ops[lvl]}"/>')
        m = dt.date.fromisoformat(wk["contributionDays"][0]["date"]).strftime("%b")
        if m != last_month:
            if wi - last_wi >= 3 and wi < len(weeks) - 2:
                s.t(round(x, 1), gy - 10, m, "JB", 10.5, c["faint"])
                last_wi = wi
            last_month = m
    for wd, lab in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        s.t(gx - 10, gy + wd * (cell + gap) + 11, lab, "JB", 10, c["faint"], "end")
    ly = h - 26
    s.t(24, ly, f"current streak {cur}d · member since {user['createdAt'][:4]}", "JB", 11, c["faint"])
    lx = w - 24 - 5 * (cell + 4) - 40
    s.t(lx - 8, ly, "less", "JB", 10.5, c["faint"], "end")
    for i in range(5):
        if i == 0:
            s.add(f'<rect x="{lx + i*(cell+4)}" y="{ly-11}" width="{cell}" height="{cell}" rx="3" fill="{c["panel2"]}" stroke="{c["line"]}" stroke-width=".6"/>')
        else:
            col = c["teal"] if i == 4 else c["acc"]
            s.add(f'<rect x="{lx + i*(cell+4)}" y="{ly-11}" width="{cell}" height="{cell}" rx="3" fill="{col}" fill-opacity="{ops[i-1]}"/>')
    s.t(lx + 5 * (cell + 4) + 4, ly, "more", "JB", 10.5, c["faint"])
    return s.render()


def lang_palette(c):
    return [c["acc"], c["teal"], "#D9A066", "#9C5B47", "#5E8C88", "#C9B79C", c["faint"], c["line2"]]


def languages_card(c, user):
    langs = languages(user)
    w, h = 1000, 176
    s = Svg(c, w, h, "Languages across every repo I work on: " + ", ".join(f"{n} {p*100:.0f}%" for n, p in langs))
    panel(s, 0, 0, w, h, 10)
    section_label(s, 24, 34, "02", "languages · every repo I work on, public + private")
    bx, by, bw, bh = 24, 56, w - 48, 14
    s.add(f'<clipPath id="lb"><rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="7"/></clipPath><g clip-path="url(#lb)">')
    x = bx
    pal = lang_palette(c)
    for i, (n, p) in enumerate(langs):
        seg = bw * p
        s.add(f'<rect x="{x:.1f}" y="{by}" width="{seg + 0.5:.1f}" height="{bh}" fill="{pal[i % len(pal)]}">'
              f'<animate attributeName="width" from="0" to="{seg + 0.5:.1f}" begin="{0.1 + i*0.08:.2f}s" dur="0.6s" fill="freeze"/></rect>')
        x += seg
    s.add("</g>")
    cols = 4
    colw = (w - 48) / cols
    for i, (n, p) in enumerate(langs):
        x = 24 + (i % cols) * colw
        y = 104 + (i // cols) * 34
        s.add(f'<rect x="{x}" y="{y-10}" width="10" height="10" rx="2" fill="{pal[i % len(pal)]}"/>')
        s.t(x + 18, y, esc(n), "INB", 14, c["text"])
        s.t(x + colw - 30, y, f"{p*100:.1f}%", "JB", 12.5, c["muted"], "end")
    return s.render()


BOOK = "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z"
STAR = "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"


def repo_card(c, repo, desc, now):
    w, h = 490, 168
    lang = repo.get("primaryLanguage") or {}
    s = Svg(c, w, h, f"{repo['name']}: {desc}")
    panel(s, 0, 0, w, h, 10)
    s.add(f'<path d="{BOOK}" transform="translate(22 22) scale(1.05)" fill="{c["muted"]}"/>')
    s.t(46, 36, esc(repo["name"]), "INB", 17, c["teal"])
    nx = 46 + len(repo["name"]) * 9.6 + 12
    s.add(f'<rect x="{nx:.0f}" y="21" width="56" height="20" rx="10" fill="none" stroke="{c["line2"]}"/>')
    s.t(round(nx + 28, 1), 35, "Public", "IN", 11.5, c["muted"], "middle")
    s.t(w - 22, 36, "↗", "JB", 15, c["faint"], "end")
    para(s, 22, 72, desc, w - 44, 14, "IN", c["muted"], 1.5)
    fy = h - 24
    s.add(f'<line x1="22" y1="{fy-22}" x2="{w-22}" y2="{fy-22}" stroke="{c["line"]}" stroke-dasharray="2 4"/>')
    x = 22
    if lang:
        s.add(f'<circle cx="{x+6}" cy="{fy-4.5}" r="6" fill="{lang["color"] or c["faint"]}"/>')
        s.t(x + 18, fy, esc(lang["name"]), "IN", 13, c["text"])
        x += 18 + len(lang["name"]) * 7.4 + 22
    s.add(f'<path d="{STAR}" transform="translate({x} {fy-12}) scale(0.85)" fill="{c["acc"] if repo["stargazerCount"] else c["faint"]}"/>')
    s.t(x + 19, fy, str(repo["stargazerCount"]), "IN", 13, c["text"])
    s.t(w - 22, fy, f"updated {ago(repo['pushedAt'], now)}", "JB", 11, c["faint"], "end")
    return s.render()


def contact_strip(c):
    w, h = 1000, 150
    s = Svg(c, w, h, "Let's talk backend. tomascaporaso@gmail.com")
    s.add(f'<defs><radialGradient id="cg" cx="0.95" cy="1" r="0.6"><stop offset="0" stop-color="{c["acc"]}" stop-opacity="{c["glow"]}"/>'
          f'<stop offset="1" stop-color="{c["acc"]}" stop-opacity="0"/></radialGradient></defs>')
    panel(s, 0, 0, w, h, 12)
    s.add(f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="12" fill="url(#cg)"/>')
    s.t(32, 68, f'Let’s talk <tspan fill="{c["acc"]}">backend.</tspan>', "SGB", 40, c["text"], ls=-1.4)
    s.t(34, 104, "Part-time and async-friendly · UTC-3, overlaps with US hours.", "IN", 15.5, c["muted"])
    bw = len("tomascaporaso@gmail.com →") * 13 * 0.6 + 36
    button(s, w - 32 - bw, 54, "tomascaporaso@gmail.com →", True)
    return s.render()


# ----------------------------------------------------------------------------- README

def pic(name, alt, width="100%"):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/r/{name}-dark.svg">'
            f'<source media="(prefers-color-scheme: light)" srcset="assets/r/{name}-light.svg">'
            f'<img alt="{html.escape(alt)}" src="assets/r/{name}-dark.svg" width="{width}"></picture>')


def readme():
    return f"""{pic("activity", "Contribution activity over the last 12 months")}

{pic("languages", "Languages across every repo I work on")}
"""


def main():
    cached = "--cached" in sys.argv
    if os.environ.get("GITHUB_ACTIONS") and not os.environ.get("PROFILE_TOKEN"):
        # The default Actions token can't see private repos or private contributions;
        # keep the committed cards instead of overwriting them with partial data.
        print("::warning::PROFILE_TOKEN secret not set — keeping the current cards.")
        return
    user = load(cached)
    now = dt.datetime.now(dt.timezone.utc)
    by_name = {r["name"]: r for r in user["repositories"]["nodes"]}
    repos = [(by_name[n], d) for n, d, _ in REPOS if n in by_name]
    OUT.mkdir(parents=True, exist_ok=True)
    count = 0
    for theme, c in THEMES.items():
        files = {
            "activity": activity_card(c, user, now),
            "languages": languages_card(c, user),
        }
        for name, body in files.items():
            (OUT / f"{name}-{theme}.svg").write_text(body, encoding="utf-8")
            count += 1
    # same card in the landing page palette (masega360.github.io loads these)
    for theme, c in LANDING.items():
        (OUT / f"activity-landing-{theme}.svg").write_text(activity_card(c, user, now), encoding="utf-8")
        count += 1
    (ROOT / "README.md").write_text(readme(), encoding="utf-8")
    print(f"wrote {count} svgs + README.md")


if __name__ == "__main__":
    main()
