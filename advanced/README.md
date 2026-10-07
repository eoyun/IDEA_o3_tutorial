# IDEA o3 DRC advanced hands-on

메인 README 1 ~ 8장의 명령을 이미 실행해 본 사람을 위한 실습입니다.
그 명령들이 **안에서 어떻게 구성되는지** (steering file, beam 조준, condor 제출 파일, Digi, Pythia card, 4-jet 분석) 를
빈칸을 채우면서 직접 만들어 봅니다.

## 규칙

- **로컬 (로그인 서버) 에서 시뮬레이션을 돌리지 않습니다.** ddsim 하나가 약 10 GB, Digi 하나가 3 ~ 6 GB 를 씁니다.
  20명이 동시에 돌리면 서버가 멈춥니다. 각 장의 "로컬에서 실제로 돌리는 명령" 은 읽기만 하세요.
- 로컬에서 해도 되는 가벼운 확인:
  - `ddsim --steeringFile X --dumpSteeringFile` (몇 초)
  - `python3 01_steering_gun/check_steering.py X` (약 10초)
  - `condor_submit -dry-run`
  - `podio-dump`
  - 이 디렉터리의 python 스크립트 (`check_beam.py`, `find_hit_tower.py`, `check_hepmc.py`, `reco_4jets.py`, ...)
  - Pythia 만 `-n 5` 로 (05 장, 약 380 MB)
- 빈칸은 `____TODO_n____` 입니다. 빈칸 파일 (`*_blank.*`) 은 `advanced/work/` 에 복사해서 채웁니다.
  `advanced/work/` 는 git 이 무시하므로 `git pull` 과 충돌하지 않습니다.
- 정답은 `advanced/solutions/` 에 있습니다. 막히면 그 장의 README 힌트를 먼저 보세요.

## 순서

| 장 | 내용 | 어디서 | 시간 (대략) |
|---|---|---|---|
| [00_inspect](00_inspect/README.md) | 최종 설정, 파일 내용, condor 에 넘어가는 값을 확인하는 방법 | 로컬 | 20분 |
| [01_steering_gun](01_steering_gun/README.md) | gun steering file 의 핵심 12줄 채우기 | 로컬 (dump 만) | 30분 |
| [02_beam_pointing](02_beam_pointing/README.md) | barrel tower n 을 맞히는 gun position / direction 계산 | 로컬 (python) | 30분 |
| [03_condor_gun_sim](03_condor_gun_sim/README.md) | wrapper 와 `.sub` 채우기, gun Sim 1 job × 20 event 제출 | condor | job 약 30분 |
| [04_digi](04_digi/README.md) | `run_digi_reco.py` 구조, Digi 1 job 제출, 에너지 확인 | condor | job 약 10분 |
| [05_physics_WW_ZH](05_physics_WW_ZH/README.md) | Pythia card, physics steering, gen+sim, Digi, 4-jet 분석 (`reco_4jets.py`) | condor + 로컬 분석 | job 약 30 ~ 40분 |

```
00 ─> 01 ─> 02 ─> 03 ─> 04 ─> 05
 └──────────────────────────> 05 (card, steering, 분석은 03, 04 를 기다리지 않고 시작 가능)
```

**job 은 시작해서 첫 event 까지 약 20분이 걸립니다** (geometry 로딩). 제출한 뒤에는 기다리지 말고 다음 장을 읽으세요.
예: 03 을 제출하고 05 의 Pythia card 를 채우고, 03 이 끝나면 04 를 제출합니다.

## 자원

이 장들의 정답으로 실제로 돌린 값입니다 (2026-10-07). 일반적인 범위는 메인 README [13장](../README.md#13-자원--시간--용량-안내) 을 보세요.

| job | `request_memory` | 실제 최대 메모리 | 시간 | 출력 |
|---|---|---|---|---|
| gun Sim, e- 40 GeV, 20 event (03) | 16000 MB | 9.3 GB | 32분 | 12 MB |
| gun Digi, 20 event (04) | 5000 MB | 3.3 GB | 13분 | 12 MB |
| gen + sim, WW 또는 ZH, 5 event (05) | 12000 MB | 9.7 GB | 31분 | 22 MB |
| physics Digi, 5 event (05) | 8000 MB | 3.3 GB | 14분 | 20 MB |
| (참고) gen + sim, 20 event (reference 샘플) | 12000 MB | 9.8 ~ 10.2 GB | 28 ~ 74분, 평균 51분 | 80 MB |
| (참고) physics Digi, 20 event (reference 샘플) | 16000 MB | 5.0 ~ 8.0 GB | 약 15분 | 75 MB |

physics Digi 의 메모리는 job 당 event 수에 따라 늘어납니다 (5 event 3.3 GB, 20 event 최대 8 GB). 05 에서 event 수를 늘리면 `request_memory` 도 올리세요.

시간은 node 와 서버 부하에 따라 두 배 가까이 달라집니다.

한 사람이 동시에 3 ~ 4 job, 20명이면 약 80 job 입니다. **job 수와 event 수는 README 에 적힌 값보다 늘리지 마세요.**
peak 를 보기에 부족한 통계는 아래의 reference 샘플로 봅니다.

## reference 샘플 (05 장)

`$TUTORIAL_SAMPLES` 에 미리 만들어 둔 샘플입니다 (각 50 job × 20 event).

| 디렉터리 | 내용 |
|---|---|
| `o3_WW_qqqq_eCM240_noOpt_{Gen,Sim,Digi}` | e+e- → W+W- → qqqq, 240 GeV, ISR on |
| `o3_ZH_qqbb_eCM240_noOpt_{Gen,Sim,Digi}` | e+e- → ZH, Z → qq, H → bb, 240 GeV, ISR on |
| `o3_ZH_qqbb_eCM240_ISRoff_noOpt_{Gen,Sim,Digi}` | 위와 같고 ISR off (`PDF:lepton = off`) |

card 는 `advanced/solutions/05_physics_WW_ZH/` 의 것과 같습니다. 세 샘플 모두 Digi 1000 event 가 모두 있습니다.
`reco_4jets.py --truth` 로 얻은 값은 [05 의 "reference 샘플의 결과"](05_physics_WW_ZH/README.md#reference-샘플의-결과) 에 있습니다.
