#!/bin/bash
# 미리 만들어 둔 예제 샘플에서 디렉터리마다 ROOT 파일 하나씩을 내 디렉터리로 복사한다.
# (샘플 전체는 70 GB 가 넘어서 통째로 가져갈 수 없다. 파일 구조를 열어 보는 용도.)
#
# 사용법:
#     ./copy_example_files.sh                    # Digi 파일만, ./example_files/ 아래로 (약 0.9 GB)
#     ./copy_example_files.sh -o /my/path        # 복사할 위치 지정
#     ./copy_example_files.sh --with-sim         # Sim 파일도 같이 (총 약 2.1 GB)
#     ./copy_example_files.sh -n                 # 복사하지 않고 무엇을 얼마나 복사할지만 출력
#
# 결과: <출력 위치>/<샘플 디렉터리 이름>/<ROOT 파일 하나>
# 이미 같은 크기의 파일이 있으면 건너뛰므로 중단되었을 때 다시 실행해도 된다.
#
# 샘플 위치는 $TUTORIAL_SAMPLES (setup_env.sh 를 source 했으면 자동). 없으면 기본 경로를 쓴다.

set -u

SAMPLES="${TUTORIAL_SAMPLES:-/fcc/home/sungwon/2026_Oct_KEY4HEP_tutorial/k4geo/example/condor_output}"
OUTDIR="./example_files"
WITH_SIM=0
DRYRUN=0

while [ $# -gt 0 ]; do
  case "$1" in
    -o|--output) OUTDIR="${2:?-o 뒤에 경로가 필요합니다}"; shift 2 ;;
    --with-sim)  WITH_SIM=1; shift ;;
    -n|--dry-run) DRYRUN=1; shift ;;
    -h|--help)   sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "알 수 없는 옵션: $1  (./copy_example_files.sh -h)" >&2; exit 1 ;;
  esac
done

if [ ! -d "$SAMPLES" ] || [ ! -r "$SAMPLES" ]; then
  echo "샘플 경로를 읽을 수 없습니다: $SAMPLES" >&2
  echo "fcc_users 그룹이고 FCC 서버에 로그인한 상태인지 확인하세요." >&2
  exit 1
fi

# 샘플 디렉터리마다 첫 번째 파일을 고른다. TrackHitDistances_*.root 같은 부산물은 제외.
declare -a SRC=() DST=()
total=0
for d in "$SAMPLES"/*_Digi "$SAMPLES"/*_Sim; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  case "$name" in
    *_Digi) pat='*_digi_*.root' ;;
    *_Sim)  [ "$WITH_SIM" = 1 ] || continue; pat='*_sim_*.root' ;;
  esac
  f=$(cd "$d" && ls -v $pat 2>/dev/null | head -n 1)
  [ -n "$f" ] || { echo "경고: $name 에 $pat 파일이 없어 건너뜁니다" >&2; continue; }
  SRC+=("$d/$f"); DST+=("$OUTDIR/$name/$f")
  total=$(( total + $(stat -c %s "$d/$f") ))
done

n=${#SRC[@]}
if [ "$n" -eq 0 ]; then
  echo "복사할 파일을 찾지 못했습니다 (샘플 경로: $SAMPLES)" >&2
  exit 1
fi

echo "샘플 경로 : $SAMPLES"
echo "복사 위치 : $OUTDIR"
echo "파일 개수 : $n  (Sim 포함: $([ "$WITH_SIM" = 1 ] && echo 예 || echo 아니오))"
printf "총 용량   : %.2f GB\n" "$(echo "$total" | awk '{print $1/1e9}')"

if [ "$DRYRUN" = 1 ]; then
  for i in "${!SRC[@]}"; do
    printf "  %-68s %6.1f MB\n" "${DST[$i]#"$OUTDIR"/}" "$(stat -c %s "${SRC[$i]}" | awk '{print $1/1e6}')"
  done
  exit 0
fi

avail=$(df -B1 --output=avail "$(mkdir -p "$OUTDIR" && echo "$OUTDIR")" | tail -n 1)
if [ "$avail" -lt "$total" ]; then
  echo "복사 위치의 여유 공간이 부족합니다 ($(echo "$avail" | awk '{printf "%.2f", $1/1e9}') GB). -o 로 다른 경로를 지정하세요." >&2
  exit 1
fi

copied=0; skipped=0
for i in "${!SRC[@]}"; do
  src=${SRC[$i]}; dst=${DST[$i]}
  if [ -f "$dst" ] && [ "$(stat -c %s "$dst")" = "$(stat -c %s "$src")" ]; then
    skipped=$((skipped + 1)); continue
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst.part" && mv "$dst.part" "$dst" || { echo "복사 실패: $src" >&2; exit 1; }
  copied=$((copied + 1))
  echo "[$((copied + skipped))/$n] ${dst#"$OUTDIR"/}"
done

echo "완료: $copied 개 복사, $skipped 개는 이미 있어서 건너뜀 -> $OUTDIR"
