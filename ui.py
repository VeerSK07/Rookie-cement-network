"""
Presentation layer: design tokens, injected CSS, and small HTML builders.

Nothing here knows anything about the optimisation. app.py holds the logic,
model.py holds the maths, this file holds the look.
"""

import html
import streamlit as st

# ---------------------------------------------------------------- tokens

BG       = "#EDF3EB"   # page, light green
SIDEBAR  = "#E4EFE1"   # sidebar, a shade deeper
SURFACE  = "#FFFFFF"   # cards and tables
INK      = "#16294D"   # navy, main text
INK2     = "#465A77"
INK3     = "#77879B"
RULE     = "#D3E2D0"
ACCENT   = "#2E7D4F"   # green, primary
ACCENT_D = "#1E5C39"
BAR      = "#2F6FA8"   # single hue for magnitude in every chart

OK_BG, OK_BR, OK_INK       = "#DCF0E2", "#2E7D4F", "#1B5E34"
WARN_BG, WARN_BR, WARN_INK = "#FBF0D5", "#B7791F", "#8A5A0B"
ERR_BG, ERR_BR, ERR_INK    = "#FBE7E5", "#C0392B", "#96271B"
INFO_BG, INFO_BR, INFO_INK = "#E4EEF9", "#2F6FA8", "#1B4F8A"

FONT = ('"Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, '
        'sans-serif')

TONE = {
    "ok":      (OK_BG, OK_INK, OK_BR),
    "warn":    (WARN_BG, WARN_INK, WARN_BR),
    "err":     (ERR_BG, ERR_INK, ERR_BR),
    "info":    (INFO_BG, INFO_INK, INFO_BR),
    "accent":  ("#E2F0E7", ACCENT_D, ACCENT),
    "navy":    ("#E3E9F3", INK, INK),
    "neutral": ("#EFF2F0", INK2, INK3),
}

ICON = {"ok": "✓", "warn": "⚠", "err": "⚠", "info": "ℹ"}


# ---------------------------------------------------------------- css

