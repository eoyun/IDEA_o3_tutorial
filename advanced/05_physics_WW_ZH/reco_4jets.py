#!/usr/bin/env python3
"""fully hadronic WW->qqqq / ZH->qqbb (240 GeV) Digi -> Durham exclusive 4-jet -> chi2 pairing -> m(jj).

Jet clustering (analysis/reco_physics_jets.py 와 같은 방식, 4 jet)
  입력 : ECAL S, ECAL C, DRC S, DRC C hit 을 EM calibration constant 로 GeV 로 바꾸고 massless 4-vector (E, E*r_hat) 로 본다.
         DRC fiber 는 projective tower 로 묶는다 (tower = cellID & 0xFFFFFFFF, S 와 C 따로). --no-proto-cluster 면 fiber 그대로.
  알고리즘 : fastjet ee_genkt (R = 2pi, p = 1) = Durham, exclusive_jets(4).
  jet 4-vector : constituent 를 channel 별로 다시 합친 뒤 jet 단위로 DR 보정
     P_jet = (P_S,ecal - chi_crystal*P_C,ecal)/(1 - chi_crystal) + (P_S,drc - chi_fiber*P_C,drc)/(1 - chi_fiber)
  jet energy rescaling, kinematic fit, b-tagging 은 하지 않는다.

Pairing : 4 jet 을 두 쌍으로 묶는 방법 3가지 중 chi2 가 가장 작은 것.
  WW : chi2 = ((m1 - mW)/sigma)^2 + ((m2 - mW)/sigma)^2
  ZH : 어느 쌍이 Z 인지까지 6가지.  chi2 = ((m_Z - mZ)/sigma_Z)^2 + ((m_H - mH)/sigma_H)^2

--truth (pairing 결정에는 쓰지 않고 평가에만 쓴다)
  parton : MCParticles 에서 W/Z/H (|PDG| 24/23/25) 의 decay quark (generatorStatus 23) 4개.
  matching : reco jet 4개와 quark 4개를 각도 합이 가장 작은 순열 (24가지) 로 짝짓는다 -> "정답 pairing".
  pairing 효율 : chi2 가 고른 pairing (ZH 는 Z/H 역할까지) 이 정답과 같은 비율. 전체와, 4 jet 모두
                 quark 와의 각도가 --match-cut 보다 작은 event (well_matched) 만 따로 출력한다.
                 (Durham jet 이 quark 를 따라가지 않는 event 는 "정답 pairing" 자체가 의미 없다.)
  m(jj) 비교 : reco jet + chi2 pairing / reco jet + 정답 pairing / gen jet + 정답 pairing (nu 제외, nu 포함).
  gen jet : generatorStatus 1 인 MCParticles (Geant4 이전의 stable 입자) 로 같은 Durham 4-jet.
            |cos(theta)| > --gen-cos-max 인 입자는 뺀다 (beam pipe 방향, calorimeter 가 덮지 않는 곳).
            nu (|PDG| 12, 14, 16) 를 뺀 것과 넣은 것 두 번 만든다.
  jet 응답 : reco jet 과 gen jet (nu 제외) 을 같은 방법으로 짝지어 E_reco / E_gen.

출력 (ROOT 파일 하나, PNG 없음)
  TTree "events", histogram (h_m<W|Z|H>_chi2, _true, _gen, _gen_nu, h_Esum, h_chi2, h_Eratio, ...), canvas c_mass_<W|Z|H>, c_summary

예)
  python3 reco_4jets.py --mode WW -i $TUTORIAL_SAMPLES/o3_WW_qqqq_eCM240_noOpt_Digi -o WW_4jets.root --truth
  python3 reco_4jets.py --mode ZH -i $TUTORIAL_SAMPLES/o3_ZH_qqbb_eCM240_noOpt_Digi -o ZH_4jets.root --truth
"""
import argparse
import itertools
import math
import os
import sys
import time
from array import array

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.environ.get("IDEA_TUTORIAL_ROOT", os.path.join(HERE, "..", "..")), "analysis"))

from common import CHANNELS, DEFAULT_CALIB_JSON, expand_inputs, gauss_fit, iter_events, load_calib  # noqa: E402
from reco_physics_jets import TOWER_MASK, init_fastjet, kin  # noqa: E402

import ROOT  # noqa: E402

ROOT.gStyle.SetOptStat(0)
ROOT.TH1.AddDirectory(False)

