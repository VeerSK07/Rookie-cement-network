"""
The Rookie - India cement network design, FY2030
Interactive scenario tool.

Every number on screen comes from re-solving the mixed integer programme in
model.py. Nothing is pre-computed or hard-coded, except the four proven optima
kept in model.PROVEN, which the app uses to check itself.
"""

import json
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

import model as M

# one hue, because every chart here encodes magnitude of a single measure
HUE = "#2B6CB0"
INK = "#1A1D23"
MUTED = "#6B7280"

st.set_page_config(page_title="The Rookie - Cement Network Design",
                   layout="wide", initial_sidebar_state="expanded")

# The sidebar holds two editable tables. The default width squeezes the
# editable column off the right edge, so widen it.
st.markdown("""<style>
[data-testid="stSidebar"] { min-width: 25rem; max-width: 25rem; }
</style>""", unsafe_allow_html=True)

MOD_CHOICES = ["Closed", "S", "M", "L"]


# ---------------------------------------------------------------- solving

@st.cache_data(show_spinner=False, max_entries=200)
def run(demand, cement_rate, clinker_rate, clinker_factor, limestone_per_clinker,
        utilisation_cap, cement_max_km, clinker_max_km, limestone_price,
        wacc, life_years, unavailable, fixed_network):
    """Hashable wrapper around model.solve so Streamlit can cache it."""
    fn = None
    if fixed_network is not None:
        fn = (dict(fixed_network[0]), dict(fixed_network[1]))
    return M.solve(demand=list(demand), cement_rate=cement_rate,
                   clinker_rate=clinker_rate, clinker_factor=clinker_factor,
                   limestone_per_clinker=limestone_per_clinker,
                   utilisation_cap=utilisation_cap,
                   cement_max_km=cement_max_km, clinker_max_km=clinker_max_km,
                   limestone_price=dict(limestone_price), wacc=wacc,
                   life_years=life_years, unavailable=tuple(unavailable),
                   fixed_network=fn)


def rs_per_tonne(crore, mt):
    """Rs crore over Mt -> Rs per tonne."""
    return 10.0 * crore / mt if mt else 0.0


# ---------------------------------------------------------------- sidebar

st.sidebar.markdown("### Scenario")
preset = st.sidebar.selectbox(
    "Start from",
    ["Base", "A", "B", "C"],
    format_func=lambda k: M.SCENARIOS[k]["label"],
    help="Pick a case scenario as the starting point, then change anything below.")
st.sidebar.caption(M.SCENARIOS[preset]["note"])

pk = M.SCENARIOS[preset]["kwargs"]


def key(name):
    """Widget keys carry the preset, so switching preset resets the inputs."""
    return "%s__%s" % (name, preset)


# ---- demand
st.sidebar.markdown("### Market demand")
d0 = pk.get("demand", M.DEMAND_BASE)
scale = st.sidebar.slider(
    "Scale every market", 0.50, 1.50, 1.00, 0.01, key=key("scale"),
    help="Multiply all twelve markets at once. 1.00 is the scenario as given.")
with st.sidebar.expander("Edit individual markets", expanded=False):
    _vals = []
    for _j in range(0, 12, 2):
        _cc = st.columns(2)
        for _k in (0, 1):
            _m = M.MARKETS[_j + _k]
            _vals.append(_cc[_k].number_input(
                "%s %s" % (_m, M.MARKET_CITY[_m]),
                min_value=0.0, max_value=20.0, value=float(d0[_j + _k]),
                step=0.005, format="%.3f", key=key("d_" + _m)))
demand = tuple(round(v * scale, 6) for v in _vals)
st.sidebar.caption("Total demand **%.2f Mt** (case base is %.2f Mt)"
                   % (sum(demand), sum(M.DEMAND_BASE)))

# ---- freight and money
st.sidebar.markdown("### Freight and money")
c1, c2 = st.sidebar.columns(2)
cement_rate = c1.number_input("Cement road, Rs/t-km", 0.5, 12.0,
                              float(pk.get("cement_rate", M.DEF["cement_rate"])),
                              0.01, key=key("cfr"))
