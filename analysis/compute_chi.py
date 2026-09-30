#!/usr/bin/env python3
"""Dual-readout 보정 상수 chi 계산 (fiber DRC, crystal ECAL).

    E_DR = (S - chi * C) / (1 - chi)

hadron shower 에서는 shower 마다 electromagnetic fraction (f_em) 이 크게 달라서 S 와 C 가 모두
beam energy 보다 작고 event 마다 요동친다. chi 는 이 요동이 상쇄되도록 정하는 상수이다.
같은 beam energy E 의 여러 event 에서  <S> = E (f_em + (1-f_em)/e_h ...)  꼴이므로,
평균값만으로  chi = (1 - <S>/E) / (1 - <C>/E)  가 나온다.

입력: make_pion_ntuple.py 가 만든 ntuple (40 GeV pi-)

계산 순서
  1) cut 전 (모든 event) 의 S_c, C_c, S_f, C_f, S_tot, C_tot 분포 와 shower start 위치 (r_end)
  2) chi_fiber 를 "ECAL 을 MIP 로 통과해 DRC 에서 shower 가 시작한 event" 만 골라서 계산.
     ECAL 에서 에너지를 거의 잃지 않은 event 만 봐야 fiber 만의 chi 를 깨끗하게 구할 수 있다.
       - truth 선택 [채택]  : primary pi- 의 endpoint (= shower 시작) 가 DRC 안 (shower_region == 3)
       - MIP-cut 선택 [비교]: crystal S 에너지 S_c < --mip-cut (실제 실험에서 쓸 수 있는 선택)
     각 선택의 cut 후 분포를 저장하고 chi_fiber 를 비교한다.
  3) 채택한 chi_fiber 로 fiber 의 E_DR,fiber = (S_f - chi_f C_f)/(1 - chi_f) 를 만든다.
  4) chi_crystal 은 모든 event 에서: crystal 이 받은 나머지 에너지 E' = E - <E_DR,fiber> 를 써서
        chi_crystal = (1 - <S_c>/E') / (1 - <C_c>/E')
     주의: E' 가 <S_c> 와 비슷한 크기라 chi_crystal 은 E' 의 작은 변화에 민감하다 (아래 출력의
     sensitivity 참고). 대신 "total E_DR 의 RMS 가 최소가 되는 chi" 를 scan 한 값도 같이 계산한다.
  5) total E_DR = E_DR,fiber + E_DR,crystal (모든 event) 분포와 Gaussian fit.

출력: ROOT 파일 (histogram + TCanvas), 터미널 요약, --json 의 "chi" 항목 갱신

예)
  python3 compute_chi.py pion_ntuple_40GeV.root -o chi_40GeV.root --json my_calib_constants.json
"""
import argparse
import math
import sys

import numpy as np
import ROOT
from common import (R_DRC_INNER, R_ECAL_INNER, R_SOLENOID_INNER, gauss_fit, merge_json)

REGION_NAMES = {-1: "no primary", 0: "tracker", 1: "crystal ECAL", 2: "solenoid gap", 3: "fiber DRC"}


def th1(name, title, values, nbins=200, lo=None, hi=None, pad=0.05):
    """numpy 배열 -> TH1D. 범위를 안 주면 데이터 범위 (overflow 로 event 를 잃지 않도록)."""
    if lo is None:
        lo, hi = float(values.min()), float(values.max())
        span = max(hi - lo, 1e-9)
        lo, hi = lo - pad * span, hi + pad * span
    h = ROOT.TH1D(name, title, nbins, lo, hi)
    h.Sumw2()
    if len(values):
        h.FillN(len(values), np.ascontiguousarray(values, dtype=np.float64), np.ones(len(values)))
    return h


def chi_from_means(mean_s, mean_c, energy):
    return (1.0 - mean_s / energy) / (1.0 - mean_c / energy)


