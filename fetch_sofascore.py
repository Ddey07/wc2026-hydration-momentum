#!/usr/bin/env python3
"""
Regenerate the SofaScore-sourced data files from SofaScore's public API.

WHY THIS EXISTS
---------------
The manuscript's outcome is SofaScore's *Attack Momentum* index, and the
event-based check uses SofaScore's expected-goals (xG) values. Those two series
are SofaScore's own model outputs and are NOT redistributed in this repository.
Instead, `data/manifest.json` ships only the public/author-derived metadata for
every match (fixture, final score, goal minutes, and the commentary-derived
hydration-break timings), *without* the momentum arrays. Running this script
downloads the momentum graph and shot map for each match from SofaScore's public
endpoints and reassembles the analysis-ready files:

    data/wc2026_group_momentum.json
    data/wc2026_knockout_raw.json
    data/wc_control_intl.json
    data/wc_control_pastwc.json
    data/wc_control_group_momentum.json
    data/wc_control_momentum.json
    data/xg_2026.json

After running it, `WC2026_analysis.ipynb` reproduces the full analysis.

IMPORTANT / HONEST CAVEATS
--------------------------
* This script requires network access and was NOT executed in the environment
  that produced this repository. SofaScore's public API is undocumented and may
  change its endpoint paths, field names, rate limits, or access policy at any
  time. Treat this as a faithful re-implementation of how the data were gathered,
  and verify the output against the expected schema (see `--check`) before use.
* Respect SofaScore's terms of use and rate limits. A polite delay is applied
  between requests; do not remove it.
* Goal minutes and break timings are taken from the manifest (public facts /
  author derivation) and are not re-fetched; only the momentum arrays and xG
  values are downloaded.

USAGE
-----
    python fetch_sofascore.py            # fetch everything into data/
    python fetch_sofascore.py --check    # validate existing data/ against manifest
    python fetch_sofascore.py --sleep 2  # set per-request delay (seconds)
"""
import argparse, json, os, sys, time, urllib.request

API = "https://api.sofascore.com/api/v1/event/{id}/{path}"
HEADERS = {
    # SofaScore serves JSON to browser-like clients; a UA is required.
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json",
}
DATA = "data"
MOMENTUM_FILES = [
    "wc2026_group_momentum.json", "wc2026_knockout_raw.json",
    "wc_control_intl.json", "wc_control_pastwc.json",
    "wc_control_group_momentum.json", "wc_control_momentum.json",
]


def _get(event_id, path, sleep):
    """GET one SofaScore endpoint; return parsed JSON or None on 404/empty."""
    url = API.format(id=event_id, path=path)
    req = urllib.request.Request(url, headers=HEADERS)
    time.sleep(sleep)  # politeness / rate-limit; do not remove
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def fetch_momentum(event_id, sleep):
    """Attack Momentum graph -> list of minute-ordered values, and start minute.

    Endpoint: /event/{id}/graph -> {"graphPoints": [{"minute": m, "value": v}, ...]}
    The stored `mom` array is the ordered sequence of `value`s; `startMin` is the
    first point's minute (usually 1).
    """
    g = _get(event_id, "graph", sleep)
    if not g or "graphPoints" not in g or not g["graphPoints"]:
        return None, None
    pts = sorted(g["graphPoints"], key=lambda p: p["minute"])
    return [p["value"] for p in pts], int(pts[0]["minute"])


def fetch_xg(event_id, sleep):
    """Shot map -> list of {"t": minute+addedTime/100, "h": 1/0, "xg": value}.

    Endpoint: /event/{id}/shotmap -> {"shotmap": [{"time": m, "addedTime": a,
              "isHome": bool, "xg": x}, ...]}. Shots without an xG value are
              skipped (they contribute a true zero to net xG).
    """
    s = _get(event_id, "shotmap", sleep)
    if not s or "shotmap" not in s:
        return None
    out = []
    for sh in s["shotmap"]:
        if sh.get("xg") is None:
            continue
        t = float(sh.get("time", 0)) + float(sh.get("addedTime", 0)) / 100.0
        out.append({"t": round(t, 2), "h": 1 if sh.get("isHome") else 0,
                    "xg": float(sh["xg"])})
    return out


def check(manifest):
    """Validate that data/ files exist and carry momentum arrays of sane length."""
    ok = True
    for f in MOMENTUM_FILES:
        p = os.path.join(DATA, f)
        if not os.path.exists(p):
            print(f"  MISSING: {p}"); ok = False; continue
        recs = json.load(open(p))
        short = [r["id"] for r in recs if not (isinstance(r.get("mom"), list) and len(r["mom"]) > 10)]
        note = f" ({len(short)} short/empty series, excluded by the length gate)" if short else ""
        print(f"  {f}: {len(recs)} records with momentum arrays{note}")
    xp = os.path.join(DATA, "xg_2026.json")
    print(f"  xg_2026.json: {'present' if os.path.exists(xp) else 'MISSING'}")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate existing data/ and exit")
    ap.add_argument("--sleep", type=float, default=1.5, help="delay between requests (s)")
    args = ap.parse_args()

    mpath = os.path.join(DATA, "manifest.json")
    if not os.path.exists(mpath):
        sys.exit(f"manifest not found at {mpath}; this repository ships it under data/.")
    manifest = json.load(open(mpath))

    if args.check:
        sys.exit(0 if check(manifest) else 1)

    # 1) momentum arrays -> reassemble each source file
    for f in MOMENTUM_FILES:
        recs = manifest[f]
        print(f"[{f}] fetching momentum for {len(recs)} matches ...")
        out = []
        for i, r in enumerate(recs, 1):
            mom, start = fetch_momentum(r["id"], args.sleep)
            if mom is None:
                print(f"  ! no momentum graph for event {r['id']} ({r.get('home')}-{r.get('away')}); skipped")
                continue
            rec = dict(r)
            rec["mom"] = mom
            if start is not None:
                rec.setdefault("startMin", start)
            out.append(rec)
            if i % 25 == 0:
                print(f"  ... {i}/{len(recs)}")
        json.dump(out, open(os.path.join(DATA, f), "w"))
        print(f"  wrote {os.path.join(DATA, f)} ({len(out)} records)")

    # 2) xG (2026 events with a shot map)
    ids = manifest["__xg_event_ids__"]
    print(f"[xg_2026.json] fetching shot maps for {len(ids)} events ...")
    xg = {}
    for i, eid in enumerate(ids, 1):
        shots = fetch_xg(eid, args.sleep)
        if shots is not None:
            xg[str(eid)] = shots
        if i % 25 == 0:
            print(f"  ... {i}/{len(ids)}")
    json.dump(xg, open(os.path.join(DATA, "xg_2026.json"), "w"))
    print(f"  wrote {os.path.join(DATA, 'xg_2026.json')} ({len(xg)} events)")

    print("\nDone. Validate with:  python fetch_sofascore.py --check")


if __name__ == "__main__":
    main()
