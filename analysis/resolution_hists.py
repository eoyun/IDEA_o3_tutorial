#!/usr/bin/env python3
"""beam energy 하나의 Digi 샘플 -> 에너지 분포 histogram 9개 (EM / hadron 공용).

  {ECAL, DRC, Total} x {S, C, DR}   ->  h_ECAL_S, h_ECAL_C, h_ECAL_DR, h_DRC_S, ... h_Total_DR
  ECAL = crystal (SCEPCal),  DRC = fiber,  Total = ECAL + DRC

  S, C : (raw sum) * calibration constant  [GeV]      (constants: --calib-json 의 "constants")
  DR   : E_DR = (S - chi*C) / (1 - chi)               (chi: --calib-json 의 "chi")
         ECAL_DR  = (S_c - chi_crystal*C_c) / (1 - chi_crystal)
         DRC_DR   = (S_f - chi_fiber*C_f)   / (1 - chi_fiber)
         Total_DR = ECAL_DR + DRC_DR

9개 모두 Gaussian fit (2-pass) 을 하고 fit 함수는 histogram 에 붙어서 저장된다.
EM 이면 S/C 의 Gaussian mean, sigma 를 그대로 쓰고, hadron 이면 S/C 는 Gaussian 이 아니므로
histogram mean / RMS 를 쓰는 것이 관례다 (draw_resolution.py 가 알아서 고른다).
chi 는 hadron 용 값이라 EM 샘플의 ECAL_DR / Total_DR 은 의미가 없다 (그려지지만 쓰지 않는다).

예)
  python3 resolution_hists.py -i $TUTORIAL_SAMPLES/o3_res_eminus_40GeV_p0_noOpt_Digi -o em_40GeV.root
  python3 resolution_hists.py -i $TUTORIAL_SAMPLES/o3_res_piminus_40GeV_p0_noOpt_Digi -o had_40GeV.root
"""
import argparse
import sys

import ROOT
from common import (CHANNELS, DEFAULT_CALIB_JSON, dr_energy, expand_inputs, gauss_fit, guess_beam_energy,
                    iter_events, load_calib, make_hist)

REGIONS = ("ECAL", "DRC", "Total")
KINDS = ("S", "C", "DR")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--input", nargs="+", required=True, help="Digi 디렉터리 / 파일 / glob")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--calib-json", default=DEFAULT_CALIB_JSON)
    ap.add_argument("--energy", type=float, default=None, help="beam energy [GeV] (없으면 경로에서 추정)")
    ap.add_argument("--chi-fiber", type=float, default=None, help="json 의 chi_fiber 를 덮어쓴다")
    ap.add_argument("--chi-crystal", type=float, default=None, help="json 의 chi_crystal 을 덮어쓴다")
    ap.add_argument("--nbins", type=int, default=200, help="histogram bin 수 (Gaussian fit 은 bin 폭에 조금 의존한다)")
    ap.add_argument("--max-events", type=int, default=None)
    args = ap.parse_args()

    files = expand_inputs(args.input, "digi")
    if not files:
        sys.exit("입력 파일이 없다")
    consts, chi = load_calib(args.calib_json)
    chi_f = args.chi_fiber if args.chi_fiber is not None else chi.get("chi_fiber")
    chi_c = args.chi_crystal if args.chi_crystal is not None else chi.get("chi_crystal")
    if chi_f is None or chi_c is None:
        sys.exit("chi_fiber / chi_crystal 이 없다: compute_chi.py 를 먼저 돌리거나 --chi-fiber/--chi-crystal 을 줄 것")
    energy = args.energy or guess_beam_energy(files)
    print(f"{len(files)} files, beam energy = {energy} GeV, chi_fiber = {chi_f:.5f}, chi_crystal = {chi_c:.5f}")

    values = {(r, k): [] for r in REGIONS for k in KINDS}
    for _, _, gidx, frame in iter_events(files):
        if args.max_events is not None and gidx >= args.max_events:
            break
        cal = {ch: sum(h.getEnergy() for h in frame.get(coll)) * consts[const]
               for ch, (coll, const) in CHANNELS.items()}
        s_c, c_c, s_f, c_f = cal["ecal_S"], cal["ecal_C"], cal["drc_S"], cal["drc_C"]
        dr_c, dr_f = dr_energy(s_c, c_c, chi_c), dr_energy(s_f, c_f, chi_f)
        for region, (s, c, dr) in (("ECAL", (s_c, c_c, dr_c)), ("DRC", (s_f, c_f, dr_f)),
                                    ("Total", (s_c + s_f, c_c + c_f, dr_c + dr_f))):
            values[(region, "S")].append(s)
            values[(region, "C")].append(c)
            values[(region, "DR")].append(dr)

    n = len(values[("ECAL", "S")])
    if n == 0:
        sys.exit("event 가 하나도 없다")
    print(f"\n{n} events\n")

    fout = ROOT.TFile(args.output, "RECREATE")
    print(f"{'hist':<11}{'gauss mean':>12}{'gauss sigma':>13}{'sigma/mean':>12}{'hist mean':>11}{'hist RMS':>10}")
    for region in REGIONS:
        for kind in KINDS:
            name = f"h_{region}_{kind}"
            h = make_hist(name, f"{region} {kind};E [GeV];Events", values[(region, kind)], nbins=args.nbins)
            fit = gauss_fit(h)
            if fit:
                mean, sigma = fit[0], fit[1]
                print(f"{name:<11}{mean:12.3f}{sigma:13.3f}{sigma / mean:12.4f}{h.GetMean():11.3f}{h.GetRMS():10.3f}")
            else:
                print(f"{name:<11}  fit 실패")
            h.Write()
    for key, val in (("beam_energy_gev", energy), ("n_events", n), ("chi_fiber", chi_f), ("chi_crystal", chi_c)):
        ROOT.TNamed(key, str(val)).Write()
    fout.Close()
    print(f"\nwrote {args.output}")


if __name__ == "__main__":
    main()
