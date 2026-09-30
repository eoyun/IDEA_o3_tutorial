#!/usr/bin/env python3
"""physics 샘플 (Z->ee, Z->qq) Digi -> hit 단위 ntuple (event 당 한 줄, hit 은 std::vector).

이후 plot_physics_hits.py 와 reco_physics_jets.py 는 이 ntuple 만 읽는다 (podio 불필요).
한 번만 돌리면 되는 느린 단계이다.

4개 channel 의 hit 을 EM calibration constant 로 GeV 로 환산해 저장한다:
  ecal_S : SCEPCal_MainScounts               (p.e. count)  * S_crystal
  ecal_C : SCEPCal_MainCcounts               (p.e. count)  * C_crystal
  drc_S  : DRcaloSiPMreadoutDigiHit_scint    (Digi hit)    * S_fiber
  drc_C  : DRcaloSiPMreadoutDigiHit          (Digi hit)    * C_fiber
crystal ECAL 에는 digitizer 가 없어서 Sim 의 p.e. count 를 쓴다 (Digi 파일에 그대로 복사되어 있다).
hit 위치는 저장된 그대로 (ECAL: crystal 위치, DRC: fiber 앞쪽 끝).

TTree "hits" 의 branch (event 당 1 entry):
  <ch>_E, <ch>_x, <ch>_y, <ch>_z : vector<float>   (GeV, mm)
  <ch>_cellID                    : vector<ULong64_t>
  sum_<ch>                       : double          (calibrated E 의 합)
metadata (TNamed): constants, chi_fiber, chi_crystal, n_events, inputs

예)
  python3 make_physics_ntuple.py -i $TUTORIAL_SAMPLES/o3_ee_eCM91_seedfix_noOpt_Digi -o ee_ntuple.root
"""
import argparse
import json
import sys
import time
from array import array

import ROOT
from common import CHANNELS, DEFAULT_CALIB_JSON, expand_inputs, iter_events, load_calib


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--input", nargs="+", required=True, help="Digi 디렉터리 / 파일 / glob")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--calib-json", default=DEFAULT_CALIB_JSON)
    ap.add_argument("--max-events", type=int, default=None)
    args = ap.parse_args()

    files = expand_inputs(args.input, "digi")
    if not files:
        sys.exit("입력 파일이 없다")
    consts, chi = load_calib(args.calib_json)
    print(f"{len(files)} files; constants = {consts}")

    fout = ROOT.TFile(args.output, "RECREATE")
    tree = ROOT.TTree("hits", "calibrated hits: ECAL S/C, DRC S/C")
    vec = {}
    for ch in CHANNELS:
        for var in ("E", "x", "y", "z"):
            vec[f"{ch}_{var}"] = ROOT.std.vector("float")()
            tree.Branch(f"{ch}_{var}", vec[f"{ch}_{var}"])
        vec[f"{ch}_cellID"] = ROOT.std.vector("unsigned long long")()
        tree.Branch(f"{ch}_cellID", vec[f"{ch}_cellID"])
    tot = {ch: array("d", [0.0]) for ch in CHANNELS}
    for ch in CHANNELS:
        tree.Branch(f"sum_{ch}", tot[ch], f"sum_{ch}/D")

    n = 0
    t0 = time.time()
    for _, _, gidx, frame in iter_events(files, verbose=False):
        if args.max_events is not None and gidx >= args.max_events:
            break
        for ch, (coll, const) in CHANNELS.items():
            k = consts[const]
            for name in ("E", "x", "y", "z", "cellID"):
                vec[f"{ch}_{name}"].clear()
            s = 0.0
            for hit in frame.get(coll):
                e = hit.getEnergy() * k
                pos = hit.getPosition()
                vec[f"{ch}_E"].push_back(e)
                vec[f"{ch}_x"].push_back(pos.x)
                vec[f"{ch}_y"].push_back(pos.y)
                vec[f"{ch}_z"].push_back(pos.z)
                vec[f"{ch}_cellID"].push_back(hit.getCellID())
                s += e
            tot[ch][0] = s
        tree.Fill()
        n += 1
        if n % 100 == 0:
            print(f"  {n} events ({time.time() - t0:.0f} s)", flush=True)

    tree.Write()
    for key, val in (("constants", json.dumps(consts)), ("chi_fiber", repr(chi.get("chi_fiber"))),
                     ("chi_crystal", repr(chi.get("chi_crystal"))), ("n_events", str(n)),
                     ("inputs", ";".join(files))):
        ROOT.TNamed(key, val).Write()
    fout.Close()
    print(f"wrote {n} events -> {args.output} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