clinker_rate = c2.number_input("Clinker rail, Rs/t-km", 0.2, 8.0,
                               float(pk.get("clinker_rate", M.DEF["clinker_rate"])),
                               0.01, key=key("clfr"))
c3, c4 = st.sidebar.columns(2)
wacc = c3.number_input("WACC", 0.02, 0.30, M.DEF["wacc"], 0.005,
                       format="%.3f", key=key("wacc"))
life = c4.number_input("Asset life, years", 5, 40, M.DEF["life_years"], 1,
                       key=key("life"))
st.sidebar.caption("Capital recovery factor **%.4f** - each Rs 100 crore of capex "
                   "carries Rs %.2f crore a year." % (M.crf(wacc, life),
                                                      100 * M.crf(wacc, life)))

with st.sidebar.expander("Limestone price by belt"):
    _lsv = []
    for _j in range(0, 6, 2):
        _cc = st.columns(2)
        for _k in (0, 1):
            _i = M.INTEGRATED[_j + _k]
            _short = M.PLANT_NAME[_i].split("-")[0].split(" (")[0]
            _lsv.append(_cc[_k].number_input(
                "%s %s" % (_i, _short),
                min_value=50.0, max_value=600.0,
                value=float(M.LIMESTONE_PRICE[_i]), step=1.0, format="%.0f",
                key=key("ls_" + _i)))
limestone_price = tuple(zip(M.INTEGRATED, _lsv))

# ---- technical constraints
st.sidebar.markdown("### Constraints")
c5, c6 = st.sidebar.columns(2)
cement_max = c5.number_input("Max cement lane, km", 100, 3000,
                             M.DEF["cement_max_km"], 50, key=key("cemlim"))
clinker_max = c6.number_input("Max clinker lane, km", 100, 3000,
                              M.DEF["clinker_max_km"], 50, key=key("cllim"))
c7, c8 = st.sidebar.columns(2)
util = c7.number_input("Utilisation cap", 0.50, 1.00, M.DEF["utilisation_cap"],
                       0.01, format="%.2f", key=key("util"))
cf = c8.number_input("Clinker factor", 0.40, 1.00, M.DEF["clinker_factor"],
                     0.01, format="%.2f", key=key("cf"))
lsq = st.sidebar.number_input("Limestone per tonne of clinker", 1.0, 2.5,
                              M.DEF["limestone_per_clinker"], 0.05,
                              format="%.2f", key=key("lsq"))

# ---- availability
st.sidebar.markdown("### Site availability")
unavailable = st.sidebar.multiselect(
    "Integrated belts that cannot be built",
    M.INTEGRATED, default=list(pk.get("unavailable", ())),
    format_func=lambda i: "%s - %s" % (i, M.PLANT_NAME[i]), key=key("ban"))

# ---- network mode
st.sidebar.markdown("### Network")
mode = st.sidebar.radio("How is the network decided?",
                        ["Let the model choose", "I specify the network"],
                        key=key("mode"))
fixed_network = None
if mode == "I specify the network":
    start = st.sidebar.selectbox("Pre-fill with",
                                 ["Base optimum", "Robust design", "Nothing open"],
                                 key=key("start"))
    src = {"Base optimum": M.BASE_NETWORK, "Robust design": M.ROBUST_NETWORK,
           "Nothing open": ({}, {})}[start]
    st.sidebar.caption("Set a module size for each site. The model then optimises "
                       "only the flows.")
    pl, gl = {}, {}
    for i in M.INTEGRATED:
        dflt = src[0].get(i, "Closed")
        v = st.sidebar.selectbox("%s - %s" % (i, M.PLANT_NAME[i]), MOD_CHOICES,
                                 index=MOD_CHOICES.index(dflt),
                                 key=key("pm_" + i))
        if v != "Closed":
            pl[i] = v
    for g in M.GRINDING:
        dflt = src[1].get(g, "Closed")
        v = st.sidebar.selectbox("%s - %s" % (g, M.GRINDER_NAME[g]), MOD_CHOICES,
                                 index=MOD_CHOICES.index(dflt),
                                 key=key("gm_" + g))
        if v != "Closed":
            gl[g] = v
    fixed_network = (tuple(sorted(pl.items())), tuple(sorted(gl.items())))

