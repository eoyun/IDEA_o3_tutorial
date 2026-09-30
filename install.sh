#!/bin/bash
# IDEA o3 tutorial 설치 스크립트: genfit -> k4geo -> k4RecTracker 를 내려받아 빌드하고
# digitization 에 필요한 ONNX 모델 파일을 받는다.
#
# 사용법:
#     ./install.sh          # 기본: make -j4
#     ./install.sh 2        # 2 core 로 빌드
#
# 설치 위치: <이 repo>/packages/{genfit,k4geo,k4RecTracker}
# 소요 시간: 4 core 기준 수십 분 (대부분 k4geo). 백그라운드 (tmux/nohup)로 돌려 두는 것을 권장.
#     nohup ./install.sh > install.log 2>&1 &
#
# 중간에 실패했으면 원인을 고치고 다시 실행하면 된다. 이미 끝난 패키지는 건너뛴다.
# (처음부터 다시 하려면 packages/<패키지>/.install_done 파일을 지우거나 FORCE=1 ./install.sh)
#
# 개인 fork 를 쓰고 싶으면 환경변수로 덮어쓴다. 예:
#     K4GEO_REPO=https://github.com/<id>/k4geo.git K4GEO_BRANCH=my_branch ./install.sh

set -eo pipefail

NJOBS="${1:-4}"

TUTORIAL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export IDEA_TUTORIAL_ROOT="$TUTORIAL_ROOT"
PKG_DIR="${IDEA_TUTORIAL_PKG_DIR:-$TUTORIAL_ROOT/packages}"
export IDEA_TUTORIAL_PKG_DIR="$PKG_DIR"

GENFIT_REPO="${GENFIT_REPO:-https://github.com/GenFit/GenFit.git}"
GENFIT_REV="${GENFIT_REV:-1eceeb7}"
K4GEO_REPO="${K4GEO_REPO:-https://github.com/swkim95/k4geo.git}"
K4GEO_BRANCH="${K4GEO_BRANCH:-geo_o3_tutorial}"
K4RECTRACKER_REPO="${K4RECTRACKER_REPO:-https://github.com/swkim95/k4RecTracker.git}"
K4RECTRACKER_BRANCH="${K4RECTRACKER_BRANCH:-edm4hep_trackstate_fix}"
ONNX_URL="${ONNX_URL:-https://fccsw.web.cern.ch/fccsw/filesForSimDigiReco/IDEA/IDEA_o1_v03/SimpleGatrIDEAv3o1.onnx}"
FORCE="${FORCE:-0}"

log() { echo; echo "==================== [install] $* ($(date '+%F %T'))"; }

# key4hep 환경 (setup_env.sh 와 같은 release). 로컬 빌드 경로는 아직 없으므로 setup.sh 만 source.
RELEASE="${IDEA_TUTORIAL_KEY4HEP_RELEASE:-2026-04-08}"
unset KEY4HEP_STACK
set --
source /cvmfs/sw.hsf.org/key4hep/setup.sh -r "$RELEASE" > /dev/null
log "key4hep $RELEASE, NJOBS=$NJOBS, packages -> $PKG_DIR"
mkdir -p "$PKG_DIR"

is_done() { [ "$FORCE" != "1" ] && [ -f "$PKG_DIR/$1/.install_done" ]; }

clone_or_update() {  # <name> <repo> <rev-or-branch>
  local name=$1 repo=$2 rev=$3
  if [ ! -d "$PKG_DIR/$name/.git" ]; then
    git clone "$repo" "$PKG_DIR/$name"
  fi
  git -C "$PKG_DIR/$name" fetch --tags origin
  git -C "$PKG_DIR/$name" checkout "$rev"
}

# ---------------------------------------------------------------- genfit
# CVMFS 의 genfit 은 ROOT dictionary (.pcm) 가 빠져 있어서 k4RecTracker Tracking 에 쓸 수 없다.
if is_done genfit; then
  log "genfit: 이미 설치됨, 건너뜀"
else
  log "genfit ($GENFIT_REV) 빌드"
  clone_or_update genfit "$GENFIT_REPO" "$GENFIT_REV"
  cmake -S "$PKG_DIR/genfit" -B "$PKG_DIR/genfit/build" \
        -DCMAKE_INSTALL_PREFIX="$PKG_DIR/genfit/install" \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_TESTING=OFF
  cmake --build "$PKG_DIR/genfit/build" -j"$NJOBS" --target install
  touch "$PKG_DIR/genfit/.install_done"
