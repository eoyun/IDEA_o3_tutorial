# 05. physics: WW → qqqq, ZH → qqbb (240 GeV)

fully hadronic 4-jet event 두 가지를 처음부터 만들어 봅니다.

```
Pythia8 card ──(k4run gen/pythia.py)──> HepMC ──(ddsim, 자기장 ON)──> Sim ──(04 의 Digi)──> Digi ──> reco_4jets.py
```

- `e+e- → W+W- → qqqq`: 4 jet 을 W 두 개로 짝짓습니다.
- `e+e- → ZH, Z → qq, H → bb`: 4 jet 중 어느 두 개가 H 인지 고릅니다.
- 직접 만드는 샘플은 job 1개 × 5 event 입니다. peak 는 미리 만든 reference 샘플 (약 1000 event) 로 봅니다.

```bash
cd IDEA_o3_tutorial && source setup_env.sh
cp advanced/05_physics_WW_ZH/p8_ee_WW_qqqq_eCM240_blank.cmd    advanced/work/p8_ee_WW_qqqq_eCM240.cmd
cp advanced/05_physics_WW_ZH/p8_ee_ZH_qqbb_eCM240_blank.cmd    advanced/work/p8_ee_ZH_qqbb_eCM240.cmd
cp advanced/05_physics_WW_ZH/SteeringFile_o3_physics_blank.py  advanced/work/SteeringFile_o3_physics.py
cp advanced/05_physics_WW_ZH/wrapper_gen_sim_blank.sh          advanced/work/wrapper_gen_sim.sh
cp advanced/05_physics_WW_ZH/submit_gen_sim_blank.sub          advanced/work/submit_gen_sim.sub
chmod +x advanced/work/wrapper_gen_sim.sh
```

## 1. Pythia card

메인 tutorial 의 `gen/p8_ee_Zqq_eCM91.cmd` 와 같은 형식입니다. 한 줄이 `이름 = 값` 인 설정입니다.

| 빈칸 | 무엇 | 힌트 |
|---|---|---|
| WW `TODO_1`, ZH `TODO_1` | `Beams:eCM` | 중심 에너지 [GeV]. ZH 는 문턱 (91 + 125 = 216 GeV) 을 넘어 cross section 이 최대에 가까운 240 GeV 에서 측정한다 |
| WW `TODO_2` | process 스위치 | `WeakDoubleBoson:` 그룹의 f fbar → W+ W- (`... = on`) |
| ZH `TODO_2` | process 스위치 | `HiggsSM:` 그룹의 f fbar → H Z (Higgsstrahlung) |
| WW `TODO_3`, `TODO_4` | W (PDG 24) decay | `24:onMode = off` 로 모든 decay 를 끈 뒤, `24:onIfAny = ...` 로 quark (PDG 1 ~ 5) 가 들어 있는 channel 만 켠다 |
| ZH `TODO_3`, `TODO_4` | Z (PDG 23) decay | 위와 같은 방법 |
| ZH `TODO_5`, `TODO_6` | H (PDG 25) decay | b quark 만. H → bb 는 BR 약 58% 로 가장 크다 |

- `onMode = off` 없이 `onIfAny` 만 쓰면 다른 channel 도 그대로 켜져 있습니다.
- decay 를 강제하면 b-tagging 없이도 샘플이 순수한 4-jet 이 됩니다 (이 tutorial 의 reconstruction 에는 vertexing 과 flavour tagging 이 없습니다).
- ISR: Pythia 는 lepton beam 에도 PDF 를 쓰고 (`PDF:lepton = on` 이 기본값), 이것이 beam 의 photon 방출 (ISR) 입니다.
  그래서 실제 hard process 의 에너지 `sqrt(s_hat)` 가 240 GeV 보다 작은 event 가 섞입니다.

### 로컬 확인 (허용: 약 380 MB, 수 초)

Pythia 만 돌리는 것은 가볍습니다. 5 event 만 만들어 decay mode 를 확인하세요.

```bash
cd advanced/work
k4run $IDEA_TUTORIAL_ROOT/gen/pythia.py -n 5 \
      --Pythia8.PythiaInterface.pythiacard p8_ee_ZH_qqbb_eCM240.cmd \
      --HepMCFileWriter.Filename ZH_test.hepmc --IOSvc.Output ZH_test_gen.root
python3 ../05_physics_WW_ZH/check_hepmc.py ZH_test.hepmc
```

`check_hepmc.py` 는 `sqrt(s_hat)` 의 분포, boson 의 decay 산물, stable photon 수를 출력합니다.
H 의 산물이 `|PDG| 5` 뿐이고, W / Z 의 산물이 quark (1 ~ 5) 뿐이면 맞습니다.
(W 가 photon 을 내는 것 (`(W, 22, ...)`) 은 정상입니다. decay 가 아니라 radiation 입니다.)

