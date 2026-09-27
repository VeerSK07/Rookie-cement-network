"""
The Rookie - India cement network design, FY2030
Mixed integer linear programme.

The model decides, simultaneously:
  y[i,k]   open integrated plant belt i at module size k        (binary)
  z[g,k]   open split grinding unit g at module size k          (binary)
  xc[i,m]  cement shipped from integrated plant i to market m   (Mt/yr)
  xg[g,m]  cement shipped from grinding unit g to market m      (Mt/yr)
  w[i,g]   clinker railed from integrated plant i to grinder g  (Mt/yr)

Objective: minimise annualised capex + fixed opex + limestone + cement
freight + clinker freight.

Solved with HiGHS via scipy.optimize.milp. Integer optimality tolerance is
set to zero because several candidate networks sit within 1% of each other
on cost - a loose tolerance stops on a network that looks optimal and is not.
"""

import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix

# ---------------------------------------------------------------- entities

INTEGRATED = ["I1", "I2", "I3", "I4", "I5", "I6"]
GRINDING = ["G1", "G2", "G3", "G4"]
MARKETS = ["M%d" % i for i in range(1, 13)]
MODULES = ["S", "M", "L"]

# Labels only - they do not affect the arithmetic.
# Check these against the case brief and correct here if they differ.
PLANT_NAME = {
    "I1": "Chittorgarh-Nimbahera (Rajasthan)",
    "I2": "Kachchh / Bhuj (Gujarat)",
    "I3": "Satna-Rewa (MP)",
    "I4": "Baloda Bazar-Raipur (Chhattisgarh)",
    "I5": "Kurnool-Kadapa (AP)",
    "I6": "Kalaburagi-Wadi (Karnataka)",
}
GRINDER_NAME = {
    "G1": "Dadri / Greater Noida (NCR)",
    "G2": "Pune (Maharashtra)",
    "G3": "Sankrail / Kolkata (WB)",
    "G4": "Chennai (TN)",
}
MARKET_NAME = {
    "M1": "Delhi NCR / Upper North", "M2": "Rajasthan", "M3": "Uttar Pradesh",
    "M4": "Madhya Pradesh", "M5": "Gujarat", "M6": "Maharashtra & Goa",
    "M7": "Bihar & Jharkhand", "M8": "West Bengal & NE",
    "M9": "Odisha & Chhattisgarh", "M10": "AP & Telangana",
    "M11": "Karnataka & Kerala", "M12": "Tamil Nadu",
}
MARKET_CITY = {
    "M1": "Delhi NCR", "M2": "Jaipur", "M3": "Lucknow", "M4": "Bhopal",
    "M5": "Ahmedabad", "M6": "Pune", "M7": "Patna", "M8": "Kolkata",
    "M9": "Bhubaneswar", "M10": "Hyderabad", "M11": "Bengaluru", "M12": "Chennai",
}

# Approximate coordinates, degrees north and east, for the network map only.
# These are NOT from the case brief - the brief supplies a distance matrix, not
# positions. They are the published locations of the named towns and cities and
# are used for drawing only. No cost or distance in the model comes from them.
COORD = {
    "I1": (24.88, 74.63), "I2": (23.25, 69.67), "I3": (24.58, 80.83),
    "I4": (21.66, 82.16), "I5": (15.83, 78.04), "I6": (17.33, 76.83),
    "G1": (28.55, 77.55), "G2": (18.52, 73.86), "G3": (22.57, 88.22),
    "G4": (13.08, 80.27),
    "M1": (28.61, 77.21), "M2": (26.91, 75.79), "M3": (26.85, 80.95),
    "M4": (23.26, 77.41), "M5": (23.02, 72.57), "M6": (18.52, 73.86),
    "M7": (25.59, 85.14), "M8": (22.57, 88.36), "M9": (20.30, 85.82),
    "M10": (17.39, 78.49), "M11": (12.97, 77.59), "M12": (13.08, 80.27),
}

# ---------------------------------------------------------------- case data

# limestone landed price, rupees per tonne of limestone, by belt
LIMESTONE_PRICE = {"I1": 205, "I2": 225, "I3": 195, "I4": 200, "I5": 210, "I6": 215}

