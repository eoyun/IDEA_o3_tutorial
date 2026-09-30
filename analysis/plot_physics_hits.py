#!/usr/bin/env python3
"""physics 샘플 (Z->ee / Z->qq) ntuple (make_physics_ntuple.py) -> hit 수준 분석. 출력은 ROOT 파일 하나.

1) hit 4-vector 합
   각 hit 을 massless 4-vector  (E, E*r_hat)  로 보고 (r_hat = 원점 -> hit 위치 방향), event 마다 합한다.
     region  : ECAL (crystal), DRC (fiber), Total (= ECAL + DRC)
     channel : S, C, DR   (DR: P_DR = (P_S - chi*P_C)/(1-chi), ECAL 은 chi_crystal, DRC 는 chi_fiber,
                           Total = ECAL_DR + DRC_DR)
   histogram:  h_E_<region>_<ch>  (합 4-vector 의 E),   h_M_<region>_<ch>  (합 4-vector 의 invariant mass)
   Z 가 정지해 있다면 M 이 Z mass (91.19 GeV) 근처에서 peak 를 가져야 한다.
   Total 의 E, M 은 Gaussian fit (2-pass) 결과를 터미널에 출력한다.
2) hit 분포: 에너지, event 당 hit 수, z-r 위치        h_hitE_<ch>, h_nhit_<ch>, h2_zr_<ch>
3) eta-phi map (S / C, ECAL / DRC): 모든 event 를 합친 것과 한 event (--event N)   h2_etaphi_<ch>, h2_evt_etaphi_<ch>
   <ch> = ecal_S, ecal_C, drc_S, drc_C.  2D map 의 z 값은 hit energy [GeV] 의 합.

TCanvas 도 같은 ROOT 파일에 들어간다 (PNG 는 만들지 않는다):  root -l out.root  ->  new TBrowser

예)
  python3 plot_physics_hits.py ee_ntuple.root -o ee_hits.root
  python3 plot_physics_hits.py qq_ntuple.root -o qq_hits.root --event 5
"""
import argparse
import math
import sys

import numpy as np
import ROOT
from common import gauss_fit

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kError
ROOT.gStyle.SetOptStat(0)
ROOT.TH1.AddDirectory(False)

CH = ("ecal_S", "ecal_C", "drc_S", "drc_C")
REGIONS = ("ECAL", "DRC", "Total")
KINDS = ("S", "C", "DR")
COLORS = {"S": ROOT.kRed + 1, "C": ROOT.kBlue + 1, "DR": ROOT.kBlack}
NB = 300


def vec_np(v, dtype=np.float32):
    n = int(v.size())
    return np.frombuffer(v.data(), dtype=dtype, count=n).astype(np.float64) if n else np.zeros(0)


def four_vector(e, x, y, z):
    """[E, px, py, pz] of the sum of massless hit vectors."""
    if e.size == 0:
        return np.zeros(4)
    r = np.sqrt(x * x + y * y + z * z)
    r[r == 0] = 1.0
    return np.array([e.sum(), (e * x / r).sum(), (e * y / r).sum(), (e * z / r).sum()])


def inv_mass(p):
    m2 = p[0] ** 2 - p[1] ** 2 - p[2] ** 2 - p[3] ** 2
    return math.copysign(math.sqrt(abs(m2)), m2)


def fill(h, values, weights=None):
    if len(values) == 0:
        return
    v = np.ascontiguousarray(values, dtype=np.float64)
    if weights is None:
        h.FillN(len(v), v, np.ones(len(v)))
    else:
        h.FillN(len(v), v, np.ascontiguousarray(weights, dtype=np.float64))


def fill2(h, x, y, w):
    if len(x) == 0:
        return
    h.FillN(len(x), np.ascontiguousarray(x, dtype=np.float64), np.ascontiguousarray(y, dtype=np.float64),
            np.ascontiguousarray(w, dtype=np.float64))


def eta_phi(x, y, z):
    return np.arcsinh(z / np.maximum(np.hypot(x, y), 1e-9)), np.arctan2(y, x)


