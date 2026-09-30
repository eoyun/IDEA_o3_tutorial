#!/usr/bin/env python3
"""40 GeV pi- 샘플 -> chi 계산용 flat ntuple (event 당 한 줄).

한 번만 돌리면 되는 느린 단계이고 (event loop), compute_chi.py 는 이 ntuple 만 읽어서 빠르게
여러 번 돌릴 수 있다. 입력은 Digi 파일 하나면 된다 (ECAL Sim collection 과 MCParticles 가 복사되어 있음).

각 event 에서 저장하는 것 (모두 EM calibration constant 로 GeV 로 환산):
  S_c, C_c : crystal ECAL S / C  = (SCEPCal_MainS/Ccounts p.e. 합) * S_crystal / C_crystal
  S_f, C_f : fiber DRC S / C     = (DRcaloSiPMreadoutDigiHit_scint / DigiHit 합) * S_fiber / C_fiber
  S_tot, C_tot : ECAL + DRC
  r_end, z_end : primary pi- 의 endpoint (Geant4 가 추적을 끝낸 위치 = 첫 hadronic interaction, 즉
                 hadron shower 가 시작한 위치. 아무것도 안 하고 통과하면 world 밖)
  shower_region : r_end 를 detector 반경으로 분류
        0 tracker      : r_end < 2250 mm   (ECAL 에 닿기 전에 shower 시작)
        1 crystal ECAL : 2250 <= r_end < 2500 mm
        2 solenoid gap : 2500 <= r_end < 2805 mm (crystal 바깥 ~ DRC 앞)
        3 fiber DRC    : r_end >= 2805 mm  (DRC 에서 shower 시작 = ECAL 은 MIP 로 통과)
  raw 합 (S_c_pe, C_c_pe, S_f_raw, C_f_raw): calibration 을 다시 하고 싶을 때를 위해 보관

예)
  python3 make_pion_ntuple.py -i $TUTORIAL_SAMPLES/o3_calibB_piminus_40GeV_p0_noOpt_scaleADC1_Digi \\
      -o pion_ntuple_40GeV.root
"""
import argparse
import math
import sys
from array import array

import ROOT
from common import (CHANNELS, DEFAULT_CALIB_JSON, R_DRC_INNER, R_ECAL_INNER, R_SOLENOID_INNER,
                    expand_inputs, iter_events, load_calib)


def classify_region(r_end):
    if r_end < R_ECAL_INNER:
        return 0
    if r_end < R_SOLENOID_INNER:
        return 1
    if r_end < R_DRC_INNER:
        return 2
    return 3


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--input", nargs="+", required=True, help="Digi 디렉터리 / 파일 / glob")
    ap.add_argument("-o", "--output", default="pion_ntuple.root")
    ap.add_argument("--calib-json", default=DEFAULT_CALIB_JSON, help="4개의 EM calibration constant 가 든 json")
    ap.add_argument("--max-events", type=int, default=None)
    args = ap.parse_args()

    files = expand_inputs(args.input, "digi")
    if not files:
        sys.exit("입력 파일이 없다")
    consts, _ = load_calib(args.calib_json)
    print(f"{len(files)} files; constants ({args.calib_json}): {consts}")

    fout = ROOT.TFile(args.output, "RECREATE")
    tree = ROOT.TTree("pion_dr", "Per-event calibrated S/C energies + primary pi- endpoint")
    d_names = ["S_c", "C_c", "S_f", "C_f", "S_tot", "C_tot", "S_c_pe", "C_c_pe", "S_f_raw", "C_f_raw",
               "r_end", "z_end", "primary_energy"]
    i_names = ["shower_region", "has_primary", "evt_idx"]
    buf = {n: array("d", [0.0]) for n in d_names}
    buf.update({n: array("i", [0]) for n in i_names})
    for n in d_names:
        tree.Branch(n, buf[n], f"{n}/D")
    for n in i_names:
        tree.Branch(n, buf[n], f"{n}/I")

    n_events = 0
    n_no_primary = 0
    for _, _, gidx, frame in iter_events(files):
        if args.max_events is not None and n_events >= args.max_events:
            break
        raw = {ch: sum(h.getEnergy() for h in frame.get(coll)) for ch, (coll, _) in CHANNELS.items()}
        cal = {ch: raw[ch] * consts[CHANNELS[ch][1]] for ch in CHANNELS}

        # gun 이 쏜 primary = parent 가 없는 MCParticle 하나
        primaries = [p for p in frame.get("MCParticles") if p.parents_size() == 0]
        if len(primaries) == 1:
            end = primaries[0].getEndpoint()
            r_end, z_end = math.hypot(end.x, end.y), end.z
            energy = primaries[0].getEnergy()
            region, has_primary = classify_region(r_end), 1
        else:
            n_no_primary += 1
            r_end = z_end = energy = -1.0
            region, has_primary = -1, 0

        buf["S_c"][0], buf["C_c"][0] = cal["ecal_S"], cal["ecal_C"]
        buf["S_f"][0], buf["C_f"][0] = cal["drc_S"], cal["drc_C"]
        buf["S_tot"][0] = cal["ecal_S"] + cal["drc_S"]
        buf["C_tot"][0] = cal["ecal_C"] + cal["drc_C"]
        buf["S_c_pe"][0], buf["C_c_pe"][0] = raw["ecal_S"], raw["ecal_C"]
        buf["S_f_raw"][0], buf["C_f_raw"][0] = raw["drc_S"], raw["drc_C"]
        buf["r_end"][0], buf["z_end"][0], buf["primary_energy"][0] = r_end, z_end, energy
        buf["shower_region"][0], buf["has_primary"][0], buf["evt_idx"][0] = region, has_primary, gidx
        tree.Fill()
        n_events += 1

    fout.cd()
    tree.Write()
    fout.Close()
    print(f"\n{n_events} events ({n_no_primary} without a unique primary) -> {args.output} (tree 'pion_dr')")


if __name__ == "__main__":
    main()
