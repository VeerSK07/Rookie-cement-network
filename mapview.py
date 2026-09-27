"""
The network map.

Draws the solved network on an outline of India: which belts are open, which
grinding units are open, every market, and the cement and clinker lanes that
connect them.

The outline is Natural Earth 110m admin-0 (public domain, CC0), trimmed to
India and rounded to three decimal places. It is a schematic backdrop, not a
survey map. Coordinates for the sites come from model.COORD and are used for
drawing only - every distance in the optimisation comes from the brief's own
matrix, never from these positions.
"""

import json
import os

import altair as alt
import pandas as pd

import model as M
import ui

INDIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "india.json")

PLANT_C = "#2E7D4F"    # integrated plants, green
GRIND_C = "#2F6FA8"    # split grinding units, blue
MKT_C = "#C1652B"      # markets, warm orange
CEMENT_C = "#44566E"   # cement lanes
CLINKER_C = "#2F6FA8"  # clinker lanes


def _outline():
    with open(INDIA, encoding="utf-8") as fh:
        gj = json.load(fh)
    return alt.Data(values=gj, format=alt.DataFormat(property="features", type="json"))


def build(sol, open_only=True, show_cement=True, show_clinker=True):
    """Return an Altair chart of the solved network, or None if nothing to draw."""
    if not sol.get("ok"):
        return None

    base = alt.Chart(_outline()).mark_geoshape(
        fill="#E8F1E6", stroke="#B9CDB5", strokeWidth=0.8
    ).project(type="mercator")

    # ---- nodes
    nodes = []
    for i in M.INTEGRATED:
        opened = i in sol["plants"]
        if open_only and not opened:
            continue
        lat, lon = M.COORD[i]
        nodes.append(dict(
            code=i, lat=lat, lon=lon, kind="Integrated plant",
            name=M.PLANT_NAME[i],
            detail=("module %s  ·  clinker %.2f Mt  ·  ground %.2f Mt"
                    % (sol["plants"][i], sol["clinker_made"].get(i, 0),
                       sol["ground"].get(i, 0))) if opened else "not opened",
            size=420 if opened else 120, opened=opened))
    for g in M.GRINDING:
        opened = g in sol["grinders"]
        if open_only and not opened:
            continue
        lat, lon = M.COORD[g]
        nodes.append(dict(
            code=g, lat=lat, lon=lon, kind="Grinding unit",
            name=M.GRINDER_NAME[g],
            detail=("module %s  ·  ground %.2f Mt"
                    % (sol["grinders"][g], sol["ground"].get(g, 0))) if opened else "not opened",
            size=300 if opened else 110, opened=opened))
    for m in M.MARKETS:
        lat, lon = M.COORD[m]
        served = (sum(v for (i, mm), v in sol["xc"].items() if mm == m)
                  + sum(v for (gg, mm), v in sol["xg"].items() if mm == m))
        nodes.append(dict(code=m, lat=lat, lon=lon, kind="Market",
                          name=M.MARKET_NAME[m],
                          detail="%s  ·  %.3f Mt" % (M.MARKET_CITY[m], served),
                          size=95, opened=True))
    ndf = pd.DataFrame(nodes)

    # ---- lanes, two rows per lane so mark_line can join them
    lanes = []
    lid = 0
    if show_cement:
        for (i, m), v in sol["xc"].items():
            lid += 1
            for end in (i, m):
                lanes.append(dict(lid=lid, code=end, lat=M.COORD[end][0],
                                  lon=M.COORD[end][1], kind="Cement", vol=v,
                                  label="%s → %s  %.3f Mt" % (i, m, v)))
        for (g, m), v in sol["xg"].items():
            lid += 1
            for end in (g, m):
                lanes.append(dict(lid=lid, code=end, lat=M.COORD[end][0],
                                  lon=M.COORD[end][1], kind="Cement", vol=v,
                                  label="%s → %s  %.3f Mt" % (g, m, v)))
    if show_clinker:
        for (i, g), v in sol["w"].items():
            lid += 1
            for end in (i, g):
                lanes.append(dict(lid=lid, code=end, lat=M.COORD[end][0],
                                  lon=M.COORD[end][1], kind="Clinker", vol=v,
                                  label="%s → %s  %.3f Mt clinker" % (i, g, v)))
    ldf = pd.DataFrame(lanes)

    layers = [base]

    if len(ldf):
        cem = ldf[ldf["kind"] == "Cement"]
        cli = ldf[ldf["kind"] == "Clinker"]
        if len(cli):
            layers.append(alt.Chart(cli).mark_line(
                color=CLINKER_C, strokeDash=[6, 4], opacity=0.85
            ).encode(
                longitude="lon:Q", latitude="lat:Q", detail="lid:N",
                strokeWidth=alt.StrokeWidth(
                    "vol:Q", title="Mt a year",
                    scale=alt.Scale(range=[1, 6]),
                    legend=alt.Legend(orient="bottom-left")),
                tooltip=[alt.Tooltip("label:N", title="Clinker lane")]))
        if len(cem):
            layers.append(alt.Chart(cem).mark_line(
                color=CEMENT_C, opacity=0.55
            ).encode(
                longitude="lon:Q", latitude="lat:Q", detail="lid:N",
                strokeWidth=alt.StrokeWidth("vol:Q", legend=None,
                                            scale=alt.Scale(range=[0.8, 5])),
                tooltip=[alt.Tooltip("label:N", title="Cement lane")]))

    shape_scale = alt.Scale(
        domain=["Integrated plant", "Grinding unit", "Market"],
        range=["triangle-up", "square", "circle"])
    colour_scale = alt.Scale(
        domain=["Integrated plant", "Grinding unit", "Market"],
        range=[PLANT_C, GRIND_C, MKT_C])

    layers.append(alt.Chart(ndf).mark_point(filled=True, stroke="white",
                                            strokeWidth=1.4).encode(
        longitude="lon:Q", latitude="lat:Q",
        shape=alt.Shape("kind:N", scale=shape_scale, legend=None),
        color=alt.Color("kind:N", scale=colour_scale, legend=None),
        size=alt.Size("size:Q", scale=None),
        tooltip=[alt.Tooltip("code:N", title="Code"),
                 alt.Tooltip("name:N", title="Location"),
                 alt.Tooltip("kind:N", title="Type"),
                 alt.Tooltip("detail:N", title="Detail")]))

    sites = ndf[ndf["kind"] != "Market"]
    if len(sites):
        layers.append(alt.Chart(sites).mark_text(
            align="left", dx=11, dy=-9, fontSize=10.5, fontWeight=600,
            color=ui.INK
        ).encode(longitude="lon:Q", latitude="lat:Q", text="code:N"))
    mk = ndf[ndf["kind"] == "Market"]
    layers.append(alt.Chart(mk).mark_text(
        align="left", dx=8, dy=8, fontSize=9.5, color=ui.INK2
    ).encode(longitude="lon:Q", latitude="lat:Q", text="code:N"))

    return alt.layer(*layers).properties(height=560).configure_view(
        strokeWidth=0, fill="#FFFFFF"
    ).configure_legend(
        labelFont=ui.FONT, titleFont=ui.FONT, labelColor=ui.INK2,
        titleColor=ui.INK2, labelFontSize=11, titleFontSize=11,
        symbolStrokeWidth=1.2)