### 과제: ISR 끄기 (ZH 만)

```bash
cp p8_ee_ZH_qqbb_eCM240.cmd p8_ee_ZH_qqbb_eCM240_ISRoff.cmd
echo "PDF:lepton = off" >> p8_ee_ZH_qqbb_eCM240_ISRoff.cmd
```

같은 방법으로 5 event 를 만들어 `check_hepmc.py` 로 비교합니다. 50 event 로 확인한 값:

| card | `sqrt(s_hat)` 최소 | 239 GeV 미만 비율 |
|---|---|---|
| WW, ISR on | 181 GeV | 0.40 |
| ZH, ISR on | 226 GeV | 0.28 |
| ZH, ISR off | 240.00 GeV | 0.00 |

ISR off 에서도 stable photon 은 많습니다. 대부분 hadron decay (π0 → γγ) 에서 나온 것이라 ISR 과 상관없습니다.

## 2. physics steering

01 의 gun steering 과 다른 곳만 빈칸입니다.

| 빈칸 | 무엇 | 왜 |
|---|---|---|
| `TODO_1` | geometry XML | physics 는 실제 detector 처럼 자기장 (2 T) 을 켠다. 메인 README 3장의 표 |
| `TODO_2` | `SIM.enableGun` | 입자를 HepMC 파일에서 읽는다 |
| `TODO_3` | `SIM.inputFiles` | 파일 이름은 wrapper 가 command line (`--inputFiles`) 으로 준다. 여기는 빈 list |
| `TODO_4` | `SIM.vertexSigma` | vertex 를 smearing 하지 않는다 (x, y, z, t 네 개) |

확인: `ddsim --steeringFile SteeringFile_o3_physics.py --inputFiles x.hepmc --dumpSteeringFile > dump.txt`
(입력 파일이 없어도 dump 는 됩니다.)

## 3. gen + sim wrapper 와 `.sub`

job 하나가 Pythia 로 HepMC 를 만들고, 바로 이어서 그 파일로 ddsim 을 돌립니다.

| `wrapper_gen_sim.sh` 빈칸 | 무엇 | 힌트 |
|---|---|---|
| `TODO_1` | `SEED` | 03 과 같은 규칙 (job 번호 + 1) |
| `TODO_2` | Pythia event 수 | 인자로 받은 변수 |
| `TODO_3` | Pythia card | **원본 card 가 아니라** seed 를 바꾼 사본 |
| `TODO_4` | HepMC 출력 | 위에서 만든 변수 |
| `TODO_5` | ddsim 입력 | Pythia 가 쓴 HepMC |

**왜 card 사본에 seed 를 넣는가:** Pythia 의 random seed 는 card 안의 `Random:seed` 입니다.
모든 job 이 같은 card 를 쓰면 모든 job 이 똑같은 event 를 만듭니다. 그래서 job 마다 `sed` 로 seed 만 바꾼 사본
(`<TAG>_Gen/<TAG>_card_<번호>.cmd`) 을 만들어 씁니다. 사본은 남겨 두므로 나중에 어떤 설정으로 만들었는지 볼 수 있습니다.

| `submit_gen_sim.sub` 빈칸 | 무엇 | 힌트 |
|---|---|---|
| `TODO_1` | `STEERING` | `advanced/work/` 의 physics steering |
| `TODO_2` | `arguments` | wrapper 맨 위의 6개를 순서대로 |
| `TODO_3` | `request_memory` | 메인 README 13.3 의 gen+sim 값 |

```bash
cd $IDEA_TUTORIAL_ROOT
condor_submit -dry-run dry.ad advanced/work/submit_gen_sim.sub && grep -E "^(Args|AcctGroup|RequestMemory)=" dry.ad
condor_submit advanced/work/submit_gen_sim.sub                                  # WW (파일의 기본값)
condor_submit -a "TAG=my_ZH_qqbb" \
    -a "CARD=$IDEA_TUTORIAL_ROOT/advanced/work/p8_ee_ZH_qqbb_eCM240.cmd" advanced/work/submit_gen_sim.sub
```

- Pythia 는 몇 초면 끝나고, 나머지는 ddsim 입니다. startup 약 20분 + 5 event 에 수 분입니다.
- wrapper 는 card, steering, wrapper 자신에 빈칸이 남아 있으면 바로 멈춥니다.

## 4. Digi

04 의 `submit_digi.sub` 를 그대로 쓰고, 자기장 ON 설정으로 덮어씁니다.

