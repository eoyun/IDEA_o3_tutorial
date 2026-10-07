# 00. 가볍게 확인하는 도구

시뮬레이션을 돌리지 않고 설정과 결과 파일을 확인하는 방법입니다. 아래 명령은 모두 몇 초 안에 끝나고
메모리도 거의 쓰지 않으므로 **로컬에서 실행해도 됩니다.** 다음 장들에서 계속 씁니다.

```bash
cd IDEA_o3_tutorial
source setup_env.sh
```

| 도구 | 무엇을 보나 | 언제 쓰나 |
|---|---|---|
| `ddsim --dumpSteeringFile` | steering file + 명령행 옵션이 합쳐진 최종 ddsim 설정 | Sim 을 제출하기 전 |
| `podio-dump` | 출력 파일 (Sim, Digi) 의 collection 목록, 크기, 내용 | job 이 끝난 뒤 |
| `condor_submit -dry-run` | condor 에 실제로 넘어가는 값 (group, 메모리, arguments) | condor 제출 전 |

## 1. `ddsim --dumpSteeringFile`

steering file 을 읽고, 명령행 옵션을 덮어쓴 **최종 설정** 을 steering file 형식으로 출력한 뒤 바로 끝납니다.
geometry 를 올리지 않으므로 1초 정도 걸립니다.

```bash
ddsim --steeringFile sim/SteeringFile_o3_gun.py --dumpSteeringFile > dump.txt
grep -E "compactFile|gun\.(particle|energy|position|direction)|vertexSigma =|mapActions =" dump.txt
```

```
SIM.compactFile = ['.../IDEA_o3_v01/IDEA_o3_v01_noField.xml']
SIM.vertexSigma = [8.0, 8.0, 8.0, 0]
SIM.action.mapActions = {..., 'DRcalo': ('DRCaloSDAction', {'skipScint': 'true'})}
SIM.gun.direction = (-0.017452, 0.9998, 0.009816)
SIM.gun.energy = 40.0
SIM.gun.particle = "e-"
SIM.gun.position = (48.9638, 0.0, 0.0)
```

명령행 옵션이 steering 을 덮어쓰는 것도 바로 확인할 수 있습니다.

```bash
ddsim --steeringFile sim/SteeringFile_o3_gun.py --dumpSteeringFile \
      --gun.energy "20*GeV" --gun.position "(53.2145, 0, 0)" | grep -E "gun\.(energy|position)"
# SIM.gun.energy = "20*GeV"
# SIM.gun.position = ('53.2145', '0', '0')
```

- 숫자가 문자열로 바뀌어 보이지만 정상입니다. ddsim 이 실행할 때 읽어서 숫자로 씁니다 (길이 단위는 mm).
- `-` 로 시작하는 값은 option 으로 오해받습니다. `--gun.direction -0.017,0.99,0.01` 은
  `expected one argument` 오류가 납니다. `--gun.direction "(-0.017452, 0.999800, 0.009816)"` 처럼 괄호로 감싸세요.
- 함수 안에서만 쓰이는 설정 (output plugin, optical physics) 은 출력에 나오지 않습니다. 그런 부분은 실제 job 의 로그로 확인합니다.
- 옵션 이름이 기억나지 않으면 `ddsim --help` 를 보세요.

## 2. `podio-dump`

```bash
podio-dump <파일>                 # 첫 event 의 collection 목록 (이름, type, 개수)
podio-dump -e 3 <파일>            # 3번 event
podio-dump -s <파일>              # collection 별 디스크 용량 (어느 collection 이 큰지)
podio-dump -d -e 0 <파일> > ev0.txt   # 첫 event 의 모든 내용. 매우 크다 (gun Sim 1 event 에 약 9 MB) -> 꼭 파일로
```

파일은 `$TUTORIAL_SAMPLES` 에서 바로 읽어도 되고, `./copy_example_files.sh` 로 복사한 것을 써도 됩니다.

```bash
SIMF=$TUTORIAL_SAMPLES/o3_calibB_drc_eminus_40GeV_p0_noOpt_Sim/o3_calibB_drc_eminus_40GeV_p0_noOpt_sim_0.root
DIGIF=$TUTORIAL_SAMPLES/o3_calibB_drc_eminus_40GeV_p0_noOpt_scaleADC1_Digi/o3_calibB_drc_eminus_40GeV_p0_noOpt_scaleADC1_digi_0.root
podio-dump $SIMF
podio-dump $DIGIF
```

### Sim 파일 (ddsim 출력) 에 들어 있는 것