st.sidebar.divider()
st.sidebar.caption("Module sizes - integrated: S 3.0/2.5 Mt, M 4.5/3.5 Mt, "
                   "L 6.0/5.0 Mt clinker/grinding. Grinding only: S 2.5, M 4.0, "
                   "L 6.0 Mt.")


# ---------------------------------------------------------------- solve

with st.spinner("Solving the mixed integer programme..."):
    sol = run(demand, cement_rate, clinker_rate, cf, lsq, util,
              int(cement_max), int(clinker_max), limestone_price,
              wacc, int(life), tuple(unavailable), fixed_network)
    base = run(tuple(M.DEMAND_BASE), M.DEF["cement_rate"], M.DEF["clinker_rate"],
               M.DEF["clinker_factor"], M.DEF["limestone_per_clinker"],
               M.DEF["utilisation_cap"], M.DEF["cement_max_km"],
               M.DEF["clinker_max_km"],
               tuple(M.LIMESTONE_PRICE.items()), M.DEF["wacc"],
               M.DEF["life_years"], (), None)


# ---------------------------------------------------------------- header

st.title("The Rookie - India cement network design, FY2030")
st.caption("Group 7 - Supply Chain Planning and Coordination. Change any input on "
           "the left and the network is re-optimised from scratch. "
           "%d decision variables, %d constraints, solved with HiGHS to a zero "
           "integer optimality gap." % (sol["n_vars"], sol["n_cons"]))

total_demand = sum(demand)

if not sol["ok"]:
    st.error("**No feasible network exists under these inputs.** "
             "This is not an expensive answer - it is the absence of one.")
    dg = sol["diagnosis"]
    st.markdown("**Why**, %s:" % dg["note"])
    for line in dg["reasons"]:
        st.markdown("- " + line)
    st.info("The point worth making to a board: a cost problem can be paid for. "
            "An infeasible design cannot. Relax the distance limit, lift the "
            "utilisation cap, or open another belt on the left and watch which "
            "one actually rescues it.")
    st.stop()

k1, k2, k3, k4, k5 = st.columns(5)
if base["ok"]:
    gap_pct = 100 * (sol["total"] / base["total"] - 1)
    if abs(gap_pct) < 0.05:
        d_txt, d_col = "at the base optimum", "off"
    else:
        d_txt, d_col = "%+.1f%% vs base optimum" % gap_pct, "inverse"
else:
    d_txt, d_col = None, "normal"
k1.metric("Annual relevant cost", "Rs %s cr" % format(round(sol["total"]), ","),
          delta=d_txt, delta_color=d_col)
k2.metric("Cost per tonne", "Rs %s" % format(round(rs_per_tonne(sol["total"], total_demand)), ","))
k3.metric("Integrated plants", "%d of %d" % (len(sol["plants"]), len(M.INTEGRATED)))
k4.metric("Grinding units", "%d of %d" % (len(sol["grinders"]), len(M.GRINDING)))
k5.metric("Avg cement lead", "%d km" % round(sol["cement_lead"]),
          delta="clinker %s" % ("%d km" % round(sol["clinker_lead"])
                                if sol["clinker_lead"] else "none"),
          delta_color="off")

tabs = st.tabs(["Network", "Cost", "Flows", "Checks", "Compare", "Method"])


# ---------------------------------------------------------------- network

