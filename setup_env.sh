#!/bin/bash
# IDEA o3 tutorial 환경 설정. 새 터미널을 열 때마다 (또는 condor wrapper 안에서) 실행:
#
#     source /path/to/IDEA_o3_tutorial/setup_env.sh
#
# install.sh 가 만든 로컬 빌드 (genfit, k4geo, k4RecTracker)를 CVMFS key4hep 위에 얹는다.

# 이 파일이 있는 디렉터리 = tutorial repo 루트
export IDEA_TUTORIAL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# install.sh 가 패키지를 내려받아 빌드하는 위치 (install.sh 의 INSTALL_DIR 과 같아야 함)
export IDEA_TUTORIAL_PKG_DIR="${IDEA_TUTORIAL_PKG_DIR:-$IDEA_TUTORIAL_ROOT/packages}"

# key4hep 릴리즈. install.sh 와 반드시 같은 것을 써야 한다 (ABI 호환).
export IDEA_TUTORIAL_KEY4HEP_RELEASE="${IDEA_TUTORIAL_KEY4HEP_RELEASE:-2026-04-08}"

# 이미 다른 key4hep 환경이 잡혀 있어도 다시 잡을 수 있도록 지운다.
unset KEY4HEP_STACK
_saved_args=("$@")
set --
source /cvmfs/sw.hsf.org/key4hep/setup.sh -r "$IDEA_TUTORIAL_KEY4HEP_RELEASE" > /dev/null
set -- "${_saved_args[@]}"
unset _saved_args

# 로컬 k4geo 소스 디렉터리 (compact XML 위치). CVMFS 의 $K4GEO 는 건드리지 않는다:
# analysis/common.py 가 CVMFS 의 $K4GEO 를 사용한다.
export K4GEO_LOCAL="$IDEA_TUTORIAL_PKG_DIR/k4geo"
export K4RECTRACKER_LOCAL="$IDEA_TUTORIAL_PKG_DIR/k4RecTracker"
export GENFIT_LOCAL="$IDEA_TUTORIAL_PKG_DIR/genfit"

# 로컬 빌드를 CVMFS 것보다 먼저 찾도록 앞에 붙인다. (순서 중요: genfit -> k4RecTracker -> k4geo)
export LD_LIBRARY_PATH="$GENFIT_LOCAL/install/lib64:$K4RECTRACKER_LOCAL/install/lib:$K4GEO_LOCAL/install/lib:$LD_LIBRARY_PATH"
export PYTHONPATH="$K4RECTRACKER_LOCAL/install/python:$PYTHONPATH"

# 미리 만들어 둔 sungwon 샘플 (읽기 전용). 분석 스크립트 예제들이 이 경로를 쓴다.
export TUTORIAL_SAMPLES="${TUTORIAL_SAMPLES:-/fcc/home/sungwon/2026_Oct_KEY4HEP_tutorial/k4geo/example/condor_output}"

# 이 tutorial 로 만드는 출력 위치
export TUTORIAL_OUTPUT="${TUTORIAL_OUTPUT:-$IDEA_TUTORIAL_ROOT/condor_output}"

echo "[setup_env] key4hep $IDEA_TUTORIAL_KEY4HEP_RELEASE  |  tutorial root: $IDEA_TUTORIAL_ROOT"
echo "[setup_env] local packages: $IDEA_TUTORIAL_PKG_DIR"
