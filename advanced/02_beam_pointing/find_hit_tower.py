#!/usr/bin/env python3
"""Sim 또는 Digi 파일에서 beam 이 실제로 어느 DRC tower 에 맞았는지 확인한다.

event 마다
  - 1차 입자 (MCParticles 중 generatorStatus == 1) 의 생성 위치와 방향
  - DRC S channel hit 을 tower 별로 합했을 때 가장 에너지가 큰 tower 의 (eta 번호, phi 번호)
  - DRC hit 의 에너지 가중 평균 위치의 theta, phi
를 구하고, 모든 event 에 대한 요약을 출력한다.

tower 번호는 cellID 에서 읽는다 (readout: system:5,assembly:1,eta:-8,phi:9,...).
  eta 번호: barrel 0~39 (theta = 90 deg 에서 0 번), endcap 40~74. +z 쪽은 0 이상, -z 쪽은 음수.
  phi 번호: 0~143 (2.5 deg 씩).

예)
  python3 find_hit_tower.py $TUTORIAL_OUTPUT/my_tower7_Sim/my_tower7_sim_0.root
  python3 find_hit_tower.py my_digi.root --max-events 20
"""
import argparse
import math
import sys
from collections import Counter

from podio import root_io

SIM_COLL = "DRcaloSiPMreadout_scint"
DIGI_COLL = "DRcaloSiPMreadoutDigiHit_scint"


def decode(cell_id):
    """cellID -> (eta 번호, phi 번호). eta 는 부호 있는 8 bit."""
    eta = (cell_id >> 6) & 0xFF
    if eta >= 128:
        eta -= 256
    phi = (cell_id >> 14) & 0x1FF
    return eta, phi


def primary(frame):
    for p in frame.get("MCParticles"):
        if p.getGeneratorStatus() == 1:
            v, m = p.getVertex(), p.getMomentum()
            pmag = math.sqrt(m.x ** 2 + m.y ** 2 + m.z ** 2)
            return (v.x, v.y, v.z), (m.x / pmag, m.y / pmag, m.z / pmag)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="*_sim_*.root 또는 *_digi_*.root")
    ap.add_argument("--max-events", type=int, default=None)
    ap.add_argument("-v", "--verbose", action="store_true", help="event 마다 출력")
    args = ap.parse_args()

    towers = Counter()
    frac_sum, n_evt = 0.0, 0
    th_list, ph_list = [], []
    dirs, verts = [], []
    coll = None
    for path in args.files:
        events = root_io.Reader(path).get("events")
        for frame in events:
            if args.max_events is not None and n_evt >= args.max_events:
                break
            if coll is None:
                names = set(frame.getAvailableCollections())
                coll = SIM_COLL if SIM_COLL in names else DIGI_COLL
                print(f"DRC collection: {coll}")
            prim = primary(frame)
            if prim:
                verts.append(prim[0])
                dirs.append(prim[1])
            e_tower = Counter()
            sx = sy = sz = se = 0.0
            for h in frame.get(coll):
                e = h.getEnergy()
                if e <= 0:
                    continue
                e_tower[decode(h.getCellID())] += e
                pos = h.getPosition()
                sx, sy, sz, se = sx + e * pos.x, sy + e * pos.y, sz + e * pos.z, se + e
            n_evt += 1
            if se <= 0:
                continue
            best, e_best = e_tower.most_common(1)[0]
            towers[best] += 1
            frac_sum += e_best / se
            x, y, z = sx / se, sy / se, sz / se
            th = math.degrees(math.atan2(math.hypot(x, y), z))
            ph = math.degrees(math.atan2(y, x))
            th_list.append(th)
            ph_list.append(ph)
            if args.verbose:
                print(f"  event {n_evt - 1}: tower (eta, phi) = {best}, E fraction = {e_best / se:.2f}, "
                      f"centroid theta = {th:.2f} deg, phi = {ph:.2f} deg")

    if not th_list:
        sys.exit("DRC hit 이 있는 event 가 없다")
    mean = lambda v: sum(v) / len(v)
    print(f"\n{n_evt} events")
    if dirs:
        d = [mean([v[k] for v in dirs]) for k in range(3)]
        x = [mean([v[k] for v in verts]) for k in range(3)]
        print(f"1차 입자 (평균)   : 위치 = ({x[0]:.1f}, {x[1]:.1f}, {x[2]:.1f}) mm,  "
              f"방향 = ({d[0]:.6f}, {d[1]:.6f}, {d[2]:.6f})")
        print(f"                   방향의 theta = {math.degrees(math.atan2(math.hypot(d[0], d[1]), d[2])):.3f} deg, "
              f"phi = {math.degrees(math.atan2(d[1], d[0])):.3f} deg")
    print(f"DRC hit 중심 (평균): theta = {mean(th_list):.3f} deg, phi = {mean(ph_list):.3f} deg")
    print(f"가장 에너지가 큰 tower 가 받은 비율 (평균): {frac_sum / len(th_list):.2f}")
    print("가장 에너지가 큰 tower (eta 번호, phi 번호) 와 그런 event 수:")
    for (eta, phi), cnt in towers.most_common(5):
        print(f"  eta {eta:4d}, phi {phi:4d} : {cnt} events")


if __name__ == "__main__":
    main()
