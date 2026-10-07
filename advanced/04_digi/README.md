# 04. 내 Sim 으로 Digi 돌리기

03 에서 만든 tower 10 Sim 출력을 Digi 로 바꾸고, 분석 스크립트로 에너지 분포를 봅니다.
**Sim job 이 끝난 뒤에** 제출합니다 (Digi 는 `*_sim_<번호>.root` 를 바로 읽습니다).

```bash
cd IDEA_o3_tutorial && source setup_env.sh
cp advanced/04_digi/wrapper_digi_blank.sh  advanced/work/wrapper_digi.sh
cp advanced/04_digi/submit_digi_blank.sub  advanced/work/submit_digi.sub
chmod +x advanced/work/wrapper_digi.sh
```

## `run_digi_reco.py` 가 하는 일

Gaudi (`k4run`) job 입니다. `TopAlg` 에 넣은 algorithm 이 event 마다 이 순서로 실행됩니다.

| 순서 | algorithm | 입력 → 출력 | 비고 |
|---|---|---|---|
| 1 | `DDPlanarDigi` (VTXB, VTXD, SiWrB, SiWrD, muon) | Sim tracker hit → digitized hit | 위치 smearing |
| 2 | `DCHdigi_v02` | drift chamber hit → `DCH_DigiCollection` | |
| 3 | `TracksFromGenParticles`, `PlotTrackHitDistances`, `TrackdNdxDelphesBased` | MCParticles → helix track, 진단 histogram | **`DIGI_SKIP_HELIX_TRACKING=1` 이면 건너뜀** |
| 4 | `GGTFTrackFinder` | tracker hit → `CDCHTracks` | ONNX 모델 (`digi/SimpleGatrIDEAv3o1.onnx`). track state 는 없음 |
| 5 | `SimulateSiPMwithEdep` | `DRcaloSiPMreadout_scint` → `DRcaloSiPMreadoutDigiHit_scint` | DRC **S** channel. fiber 의 energy deposit 을 photon 수로 바꾸고 SiPM 응답 emulation |
| 6 | `SimulateSiPMwithOpticalPhoton` | `DRcaloSiPMreadoutSimHit` → `DRcaloSiPMreadoutDigiHit` | DRC **C** channel. Cherenkov photon 의 시간/파장으로 SiPM 응답 emulation |
| 7 | `CaloTopoClusterFCCee` | DRC digi hit → `TopoClusterAll` | |
| 8 | `CreateTruthLinks` | hit/cluster ↔ MCParticles | |

- crystal ECAL (SCEPCal) 은 digitizer 가 없습니다. Sim 의 `SCEPCal_MainScounts` / `Ccounts` 가 출력에 그대로 복사됩니다.
- 출력에서 `*scintContrib*`, `*Waveform*`, `*TimeStruct*`, `*WaveLen*` 은 지웁니다 (크기 때문).
- 두 SiPM algorithm 의 `scaleADC = 1.0` 은 고정입니다. nominal calibration constant 가 이 값 기준입니다.

### 왜 환경변수 두 개가 필요한가

- `DIGI_COMPACT_XML`: digitizer 는 cellID 를 위치로 바꾸려고 geometry 를 다시 읽습니다. **Sim 에 쓴 XML 과 같아야** 합니다.
  `run_digi_reco.py` 는 기본값 없이 이 값을 요구합니다 (모르고 다른 geometry 로 돌리지 않게).
- `DIGI_SKIP_HELIX_TRACKING`: 3번의 helix track 은 자기장으로 궤적을 만듭니다. 자기장 OFF geometry 에서는
  `Helix, invalid parameter: bField 0` 으로 event loop 전체가 죽습니다. 3번은 진단용이라 calorimeter 분석에는 필요 없어서 끕니다.

| Sim | `DIGI_COMPACT_XML` | `DIGI_SKIP_HELIX_TRACKING` |
|---|---|---|
| gun, full o3, 자기장 OFF (03 의 샘플) | `FCCee/IDEA/compact/IDEA_o3_v01/IDEA_o3_v01_noField.xml` | 1 |
| physics (05 의 샘플) | `FCCee/IDEA/compact/IDEA_o3_v01/IDEA_o3_v01.xml` | 0 |

## 빈칸: `wrapper_digi.sh`

