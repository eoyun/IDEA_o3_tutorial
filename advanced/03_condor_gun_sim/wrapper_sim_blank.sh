#!/bin/bash
# [advanced 03] condor executable: particle gun Sim (ddsim) 1 job. 빈칸을 채운다.
# arguments: <PROCESS> <IDEA_TUTORIAL_ROOT> <TAG> <STEERING> <NEV>
# 출력: $TUTORIAL_OUTPUT/<TAG>_Sim/<TAG>_sim_<PROCESS>.root
set -eo pipefail

PROCESS=${1:?"usage: wrapper_sim.sh <PROCESS> <ROOT> <TAG> <STEERING> <NEV>"}
ROOT=${2:?}
TAG=${3:?}
STEERING=${4:?}
NEV=${5:?}

for f in "$0" "$STEERING"; do
  if grep -q "____TODO""_[0-9]" "$f"; then
    echo "빈칸이 남아 있다 ($f):" >&2
    grep -n "____TODO""_[0-9]" "$f" >&2
    exit 1
  fi
done

# condor job 은 새 shell 에서 시작한다
source ____TODO_1____

# ---- 02 에서 계산한 값 (mm, 단위 없는 방향 벡터). 형식: "(x, y, z)" ----
GUN_PARTICLE="____TODO_2____"
GUN_ENERGY="____TODO_3____"
GUN_POSITION="____TODO_4____"
GUN_DIRECTION="____TODO_5____"

OUTDIR="$TUTORIAL_OUTPUT/${TAG}_Sim"
mkdir -p "$OUTDIR"
OUTFILE="$OUTDIR/${TAG}_sim_${PROCESS}.root"

echo "host: $(hostname)  process: $PROCESS  steering: $STEERING  nev: $NEV"
echo "gun: $GUN_PARTICLE $GUN_ENERGY  position $GUN_POSITION  direction $GUN_DIRECTION"
echo "output: $OUTFILE"

ddsim \
  --steeringFile "$STEERING" \
  --numberOfEvents ____TODO_6____ \
  --gun.particle "$GUN_PARTICLE" \
  --gun.energy "$GUN_ENERGY" \
  --gun.position "$GUN_POSITION" \
  --gun.direction "$GUN_DIRECTION" \
  --random.enableEventSeed \
  --random.seed ____TODO_7____ \
  --outputFile ____TODO_8____ \
  2>&1 | stdbuf -oL awk '{ print strftime("[%Y-%m-%d %H:%M:%S]"), $0 }'
