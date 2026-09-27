# The Rookie — India cement network design, FY2030

An interactive scenario tool for the SCPC group assignment. Group 7.

Change any input and the mixed integer programme is re-solved from scratch —
there are no pre-computed answers on screen. A full solve takes about 0.4
seconds.

## What it does

- Chooses which of six integrated plant belts to open, at which of three module
  sizes, and which of four split grinding locations to open, at which size.
- Optimises the clinker and cement flows at the same time, because those
  decisions cannot be taken one after another.
- Reports the annual relevant cost, its four components, per-site utilisation
  against the 90 % ceiling, and who serves each market from how far away.
- Re-derives every constraint from the answer and shows a pass/fail table, so
  the output is auditable rather than trusted.
- Compares its own result against the four independently verified optima.
- When there is no feasible network, says **why** in plain language — which
  markets are out of reach, which grinding unit has no clinker source, or how
  far short the capacity falls — instead of showing a solver error code.

## Files

| File | What it is |
|---|---|
| `model.py` | The case data and the formulation. `solve()` builds and solves the MILP; `diagnose()` explains infeasibility; `validate()` re-checks every constraint. |
| `app.py` | The Streamlit interface. No modelling logic. |
| `requirements.txt` | Four packages. HiGHS ships inside SciPy, so there is no separate solver to install. |
| `.streamlit/config.toml` | Theme and server settings. |

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

It opens on http://localhost:8501.

## Deploy it to Streamlit Community Cloud — free

1. **Create the GitHub repo.** Make it **private** if you would rather your
   classmates not find the code; Community Cloud can deploy from a private repo.
   Push these four files plus the `.streamlit` folder.

   ```bash
   git init
   git add .
   git commit -m "The Rookie - cement network design scenario tool"
   git branch -M main
   git remote add origin https://github.com/<you>/rookie-cement-network.git
   git push -u origin main
   ```

2. **Sign in at https://share.streamlit.io** with the same GitHub account and
   authorise it. If the repo is private, grant the private-repo scope when asked.

3. **Click "Create app" → "Deploy a public app from GitHub"** and fill in:
   - Repository: `<you>/rookie-cement-network`
   - Branch: `main`
   - Main file path: `app.py`
   - Advanced settings → Python version: **3.11** or **3.12**

4. **Deploy.** The first build installs SciPy and takes three to five minutes.
   After that it is a normal web page.

5. **Pick a readable URL.** Under the app's settings you can set a custom
   subdomain, so the link you send is something like
   `rookie-cement-network.streamlit.app` rather than a random string.

## Before you send the link

- **Open it yourself first.** A free Community Cloud app goes to sleep after a
  stretch of inactivity, and the first visitor after that sees a "waking up"
  screen for 30 to 60 seconds. Visiting it a few minutes before you send the
  link removes that first impression entirely.
- **Click through every tab once.** Anything that is going to error will error
  on the first run of a cold container, not the tenth.
- **Say one line in the email about what to try.** Something like: *switch the
  scenario to "C — Chittorgarh delayed", then set Network to "I specify the
  network" and pre-fill with the base optimum — the app will tell you why that
  design cannot be built at all.* A reviewer who is handed a specific thing to
  try forms a much better impression than one left to hunt.

## Notes on the model

- Mt are converted to lakh tonnes internally, so that
  (₹/tonne-km × km × Mt) lands directly in ₹ crore.
- Capex is annualised with a capital recovery factor, default
  11 % over 20 years, giving 0.1256. Both are editable in the sidebar.
- The integer optimality tolerance is **zero**. Several candidate networks sit
  within one per cent of each other on cost, so a loose tolerance stops on a
  network that looks optimal and is not. If you rebuild this in Excel Solver,
  set the integer tolerance to 0.01 % or tighter.
- Limestone is charged at the plant that produces the clinker, even when that
  clinker is railed onward to a grinding unit.
- Entity labels in `model.py` (`PLANT_NAME`, `GRINDER_NAME`, `MARKET_NAME`) are
  cosmetic. Check them against the brief and edit them in that one place if they
  differ.

## Verified against

| Scenario | App | Independently solved | Difference |
|---|---|---|---|
| Base | 7,792.3 | 7,792.3 | 0.0 |
| A — regional demand shift | 7,889.4 | 7,889.4 | 0.0 |
| B — freight shock | 8,518.1 | 8,518.1 | 0.0 |
| C — Chittorgarh delayed | 8,215.1 | 8,215.1 | 0.0 |

All figures ₹ crore a year. The base network frozen and re-run under scenario C
is infeasible: usable clinker falls to 17.55 Mt against the 22.29 Mt required,
and usable grinding to 30.60 Mt against demand of 33.78 Mt. Every market stays
inside the 800 km limit — the design fails on capacity, not on distance.