def inject():
    st.markdown("""<style>
:root {
  --bg:%(BG)s; --sb:%(SIDEBAR)s; --sf:%(SURFACE)s;
  --ink:%(INK)s; --ink2:%(INK2)s; --ink3:%(INK3)s;
  --rule:%(RULE)s; --accent:%(ACCENT)s; --accentd:%(ACCENT_D)s;
}
html, body, [data-testid="stAppViewContainer"] { background:var(--bg); }
[data-testid="stAppViewContainer"], [data-testid="stSidebar"] { font-family:%(FONT)s; }
[data-testid="stAppViewContainer"] p, [data-testid="stAppViewContainer"] h1,
[data-testid="stAppViewContainer"] h2, [data-testid="stAppViewContainer"] h3,
[data-testid="stAppViewContainer"] h4, [data-testid="stAppViewContainer"] label,
[data-testid="stAppViewContainer"] button, [data-testid="stAppViewContainer"] input,
[data-testid="stAppViewContainer"] td, [data-testid="stAppViewContainer"] th
  { font-family:inherit; }
[data-testid="stHeader"] { background:transparent; }
.block-container { padding-top:1.1rem; padding-bottom:3rem; max-width:1550px; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
  min-width:25rem; max-width:25rem; background:var(--sb);
  border-right:1px solid var(--rule);
}
[data-testid="stSidebar"] .block-container { padding-top:1.2rem; }
[data-testid="stSidebar"] h3 {
  font-size:15px; font-weight:700; color:var(--ink);
  margin:18px 0 6px; padding-bottom:5px; border-bottom:1px solid var(--rule);
}
[data-testid="stSidebar"] label p { font-size:12.5px; color:var(--ink2); }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
  font-size:12px; color:var(--ink2);
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
  border:1px solid var(--rule); border-radius:8px; background:rgba(255,255,255,.55);
}

/* inputs sit on white so they read against the green */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] [data-baseweb="select"] > div { background:var(--sf); }

/* ---------- header band ---------- */
.hdr {
  background:linear-gradient(103deg,#DCEBD7 0%%,#E9F3E6 46%%,#F4F9F2 100%%);
  border:1px solid var(--rule); border-radius:12px;
  padding:16px 22px; margin:0 0 16px; position:relative; overflow:hidden;
}
.hdr:after {
  content:""; position:absolute; right:-40px; top:-60px; width:260px; height:260px;
  border-radius:50%%; background:rgba(46,125,79,.07);
}
.hdr .ttl {
  margin:0; font-size:28px; line-height:1.15; letter-spacing:-.015em;
  color:var(--ink); font-weight:800;
}
.hdr .ttl i {
  font-style:normal; font-weight:500; color:var(--ink2); font-size:19px;
  margin-left:12px; padding-left:13px; border-left:2px solid rgba(46,125,79,.4);
}
.hdr .sub { margin:8px 0 0; font-size:12.5px; color:var(--ink2); max-width:112ch; line-height:1.5; }

/* ---------- kpi cards ---------- */
.kpis { display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin:0 0 18px; }
.kpi {
  background:var(--sf); border:1px solid var(--rule); border-radius:11px;
  padding:13px 15px; min-width:0;
}
.kpi .lb {
  font-size:11.5px; font-weight:600; color:var(--ink2);
  display:flex; align-items:center; gap:7px; margin-bottom:5px;
}
.kpi .ic { font-size:14px; opacity:.85; }
.kpi .vl {
  font-size:26px; font-weight:800; color:var(--ink); line-height:1.15;
  white-space:nowrap; overflow:visible;
}
.kpi .dl {
  display:inline-block; margin-top:7px; font-size:11px; font-weight:600;
  padding:2px 8px; border-radius:20px;
}

/* ---------- section headings ---------- */
.sec {
  font-size:16.5px; font-weight:700; color:var(--ink);
  margin:22px 0 9px; display:flex; align-items:center; gap:9px;
}
.sec:before {
  content:""; width:3px; height:15px; border-radius:2px; background:var(--accent);
}
.note { font-size:12.5px; color:var(--ink2); margin:8px 0 0; }

/* ---------- tables ---------- */
.tw { background:var(--sf); border:1px solid var(--rule); border-radius:10px;
      overflow-x:auto; margin:0 0 6px; }
.tw::-webkit-scrollbar { height:8px; }
.tw::-webkit-scrollbar-thumb { background:var(--rule); border-radius:4px; }
table.rk { border-collapse:collapse; width:100%%; font-size:13px; }
table.rk th {
  background:#F2F7F1; color:var(--ink2); font-size:10.5px; font-weight:700;
  letter-spacing:.04em; text-transform:uppercase; text-align:left;
  padding:9px 12px; border-bottom:1px solid var(--rule); white-space:nowrap;
}
table.rk td {
  padding:9px 12px; border-bottom:1px solid #EDF2EC; color:var(--ink);
  vertical-align:middle; white-space:nowrap;
}
table.rk td.wrap { white-space:normal; min-width:200px; }
table.rk tr:last-child td { border-bottom:none; }
table.rk tr:hover td { background:#F7FBF6; }
table.rk td.r, table.rk th.r { text-align:right; font-variant-numeric:tabular-nums; }
table.rk td.c, table.rk th.c { text-align:center; }
table.rk tr.tot td { font-weight:700; background:#F2F7F1; border-top:1px solid var(--rule); }
.pill {
  display:inline-block; padding:2px 9px; border-radius:20px; font-size:11px;
  font-weight:700; letter-spacing:.02em; white-space:nowrap;
}

/* ---------- banners ---------- */
.bn { border-radius:9px; padding:12px 15px; margin:12px 0; font-size:13.5px;
      border-left:4px solid; }
.bn b.t { display:block; margin-bottom:3px; font-size:14px; }
.bn p { margin:0 0 5px; }
.bn ul { margin:6px 0 0; padding-left:20px; }
.bn li { margin-bottom:4px; }

/* ---------- tabs ---------- */
[role="tablist"] {
  gap:4px !important; background:var(--sf); border:1px solid var(--rule);
  border-radius:10px; padding:5px; margin-bottom:16px;
}
[data-testid="stTab"], [role="tab"] {
  height:34px; padding:0 16px !important; border-radius:7px; font-size:13.5px;
  font-weight:600; color:var(--ink2);
}
[data-testid="stTab"] p, [role="tab"] p { font-size:13.5px; font-weight:600; }
[role="tab"][aria-selected="true"] { background:var(--accent); }
[role="tab"][aria-selected="true"], [role="tab"][aria-selected="true"] p { color:#fff !important; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display:none !important; }

/* ---------- misc ---------- */
[data-testid="stVegaLiteChart"], .stVegaLiteChart {
  background:var(--sf); border:1px solid var(--rule); border-radius:10px; padding:10px;
}
.stDownloadButton button, .stButton button {
  background:var(--accent); color:#fff; border:none; border-radius:8px;
  font-weight:600; font-size:13px;
}
.stDownloadButton button:hover, .stButton button:hover { background:var(--accentd); color:#fff; }
hr { border-color:var(--rule); }
.foot { font-size:11.5px; color:var(--ink3); margin-top:26px; padding-top:12px;
        border-top:1px solid var(--rule); }
</style>""" % dict(BG=BG, SIDEBAR=SIDEBAR, SURFACE=SURFACE, INK=INK, INK2=INK2,
                   INK3=INK3, RULE=RULE, ACCENT=ACCENT, ACCENT_D=ACCENT_D,
                   FONT=FONT), unsafe_allow_html=True)


