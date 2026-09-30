#!/usr/bin/env python3
"""EM calibration: 40 GeV e- 샘플에서 S / C channel 의 calibration constant 를 구한다.

    (raw sum) * constant = beam energy [GeV]        <- mean 기준 (평균이 beam energy 가 되도록)

  --detector ecal : SCEPCal (crystal ECAL) S/C  ->  S_crystal, C_crystal
                    raw = SCEPCal_MainScounts / SCEPCal_MainCcounts 의 photo-electron 수 합
                    입력: full geometry e- 샘플, 예) o3_res_eminus_40GeV_p0_noOpt_Digi
  --detector drc  : fiber DRC S/C  ->  S_fiber, C_fiber
                    raw = DRcaloSiPMreadoutDigiHit_scint / DRcaloSiPMreadoutDigiHit 의 hit energy 합
                    입력: DRC-only geometry e- 샘플, 예) o3_calibB_drc_eminus_40GeV_p0_noOpt_scaleADC1_Digi
                    (full geometry 에서는 전자가 ECAL 에서 다 멈춰서 DRC 신호가 거의 없다)

Digi 파일에는 Sim 의 SCEPCal collection 이 그대로 들어 있으므로 입력은 Digi 파일 하나면 된다.

출력:
  ROOT 파일 : raw 합 / calibration 후 에너지 histogram + TCanvas
  터미널    : mean, RMS, 각 constant
  json      : --json 파일의 "constants" 항목을 갱신 (다른 항목은 유지). ecal 과 drc 를 같은 json
              에 차례로 넣으면 4개 constant 가 모두 채워진다.

예)
  python3 em_calib.py -i $TUTORIAL_SAMPLES/o3_res_eminus_40GeV_p0_noOpt_Digi --detector ecal \\
      -o em_calib_ecal.root --json my_calib_constants.json
  python3 em_calib.py -i $TUTORIAL_SAMPLES/o3_calibB_drc_eminus_40GeV_p0_noOpt_scaleADC1_Digi --detector drc \\
      -o em_calib_drc.root --json my_calib_constants.json
"""
import argparse
import math
import sys

import ROOT
from common import (CHANNELS, expand_inputs, guess_beam_energy, iter_events, make_hist,
                    merge_json)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--input", nargs="+", required=True, help="Digi 디렉터리 / 파일 / glob")
    ap.add_argument("--detector", choices=("ecal", "drc"), required=True)
    ap.add_argument("--energy", type=float, default=None, help="beam energy [GeV] (기본: 경로에서 추정)")
    ap.add_argument("-o", "--output", default="em_calib.root")
    ap.add_argument("--json", default="my_calib_constants.json", help="constant 를 기록할 json")
    ap.add_argument("--max-events", type=int, default=None)
    args = ap.parse_args()

    files = expand_inputs(args.input, "digi")
    if not files:
        sys.exit("입력 파일이 없다")
    energy = args.energy or guess_beam_energy(files) or 40.0
    print(f"{len(files)} files, beam energy = {energy} GeV, detector = {args.detector}")

    prefix = "ecal" if args.detector == "ecal" else "drc"
    chan_s, chan_c = f"{prefix}_S", f"{prefix}_C"
    coll_s, const_s = CHANNELS[chan_s]
    coll_c, const_c = CHANNELS[chan_c]

    raw_s, raw_c = [], []
    for _, _, _, frame in iter_events(files):
        if args.max_events is not None and len(raw_s) >= args.max_events:
            break
        raw_s.append(sum(h.getEnergy() for h in frame.get(coll_s)))
        raw_c.append(sum(h.getEnergy() for h in frame.get(coll_c)))
    n = len(raw_s)
    if n == 0:
        sys.exit("event 가 없다")

    unit = "p.e." if args.detector == "ecal" else "raw digi sum"
    hs = make_hist(f"h_{chan_s}_raw", f"{prefix.upper()} S channel raw sum;raw sum [{unit}];Events", raw_s)
    hc = make_hist(f"h_{chan_c}_raw", f"{prefix.upper()} C channel raw sum;raw sum [{unit}];Events", raw_c)

    result = {}
    cal_hists = []
    print(f"\n{n} events")
    for name, chan, raw, hist, const_name in (("S", chan_s, raw_s, hs, const_s), ("C", chan_c, raw_c, hc, const_c)):
        mean = sum(raw) / n
        rms = math.sqrt(sum((v - mean) ** 2 for v in raw) / (n - 1))
        sem = rms / math.sqrt(n)
        const = energy / mean
        const_err = const * sem / mean
        print(f"  {chan}: mean = {mean:.6g} +- {sem:.3g} [{unit}]  RMS = {rms:.4g}"
              f"   ->  {const_name} = {energy:g} / mean = {const:.6e} +- {const_err:.2e}")
        result[const_name] = {
            "value": const, "sem": const_err, "raw_signal_mean": mean, "raw_signal_sem": sem,
            "raw_signal_units": unit, "n_events": n, "beam_energy_gev": energy,
            "source": ";".join(files[:1]) + (" ..." if len(files) > 1 else ""),
        }
        cal = make_hist(f"h_{chan}_calibrated", f"{chan} calibrated energy;E [GeV];Events",
                        [v * const for v in raw])
        cal_hists.append(cal)

    out = ROOT.TFile(args.output, "RECREATE")
    canvas = ROOT.TCanvas("c_em_calib", f"EM calibration ({args.detector})", 1200, 800)
    canvas.Divide(2, 2)
    for pad, h in enumerate([hs, hc] + cal_hists, start=1):
        canvas.cd(pad)
        h.Draw("hist")
    canvas.Write()
    for h in [hs, hc] + cal_hists:
        h.Write()
    out.Close()

    merge_json(args.json, "constants", result)
    print(f"\nwrote {args.output}, updated 'constants' in {args.json}")


if __name__ == "__main__":
    main()
