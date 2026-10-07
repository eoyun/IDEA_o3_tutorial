#!/bin/bash
# [advanced 04] condor executable: Digi/reco (k4run digi/run_digi_reco.py) 1 job.
# arguments: <PROCESS> <IDEA_TUTORIAL_ROOT> <SIM_DIR> <DIGI_TAG> <DIGI_COMPACT_XML> <SKIP_HELIX>
#   SIM_DIR 안의 *_sim_<PROCESS>.root 를 읽어서
#   $TUTORIAL_OUTPUT/<DIGI_TAG>_Digi/<DIGI_TAG>_digi_<PROCESS>.root 를 쓴다.
set -eo pipefail

if grep -q "____TODO""_[0-9]" "$0"; then
  echo "빈칸이 남아 있다:" >&2
  grep -n "____TODO""_[0-9]" "$0" >&2
  exit 1
fi

PROCESS=${1:?"usage: wrapper_digi.sh <PROCESS> <ROOT> <SIM_DIR> <DIGI_TAG> <DIGI_COMPACT_XML> <SKIP_HELIX>"}
ROOT=${2:?}
SIM_DIR=${3:?}
DIGI_TAG=${4:?}

# run_digi_reco.py 는 이 두 환경변수를 읽는다
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