| 빈칸 | 무엇 | 힌트 |
|---|---|---|
| `TODO_1` | `DIGI_COMPACT_XML` | `.sub` 에서 다섯 번째 인자로 넘어온다. 다른 인자처럼 `${N:?}` 로 받으면 빠졌을 때 바로 멈춘다 |
| `TODO_2` | `DIGI_SKIP_HELIX_TRACKING` | 여섯 번째 인자 |
| `TODO_3` | Gaudi option 파일 | repo 의 `digi/run_digi_reco.py` (`$ROOT` 기준) |
| `TODO_4` | 입력 파일 | 위에서 `ls` 로 찾은 변수 |
| `TODO_5` | 출력 파일 | 위에서 만든 변수 |

## 빈칸: `submit_digi.sub`

| 빈칸 | 무엇 | 힌트 |
|---|---|---|
| `TODO_1` | `DIGI_TAG` | 03 의 `TAG` 와 같게 하면 찾기 쉽다 |
| `TODO_2` | `SIM_DIR` | 03 의 출력 디렉터리. `$ENV(TUTORIAL_OUTPUT)` 와 `$(DIGI_TAG)` 를 쓴다 |
| `TODO_3` | `DIGI_COMPACT_XML` | 위 표 |
| `TODO_4` | `DIGI_SKIP_HELIX` | 위 표 |
| `TODO_5` | `request_memory` | 메인 README 13.3 의 gun Digi 값 |

`NJOBS` 는 Sim 의 job 수와 같게 합니다 (Digi job `N` 이 Sim 파일 `*_sim_N.root` 를 읽습니다).

## 제출과 확인

```bash
condor_submit -dry-run dry.ad advanced/work/submit_digi.sub
grep -E "^(Args|AcctGroup|RequestMemory) " dry.ad
condor_submit advanced/work/submit_digi.sub
condor_tail <cluster>.0
```

startup 이 5 ~ 15분, event 당 1초 미만입니다 (메인 README 13.2). 끝나면:

```bash
D=$TUTORIAL_OUTPUT/my_eminus_40GeV_tower10_Digi
podio-dump $D/my_eminus_40GeV_tower10_digi_0.root | head -45       # event 수, DigiHit collection
python3 advanced/02_beam_pointing/find_hit_tower.py $D/*_digi_*.root # Digi 파일로도 eta 10, phi 36
cd analysis
python3 resolution_hists.py -i $D -o ../advanced/work/tower10_40GeV.root --max-events 20
```

- `podio-dump` 에 `DRcaloSiPMreadoutDigiHit_scint`, `DRcaloSiPMreadoutDigiHit` 가 있고, `*TimeStruct*` 는 없어야 합니다.
- Digi 파일에는 Sim 의 `DRcaloSiPMreadout_scint` 도 남아 있어서, `find_hit_tower.py` 는 그것을 읽고 03 과 같은 결과를 냅니다.
- `resolution_hists.py` 는 p0 (tower 0) 에서 구한 nominal constant 를 씁니다. 정답으로 돌린 20 event 의 결과 (일부):

  ```
  hist         gauss mean  gauss sigma  sigma/mean  hist mean  hist RMS
  h_ECAL_S         39.974        0.769      0.0192     40.103     0.200
  h_DRC_S           0.489        0.745      1.5218      0.294     0.144
  h_Total_S        40.394        1.079      0.0267     40.397     0.109
  ```

  전체 o3 geometry 에서는 crystal ECAL 이 앞에 있어서 40 GeV e- 의 에너지가 거의 모두 ECAL 에 남고, DRC 에는 0.3 GeV 정도만 갑니다.
  `ECAL_S` 의 `mean / 40 GeV` 를 메인 README 8.2 의 theta 의존성과 비교해 보세요. 20 event 라 Gaussian fit 은 거칠고, 에너지가 거의 없는 DRC 의 fit 은 의미가 없습니다.

## 로컬에서 실제로 돌리는 명령 (실행하지 마세요)

```bash
export DIGI_COMPACT_XML=FCCee/IDEA/compact/IDEA_o3_v01/IDEA_o3_v01_noField.xml
export DIGI_SKIP_HELIX_TRACKING=1
k4run $IDEA_TUTORIAL_ROOT/digi/run_digi_reco.py --IOSvc.Input test_sim.root --IOSvc.Output test_digi.root \
      --RootHistoSink.FileName test_trackhits.root
```

Digi 도 geometry 를 올리느라 3 ~ 6 GB 를 씁니다. condor 로만 돌립니다.

정답: `advanced/solutions/04_digi/`.
