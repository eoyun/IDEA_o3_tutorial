#!/usr/bin/env python3
"""입사 위치 (p0~p3, theta 89.44 / 66.94 / 44.44 / 25.31 deg) 에 따른 EM response.

각 점에서 40 GeV e- 의 calibration 후 S, C 에너지 평균 / beam energy 를 theta 의 함수로 그린다.
calibration constant 는 p0 에서만 구하므로 p0 의 response 는 정의상 1 이고, p1~p3 가 1 에서
얼마나 벗어나는지가 detector 의 theta 방향 균일성이다.

  --detector ecal : full geometry 샘플 4개 (p0 p1 p2 p3), S_crystal / C_crystal 적용
                    예) $TUTORIAL_SAMPLES/o3_res_eminus_40GeV_p{0,1,2,3}_noOpt_Digi
  --detector drc  : DRC-only geometry 샘플 4개, S_fiber / C_fiber 적용
                    예) $TUTORIAL_SAMPLES/o3_calibB_drc_eminus_40GeV_p{0,1,2,3}_noOpt_scaleADC1_Digi

입력 디렉터리는 p0 p1 p2 p3 순서로 준다. 출력: graph (S, C) 와 TCanvas 가 든 ROOT 파일.

예)
  python3 response_vs_theta.py --detector ecal -o response_ecal.root -i \\
      $TUTORIAL_SAMPLES/o3_res_eminus_40GeV_p0_noOpt_Digi $TUTORIAL_SAMPLES/o3_res_eminus_40GeV_p1_noOpt_Digi \\
      $TUTORIAL_SAMPLES/o3_res_eminus_40GeV_p2_noOpt_Digi $TUTORIAL_SAMPLES/o3_res_eminus_40GeV_p3_noOpt_Digi
"""
import argparse
import math
import sys

import ROOT
from common import (CHANNELS, DEFAULT_CALIB_JSON, THETA_DEG, expand_inputs, iter_events,
                    load_calib)

POINTS = ("p0", "p1", "p2", "p3")


def make_graph(name, title, thetas, values, errors, color):
    g = ROOT.TGraphErrors(len(thetas))
    for i, (t, v, e) in enumerate(zip(thetas, values, errors)):
        g.SetPoint(i, t, v)
        g.SetPointError(i, 0.0, e)
    g.SetNameTitle(name, title)
    g.SetMarkerStyle(20)
    g.SetMarkerSize(1.2)
    g.SetMarkerColor(color)
    g.SetLineColor(color)
    g.SetLineWidth(2)
    return g


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--inputs", nargs=4, required=True, metavar=("P0", "P1", "P2", "P3"),
                    help="p0 p1 p2 p3 순서의 Digi 디렉터리")
    ap.add_argument("--detector", choices=("ecal", "drc"), required=True)
    ap.add_argument("--calib-json", default=DEFAULT_CALIB_JSON, help="calibration constant 가 든 json")
    ap.add_argument("--energy", type=float, default=40.0)
    ap.add_argument("-o", "--output", default="response_vs_theta.root")
    ap.add_argument("--max-events", type=int, default=None, help="점 하나당 최대 event 수")
    args = ap.parse_args()

    consts, _ = load_calib(args.calib_json)
    prefix = args.detector
    coll_s, const_s = CHANNELS[f"{prefix}_S"]
    coll_c, const_c = CHANNELS[f"{prefix}_C"]
    k_s, k_c = consts[const_s], consts[const_c]
    print(f"{const_s} = {k_s:.6e}   {const_c} = {k_c:.6e}   ({args.calib_json})")

    thetas = [THETA_DEG[p] for p in POINTS]
    resp = {"S": [], "C": []}
    err = {"S": [], "C": []}
    for point, path in zip(POINTS, args.inputs):
        files = expand_inputs([path], "digi")
        vals = {"S": [], "C": []}
        for _, _, _, frame in iter_events(files, verbose=False):
            if args.max_events is not None and len(vals["S"]) >= args.max_events:
                break
            vals["S"].append(sum(h.getEnergy() for h in frame.get(coll_s)) * k_s / args.energy)
            vals["C"].append(sum(h.getEnergy() for h in frame.get(coll_c)) * k_c / args.energy)
        n = len(vals["S"])
        line = f"{point} (theta={THETA_DEG[point]:.2f} deg, {n} events):"
        for ch in ("S", "C"):
            mean = sum(vals[ch]) / n
            rms = math.sqrt(sum((v - mean) ** 2 for v in vals[ch]) / (n - 1))
            resp[ch].append(mean)
            err[ch].append(rms / math.sqrt(n))
            line += f"   {ch} response = {mean:.4f} +- {rms / math.sqrt(n):.4f}"
        print(line)

    out = ROOT.TFile(args.output, "RECREATE")
    ROOT.gStyle.SetOptStat(0)
    gs = make_graph("g_response_S", "S channel;#theta [deg];<E_{S}>/E_{beam}", thetas, resp["S"], err["S"], ROOT.kRed)
    gc = make_graph("g_response_C", "C channel;#theta [deg];<E_{C}>/E_{beam}", thetas, resp["C"], err["C"], ROOT.kBlue)
    mg = ROOT.TMultiGraph("mg_response", f"{prefix.upper()} response vs #theta (40 GeV e-);#theta [deg];<E>/E_{{beam}}")
    mg.Add(gs, "P")
    mg.Add(gc, "P")
    canvas = ROOT.TCanvas("c_response_vs_theta", f"{prefix.upper()} response vs theta", 900, 650)
    canvas.SetGrid()
    mg.Draw("A")
    lo = min(min(resp["S"]), min(resp["C"]))
    hi = max(max(resp["S"]), max(resp["C"]))
    mg.GetYaxis().SetRangeUser(min(lo, 1.0) - 0.05, max(hi, 1.0) + 0.05)
    leg = ROOT.TLegend(0.65, 0.75, 0.88, 0.88)
    leg.AddEntry(gs, "S channel", "lp")
    leg.AddEntry(gc, "C channel", "lp")
    leg.Draw()
    canvas.Update()
    canvas.Write()
    gs.Write()
    gc.Write()
    mg.Write()
    out.Close()
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
