"""분석 스크립트 공통 함수 (podio 읽기, calibration json, Gaussian fit).

사용 전에:  source setup_env.sh
"""
import glob
import json
import os

import ROOT
from podio import root_io

ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kError

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CALIB_JSON = os.path.join(HERE, "calib_constants.json")

# ---- collection 이름 ----
# SCEPCal (crystal ECAL): Sim collection 의 photo-electron 수 (digitizer 없음). Digi 파일에도 복사되어 있다.
ECAL_S = "SCEPCal_MainScounts"
ECAL_C = "SCEPCal_MainCcounts"
# fiber DRC: Digi collection (SiPM emulation 후, scaleADC = 1 이라 raw 신호 단위)
DRC_S = "DRcaloSiPMreadoutDigiHit_scint"
DRC_C = "DRcaloSiPMreadoutDigiHit"

# 채널 -> (collection, calibration constant 이름)
CHANNELS = {
    "ecal_S": (ECAL_S, "S_crystal"),
    "ecal_C": (ECAL_C, "C_crystal"),
    "drc_S": (DRC_S, "S_fiber"),
    "drc_C": (DRC_C, "C_fiber"),
}

# DectDimensions_IDEA_o3_v01.xml 의 반경 [mm]: shower start 위치 분류에 쓴다.
R_ECAL_INNER = 2250.0  # scepcal_barrel_inner_r
R_SOLENOID_INNER = 2500.0  # Solenoid_inner_radius (crystal ECAL 바깥)
R_DRC_INNER = 2805.0  # FiberDRCalo_barrel_tube_outer_radius (DRC 앞면)

# beam point p0~p3 의 theta [deg]
THETA_DEG = {"p0": 89.44, "p1": 66.94, "p2": 44.44, "p3": 25.31}


def expand_inputs(items, kind="digi"):
    """디렉터리 / 파일 / glob 의 리스트 -> 정렬된 파일 리스트.

    디렉터리를 주면 그 안의 *_<kind>_*.root 만 잡는다. (TrackHitDistances_N.root 같은 부산물이
    같은 디렉터리에 있으므로 '*.root' 로 잡으면 안 된다.)
    """
    files = []
    for item in items:
        if os.path.isdir(item):
            matches = sorted(glob.glob(os.path.join(item, f"*_{kind}_*.root")))
        else:
            matches = sorted(glob.glob(item))
        files.extend(matches if matches else [item])
    return list(dict.fromkeys(files))


def iter_events(files, verbose=True):
    """모든 파일의 모든 event 에 대해 (파일, 파일 내 번호, 전체 번호, frame) 을 yield."""
    global_idx = 0
    for fpath in files:
        try:
            reader = root_io.Reader(fpath)
            events = reader.get("events")
            n = len(events)
        except Exception as exc:  # 깨진 파일은 건너뛴다
            print(f"  [skip] {fpath}: {exc}")
            continue
        if verbose:
            print(f"  {os.path.basename(fpath)}: {n} events")
        for local_idx, frame in enumerate(events):
            yield fpath, local_idx, global_idx, frame
            global_idx += 1


def load_calib(path=None):
    """calibration json 을 읽어 (constants dict, chi dict) 를 돌려준다.

    constants: S_crystal, C_crystal, S_fiber, C_fiber  ((raw sum) * const = GeV)
    chi      : {"chi_fiber": .., "chi_crystal": ..} (없으면 빈 dict)
    """
    path = path or DEFAULT_CALIB_JSON
    with open(path) as f:
        data = json.load(f)
    consts = {k: v["value"] for k, v in data.get("constants", {}).items()}
    chi = {k: data["chi"][k] for k in ("chi_fiber", "chi_crystal") if k in data.get("chi", {})}
    return consts, chi


def merge_json(path, section, content):
    """json 파일의 section ('constants' 또는 'chi') 을 갱신 (다른 내용은 유지)."""
    data = {}
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
    if section == "constants":
        data.setdefault("constants", {}).update(content)
    else:
        data[section] = content
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def dr_energy(s, c, chi):
    """Dual-readout 보정 에너지 E = (S - chi*C) / (1 - chi)."""
    return (s - chi * c) / (1.0 - chi)


def padded_range(values, pad=0.1, lo_floor=None):
    lo, hi = min(values), max(values)
    span = hi - lo if hi > lo else max(abs(hi), 1.0)
    lo, hi = lo - pad * span, hi + pad * span
    if lo_floor is not None:
        lo = max(lo, lo_floor)
    return lo, hi


def make_hist(name, title, values, nbins=200, pad=0.1, lo_floor=None):
    """값 리스트의 실제 범위에 맞춰 범위를 잡은 TH1D 를 만든다.

    고정 범위를 쓰면 범위 밖 event 가 overflow 로 사라지고 TH1::GetMean() 은 overflow 를 빼고
    계산하므로 mean 이 조용히 틀려진다. 그래서 항상 데이터 범위로 잡는다.
    """
    lo, hi = padded_range(values, pad, lo_floor)
    h = ROOT.TH1D(name, title, nbins, lo, hi)
    h.Sumw2()
    for v in values:
        h.Fill(v)
    return h


def gauss_fit(hist):
    """2-pass Gaussian fit: [mean-2rms, mean+2rms] 에서 한 번, 그 결과의 peak +- 2 sigma 에서 다시.
    성공하면 (mean, sigma, mean_err, sigma_err) 를, 실패하면 None 을 돌려준다.
    fit 함수는 hist 에 붙어 있어서 hist 를 저장/그리면 같이 나온다."""
    if hist.GetEntries() < 20:
        return None
    mean, rms = hist.GetMean(), hist.GetRMS()
    res = hist.Fit("gaus", "QS", "", mean - 2 * rms, mean + 2 * rms)
    if not res.Get() or not res.Get().IsValid():
        return None
    f = hist.GetFunction("gaus")
    lo, hi = f.GetParameter(1) - 2 * f.GetParameter(2), f.GetParameter(1) + 2 * f.GetParameter(2)
    hist.Fit("gaus", "QS", "", lo, hi)
    f = hist.GetFunction("gaus")
    return f.GetParameter(1), f.GetParameter(2), f.GetParError(1), f.GetParError(2)


def guess_beam_energy(files):
    """경로 안의 '..._<N>GeV_...' 에서 beam energy 를 추정 (없으면 None)."""
    import re

    for f in files:
        m = re.search(r"(\d+(?:\.\d+)?)GeV", f)
        if m:
            return float(m.group(1))
    return None
