# GREENH2-NH3 — Integrated Green Ammonia Plant (Digital Twin Dashboard)

Undergraduate chemical engineering design project: a 1 tonne/day conceptual green-ammonia plant
(renewable power -> alkaline electrolysis + PSA nitrogen -> Haber-Bosch loop), with a DWSIM steady-state
flowsheet and an interactive Python/Streamlit dashboard.

## Features
- Interactive 3D plant (Three.js) with live flow animation, equipment telemetry and camera presets
- Mass and energy balance, equilibrium conversion, compression power (plan 5.4 formula)
- Screening techno-economics (LCOA) and CO2 comparison vs grey/blue ammonia
- Renewable variability and H2 buffer scenarios (stable, solar, hybrid)
- DWSIM validation tab: DWSIM stream results vs Python model, equipment register, mass-flow Sankey

## Run
```
pip install -r requirements.txt
python -m streamlit run greenh2_app.py
```
Internet access is needed for the 3D scene (Three.js is loaded from a CDN).

## DWSIM base case
H2 2.055 g/s, N2 9.516 g/s, 10 MPa, 488 C reactor outlet, recycle 0.95 -> about 33.9 kg/h NH3 (DWSIM) vs 34.6 kg/h (Python).

## Limitations (please read)
- Conceptual design study; NOT validated against real plant data. Not a certified or construction-ready design.
- Cost figures, PSA power (0.30 kWh/kg N2), electrolyser capex and equipment descriptions are assumptions to be replaced with cited sources.
- Renewable profiles are synthetic illustrations, not measured data.
- Close agreement with DWSIM applies only at the DWSIM base case.

## Files
- `greenh2_app.py` dashboard
- `compressor_model.py`, `green_ammonia_calc.py` calculation modules
- DWSIM flowsheet and stream-results spreadsheet