def dr(s, c, chi):
    return (s - chi * c) / (1.0 - chi)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ntuple")
    ap.add_argument("--beam-energy", type=float, default=40.0)
    ap.add_argument("--mip-cut", type=float, default=0.5,
                    help="MIP-cut 선택: S_c < 이 값 [GeV] (기본 0.5; MIP peak 는 S_c ~ 0.25 GeV)")
    ap.add_argument("-o", "--output", default="compute_chi.root")
    ap.add_argument("--json", default="my_calib_constants.json", help="'chi' 항목을 기록할 json")
    args = ap.parse_args()
    E = args.beam_energy

    df = ROOT.RDataFrame("pion_dr", args.ntuple)
    cols = ["S_c", "C_c", "S_f", "C_f", "S_tot", "C_tot", "r_end", "z_end", "shower_region"]
    a = {k: np.array(v) for k, v in df.AsNumpy(cols).items()}
    n_all = len(a["S_c"])
    print(f"{args.ntuple}: {n_all} events, beam energy {E:g} GeV\n")

    out = ROOT.TFile(args.output, "RECREATE")
    ROOT.gStyle.SetOptStat(1110)
    hists = []

    # ---------------------------------------------------------------- 1) cut 전
    print("=== 1) cut 전 (모든 event) ===")
    hall = {}
    for key, title in (("S_c", "Crystal S"), ("C_c", "Crystal C"), ("S_f", "Fiber S"), ("C_f", "Fiber C"),
                       ("S_tot", "Total S (ECAL+DRC)"), ("C_tot", "Total C (ECAL+DRC)")):
        hall[key] = th1(f"h_{key}_all", f"{title}, all events;E [GeV];Events", a[key], lo=0.0, hi=E * 1.2)
        print(f"  {key:6s}: mean = {a[key].mean():8.4f}  RMS = {a[key].std(ddof=1):8.4f} GeV")
    h_sc_zoom = th1("h_S_c_zoom", "Crystal S, MIP peak zoom;S_{c} [GeV];Events", a["S_c"], nbins=150, lo=0.0, hi=3.0)
    h2 = ROOT.TH2D("h2_Sc_vs_Sf", "Crystal S vs fiber S;S_{c} [GeV];S_{f} [GeV]", 100, 0, E * 1.1, 100, 0, E * 1.1)
    for x, y in zip(a["S_c"], a["S_f"]):
        h2.Fill(x, y)
    print("\n  shower start (primary pi- endpoint 반경) 분류:")
    for reg in (-1, 0, 1, 2, 3):
        n = int((a["shower_region"] == reg).sum())
        print(f"    {reg:2d} {REGION_NAMES[reg]:13s}: {n:5d}  ({100.0 * n / n_all:5.1f}%)")

    # shower start 위치 분포 + detector 경계선
    h_rend = th1("h_shower_start_r", "#pi^{-} shower start (primary endpoint);r [mm];Events",
                 a["r_end"][a["shower_region"] >= 0], nbins=200, lo=0.0, hi=float(np.ceil(a["r_end"].max() / 500.0) * 500.0))
    h_zr = ROOT.TH2D("h2_shower_start_zr", "#pi^{-} shower start;z [mm];r [mm]", 100, -4000, 4000, 100, 0,
                     h_rend.GetXaxis().GetXmax())
    for z, r in zip(a["z_end"], a["r_end"]):
        h_zr.Fill(z, r)
    h_region = th1("h_shower_region", "shower region (0 tracker, 1 crystal ECAL, 2 solenoid gap, 3 fiber DRC);region;Events",
                   a["shower_region"].astype(float), nbins=5, lo=-1.5, hi=3.5)

    c_before = ROOT.TCanvas("c_before_cut", "before cut", 1500, 900)
    c_before.Divide(3, 3)
    for pad, h in enumerate([hall["S_c"], hall["C_c"], hall["S_f"], hall["C_f"], hall["S_tot"], hall["C_tot"],
                              h_sc_zoom, h_rend, h_region], start=1):
        c_before.cd(pad)
        h.Draw("hist")
    lines_before = []
    c_before.cd(7)
    top = h_sc_zoom.GetMaximum() * 1.05
    mip_line = ROOT.TLine(args.mip_cut, 0, args.mip_cut, top)
    mip_line.SetLineColor(ROOT.kRed + 1)
    mip_line.SetLineStyle(2)
    mip_line.SetLineWidth(2)
    mip_line.Draw()
    lines_before.append(mip_line)

    c_start = ROOT.TCanvas("c_shower_start", "pi- shower start position", 1400, 600)
    c_start.Divide(2, 1)
    c_start.cd(1)
    ROOT.gPad.SetLogy()
    h_rend.Draw("hist")
    top = h_rend.GetMaximum() * 1.5
    labels = []
    for r, text in ((R_ECAL_INNER, "ECAL"), (R_SOLENOID_INNER, "solenoid"), (R_DRC_INNER, "DRC")):
        ln = ROOT.TLine(r, 0.5, r, top)
        ln.SetLineColor(ROOT.kRed + 1)
        ln.SetLineStyle(2)
        ln.SetLineWidth(2)
        ln.Draw()
        lb = ROOT.TLatex(r + 20, top * 0.5, f"{text} {r:g} mm")
        lb.SetTextSize(0.03)
        lb.SetTextAngle(90)
        lb.Draw()
        labels += [ln, lb]
    c_start.cd(2)
    h_zr.Draw("colz")
    for r in (R_ECAL_INNER, R_SOLENOID_INNER, R_DRC_INNER):
        ln = ROOT.TLine(-4000, r, 4000, r)
        ln.SetLineColor(ROOT.kRed + 1)
        ln.SetLineStyle(2)
        ln.Draw()
        labels.append(ln)

    # ---------------------------------------------------------------- 2) chi_fiber (두 가지 선택)
    print("\n=== 2) chi_fiber: 선택 후 <S_f>, <C_f> ===")
    selections = {
        "truth": (a["shower_region"] == 3, "truth: shower_region == 3 (DRC 에서 shower 시작) [채택]"),
        "mip": (a["S_c"] < args.mip_cut, f"MIP-cut: S_c < {args.mip_cut:g} GeV [비교]"),
    }
    res = {}
    canvases = []
    for label, (mask, desc) in selections.items():
        n_sel = int(mask.sum())
        m_s, m_c = a["S_f"][mask].mean(), a["C_f"][mask].mean()
        chi = chi_from_means(m_s, m_c, E)
        e_dr = dr(a["S_f"][mask], a["C_f"][mask], chi)
        h_edr = th1(f"h_EDR_fiber_{label}", f"Fiber E_{{DR}} ({label} selection);E [GeV];Events", e_dr)
        fit = gauss_fit(h_edr)
        sel_h = {
            "S_c": th1(f"h_S_c_{label}", f"Crystal S, {label} selection;E [GeV];Events", a["S_c"][mask], lo=0.0, hi=E * 1.2),
            "C_c": th1(f"h_C_c_{label}", f"Crystal C, {label} selection;E [GeV];Events", a["C_c"][mask], lo=0.0, hi=E * 1.2),
            "S_f": th1(f"h_S_f_{label}", f"Fiber S, {label} selection;E [GeV];Events", a["S_f"][mask], lo=0.0, hi=E * 1.2),
            "C_f": th1(f"h_C_f_{label}", f"Fiber C, {label} selection;E [GeV];Events", a["C_f"][mask], lo=0.0, hi=E * 1.2),
        }
        c = ROOT.TCanvas(f"c_chi_fiber_{label}", f"chi_fiber, {label} selection", 1500, 900)
        c.Divide(3, 2)
        for pad, h in zip((1, 2, 4, 5), sel_h.values()):
            c.cd(pad)
            h.Draw("hist")
        c.cd(6)
        h_edr.Draw()
        canvases.append(c)
        hists += list(sel_h.values()) + [h_edr]
        res[label] = {"chi": chi, "n": n_sel, "mean_S_f": m_s, "mean_C_f": m_c}
        print(f"  [{desc}]")
        print(f"     N = {n_sel} ({100.0 * n_sel / n_all:.1f}%)   <S_f> = {m_s:.4f}   <C_f> = {m_c:.4f} GeV")
        print(f"     chi_fiber = (1 - {m_s:.4f}/{E:g}) / (1 - {m_c:.4f}/{E:g}) = {chi:.5f}")
        if fit:
            print(f"     E_DR,fiber Gaussian fit: mean = {fit[0]:.3f}  sigma = {fit[1]:.3f} GeV (mean 은 ~{E:g} 이어야 함)")

    m_t, m_m = res["truth"]["chi"], res["mip"]["chi"]
    both = int((selections["truth"][0] & selections["mip"][0]).sum())
    print(f"\n  truth 와 MIP-cut 의 겹침: purity = {both}/{res['mip']['n']} = "
          f"{100 * both / max(res['mip']['n'], 1):.1f}%,  efficiency = {both}/{res['truth']['n']} = "
          f"{100 * both / max(res['truth']['n'], 1):.1f}%")
    print(f"  chi_fiber: truth = {m_t:.5f}   MIP-cut = {m_m:.5f}   (차이 {100 * abs(m_m - m_t) / m_t:.1f}%)")
    chi_f = m_t

    # ---------------------------------------------------------------- 3,4) chi_crystal
    print(f"\n=== 3,4) chi_crystal (모든 event, chi_fiber = {chi_f:.5f}) ===")
    edr_fiber_all = dr(a["S_f"], a["C_f"], chi_f)
    mean_edr_fiber = edr_fiber_all.mean()
    e_prime = E - mean_edr_fiber
    ms_c, mc_c = a["S_c"].mean(), a["C_c"].mean()
    chi_c = chi_from_means(ms_c, mc_c, e_prime)
    print(f"  <E_DR,fiber> = {mean_edr_fiber:.4f} GeV  ->  E' = {E:g} - {mean_edr_fiber:.4f} = {e_prime:.4f} GeV")
    print(f"  <S_c> = {ms_c:.4f}   <C_c> = {mc_c:.4f} GeV")
    print(f"  chi_crystal = (1 - {ms_c:.4f}/{e_prime:.4f}) / (1 - {mc_c:.4f}/{e_prime:.4f}) = {chi_c:.5f}")
    c_lo = chi_from_means(ms_c, mc_c, e_prime - 1.0)
    c_hi = chi_from_means(ms_c, mc_c, e_prime + 1.0)
    print(f"  sensitivity: E' +- 1 GeV -> chi_crystal in [{c_lo:.3f}, {c_hi:.3f}]  (E' 에 민감함)")

    scan = np.linspace(-3.0, 0.95, 400)
    rms_scan = np.array([np.std(edr_fiber_all + dr(a["S_c"], a["C_c"], c), ddof=1) for c in scan])
    chi_c_rms = float(scan[rms_scan.argmin()])
    print(f"  chi_crystal (total E_DR 의 RMS 가 최소인 값, scan) = {chi_c_rms:.4f}   (min RMS = {rms_scan.min():.3f} GeV)")

    # ---------------------------------------------------------------- 5) total E_DR
    edr_crystal_all = dr(a["S_c"], a["C_c"], chi_c)
    edr_total = edr_fiber_all + edr_crystal_all
    h_edr_fiber_all = th1("h_EDR_fiber_all", "Fiber E_{DR}, all events;E [GeV];Events", edr_fiber_all)
    h_edr_crystal_all = th1("h_EDR_crystal_all", "Crystal E_{DR}, all events;E [GeV];Events", edr_crystal_all)
    h_edr_total = th1("h_EDR_total", "Total E_{DR} = fiber + crystal, all events;E [GeV];Events", edr_total)
    fit = gauss_fit(h_edr_total)
    print(f"\n=== 5) total E_DR (모든 event) ===")
    print(f"  mean = {edr_total.mean():.3f} GeV   RMS = {edr_total.std(ddof=1):.3f} GeV")
    if fit:
        print(f"  Gaussian fit: mean = {fit[0]:.3f}  sigma = {fit[1]:.3f} GeV")
    g_scan = ROOT.TGraph(len(scan), np.ascontiguousarray(scan), np.ascontiguousarray(rms_scan))
    g_scan.SetNameTitle("g_chi_crystal_rms_scan", "total E_{DR} RMS vs #chi_{crystal};#chi_{crystal};RMS [GeV]")

    c_dr = ROOT.TCanvas("c_EDR", "E_DR", 1500, 600)
    c_dr.Divide(3, 1)
    for pad, h in enumerate([h_edr_fiber_all, h_edr_crystal_all, h_edr_total], start=1):
        c_dr.cd(pad)
        h.Draw()
    c_scan = ROOT.TCanvas("c_chi_crystal_scan", "chi_crystal scan", 700, 500)
    g_scan.Draw("AL")

    # ---------------------------------------------------------------- 저장
    out.cd()
    for obj in [c_before, c_start, *canvases, c_dr, c_scan]:
        obj.Write()
    for h in list(hall.values()) + [h_sc_zoom, h2, h_rend, h_zr, h_region, h_edr_fiber_all, h_edr_crystal_all,
                                    h_edr_total] + hists:
        h.Write()
    g_scan.Write()
    out.Close()

    merge_json(args.json, "chi", {
        "chi_fiber": chi_f, "chi_crystal": chi_c,
        "chi_fiber_truth": m_t, "chi_fiber_mip_cut": m_m, "mip_cut_gev": args.mip_cut,
        "beam_energy_gev": E, "n_events_total": n_all, "n_events_truth_selected": res["truth"]["n"],
        "chi_crystal_sensitivity": {"E_prime_minus_1GeV": c_lo, "E_prime_plus_1GeV": c_hi,
                                    "chi_crystal_rms_scan": chi_c_rms},
    })
    print(f"\nwrote {args.output}, updated 'chi' in {args.json}")


if __name__ == "__main__":
    main()