LEGEND_ITEMS = [
    ("Integrated plant", PLANT_C, "triangle"),
    ("Grinding unit", GRIND_C, "square"),
    ("Market cluster", MKT_C, "circle"),
]


def legend_html():
    """A small styled legend, rendered above the map."""
    marks = []
    for label, colour, shape in LEGEND_ITEMS:
        if shape == "triangle":
            glyph = ('<span style="display:inline-block;width:0;height:0;'
                     'border-left:6px solid transparent;border-right:6px solid transparent;'
                     'border-bottom:11px solid %s;margin-right:7px"></span>' % colour)
        elif shape == "square":
            glyph = ('<span style="display:inline-block;width:10px;height:10px;'
                     'background:%s;margin-right:7px"></span>' % colour)
        else:
            glyph = ('<span style="display:inline-block;width:10px;height:10px;'
                     'border-radius:50%%;background:%s;margin-right:7px"></span>' % colour)
        marks.append('<span style="display:inline-flex;align-items:center;'
                     'margin-right:20px">%s%s</span>' % (glyph, label))
    marks.append('<span style="display:inline-flex;align-items:center;margin-right:20px">'
                 '<span style="display:inline-block;width:24px;height:0;'
                 'border-top:3px solid %s;opacity:.55;margin-right:7px"></span>'
                 'Cement lane</span>' % CEMENT_C)
    marks.append('<span style="display:inline-flex;align-items:center">'
                 '<span style="display:inline-block;width:24px;height:0;'
                 'border-top:3px dashed %s;margin-right:7px"></span>'
                 'Clinker lane</span>' % CLINKER_C)
    return ('<div style="font-size:12.5px;color:%s;margin:4px 0 10px">%s</div>'
            % (ui.INK2, "".join(marks)))
