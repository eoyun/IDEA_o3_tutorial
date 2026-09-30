# IDEA o3 Dual-Readout Calorimeter Tutorial

FCC-ee IDEA 검출기의 **o3 calorimeter** (crystal ECAL `SCEPCal` + fiber Dual-Readout Calorimeter `DRC`)
를 key4hep 으로 시뮬레이션하고, dual-readout 분석을 해 보는 tutorial 입니다.
tutorial 에 참석하지 못한 사람도 이 문서만 따라 하면 되도록 썼습니다.

- 시뮬레이션은 모두 **noOpt** (no optical) 모드입니다. 가장 빠르고, 이 tutorial 의 결과가 모두 이 모드로 만든 것입니다.
- `condor` 는 "이렇게 제출한다" 를 보여 주는 용도입니다. 실제 분석용 대량 샘플은 미리 만들어 둔 것을 씁니다.
- full optical simulation (fullSim) 의 **Digi 는 현재 지원하지 않습니다** → [fullSim Digi 미지원](#11-fullsim-digi-미지원) 절을 읽어 주세요.

## 목차

1. [준비물](#1-준비물)
2. [설치](#2-설치-installsh)
3. [디렉터리 구조](#3-디렉터리-구조)
4. [미리 만들어 둔 샘플](#4-미리-만들어-둔-샘플)
5. [Step 1. Simulation (particle gun)](#5-step-1-simulation-particle-gun)
6. [Step 2. condor 로 제출하기](#6-step-2-condor-로-제출하기)
7. [Step 3. Digitization](#7-step-3-digitization)
8. [Step 4. 분석 (gun 샘플)](#8-step-4-분석-gun-샘플)
9. [Step 5. Physics 샘플 (Z→ee, Z→qq)](#9-step-5-physics-샘플-zee-zqq)
10. [내 fork 로 작업하기](#10-내-fork-로-작업하기)
11. [fullSim Digi 미지원](#11-fullsim-digi-미지원)
12. [자주 겪는 문제](#12-자주-겪는-문제)
13. [자원 / 시간 / 용량 안내](#13-자원--시간--용량-안내)

---

## 1. 준비물

- 이 서버의 본인 계정. **`fcc_users` 그룹** 에 속해 있어야 합니다 (`id` 로 확인).
  미리 만들어 둔 샘플이 `/fcc/home/sungwon/...` 에 있고, 이 경로는 `fcc_users` 만 읽을 수 있습니다.
- CVMFS 의 key4hep 릴리즈 (`2026-04-08`). 서버에 이미 있습니다.
- condor (`condor_submit`, `condor_q`). 서버에 이미 있습니다.
- 디스크: 설치에 수 GB. Sim / Digi 출력은 용량이 크므로 (Sim 한 파일이 수십 MB ~ 수백 MB) 조금만 만드세요.

## 2. 설치 (`install.sh`)

```bash
git clone https://github.com/swkim95/IDEA_o3_tutorial.git
cd IDEA_o3_tutorial
nohup ./install.sh > install.log 2>&1 &     # 기본 make -j4
tail -f install.log                          # 진행 상황
```

- 코어 수를 바꾸려면 인자로 줍니다: `./install.sh 2` (서버를 같이 쓰므로 **4 이하** 를 권장합니다).
- 오래 걸립니다 (서버 부하에 따라 30분 ~ 1시간 이상). 로그아웃해도 계속 돌도록 `nohup` (또는 `tmux`) 으로 돌리세요.
- 실패하면 원인을 고치고 `./install.sh` 를 다시 실행하면 됩니다. 이미 끝난 패키지는 건너뜁니다.

`install.sh` 가 하는 일 (모두 `packages/` 아래):

| 패키지 | 출처 / 버전 | 용도 |
|---|---|---|
| `genfit` | `GenFit/GenFit` @ `1eceeb7` | k4RecTracker 빌드에 필요 |
| `k4geo` | `swkim95/k4geo`, branch `geo_o3_tutorial` | o3 geometry. 이 tutorial 의 nominal 설정이 들어 있음 |
| `k4RecTracker` | `swkim95/k4RecTracker`, branch `edm4hep_trackstate_fix` | Digi 스크립트가 쓰는 tracker digitizer / tracking |
| ONNX 모델 | `digi/SimpleGatrIDEAv3o1.onnx` | tracker reco 모델 (Digi 스크립트가 읽음) |

`k4geo` 의 nominal 상태: Birks 보정 ON (dd4hep), neutral particle filtering ON, S-channel noOpt,
DRC air-gap 수정, cellID y-bit guard.

설치 후, **새 터미널을 열 때마다** 환경을 잡습니다:

```bash
cd IDEA_o3_tutorial
source setup_env.sh
which ddsim k4run       # 둘 다 나와야 함
```

`setup_env.sh` 가 하는 일: CVMFS key4hep `2026-04-08` 를 source 하고, 위에서 빌드한 `genfit`, `k4RecTracker`,
`k4geo` 를 `LD_LIBRARY_PATH` / `PYTHONPATH` 에 얹고, 아래 변수를 설정합니다.

| 변수 | 의미 |
|---|---|
| `IDEA_TUTORIAL_ROOT` | 이 repo 의 경로 |
| `K4GEO_LOCAL` | 내가 빌드한 `k4geo` 소스 (compact XML 이 여기 있음) |
| `TUTORIAL_SAMPLES` | sungwon 이 미리 만든 샘플 (읽기 전용) |
| `TUTORIAL_OUTPUT` | 내가 만드는 출력 위치 (기본 `./condor_output`) |

## 3. 디렉터리 구조

```
IDEA_o3_tutorial/
├── install.sh, setup_env.sh
├── sim/       SteeringFile_o3_gun.py        particle gun (e-, pi-) noOpt steering
│              SteeringFile_o3_physics.py    Z->ee, Z->qq (HepMC 입력) noOpt steering
├── digi/      run_digi_reco.py              noOpt Digi (scaleADC = 1)
├── gen/       pythia.py, p8_ee_Zee_eCM91.cmd, p8_ee_Zqq_eCM91.cmd
├── condor/    gun_sim/  digi/  gen_sim/     condor 제출 template (wrapper + .sub)
├── analysis/  분석 스크립트 (아래 Step 4, 5), calib_constants.json (nominal 값)
└── condor_log/                              condor 로그
```

geometry 는 세 가지가 있습니다 (`k4geo/FCCee/IDEA/compact/IDEA_o3_v01/`):

| XML | 내용 | 용도 |
|---|---|---|
| `IDEA_o3_v01.xml` | 전체 o3, 자기장 ON | physics (Z→ee, Z→qq) |
| `IDEA_o3_v01_noField.xml` | 전체 o3, 자기장 OFF | ECAL calibration / resolution (gun) |
| `IDEA_o3_v01_DRConly_noField.xml` | DRC 만 (ECAL, solenoid 없음), 자기장 OFF | DRC EM calibration (gun) |

## 4. 미리 만들어 둔 샘플

`$TUTORIAL_SAMPLES` (= `/fcc/home/sungwon/2026_Oct_KEY4HEP_tutorial/k4geo/example/condor_output`) 에 있습니다.
모두 noOpt, 입사 각도 1°, vertex smearing 8 mm 입니다. 디렉터리 이름은 `*_Sim` 과 `*_Digi` 로 끝납니다.

| 용도 | Digi 디렉터리 (Sim 은 `_Digi` → `_Sim`) |
|---|---|
| ECAL EM calibration, EM resolution (e-, p0) | `o3_res_eminus_{10,20,40,60,80}GeV_p0_noOpt_Digi` |
| ECAL theta 의존성 (e- 40 GeV, p1–p3) | `o3_res_eminus_40GeV_p{1,2,3}_noOpt_Digi` |
| DRC EM calibration, theta 의존성 (e- 40 GeV, DRC-only) | `o3_calibB_drc_eminus_40GeV_p{0,1,2,3}_noOpt_scaleADC1_Digi` |
| chi 계산 (pi- 40 GeV) | `o3_calibB_piminus_40GeV_p0_noOpt_scaleADC1_Digi` |
| hadron resolution (pi-, p0) | `o3_res_piminus_{10,20,40,60,80}GeV_p0_noOpt_Digi` |
| physics (field ON, 3000 event) | `o3_ee_eCM91_seedfix_noOpt_{Sim,Digi}`, `o3_qqbar_eCM91_seedfix_noOpt_{Sim,Digi}` |

주의: Digi 디렉터리에는 `TrackHitDistances_N.root` 같은 부산물도 있어서, 분석 스크립트에 디렉터리를 주면
`*_digi_*.root` 만 읽도록 되어 있습니다.

## 5. Step 1. Simulation (particle gun)

`sim/SteeringFile_o3_gun.py` 하나로 모든 gun 샘플을 만듭니다. 파일 위쪽 **USER SETTINGS** 블록을 고치면 됩니다.

| 설정 | 값 |
|---|---|
| `GEOMETRY` | `"full"` (ECAL + DRC) / `"DRConly"` |
| `PARTICLE`, `ENERGY` | `"e-"` (EM) 또는 `"pi-"` (hadron), 10/20/40/60/80 GeV |
| `POINT` | `"p0"` ~ `"p3"` (beam 위치/방향, 아래 표) |
| `VERTEX_SIGMA` | 8 mm |

beam 은 tower 의 pointing axis 에서 x 방향으로 약 50 mm 떨어뜨려 놓고 tower 중심을 겨냥하므로 fiber 방향과
약 **1°** 기울어져 입사합니다.

| point | theta | 조준하는 곳 |
|---|---|---|
| p0 | 89.44° | barrel 첫 tower (equator) |
| p1 | 66.94° | barrel 중간 |
| p2 | 44.44° | endcap 첫 tower (barrel/endcap 경계) |
| p3 | 25.31° | endcap 중간 |

에너지 scan 을 할 때는 `ENERGY` 를 바꿔서 energy 마다 따로 만듭니다 (resolution 용: 10, 20, 40, 60, 80 GeV).

```bash
source setup_env.sh
mkdir -p $TUTORIAL_OUTPUT && cd $TUTORIAL_OUTPUT
ddsim --steeringFile $IDEA_TUTORIAL_ROOT/sim/SteeringFile_o3_gun.py \
      --numberOfEvents 2 --outputFile test_sim.root \
      --random.enableEventSeed --random.seed 1
```

- **시작하는 데 15분 이상 걸립니다** (geometry 를 올리는 시간; event 자체는 그 뒤에 금방 돕니다).
  그래서 event 는 한 번에 여러 개 돌리는 것이 효율적이고, 대량 생산은 condor 를 씁니다.
- 명령행 옵션 (`--gun.energy "20*GeV"` 등) 은 steering file 의 값을 덮어씁니다.
- seed 는 job 마다 달라야 합니다 (같은 seed 면 똑같은 event 가 나옵니다).

### (참고) full optical simulation

steering file 안에 `[FULL-OPTICAL 1/4]` ~ `[FULL-OPTICAL 4/4]` 주석 블록이 있고, 그 위쪽에 켜는 방법이 적혀 있습니다
(geometry XML 교체, `skipScint=false`, Scintillation 물리 추가 등). **기본은 모두 꺼져 있고**, 이 tutorial 은 켜지 않습니다.
full optical Sim 은 optical photon 을 모두 추적하므로 noOpt 보다 느립니다. 그리고 그 출력의 Digi 는 지원하지 않습니다 ([아래](#11-fullsim-digi-미지원)).

## 6. Step 2. condor 로 제출하기

> **`accounting_group`**: 제출할 때는 항상 group 을 지정해야 합니다. 제공된 `.sub` 파일에는 `accounting_group = group_fcc` 가 들어 있으니 지우지 말고, 직접 `.sub` 를 만들 때도 같은 줄을 넣으세요.
> 제출 후 `condor_q -af AcctGroup` 에 `group_fcc` 가 나오는지 확인할 수 있습니다.
>
> 각 job 이 얼마나 오래 걸리고 얼마의 메모리/용량을 쓰는지는 [13장](#13-자원--시간--용량-안내)을 보고 제출하세요.

`condor/gun_sim/submit_sim.sub` 를 복사/수정해서 제출합니다 (`setup_env.sh` 를 source 한 터미널에서, repo 루트에서).
`.sub` 안의 변수 (`TAG`, `NJOBS`, `NEV`, ...) 는 파일을 고치거나 `-a "이름=값"` 으로 덮어씁니다.
(`condor_submit 파일 이름=값` 형태는 파일 안의 값이 이겨서 적용되지 않습니다.)

```bash
condor_submit -a "TAG=my_eminus_40GeV_p0" -a "NJOBS=3" -a "NEV=10" condor/gun_sim/submit_sim.sub
condor_q                                   # 내 job 상태
condor_tail <cluster>.<proc>               # 실행 중인 job 의 출력 (예: condor_tail 12345.0). .out/.err 는 job 이 끝나야 생긴다
```

- 출력: `condor_output/<TAG>_Sim/<TAG>_sim_<번호>.root`. job 번호 + 1 이 random seed 입니다.
- 사용할 steering 은 `STEERING=...` 로 바꿉니다. 사본을 만들어서 `POINT`, `ENERGY` 등을 고치세요.
- 메모리는 16000 MB 를 요청합니다 (관측된 실제 최대는 약 9.8 GB, [13장](#13-자원--시간--용량-안내) 참고).
- **job 이 시작해서 첫 event 가 나오기까지 보통 20~30분 (빠르면 10분) 걸립니다.** `.err` / `.out` 이 한참 조용해도 정상입니다.
- 시간 관계상 tutorial 에서는 제출까지만 보여 주고, 이후 분석은 미리 만든 샘플을 씁니다.

## 7. Step 3. Digitization

Sim 출력 → Digi 출력입니다. `digi/run_digi_reco.py` 가 하는 일:

- DRC S channel: `SimulateSiPMwithEdep`, DRC C channel: `SimulateSiPMwithOpticalPhoton`
  (SiPM 응답 emulation; `scaleADC = 1.0` 로 고정. 이 tutorial 의 calibration constant 는 이 값 기준)
- crystal ECAL 은 digitizer 가 없어서, Sim 의 `SCEPCal_MainScounts`, `SCEPCal_MainCcounts` (photo-electron 수) 를 그대로 씁니다.
  Digi 출력 파일에 그대로 복사되어 있으므로 **분석에는 Digi 파일 하나만 있으면 됩니다.**

환경변수 두 개가 필요합니다: `DIGI_COMPACT_XML` (Sim 에 쓴 XML, `$K4GEO_LOCAL` 기준 상대경로),
`DIGI_SKIP_HELIX_TRACKING` (자기장 OFF geometry 는 **반드시 1**).

```bash
source setup_env.sh
export DIGI_COMPACT_XML=FCCee/IDEA/compact/IDEA_o3_v01/IDEA_o3_v01_noField.xml
export DIGI_SKIP_HELIX_TRACKING=1
k4run $IDEA_TUTORIAL_ROOT/digi/run_digi_reco.py \
      --IOSvc.Input test_sim.root --IOSvc.Output test_digi.root \
      --RootHistoSink.FileName test_trackhits.root
```

condor 로는:

```bash
condor_submit -a "SIM_DIR=$TUTORIAL_OUTPUT/my_eminus_40GeV_p0_Sim" -a "DIGI_TAG=my_eminus_40GeV_p0" \
    -a "NJOBS=3" condor/digi/submit_digi.sub
```

geometry 별 설정:

| Sim 샘플 | `DIGI_COMPACT_XML` | `DIGI_SKIP_HELIX` |
|---|---|---|
| gun, full | `.../IDEA_o3_v01_noField.xml` | 1 |
| gun, DRConly | `.../IDEA_o3_v01_DRConly_noField.xml` | 1 |
| physics (Z→ee, Z→qq) | `.../IDEA_o3_v01.xml` | 0 |

## 8. Step 4. 분석 (gun 샘플)

모든 스크립트는 `analysis/` 에 있고, 결과는 **ROOT 파일** (histogram, TGraph, TCanvas) 로 저장됩니다. PNG 는 만들지 않습니다.
`root -l out.root` → `new TBrowser` 로 열어서 canvas 를 보세요. 터미널에도 핵심 숫자를 출력합니다.
`-h` 로 각 스크립트의 설명과 옵션을 볼 수 있습니다.

### 8.0 calibration constant 란

`calibration constant` 는 "raw 신호의 합 × constant = beam energy" 가 되도록 하는 상수입니다.
채널이 네 개입니다: `S_crystal`, `C_crystal` (ECAL), `S_fiber`, `C_fiber` (DRC).
nominal 값은 `analysis/calib_constants.json` 에 들어 있습니다. 직접 구하면 같은 값이 나와야 합니다.

스크립트는 기본적으로 nominal json 을 씁니다. **내가 구한 값을 쓰려면** `--json my.json` 으로 저장하고,
이후 스크립트에 `--calib-json my.json` 을 주세요.

### 8.1 EM calibration (mean 기반)

```bash
cd analysis
python3 em_calib.py -i $TUTORIAL_SAMPLES/o3_res_eminus_40GeV_p0_noOpt_Digi --detector ecal \
    -o ecal_calib.root --json my.json
python3 em_calib.py -i $TUTORIAL_SAMPLES/o3_calibB_drc_eminus_40GeV_p0_noOpt_scaleADC1_Digi --detector drc \
    -o drc_calib.root --json my.json
```

ECAL S/C 와 DRC S/C 의 constant 를 터미널에 출력하고 `my.json` 에 기록합니다.
(nominal: `S_crystal = 5.0827e-4`, `C_crystal = 1.0225e-2`, `S_fiber = 3.6158e-4`, `C_fiber = 5.4575e-4`)

### 8.2 theta 에 따른 response

```bash
python3 response_vs_theta.py --detector drc -o response_drc.root -i \
    $TUTORIAL_SAMPLES/o3_calibB_drc_eminus_40GeV_p{0,1,2,3}_noOpt_scaleADC1_Digi
python3 response_vs_theta.py --detector ecal -o response_ecal.root -i \
    $TUTORIAL_SAMPLES/o3_res_eminus_40GeV_p{0,1,2,3}_noOpt_Digi
```

p0 에서 구한 constant 를 p1–p3 에 적용했을 때 `mean / E_beam` 이 1 에서 얼마나 벗어나는지 (theta 방향 균일성) 를 봅니다.

### 8.3 dual-readout 보정: chi

dual-readout 에너지는 `E_DR = (S − χ·C) / (1 − χ)` 입니다. `χ` 를 pi- 40 GeV 샘플에서 구합니다.

```bash
python3 make_pion_ntuple.py -i $TUTORIAL_SAMPLES/o3_calibB_piminus_40GeV_p0_noOpt_scaleADC1_Digi \
    -o pion_ntuple_40GeV.root
python3 compute_chi.py pion_ntuple_40GeV.root -o chi_40GeV.root --json my.json
```

- `make_pion_ntuple.py` 는 event loop 가 들어 있는 느린 단계라 한 번만 돌리고 (수 분), `compute_chi.py` 는 그 ntuple 만 읽습니다.
- `chi_fiber`: hadron shower 가 **DRC 에서 시작한** event (truth: primary pi- 의 endpoint 반경 ≥ 2805 mm) 만 골라서 구합니다 **[채택]**.
  비교용으로 "ECAL 에서 MIP 처럼 지나간 event (ECAL S < 0.5 GeV)" 로 고른 결과도 같이 그립니다 (purity / efficiency 출력).
- `chi_crystal`: 전체 event 에서, 이미 구한 fiber DR 에너지를 빼고 남은 에너지 `E' = E_beam − E_DR,fiber` 를 crystal 이 받았다고 보고 구합니다.
  **주의: `chi_crystal` 은 `E'` 에 매우 민감합니다** (`E'` 가 ±1 GeV 변하면 0.20 ~ 0.64). 출력의 sensitivity 와 RMS-scan 값을 같이 보세요.
- shower 시작 반경 분포에 세 영역 경계 (2250 / 2500 / 2805 mm) 선이 그려집니다.
- nominal: `chi_fiber = 0.43975`, `chi_crystal = 0.50503`.

### 8.4 EM energy resolution / linearity

energy 마다 histogram 을 만들고 (9개: `{ECAL, DRC, Total} × {S, C, DR}`, 모두 Gaussian fit), 마지막에 한꺼번에 그립니다.

```bash
for E in 10 20 40 60 80; do
  python3 resolution_hists.py -i $TUTORIAL_SAMPLES/o3_res_eminus_${E}GeV_p0_noOpt_Digi -o em_${E}GeV.root
done
python3 draw_resolution.py --mode em -i em_{10,20,40,60,80}GeV.root -o em_plots.root
```

- 그림: ECAL S, C 와 Total S, C 의 resolution 과 linearity.
- resolution 은 `σ/mean` 을 `1/√E` 에 대해 `pol1` (`a/√E + c`) 로 fit 합니다. (`a` = stochastic term, `c` = constant term)
- Gaussian fit 은 histogram bin 수에 조금 의존합니다 (`--nbins`, 기본 200). 예전 결과와 몇 % 차이가 날 수 있습니다.

### 8.5 hadron energy resolution / linearity

```bash
for E in 10 20 40 60 80; do
  python3 resolution_hists.py -i $TUTORIAL_SAMPLES/o3_res_piminus_${E}GeV_p0_noOpt_Digi -o had_${E}GeV.root
done
python3 draw_resolution.py --mode had -i had_{10,20,40,60,80}GeV.root -o had_plots.root
```

- 그림: Total DR 의 resolution, 그리고 Total S / C / DR 의 linearity.
- `resolution_hists.py` 는 `--calib-json` 의 `chi` 를 씁니다 (`--chi-fiber`, `--chi-crystal` 로 덮어쓸 수도 있음).
  `Total DR = ECAL DR + DRC DR` (각각 자기 `chi` 사용).
- hadron 의 S, C 는 Gaussian 이 아니라서 linearity 는 histogram mean 을 씁니다. DR 은 Gaussian fit 입니다.
- 참고: nominal 결과에서 DR linearity 는 1 근처 (±0.5% 안팎) 이고 S, C 는 energy 가 낮을수록 1 에서 멉니다 (hadron 의 invisible energy 때문).

## 9. Step 5. Physics 샘플 (Z→ee, Z→qq)

eCM = 91 GeV 의 Z→ee, Z→qq 입니다. Pythia8 (`gen/`) → HepMC → ddsim (자기장 ON, `IDEA_o3_v01.xml`) → Digi.

### 9.1 생성 + Sim (condor 제출 예)

```bash
condor_submit -a "TAG=my_Zqq_eCM91" -a "CARD=$IDEA_TUTORIAL_ROOT/gen/p8_ee_Zqq_eCM91.cmd" \
    -a "NJOBS=2" -a "NEV=5" condor/gen_sim/submit_gen_sim.sub
# Z->ee 는 CARD=$IDEA_TUTORIAL_ROOT/gen/p8_ee_Zee_eCM91.cmd
```

job 하나가 `gen/pythia.py` (k4run) 로 HepMC 를 만들고 이어서 `sim/SteeringFile_o3_physics.py` 로 ddsim 을 돌립니다.
Pythia seed 와 ddsim seed 는 job 번호 + 1 입니다. Digi 는 [Step 3](#7-step-3-digitization) 의 physics 설정으로 제출합니다.

### 9.2 분석 (미리 만든 샘플 사용)

먼저 Digi 에서 **hit 단위 ntuple** 을 만듭니다 (3000 event 에 ee 는 약 1분, qq 는 약 3분).

```bash
python3 make_physics_ntuple.py -i $TUTORIAL_SAMPLES/o3_ee_eCM91_seedfix_noOpt_Digi -o ee_ntuple.root
python3 make_physics_ntuple.py -i $TUTORIAL_SAMPLES/o3_qqbar_eCM91_seedfix_noOpt_Digi -o qq_ntuple.root
```

**(a) hit 수준: `plot_physics_hits.py`**

```bash
python3 plot_physics_hits.py ee_ntuple.root -o ee_hits.root --event 5
python3 plot_physics_hits.py qq_ntuple.root -o qq_hits.root --event 5
```

- 각 hit 을 massless 4-vector 로 보고 event 마다 합해서 ECAL / DRC / Total 의 S, C, DR 의 E 와 invariant mass 를 그립니다.
  Total DR 질량의 Gaussian fit 이 **Z mass peak** 입니다 (nominal: Z→ee 에서 ≈ 91.8 GeV).
- hit 에너지 분포, event 당 hit 수, z–r 분포
- ECAL / DRC 의 S, C `eta–phi` 2D map (모든 event 합, 그리고 `--event N` 한 event)

**(b) jet: `reco_physics_jets.py` (Z→qq)**

```bash
python3 reco_physics_jets.py qq_ntuple.root -o qq_jets.root --event 5     # 3000 event 에 약 10분
```

- fastjet **Durham** 알고리즘으로 정확히 2 jet 을 만들고, jet 별로 DR 보정을 적용해 `m(jj)` 를 그립니다 (Gaussian fit).
  (nominal: `E_jj ≈ 88.9 GeV`, `m(jj) ≈ 88.8 GeV` 근처. 전체 event 기준이고 91.2 보다 낮게 나옵니다.)
- `c_event_display`: 한 event 의 hit 과 jet 을 `eta–phi` 평면에 그립니다.
- 빨리 돌려 보려면 `--max-events 200`.

## 10. 내 fork 로 작업하기

`install.sh` 는 `swkim95` 의 fork 를 `https` 로 받습니다. 내 수정사항을 push 하려면 본인 fork 를 remote 로 추가하세요.

```bash
cd packages/k4geo
git remote add myfork git@github.com:<내 id>/k4geo.git
git checkout -b my_work
# ... 수정 후
git push myfork my_work
```

`k4RecTracker` 도 같은 방법입니다. 내 fork 를 처음부터 받고 싶으면 설치 때 환경변수로 덮어쓰면 됩니다:

```bash
K4GEO_REPO=https://github.com/<id>/k4geo.git K4GEO_BRANCH=my_branch ./install.sh
```

`k4geo` 의 C++ 소스를 고쳤다면 `packages/k4geo/build` 에서 `make -j4 install` 을 다시 해야 합니다.

## 11. fullSim Digi 미지원

이 tutorial 의 `digi/run_digi_reco.py` 는 **noOpt Sim 출력 전용** 입니다.

- steering file 에는 full optical simulation 을 켜는 주석 블록이 있어서 fullSim **Sim** 까지는 돌릴 수 있습니다.
- 그러나 fullSim 출력의 **Digi 는 현재 지원하지 않습니다.** 별도로 받은 `k4RecCalorimeter` 에 작은 수정이 필요합니다.
  이 패키지는 `install.sh` 에 **포함되어 있지 않고**, 방법은 나중에 따로 안내합니다.
- fullSim 출력에 `run_digi_reco.py` 를 돌리지 마세요 (돌아가더라도 결과를 믿을 수 없습니다).

## 12. 자주 겪는 문제

| 증상 | 원인 / 해결 |
|---|---|
| `K4GEO_LOCAL 이 설정되지 않았다` | `source setup_env.sh` 를 안 했습니다. |
| ddsim 이 15분 넘게 아무 출력이 없다 | 정상입니다. geometry 를 올리는 중입니다. |
| Digi 가 `Helix, invalid parameter: bField 0` 으로 죽는다 | 자기장 OFF geometry 인데 `DIGI_SKIP_HELIX_TRACKING=1` 을 안 줬습니다. |
| Digi 에서 ONNX 파일을 못 찾는다 | `install.sh` 의 마지막 단계 (다운로드) 가 실패한 것입니다. `digi/SimpleGatrIDEAv3o1.onnx` 가 있는지 확인하고 `./install.sh` 를 다시 실행하세요. |
| condor job 이 `Held` | `condor_q -hold` 로 이유를 보세요. 메모리 초과면 `-a "request_memory=8000 MB"` 처럼 늘려서 다시 제출합니다. |
| 분석 스크립트가 `*.root` 를 잘못 읽는다 | 디렉터리를 줄 때는 `*_digi_*.root` 만 읽도록 되어 있습니다. 파일 glob 을 직접 줄 때는 `TrackHitDistances_*.root` 가 섞이지 않게 하세요. |
| `ModuleNotFoundError: ROOT` | `source setup_env.sh` 를 안 했습니다. |

## 13. 자원 / 시간 / 용량 안내

job 을 제출하기 전에 대략 얼마나 걸리고 얼마나 쓰는지 알아 두세요.
아래 수치는 이 geometry (IDEA o3, noOpt) 로 실제 production 을 돌렸던 condor log 와 출력 파일에서 뽑은 값입니다.

- 모두 noOpt Sim/Digi 입니다. **fullSim (full optical) 은 production 기록이 없어 수치가 없습니다.** optical photon 을 모두 추적하므로 noOpt 보다 훨씬 느리고 무겁다는 것만 알아 두세요.
- Sim job 은 100 event/job (physics 는 20 event/job) 이었고, job 당 CPU 1 core 를 썼습니다.
- **시간은 서버 부하와 node 에 따라 크게 달라집니다.** 같은 샘플도 startup 이 10분에서 28분까지 나왔습니다. 아래는 "대략 이 정도"로 보세요.

### 13.1 Sim (ddsim)

**job 시간 = startup (geometry 와 Geant4 초기화, event 수와 무관) + event 수 × (s/event).**
startup 은 첫 event 가 시작되기까지 걸린 시간입니다.

| 샘플 (noOpt) | startup (분) | s/event | 100 event job 전체 (분) | Sim 출력 (MB/event) |
|---|---|---|---|---|
| e- 10 GeV | 약 23 | 3 | 약 28 | 0.16 |
| e- 20 GeV | 약 24 | 9 | 약 35 | 0.30 |
| e- 40 GeV | 10 ~ 28 | 10 ~ 22 | 26 ~ 68 | 0.58 |
| e- 60 GeV | 약 22 | 27 | 약 67 | 0.87 |
| e- 80 GeV | 약 20 | 30 | 약 66 | 1.15 |
| pi- 10 GeV | 약 20 | 2 | 약 23 | 0.17 |
| pi- 20 GeV | 약 20 | 4 | 약 27 | 0.35 |
| pi- 40 GeV | 약 24 | 9 | 약 38 | 0.69 |
| pi- 60 GeV | 약 21 | 16 | 약 44 | 0.99 |
| pi- 80 GeV | 약 23 | 22 | 약 60 | 1.07 |
| e- 40 GeV, DRConly geometry | 17 ~ 22 | 약 9 | 33 ~ 38 | 0.89 |
| Z→ee (91 GeV, 자기장 ON) | 약 27 | 62 | 20 event 에 약 49 | 2.3 |
| Z→qq (91 GeV, 자기장 ON) | 약 19 | 26 | 20 event 에 약 28 | 2.7 |

- Sim 출력 크기는 energy 에 거의 비례합니다 (약 0.015 MB/event/GeV, 즉 40 GeV 면 약 0.6 MB/event). 100 event 면 40 GeV 파일 하나가 약 60 MB 입니다.
- physics 의 Pythia generation (hepmc 만들기) 은 50 event 에 약 10초로 무시할 만 합니다. 이 tutorial 의 `gen_sim` template 은 generation 과 Sim 을 한 job 에서 돌립니다.
- 그래서 **event 가 적은 job 은 대부분 startup 입니다.** `NEV=10` 으로 제출해도 첫 event 까지 20분 가까이 기다려야 하니, 많이 만들 때는 job 당 event 수를 늘리는 쪽이 효율적입니다.

### 13.2 Digi

| 샘플 | startup (분) | s/event | job 전체 (분) | Digi 출력 (MB/event) |
|---|---|---|---|---|
| e- gun (10 ~ 80 GeV) | 6 ~ 14 | 0.2 ~ 0.4 | 약 6 ~ 18 | 0.16 (10 GeV) ~ 1.15 (80 GeV) |
| pi- gun (10 ~ 80 GeV) | 5 ~ 12 | 0.3 ~ 2.4 | 약 6 ~ 18 | 0.13 (10 GeV) ~ 0.68 (80 GeV), 40 GeV 는 0.46 |
| e- 40 GeV, DRConly | 15 ~ 17 | 0.8 ~ 0.9 | 약 16 ~ 18 | 0.38 |
| Z→ee (자기장 ON) | 약 8 | 0.5 | 20 event 에 약 9 | 2.2 |
| Z→qq (자기장 ON) | 약 7 | 4.8 | 20 event 에 약 9 | 2.5 |

- Digi 도 시간의 대부분은 startup (geometry + ONNX 모델 로딩) 입니다. event 당 시간은 Sim 에 비해 매우 짧습니다.
- Digi 출력은 Sim 출력과 같은 자릿수입니다 (crystal ECAL 의 counts 를 복사해 담기 때문).
- Digi 는 `TrackHitDistances_*.root` 도 따로 하나 더 만듭니다 (작은 파일).

### 13.3 메모리 (RAM)

condor log 에 기록된 job 별 최대 사용량입니다. 평균은 같은 종류 job 들의 평균입니다.

| job | 평균 (MB) | 최대 (MB) | `.sub` 의 `request_memory` |
|---|---|---|---|
| Sim, e- gun | 6500 ~ 9200 (energy 가 높을수록 큼) | 약 9700 | 16000 |
| Sim, pi- gun | 7500 ~ 9300 | 약 9700 | 16000 |
| Sim, DRConly e- | 약 8500 | - | 16000 |
| Sim, Z→ee / Z→qq (gen+sim) | 약 9700 / 약 9400 | 약 9800 / 약 9600 | 12000 |
| Digi, e- / pi- gun | 약 3200 ~ 3500 | 약 4000 | 5000 |
| Digi, DRConly | 약 2700 | 약 3200 | 5000 |
| Digi, Z→ee | 약 1800 | 약 3700 | 5000 |
| Digi, Z→qq | 약 4600 | 약 6000 | 8000 으로 올려서 제출 |

- Sim 은 어느 샘플이든 최대 약 10 GB 에서 멈춥니다 (request 는 여유를 두고 16000 MB).
- gun Digi 는 최대가 4 GB 근처라서 `.sub` 기본값을 5000 MB 로 잡았습니다. physics Z→qq Digi 는 그보다 커서 `-a "request_memory=8000 MB"` 로 올려 제출하세요. 메모리를 넘으면 job 이 `Held` 가 됩니다.
- request 를 필요 이상으로 크게 잡으면 slot 을 오래 기다리고 다른 사용자에게도 불리합니다. 사용량을 본 뒤 조정하세요 (`condor_history <id> -af MemoryUsage`).

### 13.4 대략적인 계산 예

- e- 40 GeV, 100 event × 10 job: Sim job 하나에 1 시간 안팎, 출력 60 MB × 10. Digi job 하나에 10 ~ 15분, 출력 약 60 MB × 10. 메모리는 job 당 Sim 약 9 GB, Digi 약 4 GB.
- 디스크: 분석에 쓰는 것은 Digi 파일이므로 Sim 파일은 Digi 가 끝난 뒤 지워도 됩니다.
- 결과 파일이 쌓이는 곳 (`$TUTORIAL_OUTPUT`) 의 여유 공간을 미리 확인하세요 (`df -h $TUTORIAL_OUTPUT`).
