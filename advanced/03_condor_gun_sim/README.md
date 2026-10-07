# 03. condor 로 gun Sim 제출하기

01 에서 만든 steering (p0) 은 그대로 두고, **02 에서 계산한 tower 10 의 position / direction 을 wrapper 가 command line 으로 덮어써서**
e- 40 GeV 20 event 를 condor job 1개로 만듭니다.

```bash
cd IDEA_o3_tutorial && source setup_env.sh
cp advanced/03_condor_gun_sim/wrapper_sim_blank.sh  advanced/work/wrapper_sim.sh
cp advanced/03_condor_gun_sim/submit_sim_blank.sub  advanced/work/submit_sim.sub
chmod +x advanced/work/wrapper_sim.sh
# 두 파일의 ____TODO_n____ 을 채운다
```

## 전체 흐름

```
condor_submit submit_sim.sub
  └─ job 마다 (Process = 0, 1, ...) 계산 node 에서:
       wrapper_sim.sh <Process> <ROOT> <TAG> <STEERING> <NEV>
         └─ source setup_env.sh  →  ddsim --steeringFile ... --gun.position ... --outputFile ...
```

- `.sub` 는 "무엇을, 몇 개, 어떤 자원으로" 돌릴지 condor 에 알려 주는 파일입니다.
- wrapper (executable) 는 계산 node 에서 실제로 실행되는 shell script 입니다.
- ddsim 은 steering 을 먼저 읽고 command line 옵션으로 덮어씁니다. 그래서 steering 하나로 여러 tower 를 쏠 수 있습니다.

## 빈칸: `wrapper_sim.sh`

| 빈칸 | 무엇 | 왜 / 힌트 |
|---|---|---|
| `TODO_1` | `source` 할 파일 | condor job 은 **로그인 shell 의 환경을 물려받지 않는 새 shell** 에서 시작한다. `ddsim`, `K4GEO_LOCAL` 등이 없다. 인자로 받은 `$ROOT` 를 쓴다. |
| `TODO_2` | 입자 이름 | 01 과 같은 형식 |
| `TODO_3` | energy | ddsim 은 `40*GeV` 같은 문자열을 받는다 |
| `TODO_4` | position | 02 의 tower 10 값. 반드시 `"(x, y, z)"` 형식 (mm). 괄호 없이 `-0.017,...` 를 주면 argparse 가 옵션으로 오해한다. |
| `TODO_5` | direction | 02 의 tower 10 값, 같은 형식 |
| `TODO_6` | event 수 | 인자로 받은 변수 |
| `TODO_7` | random seed | job 마다 달라야 한다 (같으면 같은 event 가 반복된다). 메인 tutorial 규칙: job 번호 + 1. bash 산술: `$((A + 1))` |
| `TODO_8` | 출력 파일 | 위에서 만든 변수 |

인자를 읽은 뒤의 `grep "____TODO""_[0-9]"` 줄은 wrapper 자신이나 steering 에 빈칸이 남아 있으면 ddsim 을 시작하기 전에 job 을 멈춥니다 (20분 기다린 뒤에 실패하지 않게).
steering 의 함수 부분 (01 의 `TODO_11`, `TODO_12`) 은 제출 전에 `01_steering_gun/check_steering.py` 로 확인하세요.

## 빈칸: `submit_sim.sub`

| 빈칸 | 무엇 | 힌트 |
|---|---|---|
| `TODO_1` | `TAG` | 출력 디렉터리와 log 이름. 예: `my_eminus_40GeV_tower10` |
| `TODO_2` | `accounting_group` | 메인 README 6장 |
| `TODO_3` | `executable` | `advanced/work/` 의 wrapper 절대 경로. `$ENV(IDEA_TUTORIAL_ROOT)` 를 쓴다 |
| `TODO_4` | `arguments` | wrapper 가 받는 5개를 순서대로. job 번호는 `$(Process)`, 파일 안의 변수는 `$(TAG)` 처럼 쓴다 |
| `TODO_5` | `request_memory` | 메인 README 13.3 의 Sim 값 |
| `TODO_6` | `queue` 뒤 | job 개수. 위에 정의한 변수를 쓴다 |

## `.sub` 의 필수 항목과 이유

| 항목 | 이유 |
|---|---|
| `accounting_group = group_fcc` | 이 cluster 는 group 별로 자원을 나눈다. 항상 넣는다. |
| `executable` | 계산 node 에서 실행할 파일. 실행 권한 (`chmod +x`) 이 있어야 한다. |
| `arguments` | `$(Process)` 는 0, 1, 2, ... 로 job 마다 달라진다. 이 값으로 seed 와 출력 파일 이름을 바꿔서 job 끼리 겹치지 않게 한다. |
| `output` / `error` / `log` | stdout, stderr, condor 자신의 기록 (시작, 끝, 메모리 사용량). 실패 원인은 `.err`, 자원 사용량은 `.log` 에서 본다. `$(Process)` 를 넣어야 job 끼리 덮어쓰지 않는다. |
| `environment` | 새 shell 에 꼭 전해야 할 변수만 넘긴다 (설치 경로, 출력 경로). 나머지는 wrapper 가 `setup_env.sh` 로 만든다. |
| `request_cpus` / `request_memory` | condor 는 요청한 만큼의 slot 을 잡는다. 메모리를 실제보다 적게 잡으면 job 이 `Held` 가 되고, 너무 많이 잡으면 node 를 못 받아 오래 기다린다. |
| `should_transfer_files` / `transfer_output_files = ""` | 출력은 wrapper 가 공유 디스크 (`$TUTORIAL_OUTPUT`) 에 직접 쓴다. condor 가 따로 되돌려 보낼 파일은 없다. |
| `queue N` | job 을 N 개 만든다. 반드시 마지막 줄. |

