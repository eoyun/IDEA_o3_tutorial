# 01. particle gun steering file 직접 쓰기

`sim/SteeringFile_o3_gun.py` 에서 중요한 줄 12개를 빈칸으로 만든 `SteeringFile_o3_gun_blank.py` 를 채웁니다.
목표 설정은 **e- 40 GeV, barrel tower 0 (README 의 p0), 전체 o3 geometry (자기장 OFF), noOpt** 입니다.

```bash
cd IDEA_o3_tutorial && source setup_env.sh
mkdir -p advanced/work
cp advanced/01_steering_gun/SteeringFile_o3_gun_blank.py advanced/work/SteeringFile_o3_gun.py
# advanced/work/SteeringFile_o3_gun.py 의 ____TODO_n____ 을 채운다
```

`advanced/work/` 는 git 이 무시하는 디렉터리라서 `git pull` 과 충돌하지 않습니다. 03 ~ 05 에서도 여기에 모읍니다.

## 빈칸

| 빈칸 | 무엇 | 왜 필요한가 / 힌트 |
|---|---|---|
| `TODO_1` | geometry XML 파일 이름 (문자열) | gun 샘플은 자기장을 끈 전체 o3 를 쓴다. 자기장 (2 T) 이 있으면 40 GeV e- 도 앞면까지 약 5 cm 휘어서 조준점에서 벗어난다. 후보는 메인 README 3장의 표. |
| `TODO_2` | `SIM.enableGun` | Pythia 같은 입력 파일 없이 ddsim 의 particle gun 으로 입자를 쏜다. `True` / `False` |
| `TODO_3` | `SIM.gun.particle` | Geant4 의 입자 이름 (문자열). 전자는 `"e-"`, pi- 는 `"pi-"` |
| `TODO_4` | `SIM.gun.energy` | 위에서 `GeV` 를 import 했다. `숫자 * GeV` |
| `TODO_5` | `SIM.gun.position` | 3 개짜리 tuple, mm. p0 의 값은 메인 README 5장 / `sim/SteeringFile_o3_gun.py` 의 `BEAM_POINTS`. 02 에서 직접 계산해 본다. |
| `TODO_6` | `SIM.gun.direction` | 3 개짜리 tuple (단위 없음). 위와 같은 곳에 있다. |
| `TODO_7` | `SIM.vertexSigma` | 생성 위치를 x, y, z, t 로 Gaussian smearing. sungwon 샘플은 x, y, z 모두 8 mm, t 는 0. 같은 지점에만 쏘면 한 fiber 근처에만 에너지가 몰려서 tower 응답을 대표하지 못한다. |
| `TODO_8` | `SIM.action.calorimeterSDTypes` | 어떤 sensitive detector type 을 calorimeter 로 취급할지 (list). 기본값 `"calorimeter"` 에 DRC 의 type `"DRcaloSiPMSD"` 를 더한다. |
| `TODO_9` | DRC SD action 의 `skipScint` | noOpt: scintillation photon 을 만들지 않고 fiber 의 energy deposit 을 S channel 로 쓴다. 문자열 `"true"` / `"false"` |
| `TODO_10` | `regexSensitiveDetector` 의 `Match` | noOpt 에서는 fiber 자체가 sensitive volume 이다. volume 이름의 정규식 list. fiber 는 `core` 와 `clad` 로 되어 있다. |
| `TODO_11` | DRC output plugin 이름 (문자열) | 일반 EDM4hep output 은 DRC 의 hit collection 을 저장하지 못한다. DRC 전용 plugin: `"Geant4Output2EDM4hep_DRC"` 처럼 생긴 이름. |
| `TODO_12` | Cherenkov physics 이름 (문자열) | noOpt 에서도 C channel 은 Cherenkov photon 이 필요하다. DDG4 의 physics constructor 이름: `"Geant4...Physics"` |

## 확인

```bash
cd advanced/work
ddsim --steeringFile SteeringFile_o3_gun.py --dumpSteeringFile > dump.txt      # 몇 초
grep -E "compactFile|enableGun|gun\.(particle|energy|position|direction)|vertexSigma =|calorimeterSDTypes =|mapActions =|regexSensitiveDetector =" dump.txt
```

- 빈칸이 남아 있으면 `NameError: name '____TODO_5____' is not defined` 처럼 어느 빈칸인지 알려 줍니다.
- 원래 파일과 비교: `ddsim --steeringFile $IDEA_TUTORIAL_ROOT/sim/SteeringFile_o3_gun.py --dumpSteeringFile > ref.txt; diff ref.txt dump.txt`
  steering 경로와 함수 주소 (`<function ... at 0x...>`) 두 줄만 다르면 정답입니다.
- `TODO_11`, `TODO_12` 는 함수 안에 있어서 dump 에 나오지 않습니다. 함수만 따로 불러 보는 스크립트로 확인합니다 (약 10초, geometry 없음):

  ```bash
  python3 ../01_steering_gun/check_steering.py SteeringFile_o3_gun.py
  #   output plugin: OK
  #   user physics 'setupOpticalPhysics': OK
  ```

  이름이 틀리면 `FAILED` 와 이유가 나옵니다. 이 확인 없이 제출하면 job 이 geometry 를 다 올린 뒤 (약 20분) 출력 파일 없이 끝납니다.
- 함수 안의 값은 함수 안에 직접 써야 합니다. ddsim 은 steering 을 `exec(..., globals, locals)` 로 따로 나눠 읽어서,
  파일 위쪽에 만든 변수 (예: `NAME = "..."`) 를 함수 안에서 쓰면 `NameError` 가 납니다.
- 정답: `advanced/solutions/01_steering_gun/SteeringFile_o3_gun.py`.

## 로컬에서 실제로 돌리는 명령 (실행하지 마세요)

```bash
ddsim --steeringFile SteeringFile_o3_gun.py --numberOfEvents 2 --outputFile test_sim.root \
      --random.enableEventSeed --random.seed 1
```

ddsim 하나가 메모리를 약 10 GB 쓰고 시작에 15 ~ 20분 걸립니다. 20명이 동시에 돌리면 서버가 멈추므로
**실제 시뮬레이션은 03 에서 condor 로만 합니다.**