# integrated module -> (clinker Mt, grinding Mt, capex Rs cr, fixed opex Rs cr/yr)
IMOD = {"S": (3.0, 2.5, 2500, 90), "M": (4.5, 3.5, 3300, 120), "L": (6.0, 5.0, 4200, 155)}
# grinding module -> (grinding Mt, capex Rs cr, fixed opex Rs cr/yr)
GMOD = {"S": (2.5, 700, 28), "M": (4.0, 1000, 38), "L": (6.0, 1500, 55)}

# integrated plant -> market, road km
DIST_PLANT_MARKET = dict(zip(INTEGRATED, [
    [580, 300, 800, 400, 350, 860, 1270, 1700, 1510, 1110, 1630, 1730],
    [1150, 890, 1440, 950, 360, 820, 1900, 2300, 2040, 1350, 1700, 1910],
    [690, 680, 300, 450, 1030, 1180, 540, 960, 840, 1000, 1600, 1540],
    [1100, 1040, 710, 620, 1200, 1120, 640, 780, 490, 730, 1300, 1170],
    [1710, 1500, 1510, 1000, 1180, 640, 1570, 1580, 1150, 220, 390, 470],
    [1510, 1280, 1370, 800, 930, 410, 1510, 1600, 1200, 210, 590, 720],
]))
# grinding unit -> market, road km
DIST_GRINDER_MARKET = dict(zip(GRINDING, [
    [40, 300, 460, 710, 950, 1410, 980, 1520, 1490, 1490, 2080, 2090],
    [1410, 1140, 1410, 770, 620, 0, 1680, 1890, 1520, 610, 880, 1100],
    [1550, 1610, 1050, 1330, 1930, 1870, 550, 20, 430, 1400, 1860, 1620],
    [2110, 1930, 1840, 1410, 1650, 1100, 1780, 1630, 1200, 620, 350, 0],
]))
# integrated plant -> grinding unit, rail km
DIST_PLANT_GRINDER = dict(zip(INTEGRATED, [
    [580, 820, 1620, 1660], [1130, 780, 2190, 1830], [630, 1130, 900, 1470],
    [1030, 1070, 730, 1120], [1630, 620, 1500, 450], [1440, 390, 1520, 690],
]))

# FY2030 market demand at a 5% national share, Mt per year
DEMAND_BASE = [3.995, 1.900, 3.400, 1.745, 1.860, 3.900,
               2.800, 3.050, 3.085, 3.100, 2.500, 2.445]
# scenario A: same national total, shifted regional mix
DEMAND_SCEN_A = [3.993, 1.899, 3.731, 1.915, 1.640, 3.439,
                 3.155, 3.437, 3.476, 2.734, 2.205, 2.156]

# ---------------------------------------------------------------- defaults

DEF = dict(
    cement_rate=3.03,        # Rs per tonne-km, finished cement by road
    clinker_rate=1.60,       # Rs per tonne-km, clinker by rail
    clinker_factor=0.66,     # tonnes of clinker per tonne of cement
    limestone_per_clinker=1.5,   # tonnes of limestone per tonne of clinker
    utilisation_cap=0.90,    # no site above 90% of selected nameplate
    cement_max_km=800,
    clinker_max_km=1300,
    wacc=0.11,
    life_years=20,
)


def crf(wacc=DEF["wacc"], years=DEF["life_years"]):
    """Capital recovery factor - turns capex into an equivalent annual charge."""
    return wacc * (1 + wacc) ** years / ((1 + wacc) ** years - 1)


# Mt -> lakh tonnes, so that (Rs/tonne-km x km x Mt) lands in Rs crore
UNIT = 0.1


# ---------------------------------------------------------------- the model

