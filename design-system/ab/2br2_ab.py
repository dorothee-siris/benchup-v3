"""Phase 2B-R2 (stream VS3) A/B renders -- the three visual questions 2B-R2-2,
2B-R2-9 and the VS3 brief leave open, each drawn through the SHIPPED builders
and screenshotted in a real browser (kaleido is not installed and is not to be
added). Throwaway: `design-system/ab/**` only, never imported by the app.

  2br2_pastel_a / _b   the two candidate institution trios at the REAL bar pitch
                       (26 fields x 3 institutions, the widest Compare panel),
                       value labels in each trio's own dark twins. a = the wind
                       tunnel's proposal (in-trio CVD 6.1), b = the search
                       winner (12.6). What the render has to answer that the
                       validator cannot: is a fill at 2:1 still a bar, and is a
                       twin-coloured number on a light fill still a number.
  2br2_label_ink       variant b with the labels in INK_SECONDARY instead of the
                       twins -- the "do we even need twins" control.
  2br2_erc_a / _b      the ERC panel chart with the A/B-winning mapping (a) and
                       with the plan's listing order (b).
  2br2_dot_a / _b      the Compare overview card: best-value DOT (a) against the
                       tinted-card alternative (b).

Usage (cwd `app/`):
    ../envs/env-app/Scripts/python.exe design-system/ab/2br2_ab.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

AB_DIR = Path(__file__).resolve().parent
APP_DIR = AB_DIR.parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from lib import charts as C            # noqa: E402
from lib import palette as P           # noqa: E402
from lib import charts_compare as X    # noqa: E402

WIDTH = 1280
IDS = ["Ia", "Ib", "Ic"]
NAMES = {"Ia": "Universite de Bordeaux", "Ib": "Universite de Lille",
         "Ic": "Universite de Strasbourg"}
SLOTS = {"Ia": 0, "Ib": 1, "Ic": 2}

FIELDS = [
    (11, "Agricultural and Biological Sciences", 1), (13, "Biochemistry, Genetics and Molecular Biology", 1),
    (28, "Neuroscience", 1), (24, "Immunology and Microbiology", 1),
    (12, "Arts and Humanities", 2), (14, "Business, Management and Accounting", 2),
    (18, "Decision Sciences", 2), (20, "Economics, Econometrics and Finance", 2),
    (33, "Social Sciences", 2), (32, "Psychology", 2),
    (16, "Chemistry", 3), (17, "Computer Science", 3), (19, "Earth and Planetary Sciences", 3),
    (21, "Energy", 3), (22, "Engineering", 3), (23, "Environmental Science", 3),
    (25, "Materials Science", 3), (26, "Mathematics", 3), (31, "Physics and Astronomy", 3),
    (15, "Chemical Engineering", 3), (10, "Multidisciplinary", 3),
    (27, "Medicine", 4), (29, "Nursing", 4), (30, "Pharmacology, Toxicology and Pharmaceutics", 4),
    (35, "Dentistry", 4), (36, "Health Professions", 4),
]
ERC_PANELS = [(0, "LS1 Molecules of Life", "LS"), (1, "LS7 Prevention and Treatment", "LS"),
              (2, "PE1 Mathematics", "PE"), (3, "PE3 Condensed Matter Physics", "PE"),
              (4, "PE8 Products and Processes Engineering", "PE"),
              (5, "SH1 Markets and Organisations", "SH"), (6, "SH3 Environment and Society", "SH")]


def field_frame() -> pd.DataFrame:
    rows = []
    for n, iid in enumerate(IDS):
        for m, (fid, name, dom) in enumerate(FIELDS):
            base = 0.012 + 0.004 * ((m * 7 + n * 3) % 11)
            rows.append(dict(institution_id=iid, taxon_id=fid, taxon_label=name,
                             domain_id=dom, domain_order=dom,
                             value=base, ref_value=0.035,
                             vol_display=int(120 + 37 * ((m * 5 + n) % 13)),
                             vol_full_annual_mean=4.0 if m in (24, 25) else 60.0,
                             denominator=9000 + 100 * n))
    return pd.DataFrame(rows)


def erc_frame() -> pd.DataFrame:
    rows = []
    for n, iid in enumerate(IDS):
        for m, (pid, label, dom) in enumerate(ERC_PANELS):
            rows.append(dict(institution_id=iid, taxon_id=pid, taxon_label=label,
                             erc_domain=dom, domain_id=m, domain_order=m,
                             value=0.05 + 0.02 * ((m + n) % 5), ref_value=0.09,
                             vol_display=int(200 + 60 * ((m + n) % 7)),
                             vol_full_annual_mean=50.0, denominator=8000))
    return pd.DataFrame(rows)


def card_html(dot: bool) -> str:
    """The Compare overview card, both ways. `dot` = 2B-R2-9's ruling; the
    alternative tints the whole card in the leader's hue."""
    cards = []
    metrics = [("Publications", "12 480", "Bordeaux"),
               ("Publications tagged to a goal", "31.4 %", "Lille"),
               ("Publications in the world top decile", "9.8 %", "Strasbourg")]
    for (title, value, leader), slot in zip(metrics, (0, 1, 2)):
        mark = X.best_value_dot(slot, leader) if dot else ""
        bg = P.SURFACE if dot else P.institution_color(slot)
        cards.append(
            f'<div style="flex:1;border:1px solid {P.BORDER};border-radius:6px;'
            f'padding:14px 16px;background:{bg};">'
            f'<div style="font-size:13px;color:{P.INK_SECONDARY};">{title}</div>'
            f'<div style="font-size:26px;font-weight:600;color:{P.INK};'
            f'margin:6px 0;">{value}</div>'
            f'<div style="font-size:11px;color:{P.INK_SECONDARY};">'
            f'{mark or "highest of the three"}</div></div>')
    return ('<div style="display:flex;gap:14px;font-family:system-ui,sans-serif;'
            f'padding:18px;background:{P.SURFACE};">' + "".join(cards) + "</div>")