CH = ("ecal_S", "ecal_C", "drc_S", "drc_C")
M_W, M_Z, M_H = 80.385, 91.1876, 125.0
NEUTRINOS = (12, 14, 16)
PAIRINGS = (((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2)))
PERMS = list(itertools.permutations(range(4)))

CPP_HELPER_N = r"""
#include <vector>
#include "fastjet/ClusterSequence.hh"

// Durham exclusive N-jet. Returns [n0, idx..., n1, idx..., ...] (idx = 입력 index), jet 은 E 순서.
std::vector<int> tut_durham_n(const double* px, const double* py, const double* pz, const double* E, int n, int njet) {
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
  auto jets = fastjet::sorted_by_E(cs.exclusive_jets(njet));
  for (const auto& j : jets) {
    auto cons = j.constituents();
    out.push_back(int(cons.size()));
    for (const auto& c : cons) out.push_back(c.user_index());
  }
  return out;
}
"""


def durham_n(p4, njet=4):
    """p4 (N,4) = [E,px,py,pz] -> jet 별 입력 index 배열의 list (E 순서)."""
    flat = ROOT.tut_durham_n(np.ascontiguousarray(p4[:, 1]), np.ascontiguousarray(p4[:, 2]),
                             np.ascontiguousarray(p4[:, 3]), np.ascontiguousarray(p4[:, 0]), len(p4), njet)
    arr = np.frombuffer(flat.data(), dtype=np.intc, count=int(flat.size())).copy()
    groups, pos = [], 0
    for _ in range(njet):
        n = int(arr[pos])
        groups.append(arr[pos + 1:pos + 1 + n].astype(np.int64))
        pos += 1 + n
    return groups


def reco_inputs(frame, consts, proto):
    """(P4 (N,4), channel index (N,) 0..3). hit 에너지는 calibration constant 를 곱한 GeV."""
    p4s, chs = [], []
    for k, ch in enumerate(CH):
        coll, cname = CHANNELS[ch]
        hits = frame.get(coll)
        n = len(hits)
        if n == 0:
            continue
        e = np.empty(n)
        xyz = np.empty((n, 3))
        cid = np.empty(n, dtype=np.uint64)
        for i, h in enumerate(hits):
            e[i] = h.getEnergy()
            p = h.getPosition()
            xyz[i] = (p.x, p.y, p.z)
            cid[i] = h.getCellID()
        e *= consts[cname]
        m = e > 0
        e, xyz, cid = e[m], xyz[m], cid[m]
        if proto and k >= 2 and len(e):
            _, inv = np.unique((cid & np.uint64(TOWER_MASK)).astype(np.int64), return_inverse=True)
            et = np.bincount(inv, weights=e)
            xyz = np.column_stack([np.bincount(inv, weights=e * xyz[:, j]) / et for j in range(3)])
            e = et
        r = np.linalg.norm(xyz, axis=1)
        r[r == 0] = 1.0
        p4s.append(np.column_stack([e, e[:, None] * xyz / r[:, None]]))
        chs.append(np.full(len(e), k, dtype=np.int64))
    if not p4s:
        return np.zeros((0, 4)), np.zeros(0, dtype=np.int64)
    return np.concatenate(p4s), np.concatenate(chs)


def reco_jets(p4, chan, chi_c, chi_f):
    """Durham 4 jet + jet 단위 DR 보정. jet 4-vector (4,4) 를 E_DR 순서로."""
    jets = []
    for g in durham_n(p4, 4):
        sums = np.zeros((4, 4))
        for k in range(4):
            sel = chan[g] == k
            if sel.any():
                sums[k] = p4[g][sel].sum(axis=0)
        jets.append((sums[0] - chi_c * sums[1]) / (1 - chi_c) + (sums[2] - chi_f * sums[3]) / (1 - chi_f))
    jets.sort(key=lambda v: -v[0])
    return np.array(jets)


def mass(v):
    m2 = v[0] ** 2 - v[1] ** 2 - v[2] ** 2 - v[3] ** 2
    return math.copysign(math.sqrt(abs(m2)), m2)


def angle(a, b):
    na, nb = np.linalg.norm(a[1:]), np.linalg.norm(b[1:])
    if na == 0 or nb == 0:
        return math.pi
    return math.acos(max(-1.0, min(1.0, float(np.dot(a[1:], b[1:]) / (na * nb)))))