# ---------------------------------------------------------------- builders

def header(title, tail, subtitle):
    st.markdown(
        '<div class="hdr"><div class="ttl">%s<i>%s</i></div>'
        '<div class="sub">%s</div></div>'
        % (html.escape(title), html.escape(tail), html.escape(subtitle)),
        unsafe_allow_html=True)


def kpi_row(items):
    """items: list of dicts with label, value, and optional icon, delta, tone."""
    cells = []
    for it in items:
        d = ""
        if it.get("delta"):
            bg, ink, _ = TONE[it.get("tone", "neutral")]
            d = ('<div class="dl" style="background:%s;color:%s">%s</div>'
                 % (bg, ink, html.escape(it["delta"])))
        cells.append(
            '<div class="kpi"><div class="lb"><span class="ic">%s</span>%s</div>'
            '<div class="vl">%s</div>%s</div>'
            % (it.get("icon", ""), html.escape(it["label"]),
               html.escape(str(it["value"])), d))
    st.markdown('<div class="kpis">%s</div>' % "".join(cells),
                unsafe_allow_html=True)


def section(text):
    st.markdown('<div class="sec">%s</div>' % html.escape(text),
                unsafe_allow_html=True)


def note(text_html):
    st.markdown('<p class="note">%s</p>' % text_html, unsafe_allow_html=True)


def pill(text, tone="neutral"):
    bg, ink, _ = TONE[tone]
    return ('<span class="pill" style="background:%s;color:%s">%s</span>'
            % (bg, ink, html.escape(str(text))))


def table(df, right=(), centre=(), wrap=(), pills=None, total_row=False):
    """
    df       pandas DataFrame
    right    column names to right-align
    centre   column names to centre
    pills    {column: {cell value: tone}} - matched values render as pills
    total_row  style the final row as a total
    """
    pills = pills or {}
    cols = list(df.columns)

    def cls(c):
        k = []
        if c in right:
            k.append("r")
        if c in centre:
            k.append("c")
        if c in wrap:
            k.append("wrap")
        return (' class="%s"' % " ".join(k)) if k else ""

    head = "".join("<th%s>%s</th>" % (cls(c), html.escape(str(c))) for c in cols)
    body = []
    n = len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        tr = ' class="tot"' if (total_row and i == n - 1) else ""
        tds = []
        for c in cols:
            v = row[c]
            v = "" if v is None else v
            if c in pills and str(v) in pills[c]:
                cell = pill(v, pills[c][str(v)])
            else:
                cell = html.escape(str(v))
            tds.append("<td%s>%s</td>" % (cls(c), cell))
        body.append("<tr%s>%s</tr>" % (tr, "".join(tds)))
    st.markdown(
        '<div class="tw"><table class="rk"><thead><tr>%s</tr></thead>'
        '<tbody>%s</tbody></table></div>' % (head, "".join(body)),
        unsafe_allow_html=True)


def banner(kind, title=None, body_html="", bullets=None):
    bg, ink, br = TONE[kind]
    parts = []
    if title:
        parts.append('<b class="t">%s %s</b>' % (ICON.get(kind, ""), html.escape(title)))
    if body_html:
        parts.append("<p>%s</p>" % body_html)
    if bullets:
        parts.append("<ul>%s</ul>" % "".join("<li>%s</li>" % b for b in bullets))
    st.markdown('<div class="bn" style="background:%s;color:%s;border-left-color:%s">%s</div>'
                % (bg, ink, br, "".join(parts)), unsafe_allow_html=True)


def footer(text):
    st.markdown('<div class="foot">%s</div>' % text, unsafe_allow_html=True)


# ---------------------------------------------------------------- charts

def style(chart, height=None):
    """Apply the house look to an Altair chart."""
    c = chart.configure_view(strokeWidth=0).configure_axis(
        labelFont=FONT, titleFont=FONT, labelColor=INK2, titleColor=INK2,
        labelFontSize=11, titleFontSize=11, gridColor="#E8EFE7",
        domainColor=RULE, tickColor=RULE
    ).configure_legend(
        labelFont=FONT, titleFont=FONT, labelColor=INK2, titleColor=INK2,
        labelFontSize=11, titleFontSize=11
    ).configure_title(font=FONT, color=INK, fontSize=13)
    return c.properties(height=height) if height else c