def write_page(path: Path, body: str) -> None:
    path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'></head>"
        f"<body style='margin:0;background:{P.SURFACE};'>{body}</body></html>",
        encoding="utf-8")


def fig_body(fig) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=True,
                       config={"staticPlot": True}, default_width=f"{WIDTH}px")


def shoot(pw, variants: dict[str, str]) -> None:
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": WIDTH, "height": 1000})
    for name, body in variants.items():
        html = AB_DIR / f"{name}.html"
        write_page(html, body)
        page.goto(html.as_uri())
        page.wait_for_timeout(1400)
        page.screenshot(path=str(AB_DIR / f"{name}_{WIDTH}.png"), full_page=True)
        print("wrote", name)
        html.unlink()
    browser.close()


def with_palette(fills, twins, build):
    keep = (P.INSTITUTION_COLORS, P.INSTITUTION_COLORS_DARK)
    P.INSTITUTION_COLORS, P.INSTITUTION_COLORS_DARK = list(fills), list(twins)
    try:
        return build()
    finally:
        P.INSTITUTION_COLORS, P.INSTITUTION_COLORS_DARK = keep


def main() -> None:
    d = field_frame()
    shipped = (P.INSTITUTION_COLORS, P.INSTITUTION_COLORS_DARK)
    wt_trio = (["#FC9095", "#28CFB7", "#90B3FC"], ["#BC575E", "#0A8575", "#5575B9"])

    def bars(**kw):
        return fig_body(X.fig_metric_bars(d, "share", IDS, slots=SLOTS, names=NAMES,
                                         level="field", **kw))

    variants = {
        "2br2_pastel_a": with_palette(*wt_trio, lambda: bars()),
        "2br2_pastel_b": bars(),
        "2br2_label_ink": with_palette(shipped[0], [P.INK_SECONDARY] * 3, lambda: bars()),
        "2br2_dot_a": card_html(dot=True),
        "2br2_dot_b": card_html(dot=False),
    }
    e = erc_frame()
    variants["2br2_erc_a"] = fig_body(
        X.fig_metric_bars(e, "share", IDS, slots=SLOTS, names=NAMES, level="erc"))
    keep = dict(P.ERC_DOMAIN_COLORS)
    P.ERC_DOMAIN_COLORS.update({"PE": "#D55E00", "LS": "#009E73", "SH": "#6A3D9A"})
    variants["2br2_erc_b"] = fig_body(
        X.fig_metric_bars(e, "share", IDS, slots=SLOTS, names=NAMES, level="erc"))
    P.ERC_DOMAIN_COLORS.update(keep)

    legend = X.legend_strip(IDS, slots=SLOTS, names=NAMES)
    note = X.chart_note("Strasbourg leads in nine of twenty-six fields.",
                        "Shares are computed on the fractional counting basis over "
                        "the five complete years; the gutter shows raw publications.")
    for key in ("2br2_pastel_a", "2br2_pastel_b", "2br2_label_ink",
                "2br2_erc_a", "2br2_erc_b"):
        variants[key] = (f'<div style="font-family:system-ui,sans-serif;padding:12px;'
                         f'background:{P.SURFACE};">{legend}{note}</div>' + variants[key])

    with sync_playwright() as pw:
        shoot(pw, variants)


if __name__ == "__main__":
    main()