def hypotheses(mode):
    """(쌍 A, 쌍 B) 의 list. WW 는 3가지, ZH 는 A = Z, B = H 로 6가지."""
    if mode == "WW":
        return list(PAIRINGS)
    return [hyp for a, b in PAIRINGS for hyp in ((a, b), (b, a))]


def chi2_of(jets, hyp, targets, sigmas):
    return sum(((mass(jets[i] + jets[j]) - t) / s) ** 2 for (i, j), t, s in zip(hyp, targets, sigmas))


def same_pairing(mode, hyp_a, hyp_b):
    """WW 는 두 쌍의 순서가 의미 없고, ZH 는 A = Z, B = H 까지 같아야 같다."""
    a = tuple(frozenset(p) for p in hyp_a)
    b = tuple(frozenset(p) for p in hyp_b)
    return set(a) == set(b) if mode == "WW" else a == b


def best_match(jets, targets):
    """jets[perm[k]] 이 targets[k] 와 짝이 되는 순열 중 각도 합이 가장 작은 것. (perm, 각도 list)"""
    ang = np.array([[angle(j, t) for j in jets] for t in targets])
    best = min(PERMS, key=lambda p: sum(ang[k, p[k]] for k in range(4)))
    return best, [float(ang[k, best[k]]) for k in range(4)]


def truth_quarks(mcps, mode):
    """boson A 의 quark 2개, boson B 의 quark 2개 순서의 4-vector (4,4). 못 찾으면 None."""
    by_parent = {}
    for p in mcps:
        if p.getGeneratorStatus() != 23 or not 1 <= abs(p.getPDG()) <= 5:
            continue
        parents = [q for q in p.getParents() if abs(q.getPDG()) in (23, 24, 25)]
        if not parents:
            continue
        par = parents[0]
        mom = p.getMomentum()
        e = math.sqrt(mom.x ** 2 + mom.y ** 2 + mom.z ** 2 + p.getMass() ** 2)
        key = (par.getObjectID().index, par.getPDG())
        by_parent.setdefault(key, []).append([e, mom.x, mom.y, mom.z])
    if len(by_parent) != 2 or any(len(v) != 2 for v in by_parent.values()):
        return None
    order = {"WW": {24: 0, -24: 1}, "ZH": {23: 0, 25: 1}}[mode]
    keys = sorted(by_parent, key=lambda k: order.get(k[1], 9))
    if [order.get(k[1]) for k in keys] != [0, 1]:
        return None
    return np.array(by_parent[keys[0]] + by_parent[keys[1]])


def gen_inputs(mcps, with_nu, cos_max):
    p4 = []
    for p in mcps:
        if p.getGeneratorStatus() != 1:
            continue
        if not with_nu and abs(p.getPDG()) in NEUTRINOS:
            continue
        mom = p.getMomentum()
        pp = math.sqrt(mom.x ** 2 + mom.y ** 2 + mom.z ** 2)
        if pp == 0 or abs(mom.z) / pp > cos_max:
            continue
        p4.append([math.sqrt(pp ** 2 + p.getMass() ** 2), mom.x, mom.y, mom.z])
    return np.array(p4) if p4 else np.zeros((0, 4))


def gen_jets(p4):
    return np.array(sorted((p4[g].sum(axis=0) for g in durham_n(p4, 4)), key=lambda v: -v[0]))


