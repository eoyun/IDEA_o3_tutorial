#!/usr/bin/env python3
"""여러 ROOT 파일의 같은 이름 histogram 을 면적 1 로 맞춰 겹쳐 그린다 (예: ISR on / off).

예)
  python3 compare_hists.py ZH.root ZH_ISRoff.root --labels "ISR on" "ISR off" \
          --hists h_mH_chi2 h_mZ_chi2 h_Esum -o ZH_ISR_compare.root
"""
import argparse
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kError
ROOT.gStyle.SetOptStat(0)
ROOT.TH1.AddDirectory(False)

COLORS = (ROOT.kBlack, ROOT.kRed + 1, ROOT.kBlue + 1, ROOT.kGreen + 2, ROOT.kMagenta + 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--labels", nargs="+", default=None)
    ap.add_argument("--hists", nargs="+", required=True)
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()
    labels = args.labels or args.files
    if len(labels) != len(args.files):
        sys.exit("--labels 개수가 파일 개수와 다르다")

    fins = [ROOT.TFile.Open(f) for f in args.files]
    out = ROOT.TFile(args.output, "RECREATE")
    keep = []
    for name in args.hists:
        c = ROOT.TCanvas(f"c_{name}", name, 900, 700)
        c.SetGrid()
        leg = ROOT.TLegend(0.12, 0.72, 0.5, 0.88)
        leg.SetBorderSize(0)
        hs = []
        for k, (fin, label) in enumerate(zip(fins, labels)):
            h = fin.Get(name)
            if not h:
                print(f"  {fin.GetName()}: {name} 없음")
                continue
            h = h.Clone(f"{name}_{k}")
            if h.Integral() > 0:
                h.Scale(1.0 / h.Integral())
            h.SetLineColor(COLORS[k % len(COLORS)])
            h.SetLineWidth(2)
            h.GetYaxis().SetTitle("normalized")
            hs.append(h)
            leg.AddEntry(h, f"{label}: mean {h.GetMean():.1f}, RMS {h.GetRMS():.1f}", "l")
            print(f"  {name:<12} {label:<12} entries {int(h.GetEntries()):6d}  mean {h.GetMean():7.2f}  RMS {h.GetRMS():6.2f}")
        if not hs:
            continue
        ymax = max(h.GetMaximum() for h in hs)
        for n, h in enumerate(hs):
            h.SetMaximum(ymax * 1.3)
            h.Draw("hist" if n == 0 else "hist same")
        leg.Draw()
        c.Write()
        keep += [c, leg, hs]
    out.Close()
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