fi

# ---------------------------------------------------------------- k4geo
# IDEA_o3 geometry (DRC air-gap 수정, noOpt S-channel SD action 등) 이 들어 있는 fork.
if is_done k4geo; then
  log "k4geo: 이미 설치됨, 건너뜀"
else
  log "k4geo ($K4GEO_BRANCH) 빌드"
  clone_or_update k4geo "$K4GEO_REPO" "$K4GEO_BRANCH"
  cmake -S "$PKG_DIR/k4geo" -B "$PKG_DIR/k4geo/build" \
        -DCMAKE_INSTALL_PREFIX="$PKG_DIR/k4geo/install" \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_CXX_STANDARD=20 -DBUILD_TESTING=OFF
  cmake --build "$PKG_DIR/k4geo/build" -j"$NJOBS" --target install
  touch "$PKG_DIR/k4geo/.install_done"
fi

# ---------------------------------------------------------------- k4RecTracker
# DCHdigi_v02 / GGTFTrackFinder 를 위해 필요. CVMFS 버전은 우리 k4geo 와 맞지 않는다.
# 전체 install 타겟은 (우리와 무관한) 다른 모듈 때문에 실패하므로 필요한 타겟만 빌드하고
# Tracking 의 manifest 파일은 직접 복사한다.
if is_done k4RecTracker; then
  log "k4RecTracker: 이미 설치됨, 건너뜀"
else
  log "k4RecTracker ($K4RECTRACKER_BRANCH) 빌드"
  clone_or_update k4RecTracker "$K4RECTRACKER_REPO" "$K4RECTRACKER_BRANCH"
  KRT="$PKG_DIR/k4RecTracker"
  cmake -S "$KRT" -B "$KRT/build" \
        -DCMAKE_INSTALL_PREFIX="$KRT/install" \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_CXX_STANDARD=20 -DBUILD_TESTING=OFF \
        -DCMAKE_PREFIX_PATH="$PKG_DIR/k4geo/install:${CMAKE_PREFIX_PATH:-}" \
        -Dk4geo_DIR="$PKG_DIR/k4geo/install/lib/cmake/k4geo" \
        -DGenFit_INCLUDE_DIRS="$PKG_DIR/genfit/install/include" \
        -DGenFit_LIBRARIES="$PKG_DIR/genfit/install/lib64/libgenfit2.so"
  cmake --build "$KRT/build" -j"$NJOBS" --target DCHdigi DCHdigi_MergeComponents \
        DCHdigi_MergeConfDB2 DCHdigi_MergeConfdb
  cmake --build "$KRT/build" -j"$NJOBS" --target Tracking Tracking_MergeComponents \
        Tracking_MergeConfDB2 Tracking_MergeConfdb

  B="$KRT/build"; I="$KRT/install"
  mkdir -p "$I/lib" "$I/python/Tracking" "$I/python/DCHdigi"
  cp -f "$B"/DCHdigi/{libDCHdigi.so,libextension.so,libextensionDict.so,libextensionDict_rdict.pcm,extensionDictDict.rootmap,DCHdigi.components} "$I/lib/"
  cp -f "$B"/DCHdigi.confdb "$B"/DCHdigi.confdb2 "$I/lib/"
  cp -f "$B"/Tracking/{libTracking.so,Tracking.components} "$I/lib/"
  cp -f "$B"/Tracking.confdb "$B"/Tracking.confdb2 "$I/lib/"
  cp -f "$B"/Tracking/genConfDir/Tracking/TrackingConf.py "$I/python/Tracking/"
  cp -f "$B"/DCHdigi/genConfDir/DCHdigi/DCHdigiConf.py "$I/python/DCHdigi/"
  touch "$I/python/Tracking/__init__.py" "$I/python/DCHdigi/__init__.py"
  touch "$KRT/.install_done"
fi

# ---------------------------------------------------------------- ONNX 모델 (GGTF tracking 용)
ONNX_FILE="$TUTORIAL_ROOT/digi/SimpleGatrIDEAv3o1.onnx"
if [ -s "$ONNX_FILE" ]; then
  log "ONNX 모델: 이미 있음"
else
  log "ONNX 모델 다운로드 (약 68 MB)"
  wget -O "$ONNX_FILE.part" "$ONNX_URL"
  mv "$ONNX_FILE.part" "$ONNX_FILE"
fi

log "완료. 다음부터는 새 터미널에서:  source $TUTORIAL_ROOT/setup_env.sh"