def pair_masses(jets, perm):
    """정답 pairing: quark 0,1 (boson A) 과 짝지은 jet, quark 2,3 (boson B) 과 짝지은 jet."""
    return mass(jets[perm[0]] + jets[perm[1]]), mass(jets[perm[2]] + jets[perm[3]])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("WW", "ZH"), required=True)
    ap.add_argument("-i", "--input", nargs="+", required=True, help="Digi 디렉터리 / 파일 / glob")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--truth", action="store_true", help="MCParticles 로 truth 검증")
    ap.add_argument("--calib-json", default=DEFAULT_CALIB_JSON)
    ap.add_argument("--chi-fiber", type=float, default=None)
    ap.add_argument("--chi-crystal", type=float, default=None)
    ap.add_argument("--sigma-w", type=float, default=8.0, help="WW chi2 의 sigma [GeV]")
    ap.add_argument("--sigma-z", type=float, default=8.0, help="ZH chi2 의 Z sigma [GeV]")
    ap.add_argument("--sigma-h", type=float, default=8.0, help="ZH chi2 의 H sigma [GeV]")
    ap.add_argument("--match-cut", type=float, default=0.3, help="well_matched 판정: jet-quark 각도 상한 [rad]")
    ap.add_argument("--gen-cos-max", type=float, default=0.995, help="gen jet 에 넣는 입자의 |cos(theta)| 상한")
    ap.add_argument("--no-proto-cluster", action="store_true", help="DRC fiber 를 tower 로 묶지 않는다")
    ap.add_argument("--max-events", type=int, default=None)
    args = ap.parse_args()

    files = expand_inputs(args.input, "digi")
    if not files:
        sys.exit("입력 파일이 없다")
    consts, chi = load_calib(args.calib_json)
    chi_f = args.chi_fiber if args.chi_fiber is not None else chi["chi_fiber"]
    chi_c = args.chi_crystal if args.chi_crystal is not None else chi["chi_crystal"]
    proto = not args.no_proto_cluster
    mode = args.mode
    roles = ("W", "W") if mode == "WW" else ("Z", "H")
    targets = (M_W, M_W) if mode == "WW" else (M_Z, M_H)
    sigmas = (args.sigma_w, args.sigma_w) if mode == "WW" else (args.sigma_z, args.sigma_h)
    hyps = hypotheses(mode)
    print(f"{len(files)} files, mode = {mode}, truth = {args.truth}, proto-cluster = {proto}, "
          f"chi_fiber = {chi_f:.5f}, chi_crystal = {chi_c:.5f}, sigma = {sigmas}")

    init_fastjet()
    ROOT.gInterpreter.Declare(CPP_HELPER_N)

    kinds = ["chi2"] + (["true", "gen", "gen_nu"] if args.truth else [])
    kind_title = {"chi2": "reco jet, #chi^{2} pairing", "true": "reco jet, true pairing",
                  "gen": "gen jet (no #nu), true pairing", "gen_nu": "gen jet (with #nu), true pairing"}
    hist = {}
    for r in sorted(set(roles)):
        for kd in kinds:
            hist[f"h_m{r}_{kd}"] = ROOT.TH1D(f"h_m{r}_{kd}", f"m_{{jj}} ({r}): {kind_title[kd]};m_{{jj}} [GeV];Entries",
                                            160, 0, 200)
    hist["h_Esum"] = ROOT.TH1D("h_Esum", "#Sigma E_{jet} (DR);#Sigma E_{jet} [GeV];Events", 150, 0, 300)
    hist["h_chi2"] = ROOT.TH1D("h_chi2", "minimum #chi^{2};#chi^{2}_{min};Events", 100, 0, 50)
    hist["h_jetE"] = ROOT.TH1D("h_jetE", "reco jet energy (DR);E_{jet} [GeV];Jets", 150, 0, 150)
    if args.truth:
        hist["h_Eratio"] = ROOT.TH1D("h_Eratio", "jet response;E_{reco} / E_{gen} (no #nu);Jets", 150, 0, 1.5)
        hist["h_dangle"] = ROOT.TH1D("h_dangle", "reco jet - quark angle (matched);#Delta#alpha [rad];Jets", 100, 0, 1.0)
        hist["h_m4q"] = ROOT.TH1D("h_m4q", "m of 4 decay quarks (truth);m_{4q} [GeV];Events", 130, 110, 245)
        hist["h_Esum_gen"] = ROOT.TH1D("h_Esum_gen", "#Sigma E_{gen jet} (no #nu);#Sigma E [GeV];Events", 150, 0, 300)

    out = ROOT.TFile(args.output, "RECREATE")
    tree = ROOT.TTree("events", f"{mode} 4-jet reconstruction")
    br = {}

    def branch(name, n=1, typ="d"):
        br[name] = array(typ, [0] * n)
        leaf = "I" if typ == "i" else "D"
        tree.Branch(name, br[name], f"{name}[{n}]/{leaf}" if n > 1 else f"{name}/{leaf}")

    for name in ("m_A", "m_B", "chi2", "Esum"):
        branch(name)
    for name in ("jet_E", "jet_px", "jet_py", "jet_pz"):
        branch(name, 4)
    branch("evt_idx", typ="i")
    branch("valid", typ="i")
    if args.truth:
        for name in ("truth_valid", "pair_correct", "well_matched"):
            branch(name, typ="i")
        for name in ("m_A_true", "m_B_true", "m_A_gen", "m_B_gen", "m_A_gen_nu", "m_B_gen_nu", "m4q", "Esum_gen"):
            branch(name)
        for name in ("match_angle", "E_ratio"):
            branch(name, 4)

    n_valid = n_truth = n_correct = n_well = n_well_correct = 0
    t0 = time.time()
    for _, _, gidx, frame in iter_events(files, verbose=False):
        if args.max_events is not None and gidx >= args.max_events:
            break
        for a in br.values():
            for k in range(len(a)):
                a[k] = 0
        br["evt_idx"][0] = gidx
        p4, chan = reco_inputs(frame, consts, proto)
        if len(p4) < 4:
            tree.Fill()
            continue
        jets = reco_jets(p4, chan, chi_c, chi_f)
        chi2s = [chi2_of(jets, h, targets, sigmas) for h in hyps]
        best = hyps[int(np.argmin(chi2s))]
        m_a, m_b = (mass(jets[i] + jets[j]) for i, j in best)
        esum = float(jets[:, 0].sum())
        br["valid"][0] = 1
        br["m_A"][0], br["m_B"][0], br["chi2"][0], br["Esum"][0] = m_a, m_b, min(chi2s), esum
        for k in range(4):
            br["jet_E"][k], br["jet_px"][k], br["jet_py"][k], br["jet_pz"][k] = jets[k]
            hist["h_jetE"].Fill(jets[k][0])
        hist[f"h_m{roles[0]}_chi2"].Fill(m_a)
        hist[f"h_m{roles[1]}_chi2"].Fill(m_b)
        hist["h_Esum"].Fill(esum)
        hist["h_chi2"].Fill(min(chi2s))
        n_valid += 1

        if args.truth:
            mcps = frame.get("MCParticles")
            quarks = truth_quarks(mcps, mode)
            gp4 = gen_inputs(mcps, False, args.gen_cos_max)
            gp4_nu = gen_inputs(mcps, True, args.gen_cos_max)
            if quarks is not None and len(gp4) >= 4:
                perm, angs = best_match(jets, quarks)
                true_hyp = ((perm[0], perm[1]), (perm[2], perm[3]))
                correct = same_pairing(mode, best, true_hyp)
                gj = gen_jets(gp4)
                gj_nu = gen_jets(gp4_nu)
                gperm, _ = best_match(gj, quarks)
                gperm_nu, _ = best_match(gj_nu, quarks)
                m_true = pair_masses(jets, perm)
                m_gen = pair_masses(gj, gperm)
                m_gen_nu = pair_masses(gj_nu, gperm_nu)
                rperm, _ = best_match(gj, jets)
                quarks_sum = quarks.sum(axis=0)
                well = max(angs) < args.match_cut
                br["truth_valid"][0], br["pair_correct"][0], br["well_matched"][0] = 1, int(correct), int(well)
                br["m_A_true"][0], br["m_B_true"][0] = m_true
                br["m_A_gen"][0], br["m_B_gen"][0] = m_gen
                br["m_A_gen_nu"][0], br["m_B_gen_nu"][0] = m_gen_nu
                br["m4q"][0] = mass(quarks_sum)
                br["Esum_gen"][0] = float(gj[:, 0].sum())
                for k in range(4):
                    br["match_angle"][k] = angs[k]
                    br["E_ratio"][k] = jets[k][0] / gj[rperm[k]][0]
                    hist["h_Eratio"].Fill(br["E_ratio"][k])
                    hist["h_dangle"].Fill(angs[k])
                for kd, (va, vb) in (("true", m_true), ("gen", m_gen), ("gen_nu", m_gen_nu)):
                    hist[f"h_m{roles[0]}_{kd}"].Fill(va)
                    hist[f"h_m{roles[1]}_{kd}"].Fill(vb)
                hist["h_m4q"].Fill(br["m4q"][0])
                hist["h_Esum_gen"].Fill(br["Esum_gen"][0])
                n_truth += 1
                n_correct += int(correct)
                n_well += int(well)
                n_well_correct += int(well and correct)
        tree.Fill()
        if (gidx + 1) % 100 == 0:
            print(f"  {gidx + 1} events ({time.time() - t0:.0f} s)", flush=True)

    n_all = tree.GetEntries()
    print(f"\n{n_all} events, {n_valid} with 4 jets, {time.time() - t0:.0f} s")
    print(f"  sum E_jet (DR): hist mean = {hist['h_Esum'].GetMean():.2f} GeV")
    fits = {}
    for r in sorted(set(roles)):
        for kd in kinds:
            name = f"h_m{r}_{kd}"
            fit = gauss_fit(hist[name])
            fits[name] = fit
            print(f"  m({r}) {kind_title[kd].replace('#', ''):<34}: entries = {int(hist[name].GetEntries()):5d}  "
                  f"hist mean = {hist[name].GetMean():6.2f}  "
                  + (f"Gaussian fit mean = {fit[0]:6.2f}, sigma = {fit[1]:5.2f} GeV" if fit else "fit 실패 (entries < 20 또는 fit 실패)"))
    if args.truth:
        eff = n_correct / n_truth if n_truth else float("nan")
        eff_w = n_well_correct / n_well if n_well else float("nan")
        print(f"  truth: {n_truth} events matched, pairing efficiency = {n_correct}/{n_truth} = {eff:.3f}")
        print(f"         well matched (all jet-quark angles < {args.match_cut} rad): {n_well}/{n_truth} events, "
              f"pairing efficiency = {n_well_correct}/{n_well} = {eff_w:.3f}")
        print(f"  jet response E_reco/E_gen: mean = {hist['h_Eratio'].GetMean():.3f}, RMS = {hist['h_Eratio'].GetRMS():.3f}")
        print(f"  sum E_gen jet (no nu): mean = {hist['h_Esum_gen'].GetMean():.2f} GeV,  m_4q mean = {hist['h_m4q'].GetMean():.2f} GeV")

    out.cd()
    tree.Write()
    for h in hist.values():
        h.Write()
    for key, val in (("mode", mode), ("chi_fiber", chi_f), ("chi_crystal", chi_c), ("proto_cluster", proto),
                     ("sigmas", sigmas), ("n_events", n_all), ("inputs", ";".join(files))):
        ROOT.TNamed(key, str(val)).Write()
    if args.truth:
        ROOT.TNamed("pairing_efficiency", f"{n_correct}/{n_truth}").Write()
        ROOT.TNamed("pairing_efficiency_well_matched", f"{n_well_correct}/{n_well}").Write()

    keep = []
    colors = {"chi2": ROOT.kBlack, "true": ROOT.kRed + 1, "gen": ROOT.kBlue + 1, "gen_nu": ROOT.kGreen + 2}
    for r in sorted(set(roles)):
        c = ROOT.TCanvas(f"c_mass_{r}", f"m(jj) for {r}", 900, 700)
        c.SetGrid()
        hs = [hist[f"h_m{r}_{kd}"] for kd in kinds]
        ymax = max(h.GetMaximum() for h in hs)
        leg = ROOT.TLegend(0.12, 0.65, 0.55, 0.88)
        leg.SetBorderSize(0)
        for n, (kd, h) in enumerate(zip(kinds, hs)):
            h.SetLineColor(colors[kd])
            h.SetLineWidth(2)
            h.SetMaximum(ymax * 1.3)
            h.SetTitle(f"m_{{jj}} ({r});m_{{jj}} [GeV];Entries")
            h.Draw("hist" if n == 0 else "hist same")
            fit = fits[f"h_m{r}_{kd}"]
            leg.AddEntry(h, kind_title[kd] + (f": #mu = {fit[0]:.1f}, #sigma = {fit[1]:.1f}" if fit else ""), "l")
        leg.Draw()
        c.Write()
        keep += [c, leg]

    c2 = ROOT.TCanvas("c_summary", "summary", 1500, 500)
    panels = ["h_Esum", "h_chi2", "h_jetE"] + (["h_Eratio"] if args.truth else [])
    c2.Divide(len(panels), 1)
    for n, name in enumerate(panels, 1):
        c2.cd(n).SetGrid()
        hist[name].SetLineWidth(2)
        hist[name].Draw("hist")
        if name == "h_Esum" and args.truth:
            hist["h_Esum_gen"].SetLineColor(ROOT.kBlue + 1)
            hist["h_Esum_gen"].SetLineWidth(2)
            hist["h_Esum_gen"].Draw("hist same")
    c2.Write()
    keep.append(c2)
    out.Close()
    print(f"\nwrote {args.output}")


if __name__ == "__main__":
    main()
