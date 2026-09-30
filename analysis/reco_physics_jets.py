#!/usr/bin/env python3
"""Z->qq ntuple (make_physics_ntuple.py) -> fastjet Durham 2-jet -> m(jj), 그리고 hit + jet 의 eta-phi 시각화.

Jet clustering
  입력 : 모든 hit (ECAL S, ECAL C, DRC S, DRC C) 을 massless 4-vector (E, E*r_hat) 로 본다.
         DRC fiber 는 먼저 projective tower 로 묶는다 (tower = cellID & 0xFFFFFFFF, S 와 C 따로,
         E = fiber E 의 합, 위치 = E 가중 평균).  --no-proto-cluster 면 fiber hit 을 그대로 넣는다.
  알고리즘 : fastjet ee_genkt (R = 2pi, p = 1) = Durham, 정확히 2 jet 이 되도록 exclusive clustering.
  clustering 에는 보정 전 S / C hit energy 를 쓴다 (hit 하나의 DR 값은 음수가 될 수 있다).
Jet 4-vector
  jet 의 constituent 를 channel 별로 다시 합친 뒤 DR 보정을 jet 단위로 적용한다:
     P_DR,ecal = (P_S,ecal - chi_crystal*P_C,ecal) / (1 - chi_crystal)
     P_DR,drc  = (P_S,drc  - chi_fiber  *P_C,drc ) / (1 - chi_fiber)
     P_jet     = P_DR,ecal + P_DR,drc
  jet 은 E_DR 이 큰 순서로 정렬한다.  m(jj) = 두 jet 4-vector 합의 invariant mass.

출력 (ROOT 파일 하나, PNG 없음)
  TTree "jets"          : event 당 한 줄 (E_jj, m_jj, m_jj_S, m_jj_C, jet E/eta/phi, cos_jj, ...)
  h_mjj_DR / _S / _C    : m(jj)  (DR 은 Gaussian fit, 결과는 터미널에도 출력)
  h_Ejj_DR, h_Ejet, h_eta_jet, h_cos_jj
  c_mjj, c_jets         : 요약 canvas
  c_event_display       : --event N 번 event 의 eta-phi 그림 (왼쪽: hit energy map + jet 축, 오른쪽: hit 을 소속 jet 별로 색칠)
  (truth jet 과 비교하지 않는다.)

예)
  python3 reco_physics_jets.py qq_ntuple.root -o qq_jets.root --event 5
"""
import argparse
import math
import os
import subprocess
import sys
import time
from array import array

import numpy as np
import ROOT
from common import gauss_fit

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kError
ROOT.gStyle.SetOptStat(0)
ROOT.TH1.AddDirectory(False)

CH = ("ecal_S", "ecal_C", "drc_S", "drc_C")
TOWER_MASK = 0xFFFFFFFF

CPP_HELPER = r"""
#include <vector>
#include <cmath>
#include "fastjet/ClusterSequence.hh"

// Durham exclusive 2-jet. Returns [n0, idx..., n1, idx...] (idx = 입력 index).
std::vector<int> tut_durham2(const double* px, const double* py, const double* pz, const double* E, int n) {
  std::vector<int> out;
  std::vector<fastjet::PseudoJet> in;
  in.reserve(n);
  for (int i = 0; i < n; ++i) {
    fastjet::PseudoJet pj(px[i], py[i], pz[i], E[i]);
    pj.set_user_index(i);
    in.push_back(pj);
  }
  fastjet::JetDefinition jd(fastjet::ee_genkt_algorithm, 2.0 * M_PI, 1.0);
  fastjet::ClusterSequence cs(in, jd);
  auto jets = fastjet::sorted_by_E(cs.exclusive_jets(2));
  for (const auto& j : jets) {
    auto cons = j.constituents();
    out.push_back(int(cons.size()));
    for (const auto& c : cons) out.push_back(c.user_index());
  }
  return out;
}
"""