```bash
condor_submit -a "DIGI_TAG=my_WW_qqqq" \
    -a "DIGI_COMPACT_XML=FCCee/IDEA/compact/IDEA_o3_v01/IDEA_o3_v01.xml" -a "DIGI_SKIP_HELIX=0" \
    -a "request_memory=8000 MB" advanced/work/submit_digi.sub
# ZH 는 DIGI_TAG=my_ZH_qqbb
```

- 자기장이 있으므로 `DIGI_SKIP_HELIX=0` (helix track 을 만든다) 입니다. 출력에 `TracksFromGenParticles` 가 생깁니다.
- 4-jet event 는 hit 이 많아서 gun 보다 메모리를 더 씁니다 (메인 README 13.3 의 Z→qq Digi 참고).

## 5. 분석: `reco_4jets.py`

```bash
cd advanced/05_physics_WW_ZH
python3 reco_4jets.py --mode WW -i $TUTORIAL_OUTPUT/my_WW_qqqq_Digi -o ../work/my_WW.root --truth
python3 reco_4jets.py --mode WW -i $TUTORIAL_SAMPLES/o3_WW_qqqq_eCM240_noOpt_Digi -o ../work/WW.root --truth
python3 reco_4jets.py --mode ZH -i $TUTORIAL_SAMPLES/o3_ZH_qqbb_eCM240_noOpt_Digi -o ../work/ZH.root --truth
python3 reco_4jets.py --mode ZH -i $TUTORIAL_SAMPLES/o3_ZH_qqbb_eCM240_ISRoff_noOpt_Digi -o ../work/ZH_ISRoff.root --truth
```

- 1000 event 에 약 20분 걸립니다 (메모리 약 1 GB). 대부분 hit 1만 개 이상을 Durham 으로 묶는 시간입니다.
  먼저 `--max-events 300` (약 6분) 으로 돌려 보세요.

하는 일 (자세한 것은 `-h`):

1. **jet:** 메인 README 9.2 (b) 의 `reco_physics_jets.py` 와 같습니다. ECAL / DRC 의 S, C hit 을 calibration constant 로 GeV 로 바꾸고,
   DRC fiber 는 tower 로 묶은 뒤, fastjet Durham 으로 **정확히 4 jet** (`exclusive_jets(4)`) 을 만듭니다. DR 보정은 jet 단위입니다.
2. **pairing:** 4 jet 을 두 쌍으로 묶는 방법은 3가지입니다. χ² 가 가장 작은 것을 고릅니다.
   - WW: `χ² = ((m1 − mW)/σ)² + ((m2 − mW)/σ)²`
   - ZH: 어느 쌍이 Z 인지까지 6가지. `χ² = ((m_Z − mZ)/σ_Z)² + ((m_H − mH)/σ_H)²`
   - σ 는 기본 8 GeV (`--sigma-w`, `--sigma-z`, `--sigma-h`).
3. **`--truth`** (pairing 을 고를 때는 쓰지 않고, 결과를 평가할 때만 씁니다):
   - `MCParticles` 에서 W / Z / H 의 decay quark (`generatorStatus` 23) 4개를 찾습니다.
     (ISR 이 있으면 Pythia 는 boson 을 status 44 로 복사해 recoil 을 주므로, status 23 quark 의 방향은 1 GeV 이하의 pT 만큼 다를 수 있습니다. 각도 매칭에는 영향이 작습니다.)
   - reco jet 4개와 quark 4개를 **각도 합이 가장 작은 순열 (24가지)** 로 짝짓습니다. 이것이 "정답 pairing" 입니다.
   - **pairing efficiency:** χ² 가 고른 pairing 이 정답과 같은 비율 (ZH 는 Z / H 역할까지 맞아야 함).
     hard gluon radiation 등으로 Durham jet 이 quark 를 따라가지 않는 event 는 "정답 pairing" 자체가 애매합니다.
     그래서 4 jet 모두 quark 와 `--match-cut` (기본 0.3 rad) 안에 있는 event (`well_matched`) 의 efficiency 도 따로 출력합니다.
   - **m_jj 비교 (`c_mass_W`, `c_mass_Z`, `c_mass_H`):**
     - reco jet + χ² pairing (검정): 실제 분석과 같은 것
     - reco jet + 정답 pairing (빨강): pairing 실수를 뺀 detector 효과
     - gen jet + 정답 pairing (파랑): detector 가 없을 때. gen jet = `generatorStatus` 1 인 stable 입자로 같은 Durham 4-jet
       (|cosθ| > 0.995 인 입자는 calorimeter 가 덮지 않으므로 뺍니다, `--gen-cos-max`). ν 는 뺍니다.
     - gen jet (ν 포함) + 정답 pairing (초록): 파랑과의 차이가 ν 가 가져간 에너지입니다. b / c 의 semileptonic decay 때문에 H → bb 에서 큽니다.
   - **jet 응답 `h_Eratio`:** reco jet 과 gen jet (ν 제외) 을 각도로 짝지어 `E_reco / E_gen`.

