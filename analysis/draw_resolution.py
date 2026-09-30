#!/usr/bin/env python3
"""resolution_hists.py 의 출력 (energy 마다 하나) -> resolution / linearity canvas (ROOT 파일).

  --mode em   ECAL S, ECAL C, Total S, Total C 의 resolution 과 linearity
              (S, C 모두 Gaussian fit 의 mean, sigma 사용)
  --mode had  Total DR 의 resolution, 그리고 Total S / C / DR 의 linearity
              (DR 은 Gaussian fit, S / C 는 Gaussian 이 아니라서 histogram mean, RMS)

resolution : y = sigma/mean,  x = 1/sqrt(E),  pol1 fit  y = a/sqrt(E) + c
             (기울기 a = stochastic term, 절편 c = constant term)
linearity  : y = mean / E_beam

PNG 는 만들지 않고, TGraphErrors 와 TCanvas 를 출력 ROOT 파일에 저장한다.
    root -l out.root  ->  new TBrowser  로 열어 보면 된다.

예)
  python3 draw_resolution.py --mode em  -i em_{10,20,40,60,80}GeV.root  -o em_plots.root
  python3 draw_resolution.py --mode had -i had_{10,20,40,60,80}GeV.root -o had_plots.root
"""
import argparse
import math
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kError
ROOT.gStyle.SetOptStat(0)

# (label, histogram, 'gauss' 또는 'hist')
EM_CHANNELS = {"ECAL S": ("h_ECAL_S", "gauss"), "ECAL C": ("h_ECAL_C", "gauss"),
               "Total S": ("h_Total_S", "gauss"), "Total C": ("h_Total_C", "gauss")}
HAD_LIN = {"S": ("h_Total_S", "hist"), "C": ("h_Total_C", "hist"), "DR": ("h_Total_DR", "gauss")}
COLORS = {"S": ROOT.kRed + 1, "C": ROOT.kBlue + 1, "DR": ROOT.kBlack}


def load_points(files):
    """energy -> ROOT 파일 (histogram 을 계속 쓰기 위해 열어 둔다)."""
    points = {}
    for path in files:
        f = ROOT.TFile.Open(path)
        if not f or f.IsZombie():
            print(f"  [skip] {path}")
            continue
        tag = f.Get("beam_energy_gev")
        if not tag:
            print(f"  [skip] {path}: beam_energy_gev 없음")
            continue
        points[float(tag.GetTitle())] = f
    return dict(sorted(points.items()))


def mean_sigma(hist, method):
    """(mean, sigma, mean_err, sigma_err) 또는 None."""
    if method == "gauss":
        fn = hist.GetFunction("gaus")
        if not fn:
            return None
        return fn.GetParameter(1), fn.GetParameter(2), fn.GetParError(1), fn.GetParError(2)
    n = hist.GetEffectiveEntries()
    mean, rms = hist.GetMean(), hist.GetRMS()
    return mean, rms, rms / math.sqrt(n), rms / math.sqrt(2 * n)


def collect(points, hist_name, method):
    """[(E, response, response_err, resolution, resolution_err)]"""
    rows = []
    for energy, f in points.items():
        h = f.Get(hist_name)
        ms = mean_sigma(h, method) if h else None
        if ms is None or ms[0] <= 0:
            print(f"  [skip] {hist_name} @ {energy} GeV: 값 없음")
            continue
        mean, sigma, mean_err, sigma_err = ms
        res = sigma / mean
        res_err = res * math.hypot(sigma_err / sigma, mean_err / mean)
        rows.append((energy, mean / energy, mean_err / energy, res, res_err))
    return rows


def resolution_graph(name, rows, color):
    g = ROOT.TGraphErrors(len(rows))
    for i, (e, _, _, res, res_err) in enumerate(rows):
        g.SetPoint(i, 1.0 / math.sqrt(e), res)
        g.SetPointError(i, 0, res_err)
    g.SetName(name)
    g.SetMarkerStyle(21)
    g.SetMarkerColor(color)
    g.SetLineColor(color)
    xs = [1.0 / math.sqrt(r[0]) for r in rows]
    fit = ROOT.TF1(f"fit_{name}", "pol1", min(xs) * 0.9, max(xs) * 1.1)
    fit.SetLineColor(color)
    g.Fit(fit, "QR")
    return g, fit


def linearity_graph(name, rows, color):
    g = ROOT.TGraphErrors(len(rows))
    for i, (e, resp, resp_err, _, _) in enumerate(rows):
        g.SetPoint(i, e, resp)
        g.SetPointError(i, 0, resp_err)
    g.SetName(name)
    g.SetMarkerStyle(21)
    g.SetMarkerColor(color)
    g.SetLineColor(color)
    return g