with tabs[0]:
    rows = []
    for i, k in sorted(sol["plants"].items()):
        cl_cap, gr_cap = M.IMOD[k][0], M.IMOD[k][1]
        cl_use = sol["clinker_made"].get(i, 0.0)
        gr_use = sol["ground"].get(i, 0.0)
        rows.append({
            "Site": i, "Location": M.PLANT_NAME[i], "Module": k,
            "Clinker made (Mt)": cl_use, "Clinker nameplate (Mt)": cl_cap,
            "Clinker use %": 100 * cl_use / cl_cap,
            "Cement ground (Mt)": gr_use, "Grinding nameplate (Mt)": gr_cap,
            "Grinding use %": 100 * gr_use / gr_cap,
            "At the cap": "yes" if max(cl_use / cl_cap, gr_use / gr_cap) >= util - 1e-6 else "",
        })
    st.markdown("#### Integrated plants")
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                 column_config={c: st.column_config.NumberColumn(format="%.2f")
                                for c in ["Clinker made (Mt)", "Clinker nameplate (Mt)",
                                          "Cement ground (Mt)", "Grinding nameplate (Mt)"]}
                 | {c: st.column_config.NumberColumn(format="%.0f%%")
                    for c in ["Clinker use %", "Grinding use %"]})

    grows = []
    for g, k in sorted(sol["grinders"].items()):
        cap = M.GMOD[k][0]
        use = sol["ground"].get(g, 0.0)
        grows.append({"Site": g, "Location": M.GRINDER_NAME[g], "Module": k,
                      "Cement ground (Mt)": use, "Nameplate (Mt)": cap,
                      "Use %": 100 * use / cap,
                      "At the cap": "yes" if use / cap >= util - 1e-6 else ""})
    st.markdown("#### Split grinding units")
    st.dataframe(pd.DataFrame(grows), hide_index=True, use_container_width=True,
                 column_config={"Cement ground (Mt)": st.column_config.NumberColumn(format="%.2f"),
                                "Nameplate (Mt)": st.column_config.NumberColumn(format="%.2f"),
                                "Use %": st.column_config.NumberColumn(format="%.0f%%")})

    st.markdown("#### Capacity utilisation against the %d%% ceiling" % round(100 * util))
    ub = []
    for r in rows:
        ub.append({"Site": "%s clinker" % r["Site"], "Use": r["Clinker use %"]})
        ub.append({"Site": "%s grinding" % r["Site"], "Use": r["Grinding use %"]})
    for r in grows:
        ub.append({"Site": "%s grinding" % r["Site"], "Use": r["Use %"]})
    ubdf = pd.DataFrame(ub)
    bars = alt.Chart(ubdf).mark_bar(size=14, cornerRadiusEnd=4, color=HUE).encode(
        x=alt.X("Use:Q", title="per cent of nameplate",
                scale=alt.Scale(domain=[0, 100])),
        y=alt.Y("Site:N", sort=None, title=None),
        tooltip=[alt.Tooltip("Site:N"), alt.Tooltip("Use:Q", format=".1f", title="use %")])
    cap_rule = alt.Chart(pd.DataFrame({"x": [100 * util]})).mark_rule(
        strokeDash=[5, 4], color=MUTED).encode(x="x:Q")
    st.altair_chart((bars + cap_rule).properties(height=26 * len(ubdf) + 30),
                    use_container_width=True)
    st.caption("Dashed line is the %d%% ceiling. A cluster of bars sitting exactly "
               "on it means the plan is tight but feasible - and that any demand "
               "surprise has nowhere to go." % round(100 * util))

    closed = [i for i in M.INTEGRATED if i not in sol["plants"]]
    if closed:
        st.markdown("**Candidate belts not opened:** "
                    + ", ".join("%s (%s)" % (i, M.PLANT_NAME[i]) for i in closed)
                    + ("  -  unavailable by assumption: "
                       + ", ".join(unavailable) if unavailable else ""))


# ---------------------------------------------------------------- cost