def overlay(pad, hists, labels, colors, title, logy=False):
    pad.cd()
    pad.SetGrid()
    pad.SetLogy(logy)
    ymax = max(h.GetMaximum() for h in hists)
    leg = ROOT.TLegend(0.55, 0.68, 0.88, 0.88)
    leg.SetBorderSize(0)
    for k, (h, lab, col) in enumerate(zip(hists, labels, colors)):
        h.SetLineColor(col)
        h.SetLineWidth(2)
        h.SetTitle(title)
        h.SetMaximum(ymax * (5 if logy else 1.3))
        if logy:
            h.SetMinimum(0.5)
        h.Draw("hist" if k == 0 else "hist same")
        leg.AddEntry(h, lab, "l")
    leg.Draw()
    return leg


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ntuple")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--ecm", type=float, default=91.0, help="centre-of-mass energy [GeV] (histogram 범위)")
    ap.add_argument("--event", type=int, default=0, help="한 event 용 eta-phi map 을 그릴 event 번호")
    ap.add_argument("--chi-fiber", type=float, default=None)
    ap.add_argument("--chi-crystal", type=float, default=None)
    ap.add_argument("--max-events", type=int, default=None)
    args = ap.parse_args()

    fin = ROOT.TFile.Open(args.ntuple)
    tree = fin.Get("hits")
    if not tree:
        sys.exit(f"{args.ntuple}: TTree 'hits' 없음 (make_physics_ntuple.py 의 출력이 아니다)")
    chi_f = args.chi_fiber if args.chi_fiber is not None else float(fin.Get("chi_fiber").GetTitle())
    chi_c = args.chi_crystal if args.chi_crystal is not None else float(fin.Get("chi_crystal").GetTitle())
    nent = tree.GetEntries() if args.max_events is None else min(args.max_events, tree.GetEntries())
    print(f"{args.ntuple}: {nent} events, chi_fiber = {chi_f:.5f}, chi_crystal = {chi_c:.5f}")

    ecm = args.ecm
    lo, hi = -0.2 * ecm, 1.5 * ecm
    h = {}
    for reg in REGIONS:
        for k in KINDS:
            h[f"h_E_{reg}_{k}"] = ROOT.TH1D(f"h_E_{reg}_{k}", f"E of hit 4-vector sum, {reg} {k};E [GeV];Events", NB, lo, hi)
            h[f"h_M_{reg}_{k}"] = ROOT.TH1D(f"h_M_{reg}_{k}", f"mass of hit 4-vector sum, {reg} {k};M [GeV];Events", NB, lo, hi)
    for ch in CH:
        h[f"h_hitE_{ch}"] = ROOT.TH1D(f"h_hitE_{ch}", f"hit energy {ch};E_{{hit}} [GeV];Hits", 200, 0, 20)
        h[f"h_nhit_{ch}"] = ROOT.TH1D(f"h_nhit_{ch}", f"hits per event {ch};N_{{hit}};Events", 200, 0, 1)
        h[f"h2_zr_{ch}"] = ROOT.TH2D(f"h2_zr_{ch}", f"{ch};z [mm];r [mm];#SigmaE [GeV]", 200, -4000, 4000, 120, 0, 3600)
        h[f"h2_etaphi_{ch}"] = ROOT.TH2D(f"h2_etaphi_{ch}", f"{ch}, all events;#eta;#phi;#SigmaE [GeV]",
                                         120, -3, 3, 72, -math.pi, math.pi)
        h[f"h2_evt_etaphi_{ch}"] = ROOT.TH2D(f"h2_evt_etaphi_{ch}", f"{ch}, event {args.event};#eta;#phi;E [GeV]",
                                             120, -3, 3, 72, -math.pi, math.pi)

    nhits = {ch: [] for ch in CH}
    for i in range(nent):
        tree.GetEntry(i)
        p4, data = {}, {}
        for ch in CH:
            e, x, y, z = (vec_np(getattr(tree, f"{ch}_{v}")) for v in "Exyz")
            data[ch] = (e, x, y, z)
            p4[ch] = four_vector(e, x, y, z)
            pos = e > 0
            fill(h[f"h_hitE_{ch}"], e[pos])
            nhits[ch].append(int(pos.sum()))
            fill2(h[f"h2_zr_{ch}"], z, np.hypot(x, y), e)
            eta, phi = eta_phi(x, y, z)
            fill2(h[f"h2_etaphi_{ch}"], eta, phi, e)
            if i == args.event:
                fill2(h[f"h2_evt_etaphi_{ch}"], eta, phi, e)
        s = {"ECAL": p4["ecal_S"], "DRC": p4["drc_S"]}
        c = {"ECAL": p4["ecal_C"], "DRC": p4["drc_C"]}
        dr = {"ECAL": (s["ECAL"] - chi_c * c["ECAL"]) / (1 - chi_c), "DRC": (s["DRC"] - chi_f * c["DRC"]) / (1 - chi_f)}
        s["Total"], c["Total"] = s["ECAL"] + s["DRC"], c["ECAL"] + c["DRC"]
        dr["Total"] = dr["ECAL"] + dr["DRC"]
        for reg in REGIONS:
            for k, p in (("S", s[reg]), ("C", c[reg]), ("DR", dr[reg])):
                h[f"h_E_{reg}_{k}"].Fill(p[0])
                h[f"h_M_{reg}_{k}"].Fill(inv_mass(p))
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{nent} events", flush=True)

    for ch in CH:
        nmax = max(nhits[ch]) if nhits[ch] else 1
        hn = h[f"h_nhit_{ch}"]
        hn.SetBins(200, 0, nmax * 1.05 + 1)
        fill(hn, nhits[ch])

    print(f"\n{'Total 4-vector sum':<22}{'entries':>8}{'hist mean':>11}{'fit mean':>10}{'fit sigma':>10}{'sigma/mean':>11}")
    for var in ("E", "M"):
        for k in KINDS:
            hist = h[f"h_{var}_Total_{k}"]
            fit = gauss_fit(hist)
            label = f"{var} Total {k}"
            if fit:
                print(f"{label:<22}{int(hist.GetEntries()):>8}{hist.GetMean():>11.2f}{fit[0]:>10.2f}{fit[1]:>10.2f}{fit[1] / fit[0]:>11.3f}")
            else:
                print(f"{label:<22}{int(hist.GetEntries()):>8}{hist.GetMean():>11.2f}   fit 실패")
    for name in ("h_E_Total_DR", "h_M_Total_DR"):
        hist = h[name]
        print(f"  {name}: underflow = {hist.GetBinContent(0):.0f}, overflow = {hist.GetBinContent(NB + 1):.0f}")

    fout = ROOT.TFile(args.output, "RECREATE")
    for hist in h.values():
        hist.Write()

    keep = []
    for var, long_name in (("E", "E of hit 4-vector sum"), ("M", "invariant mass of hit 4-vector sum")):
        c = ROOT.TCanvas(f"c_{var}_4vec", long_name, 1500, 500)
        c.Divide(3, 1)
        for n, reg in enumerate(REGIONS, 1):
            keep.append(overlay(c.cd(n), [h[f"h_{var}_{reg}_{k}"] for k in KINDS], KINDS,
                                [COLORS[k] for k in KINDS], f"{reg}: {long_name}"))
        c.Write()
        keep.append(c)

    cz = ROOT.TCanvas("c_Zpeak", "Total DR 4-vector mass (Gaussian fit)", 900, 700)
    cz.SetGrid()
    hz = h["h_M_Total_DR"]
    hz.SetTitle("Total DR: mass of hit 4-vector sum;M [GeV];Events")
    hz.SetLineColor(ROOT.kBlack)
    hz.Draw("hist")
    fn = hz.GetFunction("gaus")
    if fn:
        fn.SetLineColor(ROOT.kRed)
        fn.Draw("same")
        txt = ROOT.TLatex(0.15, 0.82, f"fit: mean = {fn.GetParameter(1):.2f} GeV, #sigma = {fn.GetParameter(2):.2f} GeV")
        txt.SetNDC()
        txt.Draw()
        keep.append(txt)
    cz.Write()
    keep.append(cz)

    for name, title, key, logy in (("c_hitE", "hit energy", "h_hitE_{}", True), ("c_nhit", "hits per event", "h_nhit_{}", False)):
        c = ROOT.TCanvas(name, title, 1200, 900)
        c.Divide(2, 2)
        for n, ch in enumerate(CH, 1):
            c.cd(n).SetGrid()
            c.cd(n).SetLogy(logy)
            hist = h[key.format(ch)]
            hist.SetLineWidth(2)
            hist.Draw("hist")
        c.Write()
        keep.append(c)
    for name, title, key in (("c_zr", "hit positions (z-r, weight E)", "h2_zr_{}"),
                             ("c_etaphi_all", "eta-phi map, all events", "h2_etaphi_{}"),
                             ("c_etaphi_event", f"eta-phi map, event {args.event}", "h2_evt_etaphi_{}")):
        c = ROOT.TCanvas(name, title, 1200, 900)
        c.Divide(2, 2)
        for n, ch in enumerate(CH, 1):
            c.cd(n).SetLogz()
            c.cd(n).SetRightMargin(0.15)
            h[key.format(ch)].Draw("colz")
        c.Write()
        keep.append(c)

    fout.Close()
    print(f"\nwrote {args.output}")


if __name__ == "__main__":
    main()
