"""Scrape the public contribution calendar and render it as an animated SVG.

Stdlib only, no token: GitHub serves the calendar as public HTML.
Usage: python scripts/heatmap.py [username]  -> writes contrib-heatmap.svg at the repo root.
"""
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

USER = sys.argv[1] if len(sys.argv) > 1 else "albangerschheimer"
OUT = Path(__file__).resolve().parent.parent / "contrib-heatmap.svg"
CELL, GAP, LEFT, TOP = 11, 3, 30, 22


def fetch(user):
    req = urllib.request.Request(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": "profile-heatmap"},
    )
    html = urllib.request.urlopen(req, timeout=30).read().decode()
    counts = {}
    for cid, text in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
        m = re.match(r"(\d+) contribution", text)
        counts[cid] = int(m.group(1)) if m else 0
    days = []
    for td in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", html):
        d = re.search(r'data-date="([\d-]+)"', td)
        lvl = re.search(r'data-level="(\d)"', td)
        cid = re.search(r'id="([^"]+)"', td)
        if d and lvl:
            days.append((date.fromisoformat(d.group(1)), int(lvl.group(1)), counts.get(cid.group(1), 0)))
    if not days:
        raise SystemExit("no contribution cells found, GitHub markup changed?")
    return sorted(days)


def streaks(days):
    longest = run = 0
    for _, _, n in days:
        run = run + 1 if n else 0
        longest = max(longest, run)
    counts = [n for *_, n in days]
    if counts and counts[-1] == 0:  # nothing yet today doesn't break the streak
        counts.pop()
    current = 0
    for n in reversed(counts):
        if not n:
            break
        current += 1
    return current, longest


def render(days):
    start = days[0][0]
    weeks = (days[-1][0] - start).days // 7 + 1
    w = LEFT + weeks * (CELL + GAP) + 10
    h = TOP + 7 * (CELL + GAP) + 34
    total = sum(n for *_, n in days)
    current, longest = streaks(days)

    cells, months, last_month = [], [], None
    for d, lvl, n in days:
        offset = (d - start).days
        col, row = offset // 7, d.isoweekday() % 7  # Sunday on top, like GitHub
        x, y = LEFT + col * (CELL + GAP), TOP + row * (CELL + GAP)
        delay = (col + row) * 0.018
        cells.append(
            f'<rect class="c l{lvl}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
            f'style="animation-delay:{delay:.3f}s"><title>{n} on {d}</title></rect>'
        )
        if row == 0 and d.month != last_month:
            last_month = d.month
            if months and col < 3:  # a partial first month would overlap the next label
                months.pop()
            months.append(f'<text class="t" x="{x}" y="{TOP - 8}">{d.strftime("%b")}</text>')

    labels = "".join(
        f'<text class="t" x="0" y="{TOP + r * (CELL + GAP) + 9}">{name}</text>'
        for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri"))
    )
    fy = h - 10
    legend_x = w - 10 - 5 * (CELL + GAP) - 56
    legend = "".join(
        f'<rect class="l{i}" x="{legend_x + 28 + i * (CELL + GAP)}" y="{fy - 9}" width="{CELL}" height="{CELL}" rx="2.5"/>'
        for i in range(5)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{total} contributions in the last year">
<style>
  .t {{ font: 10px ui-monospace, SFMono-Regular, Menlo, monospace; fill: #7d8590; }}
  .l0 {{ fill: #161b22; }} .l1 {{ fill: #0e4429; }} .l2 {{ fill: #006d32; }} .l3 {{ fill: #26a641; }} .l4 {{ fill: #39d353; }}
  @media (prefers-color-scheme: light) {{
    .t {{ fill: #59636e; }}
    .l0 {{ fill: #ebedf0; }} .l1 {{ fill: #9be9a8; }} .l2 {{ fill: #40c463; }} .l3 {{ fill: #30a14e; }} .l4 {{ fill: #216e39; }}
  }}
  .c {{ transform-box: fill-box; transform-origin: center; animation: pop .35s ease-out backwards; }}
  @keyframes pop {{ from {{ opacity: 0; transform: translateY(-6px) scale(.4); }} to {{ opacity: 1; transform: none; }} }}
</style>
{"".join(months)}{labels}
{"".join(cells)}
<text class="t" x="{LEFT}" y="{fy}">{total:,} contributions in the last year · current streak {current}d · longest {longest}d</text>
<text class="t" x="{legend_x}" y="{fy}">Less</text>{legend}<text class="t" x="{legend_x + 28 + 5 * (CELL + GAP) + 2}" y="{fy}">More</text>
</svg>
"""


if __name__ == "__main__":
    OUT.write_text(render(fetch(USER)))
    print(f"wrote {OUT}")