def draw_resolution(name, title, series, fout):
    """series: [(label, rows, color)]"""
    c = ROOT.TCanvas(name, title, 900, 700)
    c.SetGrid()
    mg = ROOT.TMultiGraph(f"mg_{name}", f"{title};1/#sqrt{{E}} [GeV^{{-1/2}}];#sigma/E")
    leg = ROOT.TLegend(0.15, 0.68, 0.62, 0.88)
    keep = []
    print(f"\n[{title}]   sigma/E = a/sqrt(E) + c")
    for label, rows, color in series:
        if len(rows) < 2:
            print(f"  {label}: 점이 2개 미만이라 fit 불가")
            continue
        g, fit = resolution_graph(f"g_{name}_{label.replace(' ', '_')}", rows, color)
        mg.Add(g, "P")
        c_term, a_term = fit.GetParameter(0), fit.GetParameter(1)
        leg.AddEntry(g, f"{label}:  {100 * a_term:.1f}%/#sqrt{{E}} + {100 * c_term:.2f}%", "lep")
        print(f"  {label:<8} a = {100 * a_term:6.2f} %   c = {100 * c_term:6.2f} %   "
              f"chi2/ndf = {fit.GetChisquare():.2f}/{fit.GetNDF()}")
        g.GetListOfFunctions().Add(fit)
        keep.append(g)
        g.Write()
    mg.Draw("AP")
    mg.GetXaxis().SetLimits(0, 0.4)
    mg.SetMinimum(0)
    for g in keep:
        g.GetListOfFunctions().At(0).Draw("same")
    leg.Draw()
    c.Modified()
    fout.cd()
    mg.Write()
    c.Write()
    return c, mg, leg, keep


def draw_linearity(name, title, series, fout):
    c = ROOT.TCanvas(name, title, 900, 700)
    c.SetGrid()
    mg = ROOT.TMultiGraph(f"mg_{name}", f"{title};E_{{beam}} [GeV];<E>/E_{{beam}}")
    leg = ROOT.TLegend(0.65, 0.72, 0.88, 0.88)
    keep = []
    print(f"\n[{title}]   <E>/E_beam")
    for label, rows, color in series:
        if not rows:
            continue
        g = linearity_graph(f"g_{name}_{label.replace(' ', '_')}", rows, color)
        mg.Add(g, "P")
        leg.AddEntry(g, label, "lep")
        print(f"  {label:<8}" + "  ".join(f"{r[0]:g}GeV:{r[1]:.4f}" for r in rows))
        keep.append(g)
        g.Write()
    mg.Draw("AP")
    ymin, ymax = mg.GetYaxis().GetXmin(), mg.GetYaxis().GetXmax()
    mg.SetMinimum(min(ymin, 0.9))
    mg.SetMaximum(max(ymax, 1.1))
    line = ROOT.TLine(0, 1, mg.GetXaxis().GetXmax(), 1)
    line.SetLineStyle(2)
    line.Draw()
    leg.Draw()
    c.Modified()
    fout.cd()
    mg.Write()
    c.Write()
    return c, mg, leg, keep, line


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["em", "had"], required=True)
    ap.add_argument("-i", "--input", nargs="+", required=True, help="resolution_hists.py 출력 (energy 마다 하나)")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    points = load_points(args.input)
    if len(points) < 2:
        sys.exit("energy point 가 2개 이상 필요하다")
    print("energy points [GeV]:", list(points))

    fout = ROOT.TFile(args.output, "RECREATE")
    keep = []
    if args.mode == "em":
        data = {label: collect(points, h, m) for label, (h, m) in EM_CHANNELS.items()}
        for region in ("ECAL", "Total"):
            series = [(f"{region} S", data[f"{region} S"], COLORS["S"]), (f"{region} C", data[f"{region} C"], COLORS["C"])]
            keep.append(draw_resolution(f"c_res_{region}", f"EM resolution ({region})", series, fout))
            keep.append(draw_linearity(f"c_lin_{region}", f"EM linearity ({region})", series, fout))
    else:
        data = {label: collect(points, h, m) for label, (h, m) in HAD_LIN.items()}
        keep.append(draw_resolution("c_res_Total_DR", "Hadron resolution (Total DR)",
                                    [("Total DR", data["DR"], COLORS["DR"])], fout))
        keep.append(draw_linearity("c_lin_Total", "Hadron linearity (Total)",
                                   [(f"Total {k}", data[k], COLORS[k]) for k in ("S", "C", "DR")], fout))
    fout.Close()
    print(f"\nwrote {args.output}")


if __name__ == "__main__":
    main()