def solve(demand=None, cement_rate=None, clinker_rate=None,
          clinker_factor=None, limestone_per_clinker=None,
          utilisation_cap=None, cement_max_km=None, clinker_max_km=None,
          limestone_price=None, wacc=None, life_years=None,
          unavailable=(), fixed_network=None, time_limit=120):
    """
    Solve the network design. Every argument that is None falls back to the
    case default.

    unavailable    tuple of integrated plant codes that cannot be built
    fixed_network  (dict plant->module, dict grinder->module) to force a
                   specific network and re-optimise only the flows. Sites
                   absent from either dict are closed.
    """
    d = list(DEMAND_BASE if demand is None else demand)
    cfr = DEF["cement_rate"] if cement_rate is None else cement_rate
    clfr = DEF["clinker_rate"] if clinker_rate is None else clinker_rate
    cf = DEF["clinker_factor"] if clinker_factor is None else clinker_factor
    lsq = DEF["limestone_per_clinker"] if limestone_per_clinker is None else limestone_per_clinker
    util = DEF["utilisation_cap"] if utilisation_cap is None else utilisation_cap
    cem_lim = DEF["cement_max_km"] if cement_max_km is None else cement_max_km
    cl_lim = DEF["clinker_max_km"] if clinker_max_km is None else clinker_max_km
    lsp = dict(LIMESTONE_PRICE) if limestone_price is None else dict(limestone_price)
    r = crf(DEF["wacc"] if wacc is None else wacc,
            DEF["life_years"] if life_years is None else life_years)

    I, G, M, K = INTEGRATED, GRINDING, MARKETS, MODULES

    vy = [(i, k) for i in I for k in K]
    vz = [(g, k) for g in G for k in K]
    vxc = [(i, m) for i in I for m in M]
    vxg = [(g, m) for g in G for m in M]
    vw = [(i, g) for i in I for g in G]
    names = ([("y",) + t for t in vy] + [("z",) + t for t in vz]
             + [("xc",) + t for t in vxc] + [("xg",) + t for t in vxg]
             + [("w",) + t for t in vw])
    idx = {n: j for j, n in enumerate(names)}
    N = len(names)

    # ---- objective
    c = np.zeros(N)
    integ = np.zeros(N)
    for i, k in vy:
        _, _, capex, fixop = IMOD[k]
        c[idx[("y", i, k)]] = capex * r + fixop
        integ[idx[("y", i, k)]] = 1
    for g, k in vz:
        _, capex, fixop = GMOD[k]
        c[idx[("z", g, k)]] = capex * r + fixop
        integ[idx[("z", g, k)]] = 1
    for i, m in vxc:
        # cement freight from the plant, plus limestone for clinker made on site
        c[idx[("xc", i, m)]] = UNIT * (cfr * DIST_PLANT_MARKET[i][M.index(m)]
                                       + lsq * lsp[i] * cf)
    for g, m in vxg:
        c[idx[("xg", g, m)]] = UNIT * cfr * DIST_GRINDER_MARKET[g][M.index(m)]
    for i, g in vw:
        # clinker freight, plus limestone charged at the plant that made it
        c[idx[("w", i, g)]] = UNIT * (clfr * DIST_PLANT_GRINDER[i][G.index(g)]
                                      + lsq * lsp[i])

    # ---- constraints
    A = lil_matrix((0, N))
    lb, ub = [], []

    def add(row, lo, hi):
        nonlocal A
        A.resize((A.shape[0] + 1, N))
        for j, v in row.items():
            A[A.shape[0] - 1, j] = v
        lb.append(lo)
        ub.append(hi)

    for m in M:                                   # each market served in full
        row = {idx[("xc", i, m)]: 1 for i in I}
        row.update({idx[("xg", g, m)]: 1 for g in G})
        add(row, d[M.index(m)], d[M.index(m)])
    for i in I:                                   # on-site grinding capacity
        row = {idx[("xc", i, m)]: 1 for m in M}
        for k in K:
            row[idx[("y", i, k)]] = -util * IMOD[k][1]
        add(row, -np.inf, 0)
    for i in I:                                   # clinker capacity
        row = {idx[("xc", i, m)]: cf for m in M}
        for g in G:
            row[idx[("w", i, g)]] = 1
        for k in K:
            row[idx[("y", i, k)]] = -util * IMOD[k][0]
        add(row, -np.inf, 0)
    for g in G:                                   # clinker in = cement out x cf
        row = {idx[("w", i, g)]: 1 for i in I}
        row.update({idx[("xg", g, m)]: -cf for m in M})
        add(row, 0, 0)
    for g in G:                                   # grinding unit capacity
        row = {idx[("xg", g, m)]: 1 for m in M}
        for k in K:
            row[idx[("z", g, k)]] = -util * GMOD[k][0]
        add(row, -np.inf, 0)
    for i in I:                                   # at most one module per site
        add({idx[("y", i, k)]: 1 for k in K}, 0, 1)
    for g in G:
        add({idx[("z", g, k)]: 1 for k in K}, 0, 1)

    # ---- bounds, lane masks, site availability
    L = np.zeros(N)
    U = np.full(N, np.inf)
    for i, k in vy:
        U[idx[("y", i, k)]] = 1
    for g, k in vz:
        U[idx[("z", g, k)]] = 1
    for i, m in vxc:
        if DIST_PLANT_MARKET[i][M.index(m)] > cem_lim or i in unavailable:
            U[idx[("xc", i, m)]] = 0
    for g, m in vxg:
        if DIST_GRINDER_MARKET[g][M.index(m)] > cem_lim:
            U[idx[("xg", g, m)]] = 0
    for i, g in vw:
        if DIST_PLANT_GRINDER[i][G.index(g)] > cl_lim or i in unavailable:
            U[idx[("w", i, g)]] = 0
    for i, k in vy:
        if i in unavailable:
            U[idx[("y", i, k)]] = 0
    if fixed_network is not None:
        fi, fg = fixed_network
        for i in I:
            for k in K:
                v = 1 if (fi.get(i) == k and i not in unavailable) else 0
                L[idx[("y", i, k)]] = U[idx[("y", i, k)]] = v
        for g in G:
            for k in K:
                v = 1 if fg.get(g) == k else 0
                L[idx[("z", g, k)]] = U[idx[("z", g, k)]] = v

    res = milp(c=c,
               constraints=LinearConstraint(A.tocsr(), lb, ub),
               bounds=Bounds(L, U),
               integrality=integ,
               options={"mip_rel_gap": 0.0, "time_limit": time_limit,
                        "presolve": True})

    out = {"ok": bool(res.success), "message": str(res.message),
           "n_vars": N, "n_cons": A.shape[0]}
    if not res.success:
        out["diagnosis"] = diagnose(d, cem_lim, cl_lim, util, cf, unavailable,
                                    fixed_network)
        return out

    x = res.x
    plants = {i: k for i in I for k in K if x[idx[("y", i, k)]] > 0.5}
    grinders = {g: k for g in G for k in K if x[idx[("z", g, k)]] > 0.5}
    xc = {(i, m): x[idx[("xc", i, m)]] for i in I for m in M
          if x[idx[("xc", i, m)]] > 1e-6}
    xg = {(g, m): x[idx[("xg", g, m)]] for g in G for m in M
          if x[idx[("xg", g, m)]] > 1e-6}
    w = {(i, g): x[idx[("w", i, g)]] for i in I for g in G
         if x[idx[("w", i, g)]] > 1e-6}

    fixed = (sum(IMOD[k][2] * r + IMOD[k][3] for k in plants.values())
             + sum(GMOD[k][1] * r + GMOD[k][2] for k in grinders.values()))
    clinker_made = {i: cf * sum(v for (ii, m), v in xc.items() if ii == i)
                    + sum(v for (ii, g), v in w.items() if ii == i) for i in I}
    limestone = sum(UNIT * lsq * lsp[i] * clinker_made[i] for i in I)
    cem_tkm = (sum(v * DIST_PLANT_MARKET[i][M.index(m)] for (i, m), v in xc.items())
               + sum(v * DIST_GRINDER_MARKET[g][M.index(m)] for (g, m), v in xg.items()))
    cl_tkm = sum(v * DIST_PLANT_GRINDER[i][G.index(g)] for (i, g), v in w.items())
    cement_freight = UNIT * cfr * cem_tkm
    clinker_freight = UNIT * clfr * cl_tkm
    total = fixed + limestone + cement_freight + clinker_freight
    cement_flow = sum(xc.values()) + sum(xg.values())

    ground = {}
    for i in plants:
        ground[i] = sum(v for (ii, m), v in xc.items() if ii == i)
    for g in grinders:
        ground[g] = sum(v for (gg, m), v in xg.items() if gg == g)

    out.update(
        objective=float(res.fun),
        total=float(total),
        fixed=float(fixed),
        limestone=float(limestone),
        cement_freight=float(cement_freight),
        clinker_freight=float(clinker_freight),
        plants=plants,
        grinders=grinders,
        cement_flows={f"{a}>{b}": float(v) for (a, b), v in sorted(list(xc.items()) + list(xg.items()))},
        clinker_flows={f"{a}>{b}": float(v) for (a, b), v in sorted(w.items())},
        xc=xc, xg=xg, w=w,
        clinker_made={i: float(v) for i, v in clinker_made.items() if v > 1e-6},
        ground={k: float(v) for k, v in ground.items()},
        clinker_nameplate=float(sum(IMOD[k][0] for k in plants.values())),
        grinding_nameplate=float(sum(IMOD[k][1] for k in plants.values())
                                 + sum(GMOD[k][0] for k in grinders.values())),
        cement_lead=float(cem_tkm / cement_flow) if cement_flow else 0.0,
        clinker_lead=float(cl_tkm / sum(w.values())) if w else None,
        cement_tkm=float(cem_tkm), clinker_tkm=float(cl_tkm),
        crf=float(r),
    )
    out["checks"] = validate(out, d, util, cf, cem_lim, cl_lim)
    return out


