#!/bin/bash
# [advanced 05] condor executable: Pythia8 generation (k4run gen/pythia.py) 뒤에 ddsim 을 돌리는 1 job.
# 빈칸을 채운다.
# arguments: <PROCESS> <IDEA_TUTORIAL_ROOT> <TAG> <PYTHIA_CARD> <STEERING> <NEV>
#   출력: $TUTORIAL_OUTPUT/<TAG>_Gen/<TAG>_gen_<PROCESS>.hepmc   (Pythia 출력)
#         $TUTORIAL_OUTPUT/<TAG>_Sim/<TAG>_sim_<PROCESS>.root    (ddsim 출력)
set -eo pipefail

PROCESS=${1:?"usage: wrapper_gen_sim.sh <PROCESS> <ROOT> <TAG> <PYTHIA_CARD> <STEERING> <NEV>"}
ROOT=${2:?}
TAG=${3:?}
CARD=${4:?}
STEERING=${5:?}
NEV=${6:?}

for f in "$0" "$CARD" "$STEERING"; do
  if grep -q "____TODO""_[0-9]" "$f"; then
    echo "빈칸이 남아 있다 ($f):" >&2
    grep -n "____TODO""_[0-9]" "$f" >&2
    exit 1
  fi
done

source "$ROOT/setup_env.sh"

GENDIR="$TUTORIAL_OUTPUT/${TAG}_Gen"
SIMDIR="$TUTORIAL_OUTPUT/${TAG}_Sim"
mkdir -p "$GENDIR" "$SIMDIR"
HEPMC="$GENDIR/${TAG}_gen_${PROCESS}.hepmc"
GENROOT="$GENDIR/${TAG}_gen_${PROCESS}.root"
SIMFILE="$SIMDIR/${TAG}_sim_${PROCESS}.root"

# Pythia 의 seed 는 card 안의 Random:seed 이다. job 마다 다른 event 가 나오도록 card 사본에서 바꾼다.
SEED=____TODO_1____
JOBCARD="$GENDIR/${TAG}_card_${PROCESS}.cmd"
sed "s/^Random:seed *=.*/Random:seed = $SEED/" "$CARD" > "$JOBCARD"
grep "^Random:seed" "$JOBCARD"

echo "host: $(hostname)  process: $PROCESS  card: $CARD  nev: $NEV"

k4run "$ROOT/gen/pythia.py" \
  -n ____TODO_2____ \
  --Pythia8.PythiaInterface.pythiacard ____TODO_3____ \
  --HepMCFileWriter.Filename ____TODO_4____ \
  --IOSvc.Output "$GENROOT" \
  --RndmGenSvc.Engine.Seeds "$SEED" \
  2>&1 | stdbuf -oL awk '{ print strftime("[%Y-%m-%d %H:%M:%S]"), $0 }'

ddsim \
  --steeringFile "$STEERING" \
  --inputFiles ____TODO_5____ \
  --numberOfEvents "$NEV" \
  --random.enableEventSeed \
  --random.seed "$SEED" \
  --outputFile "$SIMFILE" \
  2>&1 | stdbuf -oL awk '{ print strftime("[%Y-%m-%d %H:%M:%S]"), $0 }'
