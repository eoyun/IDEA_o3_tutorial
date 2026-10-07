#!/usr/bin/env python3
"""Pythia 가 쓴 HepMC3 (ascii) 파일을 읽어 decay mode 와 ISR 을 확인한다 (순수 python, 가벼움).

event 마다:
  sqrt(s_hat) = eCM * sqrt(x1 * x2)   (GenPdfInfo 의 x1, x2: ISR 이 가져가고 남은 beam 에너지 비율)
  W / Z / H (|PDG| 24/23/25) 의 decay 산물 (PDG, status)
  stable photon 수

예)
  python3 check_hepmc.py ZH_qqbb.hepmc ZH_qqbb_ISRoff.hepmc
"""
import argparse
import math
from collections import Counter

BOSONS = {23: "Z", 24: "W", 25: "H"}


def read_events(fname):
    events, cur = [], None
    for line in open(fname):
        t = line.split()
        if not t:
            continue
        if t[0] == "E":
            cur = {"parts": {}, "vtx": {}, "x": None}
            events.append(cur)
        elif cur is None:
            continue
        elif t[0] == "A" and len(t) > 6 and t[2] == "GenPdfInfo":
            cur["x"] = (float(t[5]), float(t[6]))
        elif t[0] == "P":
            pid, par, pdg = int(t[1]), int(t[2]), int(t[3])
            cur["parts"][pid] = {"par": par, "pdg": pdg, "st": int(t[9])}
        elif t[0] == "V":
            plist = t[3].strip("[]")
            cur["vtx"][int(t[1])] = [int(x) for x in plist.split(",")] if plist else []
    return events


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--ecm", type=float, default=240.0)
    args = ap.parse_args()

    for fname in args.files:
        events = read_events(fname)
        roots, nphoton = [], []
        decays = Counter()
        for ev in events:
            if ev["x"]:
                roots.append(args.ecm * math.sqrt(ev["x"][0] * ev["x"][1]))
            parts = ev["parts"]
            nphoton.append(sum(1 for p in parts.values() if p["st"] == 1 and p["pdg"] == 22))
            for p in parts.values():
                parents = [p["par"]] if p["par"] > 0 else ev["vtx"].get(p["par"], [])
                for q in parents:
                    if q in parts and abs(parts[q]["pdg"]) in BOSONS and abs(p["pdg"]) != abs(parts[q]["pdg"]):
                        decays[(BOSONS[abs(parts[q]["pdg"])], abs(p["pdg"]), p["st"])] += 1
        print(f"{fname}: {len(events)} events")
        if roots:
            rs = sorted(roots)
            below = sum(r < args.ecm - 1 for r in rs) / len(rs)
            print(f"  sqrt(s_hat) [GeV]: min {rs[0]:.2f}, median {rs[len(rs) // 2]:.2f}, max {rs[-1]:.2f}, "
                  f"fraction < {args.ecm - 1:.0f} GeV = {below:.2f}")
        print(f"  stable photons / event: mean {sum(nphoton) / max(len(nphoton), 1):.1f}")
        print("  boson decay products (boson, |PDG|, status): count")
        for key, n in sorted(decays.items()):
            print(f"    {key}: {n}")


if __name__ == "__main__":
    main()
