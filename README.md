# Do In-Match Hydration Breaks Alter Match Momentum?

**A within-match case-crossover analysis of the 2026 FIFA World Cup.**

This repository contains the code and derived data for a causal-inference study of whether
the 2026 FIFA World Cup's mandatory in-match hydration breaks (brief stoppages near the 22nd
minute of each half, administered in every match) affected the momentum of the dominant
side. It is organized for open, reproducible research: once the SofaScore-sourced series
have been regenerated (one script, see [Data & regeneration](#data--regeneration)), a single
notebook runs the entire analysis end-to-end and regenerates every table and every main-text
figure in the manuscript (one supplementary figure is shipped static; see the structure section).

The manuscript is available as a preprint: [arXiv:2607.19783](https://arxiv.org/abs/2607.19783).

The headline result is that the popular "the break kills momentum" claim finds little
support: the apparent post-break fade is momentum reverting through the stoppage as if play
had continued, the average break effect is small (though the sample of 99 matches has limited
power to detect a small effect), and net expected goals (xG) shows no effect. Where a
direction appears it is state-dependent: the clearest modifier is team strength, with the
break favouring the stronger side by about +1.6 momentum points per 100 Elo points of rating
advantage (the only statistically significant interaction), and a weaker pattern by scoreline
in which a comfortably-leading side shows an implied loss of about four points. These
state-dependent signals are reported as exploratory.

---

## Important: what is, and is not, in this repository

The analysis outcome is SofaScore's *Attack Momentum* index, and the event-based check uses
SofaScore's expected-goals (xG) values. These are SofaScore's proprietary model outputs and
**are not redistributed in this repository.** Seven files are therefore deliberately absent
from `data/` and must be regenerated before the notebook will run:

```
data/wc2026_group_momentum.json      2026 WC group-stage minute momentum + goals + breaks
data/wc2026_knockout_raw.json        2026 WC knockout minute momentum + goals + city
data/xg_2026.json                    2026 WC per-shot expected-goals events
data/wc_control_intl.json            historical control momentum series (international)
data/wc_control_pastwc.json          historical control momentum series (2018/2022 WC)
data/wc_control_group_momentum.json  historical control momentum series (group stage)
data/wc_control_momentum.json        historical control momentum series
```

Everything needed to rebuild them from SofaScore's public interface is shipped:
`data/manifest.json` (public match facts and author-derived metadata for every match,
without the momentum arrays) and `fetch_sofascore.py`. A clean checkout will **not** run the
notebook until that script has been run; see the next section for its status and caveats.

---

## Quick start

```bash
# 1. Create an environment (Python 3.11 recommended) and install dependencies
pip install -r requirements.txt

# 2. Regenerate the SofaScore-sourced series (REQUIRED; needs network access; ~20 min)
python fetch_sofascore.py
python fetch_sofascore.py --check   # confirms all seven files are present and well-formed

# 3. Run the entire analysis end-to-end (regenerates every figure and table)
jupyter nbconvert --to notebook --execute --inplace WC2026_analysis.ipynb

# ...or open it interactively
jupyter lab WC2026_analysis.ipynb
```

Step 2 is the only step that needs network access. After it, the notebook reads only the
files in `data/`, writes figures to `paper/figures/`, and writes intermediate result tables
to `paper/`.

---

## Data & regeneration

`fetch_sofascore.py` reads `data/manifest.json`, downloads the Attack Momentum graph and shot
map for each match, and rebuilds the seven analysis-ready files listed above. It applies a
polite per-request delay (default 1.5 s; the manifest implies about 790 requests, roughly
20 minutes) and prints a schema check when done. Please respect SofaScore's terms of use and
do not remove the delay.

```bash
python fetch_sofascore.py            # download & rebuild the SofaScore-sourced files
python fetch_sofascore.py --check    # validate what is currently in data/
python fetch_sofascore.py --sleep 2  # use a longer per-request delay
```

**Status and caveats — please read.**

- The script is a faithful re-implementation of the collection step, but it has **not been
  run to completion by the author in a clean environment**, so a successful end-to-end
  regeneration is not yet independently verified. SofaScore's API is undocumented and may
  change.
- **Run it from an ordinary (residential) internet connection.** In testing, SofaScore's API
  returned `HTTP 403 Forbidden` to requests originating from a cloud/datacenter IP range even
  with browser-like headers, so the script is expected to fail from cloud sandboxes, CI
  runners, and similar environments. It is expected to work from a standard home or office
  connection, where SofaScore serves the same JSON that its public match pages display.
- If the script fails for you, please open an issue with the error output; the manifest
  contains everything needed to diagnose which match or endpoint changed.

The design choice here — separating the public facts (manifest) from the proprietary arrays
and regenerating rather than redistributing the latter — is deliberate. Its cost is that a
clean checkout is not a turnkey run; that is stated plainly above rather than hidden.

---

## Repository structure

```
.
├── WC2026_analysis.ipynb     # END-TO-END notebook: data load → cleaning → figures → all models
├── requirements.txt          # pinned dependencies (versions used for the manuscript)
├── LICENSE                   # MIT (code); see note on data
├── CITATION.cff              # how to cite
│
├── fetch_sofascore.py        # regenerates the SofaScore-sourced series from the public API
│
├── data/                     # inputs
│   ├── manifest.json                 # public/author-derived metadata for every match,
│   │                                 #   WITHOUT the proprietary momentum arrays
│   ├── break_times_exact.json        # commentary-derived break start/end minutes
│   ├── treated_covariates.json       # per-break covariates (Elo, WBGT, kickoff hour, ...)
│   ├── control_candidates_all.json   # historical no-break control minutes + covariates
│   ├── _gv.json                      # match metadata (Elo, city) lookup
│   │   # --- NOT SHIPPED: generated by fetch_sofascore.py (see above) ---
│   ├── wc2026_group_momentum.json
│   ├── wc2026_knockout_raw.json
│   ├── xg_2026.json
│   └── wc_control_*.json
│
├── analysis_gap.py           # Design A (clock-aligned) within-match builder  [core]
├── model_within.py           # shared loaders + base within-match model       [core]
├── analysis_designB.py       # Design B (play-aligned) within-match builder
├── external_dom.py           # external-control design: matching + CATEs
├── model_xg_designs.py       # net-xG break effect under both designs
├── make_figures2.py          # motivating figures + referent-sensitivity table
├── make_AB.py                # combined Design A / Design B figure
├── make_schematic.py         # two-designs schematic
├── make_effect_plot.py       # two-panel effect figure: by goal margin, by team strength
├── coef_table.py             # nested coefficient tables
│
├── paper/                    # notebook OUTPUT (not the manuscript source)
│   ├── figures/              # manuscript figures, regenerated by the notebook (*)
│   └── *.txt, coef_rows.tex  # intermediate result tables
│
└── provenance/               # data-collection scripts (transparency; see "Data provenance")
    ├── build_controls.py, fetch_elo.py, weather.py
```

The pipeline `.py` files live at the repository root because the notebook and the scripts
load one another by relative path (e.g. `analysis_gap.py` sources `model_within.py`). All
data inputs are under `data/`. The manuscript source (LaTeX) is not kept in this repository;
see the arXiv preprint linked above.

(*) All main-text figures and tables are regenerated by the notebook. The one exception is
`paper/figures/figA_positivity.png` (the supplementary positivity/overlap figure for the
external-control design), which is shipped as a static file: the positivity diagnostics it
depicts (matched vs. dropped events, WBGT of the dropped, and the heat split) are computed and
printed by notebook section 8, but the original plotting script for that panel was not
retained. It is a diagnostic illustration and does not enter any reported estimate.

---

## What the notebook does, section by section

The notebook mirrors the manuscript. Each section is self-contained (it re-loads the data),
so sections can also be run individually.

| Notebook section | Produces | Manuscript |
|---|---|---|
| 1 · Within-match clock-aligned builder + ladder | Design A dataset; nested-model ladder | §4 |
| 2 · Figures + referent table | Fig 1 (orientation), Fig 2, break-minute Fig; referent table | §1–§2, App. B |
| 3 · Clock-aligned coefficient table | Table 3 rows | §4.6 |
| 4 · Effect plot | Fig 5, two panels: effect by goal margin, effect by team strength (Elo) | §4.7 |
| 5 · Within-match play-aligned builder + ladder | Design B dataset; ladder | §4.6, App. B |
| 6 · Two-designs schematic | Fig 3 (schematic) | §3 |
| 7 · Combined Design A / Design B figure | Fig 4 | §3, §6.1 |
| 8 · External controls | ATT, tight-caliper matching, CATEs; positivity | §5 |
| 9 · Event-based check: net xG | xG break effect under both designs (−0.001 / +0.011) | §6.1 |

---

## Study design in brief

- **Outcome.** SofaScore *Attack Momentum*, a signed minute-resolved index, oriented toward
  the side dominant in the five minutes before the break (a "sign-adjusted" / dominance
  outcome). The clock runs through the ~3-minute break, so the three in-play minutes at each
  break are excluded and momentum is measured only after play resumes.
- **Primary design — within-match case-crossover.** Each break minute is compared to
  non-break minutes of the *same* match, differencing out all match-level factors (teams,
  strength, heat, venue, kickoff time). Two counterfactuals for the break window are
  reported: **clock-aligned (Design A)** and **play-aligned (Design B)**.
- **Robustness — external controls.** 2026 break events are matched (tight-caliper
  propensity-score matching) to no-break minutes from historical tournaments. This design
  has a positivity void in the extreme-heat regime, documented in the appendix.
- **Adjudicating outcome — net xG.** Expected goals is event-based and a true zero during a
  stoppage, so it is free of the momentum index's rebuild-lag artefact; it shows no break
  effect under either alignment.

---

## Data provenance

All data are derived from **publicly displayed** sources; no private feeds are used.

- **Match momentum & goals (2026 WC and historical controls).** Minute-resolved *Attack
  Momentum* series and goal minutes were retrieved from publicly displayed SofaScore match
  pages and stored in minute-indexed form (`wc2026_*`, `wc_control_*`). These series are
  SofaScore's property and are **not redistributed** here; they are regenerated by
  `fetch_sofascore.py` from the public metadata in `data/manifest.json`.
- **Shot / xG events (2026 WC).** Per-shot expected-goals values (`xg_2026.json`), likewise
  not redistributed and regenerated by `fetch_sofascore.py`.
- **Break timings.** Start (and, where available, end) minutes of each hydration break were
  read from public live-text match commentary (`break_times_exact.json`, and the `breaks`
  field of the manifest / regenerated `wc2026_group_momentum.json`).
- **Team strength (Elo).** Match-dated international Elo ratings.
- **Heat (WBGT).** Wet-bulb globe temperature derived from venue coordinates and kickoff
  time via a public reanalysis weather service; climate-controlled/indoor venues were
  assigned a fixed indoor value (see the manuscript, §2.2).

The scripts in `provenance/` document how the raw inputs were assembled from these sources.
They require network access and the original bulk caches (not shipped, for size), so they are
provided for **transparency**, not as part of the reproduction. The reproduction begins from
the files in `data/` once `fetch_sofascore.py` has regenerated the SofaScore-sourced series.

### Excluded matches (documented in the manuscript)
- France vs Iraq (`15186769`) is dropped: its second half featured no hydration break.
- Three group-stage matches with momentum series whose length was inconsistent with the
  nominal-minute indexing were dropped in cleaning.
The analytic sample is **99 matches / 198 break events**.

---

## Environment

Tested with Python 3.11.15 and the versions pinned in `requirements.txt`
(numpy 2.4.4, pandas 3.0.2, scipy 1.17.1, statsmodels 0.14.6, scikit-learn 1.8.0,
matplotlib 3.10.9). Results are deterministic; the only randomness (external-design
bootstrap resampling) is seeded (`numpy` default_rng(11)).

## License & citation

Code is released under the MIT License (`LICENSE`). See the license note and the "Data
provenance" section above regarding the data. If you use this repository, please cite the
manuscript ([arXiv:2607.19783](https://arxiv.org/abs/2607.19783); see `CITATION.cff`).

**Contact.** Debangan Dey, Department of Statistics, Texas A&M University — debangan@tamu.edu