## 제출과 확인

**1. dry-run** (아무것도 제출하지 않고, condor 가 이해한 내용을 파일로 씀):

```bash
condor_submit -dry-run dry.ad advanced/work/submit_sim.sub
grep -E "^(Cmd|Args|AcctGroup|RequestMemory|Environment) " dry.ad
```

`Args` 에 tag, steering 경로, event 수가 제대로 들어갔는지, `AcctGroup = "group_fcc"` 인지 봅니다.
빈칸 확인: `grep -n "____TODO" advanced/work/wrapper_sim.sh advanced/work/submit_sim.sub` 가 아무것도 출력하지 않아야 합니다.

**2. 제출과 감시**

```bash
condor_submit advanced/work/submit_sim.sub
condor_q                                  # ST 가 I (대기), R (실행), H (Held)
condor_tail <cluster>.0                   # 실행 중 출력. 몇 분 간격으로 두 번 보고 진행되는지 확인
condor_q -hold                            # Held 면 이유
condor_history <cluster>                  # 끝난 job
```

- 첫 event 까지 보통 20분 안팎입니다 (메인 README 13.1). 그동안 출력이 geometry 로딩에서 멈춰 있어도 정상입니다.
- `condor_q` 의 `RUN_TIME` 이나 상태 집계는 이 cluster 에서 늦게 갱신될 때가 있습니다. 진행은 `condor_tail` 로 보세요.
- `.out` / `.err` 는 job 이 끝나야 `condor_log/` 에 생깁니다.
- `.log` 에 `Job was evicted` 가 보이면 node 사정으로 job 이 중단된 것입니다. condor 가 다른 node 에서 처음부터 다시 시작하니 기다리면 됩니다 (`RUN_TIME` 도 0 부터 다시 셉니다).

**3. 출력 확인** (job 이 끝난 뒤)

```bash
ls -l $TUTORIAL_OUTPUT/my_eminus_40GeV_tower10_Sim/*_sim_*.root
podio-dump $TUTORIAL_OUTPUT/my_eminus_40GeV_tower10_Sim/my_eminus_40GeV_tower10_sim_0.root | head -30
python3 advanced/02_beam_pointing/find_hit_tower.py $TUTORIAL_OUTPUT/my_eminus_40GeV_tower10_Sim/*_sim_*.root
```

- 파일이 있다고 job 이 끝난 것은 아닙니다. ddsim 은 event 를 쓰면서 파일을 키웁니다. `podio-dump` 의 event 수가 `NEV` 와 같은지 보세요.
- `find_hit_tower.py` 에서 가장 많이 맞은 tower 가 **eta 10, phi 36** 이면 조준이 맞은 것입니다.
  steering 의 p0 (tower 0) 가 나오면 command line 덮어쓰기가 안 된 것이니 wrapper 의 `--gun.*` 줄을 확인하세요.
  정답으로 돌린 20 event 의 결과:

  ```
  1차 입자 (평균)   : 위치 = (52.5, -2.2, 2.2) mm,  방향 = (-0.017452, 0.978674, 0.204678)
                     방향의 theta = 78.189 deg, phi = 91.022 deg
  DRC hit 중심 (평균): theta = 78.404 deg, phi = 90.128 deg
  가장 에너지가 큰 tower 가 받은 비율 (평균): 0.21
    eta   10, phi   36 : 9 events
    eta   11, phi   36 : 3 events
    eta    9, phi   36 : 2 events
  ```

  vertex 를 8 mm smearing 하고 shower 가 옆 tower 로 퍼지므로, 이웃 tower (9, 11) 가 가장 큰 event 도 있습니다.
  hit 중심의 theta (78.4°) 가 tower 10 의 범위 (77.6° ~ 78.75°) 안에 있는지 보세요.
  방향의 phi 가 91° 인 것은 1° 기울임 때문이고, 앞면에서는 phi 90° (phi 번호 36 의 중심) 에 맞습니다.

## 로컬에서 실제로 돌리는 명령 (실행하지 마세요)

wrapper 를 로컬에서 직접 실행하면 condor 없이 같은 일을 합니다:

```bash
./advanced/work/wrapper_sim.sh 0 $IDEA_TUTORIAL_ROOT my_test advanced/work/SteeringFile_o3_gun.py 2
```

ddsim 이 약 10 GB 메모리를 쓰므로 로그인 서버에서는 실행하지 않습니다. 빈칸 확인만 하려면 위의 `grep` 을 쓰세요.

정답: `advanced/solutions/03_condor_gun_sim/`.
