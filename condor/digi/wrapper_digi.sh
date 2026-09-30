#!/bin/bash
# condor executable: Digi/reco (k4run digi/run_digi_reco.py) 1 job.
# arguments: <PROCESS> <IDEA_TUTORIAL_ROOT> <SIM_DIR> <DIGI_TAG> <DIGI_COMPACT_XML> <SKIP_HELIX>
#   SIM_DIR          : 입력 Sim 파일이 있는 디렉터리. <아무이름>_sim_<PROCESS>.root 를 찾는다.
#                      (내가 만든 Sim, 또는 sungwon 의 Sim 샘플)
#   DIGI_TAG         : 출력 이름. $TUTORIAL_OUTPUT/<DIGI_TAG>_Digi/<DIGI_TAG>_digi_<PROCESS>.root
#   DIGI_COMPACT_XML : Sim 에 쓴 compact XML ($K4GEO_LOCAL 기준 상대경로)
#   SKIP_HELIX       : 자기장 OFF geometry 이면 1, physics (자기장 ON) 이면 0
set -eo pipefail

PROCESS=${1:?"usage: wrapper_digi.sh <PROCESS> <ROOT> <SIM_DIR> <DIGI_TAG> <DIGI_COMPACT_XML> <SKIP_HELIX>"}
ROOT=${2:?}
SIM_DIR=${3:?}
DIGI_TAG=${4:?}
export DIGI_COMPACT_XML=${5:?}
export DIGI_SKIP_HELIX_TRACKING=${6:?}

source "$ROOT/setup_env.sh"

SIMFILE=$(ls "$SIM_DIR"/*_sim_${PROCESS}.root)
OUTDIR="$TUTORIAL_OUTPUT/${DIGI_TAG}_Digi"
mkdir -p "$OUTDIR"
OUTFILE="$OUTDIR/${DIGI_TAG}_digi_${PROCESS}.root"
HISTOFILE="$OUTDIR/TrackHitDistances_${PROCESS}.root"

echo "host: $(hostname)  process: $PROCESS"
echo "input:  $SIMFILE"
echo "output: $OUTFILE"
echo "compact: $DIGI_COMPACT_XML   skip helix: $DIGI_SKIP_HELIX_TRACKING"

k4run "$ROOT/digi/run_digi_reco.py" \
  --IOSvc.Input "$SIMFILE" \
  --IOSvc.Output "$OUTFILE" \
  --RootHistoSink.FileName "$HISTOFILE" \
  2>&1 | stdbuf -oL awk '{ print strftime("[%Y-%m-%d %H:%M:%S]"), $0 }'
