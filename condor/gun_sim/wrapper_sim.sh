#!/bin/bash
# condor executable: particle gun Sim (ddsim) 1 job.
# arguments: <PROCESS> <IDEA_TUTORIAL_ROOT> <TAG> <STEERING> <NEV>
#   PROCESS : job 번호 (0,1,2,...). seed = PROCESS+1 이라 job 마다 다른 event 가 나온다.
#   출력   : $TUTORIAL_OUTPUT/<TAG>_Sim/<TAG>_sim_<PROCESS>.root
# 선택: 환경변수 DDSIM_EXTRA 로 ddsim 옵션을 더 줄 수 있다 (예: --gun.energy "20*GeV").
set -eo pipefail

PROCESS=${1:?"usage: wrapper_sim.sh <PROCESS> <ROOT> <TAG> <STEERING> <NEV>"}
ROOT=${2:?}
TAG=${3:?}
STEERING=${4:?}
NEV=${5:?}

source "$ROOT/setup_env.sh"

OUTDIR="$TUTORIAL_OUTPUT/${TAG}_Sim"
mkdir -p "$OUTDIR"
OUTFILE="$OUTDIR/${TAG}_sim_${PROCESS}.root"

echo "host: $(hostname)  process: $PROCESS  steering: $STEERING  nev: $NEV"
echo "output: $OUTFILE"

ddsim \
  --steeringFile "$STEERING" \
  --numberOfEvents "$NEV" \
  --random.enableEventSeed \
  --random.seed $((PROCESS + 1)) \
  --outputFile "$OUTFILE" \
  ${DDSIM_EXTRA:-} \
  2>&1 | stdbuf -oL awk '{ print strftime("[%Y-%m-%d %H:%M:%S]"), $0 }'