with tabs[1]:
    comp = [("Annualised capex and fixed opex", sol["fixed"]),
            ("Finished cement freight", sol["cement_freight"]),
            ("Clinker freight", sol["clinker_freight"]),
            ("Limestone", sol["limestone"])]
    cdf = pd.DataFrame([{"Cost element": n,
                         "Rs crore a year": v,
                         "Share": 100 * v / sol["total"],
                         "Rs per tonne of cement": rs_per_tonne(v, total_demand)}
                        for n, v in comp])
    tot_row = pd.DataFrame([{"Cost element": "Total annual relevant cost",
                             "Rs crore a year": sol["total"], "Share": 100.0,
                             "Rs per tonne of cement": rs_per_tonne(sol["total"], total_demand)}])
    st.dataframe(pd.concat([cdf, tot_row], ignore_index=True), hide_index=True,
                 use_container_width=True,
                 column_config={
                     "Rs crore a year": st.column_config.NumberColumn(format="%.1f"),
                     "Share": st.column_config.NumberColumn(format="%.1f%%"),
                     "Rs per tonne of cement": st.column_config.NumberColumn(format="%.0f")})

    ch = alt.Chart(cdf).mark_bar(size=22, cornerRadiusEnd=4, color=HUE).encode(
        x=alt.X("Rs crore a year:Q", title="Rs crore a year"),
        y=alt.Y("Cost element:N", sort="-x", title=None),
        tooltip=[alt.Tooltip("Cost element:N"),
                 alt.Tooltip("Rs crore a year:Q", format=".1f"),
                 alt.Tooltip("Share:Q", format=".1f", title="share %")])
    st.altair_chart(ch.properties(height=190), use_container_width=True)

    fixed_share = 100 * sol["fixed"] / sol["total"]
    freight_share = 100 * (sol["cement_freight"] + sol["clinker_freight"]) / sol["total"]
    st.markdown(
        "Fixed cost is **%.1f%%** of the total and freight is **%.1f%%**, so the "
        "decision that matters most is how many plants to build and how big they "
        "are - not any single freight lane. Limestone is **%.1f%%**, which is why "
        "a cheaper belt only ever breaks a tie."
        % (fixed_share, freight_share, 100 * sol["limestone"] / sol["total"]))

    st.markdown("#### The split-grinding arithmetic, at your current rates")
    saving = cement_rate - cf * clinker_rate
    lg_cap, lg_capex, lg_opex = M.GMOD["L"]
    lg_annual = lg_capex * M.crf(wacc, life) + lg_opex
    lg_per_t = rs_per_tonne(lg_annual, util * lg_cap)
    st.markdown(
        "- One tonne of cement needs **%.2f t** of clinker. Moving that clinker "
        "costs **Rs %.2f** a km against **Rs %.2f** for the finished cement.\n"
        "- So every km you carry clinker instead of cement saves **Rs %.2f a tonne**.\n"
        "- A large grinding unit costs **Rs %.0f crore a year** and can grind "
        "**%.2f Mt** at the %d%% cap, which is **Rs %.0f a tonne**.\n"
        "- It therefore pays for itself once the market sits about **%.0f km** "
        "from the plant."
        % (cf, cf * clinker_rate, cement_rate, saving, lg_annual,
           util * lg_cap, round(100 * util), lg_per_t,
           lg_per_t / saving if saving > 0 else float("nan")))
    if saving <= 0:
        st.warning("At these rates it is no cheaper to move clinker than cement, "
                   "so split grinding has no distance argument at all.")


# ---------------------------------------------------------------- flows