# ---------------------------------------------------------------- diagnosis

def diagnose(demand, cem_lim, cl_lim, util, cf, unavailable, fixed_network):
    """
    Explain an infeasible model in words a manager can act on, instead of
    returning a bare solver status.
    """
    I, G, M = INTEGRATED, GRINDING, MARKETS
    if fixed_network is None:
        open_i = [i for i in I if i not in unavailable]
        open_g = list(G)
        i_cap = {i: IMOD["L"][1] for i in open_i}
        g_cap = {g: GMOD["L"][0] for g in open_g}
        cl_cap = {i: IMOD["L"][0] for i in open_i}
        note = "with every candidate site available at its largest module"
    else:
        fi, fg = fixed_network
        open_i = [i for i in fi if i not in unavailable]
        open_g = list(fg)
        i_cap = {i: IMOD[fi[i]][1] for i in open_i}
        g_cap = {g: GMOD[fg[g]][0] for g in open_g}
        cl_cap = {i: IMOD[fi[i]][0] for i in open_i}
        note = "with the network you specified"

    reasons = []

    # 1. markets with no source inside the cement distance limit
    unreachable = []
    for m in M:
        j = M.index(m)
        near = [(DIST_PLANT_MARKET[i][j], i) for i in open_i
                if DIST_PLANT_MARKET[i][j] <= cem_lim]
        near += [(DIST_GRINDER_MARKET[g][j], g) for g in open_g
                 if DIST_GRINDER_MARKET[g][j] <= cem_lim]
        if not near:
            best = min([(DIST_PLANT_MARKET[i][j], i) for i in open_i]
                       + [(DIST_GRINDER_MARKET[g][j], g) for g in open_g])
            unreachable.append((m, best[1], best[0]))
    if unreachable:
        reasons.append(
            "No source within the %d km cement limit for: %s. Nearest available "
            "source for each is %s."
            % (cem_lim,
               ", ".join("%s (%s)" % (m, MARKET_NAME.get(m, m)) for m, _, _ in unreachable),
               "; ".join("%s from %s at %d km" % (m, s, km) for m, s, km in unreachable)))

    # 2. a grinding unit with no clinker source inside the rail limit
    orphan = []
    for g in open_g:
        src = [i for i in open_i
               if DIST_PLANT_GRINDER[i][G.index(g)] <= cl_lim]
        if not src:
            orphan.append(g)
    if orphan:
        reasons.append(
            "Grinding unit(s) %s have no clinker source within the %d km rail limit."
            % (", ".join(orphan), cl_lim))

    # 3. not enough grinding or clinker capacity in total
    total_demand = sum(demand)
    grind = util * (sum(i_cap.values()) + sum(g_cap.values()))
    clink = util * sum(cl_cap.values())
    if grind < total_demand - 1e-9:
        reasons.append("Total usable grinding capacity is %.2f Mt against demand of "
                       "%.2f Mt." % (grind, total_demand))
    if clink < cf * total_demand - 1e-9:
        reasons.append("Total usable clinker capacity is %.2f Mt against a requirement "
                       "of %.2f Mt." % (clink, cf * total_demand))

    if not reasons:
        reasons.append("No single cause isolated. The binding limit is a combination "
                       "of distance masks and the %d%% utilisation ceiling."
                       % round(100 * util))
    return {"note": note, "reasons": reasons,
            "unreachable": [m for m, _, _ in unreachable]}