def init_fastjet():
    try:
        cflags = subprocess.check_output(["fastjet-config", "--cxxflags"], text=True).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        sys.exit(f"fastjet-config 를 쓸 수 없다 (source setup_env.sh 했는지 확인): {exc}")
    for tok in cflags.split():
        if tok.startswith("-I"):
            ROOT.gInterpreter.AddIncludePath(tok[2:])
    if ROOT.gSystem.Load("libfastjet") < 0:
        sys.exit("libfastjet 을 load 할 수 없다")
    ROOT.gInterpreter.Declare(CPP_HELPER)


def vec_np(v):
    n = int(v.size())
    return np.frombuffer(v.data(), dtype=np.float32, count=n).astype(np.float64) if n else np.zeros(0)


def vec_u64(v):
    n = int(v.size())
    return np.frombuffer(v.data(), dtype=np.uint64, count=n).copy() if n else np.zeros(0, np.uint64)


def make_inputs(tree, proto):
    """(P4 (N,4) = [E,px,py,pz], channel index (N,) 0..3, 위치 (N,3))"""
    p4s, chs, poss = [], [], []
    for k, ch in enumerate(CH):
        e, x, y, z = (vec_np(getattr(tree, f"{ch}_{v}")) for v in "Exyz")
        cid = vec_u64(getattr(tree, f"{ch}_cellID"))
        m = e > 0
        e, x, y, z, cid = e[m], x[m], y[m], z[m], cid[m]
        if proto and k >= 2 and len(e):
            uniq, inv = np.unique((cid & np.uint64(TOWER_MASK)).astype(np.int64), return_inverse=True)
            et = np.bincount(inv, weights=e)
            x = np.bincount(inv, weights=e * x) / et
            y = np.bincount(inv, weights=e * y) / et
            z = np.bincount(inv, weights=e * z) / et
            e = et
        r = np.sqrt(x * x + y * y + z * z)
        r[r == 0] = 1.0
        p4s.append(np.column_stack([e, e * x / r, e * y / r, e * z / r]))
        chs.append(np.full(len(e), k, dtype=np.int64))
        poss.append(np.column_stack([x, y, z]))
    return np.concatenate(p4s), np.concatenate(chs), np.concatenate(poss)


def durham2(p4):
    flat = ROOT.tut_durham2(np.ascontiguousarray(p4[:, 1]), np.ascontiguousarray(p4[:, 2]),
                            np.ascontiguousarray(p4[:, 3]), np.ascontiguousarray(p4[:, 0]), len(p4))
    arr = np.frombuffer(flat.data(), dtype=np.intc, count=int(flat.size())).copy()
    groups, pos = [], 0
    for _ in range(2):
        n = int(arr[pos])
        groups.append(arr[pos + 1:pos + 1 + n].astype(np.int64))
        pos += 1 + n
    return groups


def kin(v):
    """E, eta, phi, signed mass of [E,px,py,pz]."""
    e, px, py, pz = v
    p = math.sqrt(px * px + py * py + pz * pz)
    eta = math.asinh(pz / math.hypot(px, py)) if math.hypot(px, py) > 0 else (math.copysign(20.0, pz) if p > 0 else 0.0)
    m2 = e * e - p * p
    return e, eta, math.atan2(py, px), math.copysign(math.sqrt(abs(m2)), m2)


def cos_angle(a, b):
    na, nb = np.linalg.norm(a[1:]), np.linalg.norm(b[1:])
    return float(np.dot(a[1:], b[1:]) / (na * nb)) if na > 0 and nb > 0 else 0.0