with tabs[2]:
    st.markdown("#### Who serves each market")
    frows = []
    for j, m in enumerate(M.MARKETS):
        srcs = []
        for (i, mm), v in sorted(sol["xc"].items()):
            if mm == m:
                srcs.append("%s %.3f Mt @ %d km" % (i, v, M.DIST_PLANT_MARKET[i][j]))
        for (g, mm), v in sorted(sol["xg"].items()):
            if mm == m:
                srcs.append("%s %.3f Mt @ %d km" % (g, v, M.DIST_GRINDER_MARKET[g][j]))
        served = (sum(v for (i, mm), v in sol["xc"].items() if mm == m)
                  + sum(v for (g, mm), v in sol["xg"].items() if mm == m))
        frows.append({"Market": m, "Region": M.MARKET_NAME[m],
                      "Hub": M.MARKET_CITY[m], "Demand (Mt)": demand[j],
                      "Served (Mt)": served, "Sources": "  +  ".join(srcs)})
    st.dataframe(pd.DataFrame(frows), hide_index=True, use_container_width=True,
                 column_config={"Demand (Mt)": st.column_config.NumberColumn(format="%.3f"),
                                "Served (Mt)": st.column_config.NumberColumn(format="%.3f")})

    st.markdown("#### Clinker railed to grinding units")
    if sol["w"]:
        wrows = [{"From": i, "Plant": M.PLANT_NAME[i], "To": g,
                  "Grinding unit": M.GRINDER_NAME[g], "Clinker (Mt)": v,
                  "Rail km": M.DIST_PLANT_GRINDER[i][M.GRINDING.index(g)],
                  "Tonne-km (mn)": v * M.DIST_PLANT_GRINDER[i][M.GRINDING.index(g)]}
                 for (i, g), v in sorted(sol["w"].items())]
        st.dataframe(pd.DataFrame(wrows), hide_index=True, use_container_width=True,
                     column_config={"Clinker (Mt)": st.column_config.NumberColumn(format="%.3f"),
                                    "Tonne-km (mn)": st.column_config.NumberColumn(format="%.0f")})
    else:
        st.info("No clinker movement - no grinding unit is open.")

    payload = {"inputs": {"demand": list(demand), "cement_rate": cement_rate,
                          "clinker_rate": clinker_rate, "clinker_factor": cf,
                          "limestone_per_clinker": lsq, "utilisation_cap": util,
                          "cement_max_km": int(cement_max),
                          "clinker_max_km": int(clinker_max), "wacc": wacc,
                          "life_years": int(life),
                          "unavailable": list(unavailable),
                          "limestone_price": dict(limestone_price)},
               "solution": {k: sol[k] for k in
                            ["total", "fixed", "limestone", "cement_freight",
                             "clinker_freight", "plants", "grinders",
                             "cement_flows", "clinker_flows", "cement_lead",
                             "clinker_lead", "clinker_nameplate",
                             "grinding_nameplate", "crf"]}}
    st.download_button("Download this solution as JSON",
                       json.dumps(payload, indent=1),
                       file_name="rookie_solution.json", mime="application/json")


# ---------------------------------------------------------------- checks

with tabs[3]:
    st.markdown("#### Every constraint, re-derived from the answer")
    st.caption("These are not the solver's own status flags. Each row is "
               "recomputed from the returned flows, so a silent modelling error "
               "would show up here.")
    chk = pd.DataFrame([{"Check": n, "Result": v,
                         "Verdict": "PASS" if ok else "FAIL"}
                        for n, v, ok in sol["checks"]])
    st.dataframe(chk, hide_index=True, use_container_width=True)
    if all(ok for _, _, ok in sol["checks"]):
        st.success("All checks pass.")
    else:
        st.error("A check failed - do not quote these numbers.")

    st.markdown("#### Solver")
    st.markdown("- Status: **%s**\n- Decision variables: **%d**, constraints: "
                "**%d**\n- Integer optimality gap requested: **0.0**"
                % (sol["message"], sol["n_vars"], sol["n_cons"]))

    st.markdown("#### Against the proven optimum")
    matches = (tuple(demand) == tuple(M.SCENARIOS[preset]["kwargs"].get("demand", M.DEMAND_BASE))
               and cement_rate == M.SCENARIOS[preset]["kwargs"].get("cement_rate", M.DEF["cement_rate"])
               and clinker_rate == M.SCENARIOS[preset]["kwargs"].get("clinker_rate", M.DEF["clinker_rate"])
               and tuple(unavailable) == tuple(M.SCENARIOS[preset]["kwargs"].get("unavailable", ()))
               and fixed_network is None
               and cf == M.DEF["clinker_factor"] and util == M.DEF["utilisation_cap"]
               and int(cement_max) == M.DEF["cement_max_km"]
               and int(clinker_max) == M.DEF["clinker_max_km"]
               and wacc == M.DEF["wacc"] and int(life) == M.DEF["life_years"]
               and lsq == M.DEF["limestone_per_clinker"]
               and dict(limestone_price) == M.LIMESTONE_PRICE)
    if matches:
        p = M.PROVEN[preset]
        st.markdown("Inputs are the untouched **%s** scenario. This app computes "
                    "**Rs %.1f crore**; the independently verified optimum is "
                    "**Rs %.1f crore**. Difference **Rs %.2f crore**."
                    % (M.SCENARIOS[preset]["label"], sol["total"], p, sol["total"] - p))
        if abs(sol["total"] - p) < 0.5:
            st.success("The app reproduces the proven optimum.")
        else:
            st.warning("Divergence from the proven optimum - investigate before "
                       "quoting this run.")
    else:
        st.info("You have changed at least one input away from a case scenario, "
                "so there is no pre-verified answer to compare against. Reset the "
                "scenario on the left to see the self-check.")

    st.markdown("#### The tolerance warning")
    st.markdown("Several candidate networks sit within one per cent of each other "
                "on cost. The integer optimality tolerance here is **zero**. If "
                "you rebuild this in Excel Solver, set the integer tolerance to "
                "0.01% or tighter - the default 5% stops on a network that looks "
                "optimal and is not.")