# ---------------------------------------------------------------- validation

def validate(sol, demand, util, cf, cem_lim, cl_lim):
    """Re-derive every constraint from the returned solution. Nothing here
    trusts the solver - it checks it."""
    I, G, M = INTEGRATED, GRINDING, MARKETS
    xc, xg, w = sol["xc"], sol["xg"], sol["w"]
    rows = []

    worst = 0.0
    for m in M:
        got = (sum(v for (i, mm), v in xc.items() if mm == m)
               + sum(v for (g, mm), v in xg.items() if mm == m))
        worst = max(worst, abs(got - demand[M.index(m)]))
    rows.append(("Every market receives exactly its target volume",
                 "max imbalance %.2e Mt" % worst, worst < 1e-6))

    worst = 0.0
    for g in sol["grinders"]:
        got = sum(v for (i, gg), v in w.items() if gg == g)
        need = cf * sum(v for (gg, m), v in xg.items() if gg == g)
        worst = max(worst, abs(got - need))
    rows.append(("Clinker into each grinding unit equals %.2f x cement ground" % cf,
                 "max imbalance %.2e Mt" % worst, worst < 1e-6))

    hi = 0.0
    for i, k in sol["plants"].items():
        hi = max(hi, sol["clinker_made"].get(i, 0) / IMOD[k][0],
                 sol["ground"].get(i, 0) / IMOD[k][1])
    for g, k in sol["grinders"].items():
        hi = max(hi, sol["ground"].get(g, 0) / GMOD[k][0])
    rows.append(("No site above the %d%% utilisation ceiling" % round(100 * util),
                 "highest use %.1f%%" % (100 * hi), hi <= util + 1e-6))

    bad_c = max([DIST_PLANT_MARKET[i][M.index(m)] for (i, m) in xc] or [0])
    bad_g = max([DIST_GRINDER_MARKET[g][M.index(m)] for (g, m) in xg] or [0])
    rows.append(("No cement lane beyond %d km" % cem_lim,
                 "longest lane %d km" % max(bad_c, bad_g),
                 max(bad_c, bad_g) <= cem_lim))

    bad_w = max([DIST_PLANT_GRINDER[i][G.index(g)] for (i, g) in w] or [0])
    rows.append(("No clinker lane beyond %d km" % cl_lim,
                 "longest lane %d km" % bad_w, bad_w <= cl_lim))

    gap = abs(sol["objective"] - sol["total"])
    rows.append(("Objective reconciles to capex + opex + limestone + both freights",
                 "difference Rs %.4f crore" % gap, gap < 0.01))

    return rows