| collection | type | 내용 |
|---|---|---|
| `MCParticles` | `MCParticle` | 1차 입자 (gun 또는 Pythia) 와 Geant4 가 만든 2차 입자 |
| `DRcaloSiPMreadout_scint` | `SimCalorimeterHit` | DRC **S channel**: fiber 별 energy deposit (GeV). noOpt 라서 photon 이 아니라 edep 이다 |
| `DRcaloSiPMreadout_scintContributions` | `CaloHitContribution` | 위 hit 을 만든 입자별 기여 |
| `DRcaloSiPMreadoutSimHit` | `SimCalorimeterHit` | DRC **C channel**: SiPM 별로 도착한 Cherenkov photon 수 |
| `DRcaloSiPMreadoutTimeStruct`, `...WaveLen` | `RawTimeSeries` | C channel photon 의 도착 시간, 파장 분포 (Digi 의 SiPM emulation 이 읽는다) |
| `SCEPCal_MainScounts`, `SCEPCal_MainCcounts` | `SimCalorimeterHit` | crystal ECAL 의 S, C photo-electron 수 (DRConly geometry 에는 없다) |
| `DCHCollection`, `VertexBarrelCollection`, ... | `SimTrackerHit` | tracker 의 Sim hit |

### Digi 파일 (k4run 출력) 에 더 생기는 것

Digi 파일에는 Sim collection 이 대부분 복사되어 있고 (용량이 큰 `*scintContributions`, `*TimeStruct`, `*WaveLen` 은 뺀다),
아래가 추가됩니다. 그래서 분석에는 Digi 파일 하나만 있으면 됩니다.

| collection | 내용 |
|---|---|
| `DRcaloSiPMreadoutDigiHit_scint` | DRC S channel, SiPM emulation 후 (분석에 쓰는 것) |
| `DRcaloSiPMreadoutDigiHit` | DRC C channel, SiPM emulation 후 (분석에 쓰는 것) |
| `TopoClusterAll` | calorimeter cluster |
| `DCH_DigiCollection`, `VTXBDigis`, `SiWrBDigis`, ... | tracker digitization |
| `CDCHTracks` | GGTF 로 찾은 track (hit 묶음만 있고 track fit 은 하지 않았다) |
| `TracksFromGenParticles` | truth 입자로 만든 track. `DIGI_SKIP_HELIX_TRACKING=0` (자기장 ON, physics) 일 때만 생긴다 |

### 예: gun 이 의도한 방향으로 나갔는지

`MCParticles` 의 첫 줄이 gun 입자입니다 (generatorStatus = 1).

```bash
podio-dump -d -e 0 $SIMF > ev0.txt
grep -A2 "^MCParticles" ev0.txt | cut -c1-260
```

```
          id:  PDG:generatorStatus:simulatorStatus: charge: time: mass:  vertex [x, y, z]:  endpoint [x, y, z]:  momentum [x, y, z]: ...
a1cba250|+0  +11  +1  ...  +5.08e+01 +7.87e+00 +1.98e+01  ...  -6.98e-01 +3.999e+01 +3.93e-01 ...
```

- PDG 11 = e-, vertex 는 (48.96, 0, 0) mm 에서 8 mm smearing 된 값, momentum 은 (−0.70, 39.99, 0.39) GeV.
  momentum / 40 GeV = steering 의 direction (−0.017452, 0.9998, 0.009816) 입니다.
- 여러 event 를 한꺼번에 확인하려면 `advanced/02_beam_pointing/find_hit_tower.py` 를 쓰세요.

### 예: Digi 를 어떤 설정으로 만들었는지

Digi 파일에는 k4run 설정이 `configuration_metadata` 에 저장되어 있습니다.

```bash
podio-dump -c configuration_metadata -d $DIGIF | grep -E "GeoSvc.detectors|IOSvc.Input |SimulateSiPMwithEdep.scaleADC"
# , GeoSvc.detectors = "[ '.../IDEA_o3_v01_DRConly_noField.xml' ]"
# , IOSvc.Input = "[ '.../o3_calibB_drc_eminus_40GeV_p0_noOpt_Sim/o3_calibB_drc_eminus_40GeV_p0_noOpt_sim_0.root' ]"
# , SimulateSiPMwithEdep.scaleADC = "1.0000000"
```

Sim 파일에는 geometry 이름만 남습니다: `podio-dump -c runs -d $SIMF` → `detectorName  [IDEA_o3_v01_DRConly_noField]`.

## 3. `condor_submit -dry-run`

제출하지 않고, condor 에 넘어갈 job 정보 (ClassAd) 를 파일로 씁니다.

```bash
condor_submit -dry-run dry.ad condor/gun_sim/submit_sim.sub
grep -E "^(AcctGroup|RequestMemory|RequestCpus|Args|Cmd)=" dry.ad
```

```
Cmd="/.../IDEA_o3_tutorial/condor/gun_sim/wrapper_sim.sh"
Args="0 /.../IDEA_o3_tutorial my_eminus_40GeV_p0 /.../sim/SteeringFile_o3_gun.py 10"
AcctGroup="group_fcc"
RequestCpus=1
RequestMemory=16000
```

- `Args` 는 job 0 의 값입니다 (`$(Process)` = 0). `-a "NAME=값"` 이 반영되었는지도 여기서 봅니다.
- 빈칸 (`____TODO_n____`) 이 남아 있으면 그 글자가 그대로 보입니다: `grep TODO dry.ad`.