# ---------------------------------------------------------------- compare

with tabs[4]:
    if "pinned" not in st.session_state:
        st.session_state.pinned = []
    c1, c2 = st.columns([1, 4])
    label = c2.text_input("Label for this run", value=M.SCENARIOS[preset]["label"],
                          label_visibility="collapsed")
    if c1.button("Pin this run", use_container_width=True):
        st.session_state.pinned.append({
            "Run": label,
            "Total (Rs cr)": round(sol["total"], 1),
            "Rs / tonne": round(rs_per_tonne(sol["total"], total_demand)),
            "Fixed (Rs cr)": round(sol["fixed"], 1),
            "Cement freight": round(sol["cement_freight"], 1),
            "Clinker freight": round(sol["clinker_freight"], 1),
            "Limestone": round(sol["limestone"], 1),
            "Plants": " ".join("%s%s" % (i, k) for i, k in sorted(sol["plants"].items())),
            "Grinders": " ".join("%s%s" % (g, k) for g, k in sorted(sol["grinders"].items())),
            "Cement lead km": round(sol["cement_lead"]),
            "Clinker lead km": round(sol["clinker_lead"]) if sol["clinker_lead"] else 0,
            "Demand (Mt)": round(total_demand, 2),
        })
    if st.session_state.pinned:
        st.dataframe(pd.DataFrame(st.session_state.pinned).set_index("Run").T,
                     use_container_width=True)
        if st.button("Clear pinned runs"):
            st.session_state.pinned = []
            st.rerun()
    else:
        st.info("Pin two or more runs to compare them side by side. A useful pair: "
                "the base optimum, then the same scenario with Chittorgarh switched "
                "off on the left.")

    st.markdown("#### Regret of a frozen network")
    st.caption("Freeze a design, re-run it under a scenario, and compare against "
               "the best possible answer in that scenario. That difference is the "
               "regret - the price of having committed early.")
    which = st.selectbox("Freeze which design?",
                         ["Base optimum", "Robust design"], key="regret_net")
    net = M.BASE_NETWORK if which == "Base optimum" else M.ROBUST_NETWORK
    net_t = (tuple(sorted(net[0].items())), tuple(sorted(net[1].items())))
    rrows = []
    for sk, sc in M.SCENARIOS.items():
        kw = sc["kwargs"]
        args = dict(demand=tuple(kw.get("demand", M.DEMAND_BASE)),
                    cement_rate=kw.get("cement_rate", M.DEF["cement_rate"]),
                    clinker_rate=kw.get("clinker_rate", M.DEF["clinker_rate"]),
                    clinker_factor=M.DEF["clinker_factor"],
                    limestone_per_clinker=M.DEF["limestone_per_clinker"],
                    utilisation_cap=M.DEF["utilisation_cap"],
                    cement_max_km=M.DEF["cement_max_km"],
                    clinker_max_km=M.DEF["clinker_max_km"],
                    limestone_price=tuple(M.LIMESTONE_PRICE.items()),
                    wacc=M.DEF["wacc"], life_years=M.DEF["life_years"],
                    unavailable=tuple(kw.get("unavailable", ())))
        free = run(fixed_network=None, **args)
        froz = run(fixed_network=net_t, **args)
        rrows.append({
            "Scenario": sc["label"],
            "Frozen design feasible": "yes" if froz["ok"] else "NO",
            "Cost of frozen design": round(froz["total"], 1) if froz["ok"] else None,
            "Best possible": round(free["total"], 1) if free["ok"] else None,
            "Regret (Rs cr)": round(froz["total"] - free["total"], 1)
            if (froz["ok"] and free["ok"]) else None,
            "Regret %": round(100 * (froz["total"] / free["total"] - 1), 2)
            if (froz["ok"] and free["ok"]) else None})
    st.dataframe(pd.DataFrame(rrows), hide_index=True, use_container_width=True)
    if any(r["Frozen design feasible"] == "NO" for r in rrows):
        st.warning("A **NO** in that table is the finding. Regret cannot be "
                   "measured against a design that does not work - the outcome is "
                   "inoperable, not merely costly.")