def eta_phi(p4):
    px, py, pz = p4[:, 1], p4[:, 2], p4[:, 3]
    return np.arcsinh(pz / np.maximum(np.hypot(px, py), 1e-9)), np.arctan2(py, px)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ntuple")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--ecm", type=float, default=91.0, help="centre-of-mass energy [GeV] (histogram 범위)")
    ap.add_argument("--event", type=int, default=0, help="event display 를 그릴 event 번호")
    ap.add_argument("--no-proto-cluster", action="store_true", help="DRC fiber 를 tower 로 묶지 않는다")
    ap.add_argument("--chi-fiber", type=float, default=None)
    ap.add_argument("--chi-crystal", type=float, default=None)
    ap.add_argument("--max-events", type=int, default=None)
    args = ap.parse_args()

    init_fastjet()
    fin = ROOT.TFile.Open(args.ntuple)
    tree = fin.Get("hits")
    if not tree:
        sys.exit(f"{args.ntuple}: TTree 'hits' 없음 (make_physics_ntuple.py 의 출력이 아니다)")
    chi_f = args.chi_fiber if args.chi_fiber is not None else float(fin.Get("chi_fiber").GetTitle())
    chi_c = args.chi_crystal if args.chi_crystal is not None else float(fin.Get("chi_crystal").GetTitle())
    nent = tree.GetEntries() if args.max_events is None else min(args.max_events, tree.GetEntries())
    proto = not args.no_proto_cluster
    print(f"{args.ntuple}: {nent} events, proto-cluster = {proto}, chi_fiber = {chi_f:.5f}, chi_crystal = {chi_c:.5f}")

    ecm = args.ecm
    hist = {
        "h_mjj_DR": ROOT.TH1D("h_mjj_DR", "m(jj), DR;m_{jj} [GeV];Events", 300, -0.2 * ecm, 1.5 * ecm),
        "h_mjj_S": ROOT.TH1D("h_mjj_S", "m(jj), S only;m_{jj} [GeV];Events", 300, -0.2 * ecm, 1.5 * ecm),
        "h_mjj_C": ROOT.TH1D("h_mjj_C", "m(jj), C only;m_{jj} [GeV];Events", 300, -0.2 * ecm, 1.5 * ecm),
        "h_Ejj_DR": ROOT.TH1D("h_Ejj_DR", "E(jj), DR;E_{jj} [GeV];Events", 300, -0.2 * ecm, 1.5 * ecm),
        "h_Ejet": ROOT.TH1D("h_Ejet", "jet energy (DR);E_{jet} [GeV];Jets", 200, -0.2 * ecm, 1.0 * ecm),
        "h_eta_jet": ROOT.TH1D("h_eta_jet", "jet #eta;#eta_{jet};Jets", 100, -4, 4),
        "h_cos_jj": ROOT.TH1D("h_cos_jj", "cos of opening angle between the two jets;cos#theta_{jj};Events", 100, -1, 1),
    }

    out = ROOT.TFile(args.output, "RECREATE")
    otree = ROOT.TTree("jets", "Durham 2-jet reconstruction")
    sc = {}
    for name in ("E_jj", "m_jj", "m_jj_S", "m_jj_C", "cos_jj"):
        sc[name] = array("d", [0.0])
        otree.Branch(name, sc[name], f"{name}/D")
    jv = {}
    for name in ("jet_E", "jet_eta", "jet_phi", "jet_E_S", "jet_E_C", "jet_fecal"):
        jv[name] = array("d", [0.0, 0.0])
        otree.Branch(name, jv[name], f"{name}[2]/D")
    sc["evt_idx"] = array("i", [0])
    sc["valid"] = array("i", [0])
    otree.Branch("evt_idx", sc["evt_idx"], "evt_idx/I")
    otree.Branch("valid", sc["valid"], "valid/I")

    display = None
    n_invalid = 0
    t0 = time.time()
    for i in range(nent):
        tree.GetEntry(i)
        sc["evt_idx"][0] = i
        p4, chan, pos = make_inputs(tree, proto)
        if len(p4) < 2:
            n_invalid += 1
            sc["valid"][0] = 0
            for a in list(sc.values()) + list(jv.values()):
                if a is not sc["evt_idx"] and a is not sc["valid"]:
                    for k in range(len(a)):
                        a[k] = 0.0
            otree.Fill()
            continue
        groups = durham2(p4)
        jets = []
        for g in groups:
            sums = np.zeros((4, 4))
            for k in range(4):
                sel = chan[g] == k
                if sel.any():
                    sums[k] = p4[g][sel].sum(axis=0)
            p_ecal = (sums[0] - chi_c * sums[1]) / (1 - chi_c)
            p_drc = (sums[2] - chi_f * sums[3]) / (1 - chi_f)
            jets.append({"idx": g, "sums": sums, "P": p_ecal + p_drc, "fecal": p_ecal[0] / (p_ecal[0] + p_drc[0])
                         if (p_ecal[0] + p_drc[0]) != 0 else 0.0})
        jets.sort(key=lambda j: -j["P"][0])
        pz_ = jets[0]["P"] + jets[1]["P"]
        ps = sum(j["sums"][0] + j["sums"][2] for j in jets)
        pc = sum(j["sums"][1] + j["sums"][3] for j in jets)
        e_jj, _, _, m_jj = kin(pz_)
        _, _, _, m_s = kin(ps)
        _, _, _, m_c = kin(pc)
        cosjj = cos_angle(jets[0]["P"], jets[1]["P"])
        sc["E_jj"][0], sc["m_jj"][0], sc["m_jj_S"][0], sc["m_jj_C"][0], sc["cos_jj"][0] = e_jj, m_jj, m_s, m_c, cosjj
        sc["valid"][0] = 1
        for k, j in enumerate(jets):
            e, eta, phi, _ = kin(j["P"])
            jv["jet_E"][k], jv["jet_eta"][k], jv["jet_phi"][k] = e, eta, phi
            jv["jet_E_S"][k] = j["sums"][0][0] + j["sums"][2][0]
            jv["jet_E_C"][k] = j["sums"][1][0] + j["sums"][3][0]
            jv["jet_fecal"][k] = j["fecal"]
            hist["h_Ejet"].Fill(e)
            hist["h_eta_jet"].Fill(eta)
        hist["h_mjj_DR"].Fill(m_jj)
        hist["h_mjj_S"].Fill(m_s)
        hist["h_mjj_C"].Fill(m_c)
        hist["h_Ejj_DR"].Fill(e_jj)
        hist["h_cos_jj"].Fill(cosjj)
        otree.Fill()
        if i == args.event:
            display = (p4.copy(), chan.copy(), [j["idx"].copy() for j in jets], [kin(j["P"]) for j in jets])
        if (i + 1) % 200 == 0:
            print(f"  {i + 1}/{nent} events ({time.time() - t0:.0f} s)", flush=True)

    fit_m = gauss_fit(hist["h_mjj_DR"])
    fit_e = gauss_fit(hist["h_Ejj_DR"])
    print(f"\n{nent} events ({n_invalid} invalid), {time.time() - t0:.0f} s")
    print(f"  m(jj) DR : hist mean = {hist['h_mjj_DR'].GetMean():.2f}  "
          + (f"Gaussian fit mean = {fit_m[0]:.2f}, sigma = {fit_m[1]:.2f} GeV" if fit_m else "fit 실패"))
    print(f"  E(jj) DR : hist mean = {hist['h_Ejj_DR'].GetMean():.2f}  "
          + (f"Gaussian fit mean = {fit_e[0]:.2f}, sigma = {fit_e[1]:.2f} GeV" if fit_e else "fit 실패"))
    for name in ("h_mjj_S", "h_mjj_C"):
        print(f"  {name:<9}: hist mean = {hist[name].GetMean():.2f}")

    out.cd()
    otree.Write()
    for h in hist.values():
        h.Write()
    for key, val in (("chi_fiber", chi_f), ("chi_crystal", chi_c), ("proto_cluster", proto), ("n_events", nent)):
        ROOT.TNamed(key, str(val)).Write()

    keep = []
    c = ROOT.TCanvas("c_mjj", "m(jj): S, C, DR", 900, 700)
    c.SetGrid()
    ymax = max(hist[n].GetMaximum() for n in ("h_mjj_S", "h_mjj_C", "h_mjj_DR"))
    for name, col in (("h_mjj_S", ROOT.kRed + 1), ("h_mjj_C", ROOT.kBlue + 1), ("h_mjj_DR", ROOT.kBlack)):
        hist[name].SetLineColor(col)
        hist[name].SetLineWidth(2)
        hist[name].SetMaximum(ymax * 1.3)
        hist[name].SetTitle("m(jj): S only, C only, DR;m_{jj} [GeV];Events")
        hist[name].Draw("hist" if name == "h_mjj_S" else "hist same")
    fn = hist["h_mjj_DR"].GetFunction("gaus")
    if fn:
        fn.SetLineColor(ROOT.kGreen + 2)
        fn.Draw("same")
    leg = ROOT.TLegend(0.15, 0.70, 0.55, 0.88)
    leg.SetBorderSize(0)
    leg.AddEntry(hist["h_mjj_S"], "S only", "l")
    leg.AddEntry(hist["h_mjj_C"], "C only", "l")
    leg.AddEntry(hist["h_mjj_DR"], "DR" + (f": #mu = {fit_m[0]:.1f}, #sigma = {fit_m[1]:.1f} GeV" if fit_m else ""), "l")
    leg.Draw()
    c.Write()
    keep += [c, leg]

    c2 = ROOT.TCanvas("c_jets", "jet summary", 1500, 500)
    c2.Divide(3, 1)
    for n, name in enumerate(("h_Ejj_DR", "h_Ejet", "h_eta_jet"), 1):
        c2.cd(n).SetGrid()
        hist[name].SetLineWidth(2)
        hist[name].Draw("hist")
    c2.Write()
    keep.append(c2)

    if display is not None:
        p4, chan, groups, jet_kin = display
        c3 = ROOT.TCanvas("c_event_display", f"event {args.event}: hits and jets in eta-phi", 1500, 700)
        c3.Divide(2, 1)
        eta, phi = eta_phi(p4)
        h2 = ROOT.TH2D("h2_event_hits", f"event {args.event}: hit energy (S+C, ECAL+DRC tower);#eta;#phi;E [GeV]",
                       120, -3, 3, 72, -math.pi, math.pi)
        h2.FillN(len(eta), np.ascontiguousarray(eta), np.ascontiguousarray(phi), np.ascontiguousarray(p4[:, 0]))
        c3.cd(1).SetLogz()
        c3.cd(1).SetRightMargin(0.15)
        h2.Draw("colz")
        markers = []
        for k, (e, jeta, jphi, _) in enumerate(jet_kin):
            m = ROOT.TMarker(jeta, jphi, ROOT.kFullStar)
            m.SetMarkerSize(3)
            m.SetMarkerColor([ROOT.kRed, ROOT.kBlue][k])
            m.Draw()
            markers.append(m)
        c3.cd(2).SetGrid()
        frame = ROOT.TH2D("frame_event", f"event {args.event}: hits by jet;#eta;#phi", 10, -3, 3, 10, -math.pi, math.pi)
        frame.Draw()
        graphs = []
        for k, g in enumerate(groups):
            col = [ROOT.kRed, ROOT.kBlue][k]
            for marker_style, sel in ((ROOT.kFullCircle, chan[g] < 2), (ROOT.kOpenTriangleUp, chan[g] >= 2)):
                idx = g[sel]
                if len(idx) == 0:
                    continue
                gr = ROOT.TGraph(len(idx), np.ascontiguousarray(eta[idx]), np.ascontiguousarray(phi[idx]))
                gr.SetMarkerStyle(marker_style)
                gr.SetMarkerColor(col)
                gr.SetMarkerSize(0.6)
                gr.Draw("P same")
                graphs.append(gr)
            m = ROOT.TMarker(jet_kin[k][1], jet_kin[k][2], ROOT.kFullStar)
            m.SetMarkerSize(3)
            m.SetMarkerColor(ROOT.kBlack)
            m.Draw()
            markers.append(m)
        txt = ROOT.TLatex(0.13, 0.92, "circle: ECAL hit, triangle: DRC tower/fiber, star: jet axis (red: jet 0, blue: jet 1)")
        txt.SetNDC()
        txt.SetTextSize(0.028)
        txt.Draw()
        markers.append(txt)
        c3.Write()
        h2.Write()
        keep += [c3, h2, markers, graphs, frame]

    out.Close()
    print(f"\nwrote {args.output}")


if __name__ == "__main__":
    main()