출력은 ROOT 파일 하나입니다 (`TTree events`, histogram, canvas). `root -l ../work/ZH.root` → `new TBrowser`.
ISR on / off 비교는 두 파일의 `h_mH_chi2`, `h_Esum` 을 겹쳐 그려 봅니다:

```bash
python3 compare_hists.py ../work/ZH.root ../work/ZH_ISRoff.root --labels "ISR on" "ISR off" \
        --hists h_mH_chi2 h_mZ_chi2 h_Esum -o ../work/ZH_ISR_compare.root
```

### reference 샘플의 결과

자기 결과를 볼 때 비교용입니다. 각 1000 event, `--truth`, 나머지는 기본 옵션. 값은 Gaussian fit 의 mean / sigma [GeV] 입니다.

| m_jj | reco, χ² pairing | reco, 정답 pairing | gen (ν 제외) | gen (ν 포함) |
|---|---|---|---|---|
| WW: m(W) | 79.3 / 8.0 | 79.4 / 7.4 | 80.0 / 3.8 | 80.2 / 3.1 |
| ZH: m(Z) | 84.5 / 10.9 | 88.7 / 13.1 | 89.7 / 8.5 | 91.6 / 6.4 |
| ZH: m(H) | 115.3 / 12.3 | 109.9 / 18.7 | 116.7 / 14.3 | 124.8 / 4.3 |
| ZH ISR off: m(H) | 116.2 / 12.6 | 110.8 / 18.1 | 114.8 / 15.7 | 124.6 / 3.9 |

| | WW | ZH | ZH ISR off |
|---|---|---|---|
| pairing efficiency (전체) | 0.77 | 0.52 | 0.52 |
| pairing efficiency (`well_matched`) | 0.91 (595 event) | 0.67 (596 event) | 0.63 (618 event) |
| jet 응답 `E_reco / E_gen` mean (RMS) | 0.97 (0.14) | 0.96 (0.15) | 0.96 (0.15) |
| `h_Esum` mean (RMS) | 229.5 (15.0) | 219.9 (16.1) | 221.0 (17.2) |
| quark 4개의 질량 `m_4q` mean | 233.5 | 238.0 | 240.0 |

- ZH 의 χ² pairing m(H) 가 정답 pairing 보다 125 GeV 에 가깝고 좁습니다. χ² 가 m(H) ≈ 125 인 조합을 고르기 때문입니다 (분포를 만들어 내는 효과, sculpting).
  그래서 "χ² pairing 의 peak 가 좋다" 는 것만으로는 detector 성능을 말할 수 없고, 정답 pairing 과 함께 봐야 합니다.
- 1000 event 의 통계 오차는 mean 에서 약 0.5 GeV 입니다. 0.5 GeV 정도의 차이는 의미가 없습니다.

### 토론거리

- m(bb) 가 125 GeV 보다 낮고 왼쪽 꼬리가 깁니다. 초록 (ν 포함) 과 파랑 (ν 제외) 을 비교해 보세요.
- 빨강과 검정의 차이가 pairing 실수입니다. WW 와 ZH 중 어느 쪽 pairing 이 쉬운가요? 왜 그럴까요?
- `h_Esum` 이 240 GeV 보다 낮은 이유: ν, beam pipe 방향으로 빠진 입자, ISR photon, jet energy scale (rescaling 을 하지 않음).
- ISR off 에서 `h_Esum` 과 m_jj 의 꼬리가 어떻게 달라지나요? 위 표의 `m_4q` 를 보면 ZH 에서 ISR 이 가져가는 에너지는 평균 2 GeV 입니다.
  `h_Esum` 의 RMS (16 GeV) 와 비교하면 어느 효과가 큰가요? WW 의 `m_4q` 가 더 낮은 이유는? (힌트: 1장 표, cross section 이 √s 에 따라 어떻게 변하는가)

## 로컬에서 실제로 돌리는 명령 (실행하지 마세요)

```bash
./advanced/work/wrapper_gen_sim.sh 0 $IDEA_TUTORIAL_ROOT my_test advanced/work/p8_ee_ZH_qqbb_eCM240.cmd \
    advanced/work/SteeringFile_o3_physics.py 2
```

Pythia 뒤의 ddsim 이 약 10 GB 를 씁니다. 로컬에서는 위의 Pythia `-n 5` 확인까지만 하세요.

정답: `advanced/solutions/05_physics_WW_ZH/` (ISR off card 포함).