# ---------------------------------------------------------------- method

with tabs[5]:
    st.markdown("""
#### What the model decides

| Variable | Meaning | Type |
|---|---|---|
| `y[i,k]` | open integrated belt *i* at module size *k* | binary |
| `z[g,k]` | open split grinding unit *g* at module size *k* | binary |
| `xc[i,m]` | cement shipped from plant *i* to market *m* | continuous, Mt/yr |
| `xg[g,m]` | cement shipped from grinding unit *g* to market *m* | continuous, Mt/yr |
| `w[i,g]` | clinker railed from plant *i* to grinding unit *g* | continuous, Mt/yr |

#### Objective

Minimise annualised capex + fixed opex + limestone + cement freight + clinker
freight. Capex is annualised with a capital recovery factor, so a one-time
outflow and a recurring one are compared on the same basis.

#### Constraints

1. Every market receives exactly its target volume.
2. Cement ground at a plant cannot exceed the utilisation cap times its selected
   grinding nameplate.
3. Clinker made at a plant - for its own grinding plus what it rails out - cannot
   exceed the cap times its clinker nameplate.
4. Clinker arriving at a grinding unit equals the clinker factor times the cement
   it grinds.
5. A grinding unit cannot exceed the cap times its nameplate.
6. At most one module size per site.
7. Lane masks: no cement lane beyond the cement limit, no clinker lane beyond the
   clinker limit. These are imposed as variable bounds of zero, which is why an
   unreachable market makes the model infeasible rather than expensive.

#### Why the decisions cannot be taken one at a time

Where to build depends on where the market is. How big to build depends on how
much of the market that site ends up serving. Whether to rail clinker depends on
both. Sequencing these gives a feasible plan, not an optimal one - which is the
whole argument for solving them together.

#### Assumptions

- Common conversion costs, taxes, working capital and inflation are outside the
  comparison, as the brief allows.
- Limestone is charged at the plant that produces the clinker, even when that
  clinker is railed to a grinding unit.
- Flows are continuous, so a market may be served by more than one source.
- Distances are the road and rail figures given in the brief.

#### Honest limits

- Demand is deterministic within a scenario. There is no inventory, no
  seasonality, no ramp-up profile.
- Capex is a single annualised figure; no construction schedule or staged spend.
- The utilisation cap stands in for maintenance, kiln availability and product
  mix. A real plan would model those separately.
""")
    st.caption("Built with scipy.optimize.milp, which calls HiGHS. "
               "Source is two files: model.py for the formulation, app.py for the "
               "interface.")