# ---------------------------------------------------------------- scenarios

SCENARIOS = {
    "Base": dict(
        label="Base case",
        note="FY2030 demand at a 5% national share, case freight rates, every site available.",
        kwargs=dict()),
    "A": dict(
        label="A - regional demand shift",
        note="Same national total, demand shifts towards the east and north.",
        kwargs=dict(demand=DEMAND_SCEN_A)),
    "B": dict(
        label="B - freight shock",
        note="Cement road freight to Rs 3.75/t-km and clinker rail to Rs 1.85/t-km.",
        kwargs=dict(cement_rate=3.75, clinker_rate=1.85)),
    "C": dict(
        label="C - Chittorgarh delayed",
        note="The I1 Chittorgarh belt cannot be commissioned in time.",
        kwargs=dict(unavailable=("I1",))),
}

# Proven optima, solved to a zero integer gap. The app re-solves live; these
# are kept so the app can check itself against a known answer.
PROVEN = {
    "Base": 7792.3,
    "A": 7889.4,
    "B": 8518.1,
    "C": 8215.1,
}

BASE_NETWORK = ({"I1": "L", "I3": "L", "I4": "L", "I5": "M", "I6": "S"},
                {"G1": "L", "G2": "M", "G3": "M", "G4": "M"})
ROBUST_NETWORK = ({"I1": "S", "I2": "M", "I3": "L", "I4": "L", "I5": "M", "I6": "M"},
                  {"G1": "L", "G2": "M", "G3": "L", "G4": "S"})
