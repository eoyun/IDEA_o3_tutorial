#!/usr/bin/env python3
"""steering file 안의 함수 (output plugin, user physics) 를 geometry 없이 한 번 불러 본다 (약 10초, 가벼움).

--dumpSteeringFile 은 함수를 실행하지 않으므로, plugin 이름이나 physics 이름이 틀려도 통과한다.
그런 오류는 실제 job 에서 geometry 를 다 올린 뒤 (20분 뒤) 에야 드러나고, 출력 파일 없이 끝날 수 있다.
이 스크립트는 ddsim 과 같은 방법 (exec, globals 와 locals 분리) 으로 steering 을 읽은 뒤 그 함수들을 부른다.

예)
  python3 check_steering.py ../work/SteeringFile_o3_gun.py
"""
import io
import sys


def main():
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    fname = sys.argv[1]

    from DDG4 import Kernel
    from DDSim.DD4hepSimulation import DD4hepSimulation

    sim = DD4hepSimulation()
    globs, locs = {}, {"SIM": sim}
    try:
        exec(compile(io.open(fname).read(), fname, "exec"), globs, locs)
    except Exception as exc:
        sys.exit(f"steering 을 읽지 못했다: {type(exc).__name__}: {exc}")
    sim = locs["SIM"]

    checks = [("output plugin", lambda: sim.outputConfig.userOutputPlugin and sim.outputConfig.userOutputPlugin(sim))]
    checks += [(f"user physics '{fn.__name__}'", lambda fn=fn: fn(Kernel())) for fn in sim.physics._userFunctions]
    failed = 0
    for name, call in checks:
        try:
            call()
            print(f"  {name}: OK")
        except Exception as exc:
            failed += 1
            print(f"  {name}: FAILED  {type(exc).__name__}: {exc}")
    print("모두 OK" if not failed else f"{failed} 개 실패")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
