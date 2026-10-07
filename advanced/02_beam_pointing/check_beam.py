#!/usr/bin/env python3
"""gun 의 위치와 방향을 넣으면 beam 이 DRC 앞면의 어디에 맞는지 계산한다 (시뮬레이션 없음, 1초).

beam 을 직선으로 보고 DRC 앞면 (barrel: 반경 2805 mm 원통, endcap: z = +-2805 mm 평면) 과
만나는 점을 구한 뒤, 그 점이 속한 tower 의 번호, 그 tower 중심 (pointing axis 가 앞면과 만나는 점)
에서 얼마나 떨어졌는지, beam 과 tower 축 사이의 각도를 출력한다.
ECAL, solenoid 등 DRC 앞의 물질과 shower 퍼짐은 고려하지 않는다.

예)
  python3 check_beam.py --position 48.9638 0 0 --direction -0.017452 0.999800 0.009816
  python3 check_beam.py --position 48.9638 0 0 --direction -0.017452 0.999800 0.009816 --tower 0
"""
import argparse
import math
import sys

R_FRONT = 2805.0  # barrel 앞면 반경 [mm]
Z_FRONT = 2805.0  # endcap 앞면 z [mm]
DTHETA = 0.019634954  # tower 하나의 theta 폭 [rad] (= pi/160)
N_BARREL = 40  # barrel tower 0 ~ 39, endcap tower 40 ~ 74
N_ENDCAP = 35
N_PHI = 144


def tower_of(theta):
    """theta [rad] -> (부호 있는 tower 번호, tower 중심 theta). +z 쪽은 0 이상, -z 쪽은 -1 이하."""
    side = 1
    if theta > math.pi / 2:
        theta, side = math.pi - theta, -1
    if theta >= math.pi / 4:
        k = int((math.pi / 2 - theta) // DTHETA)
        n, center = k, math.pi / 2 - (k + 0.5) * DTHETA
    else:
        k = int((math.pi / 4 - theta) // DTHETA)
        n, center = N_BARREL + k, math.pi / 4 - (k + 0.5) * DTHETA
    if n >= N_BARREL + N_ENDCAP:
        return None, None
    if side < 0:
        return -n - 1, math.pi - center
    return n, center


def front_point(theta):
    """theta 방향 직선 (원점 출발) 이 DRC 앞면과 만나는 점."""
    s, c = math.sin(theta), math.cos(theta)
    t = R_FRONT / s if abs(c) * R_FRONT <= s * Z_FRONT else Z_FRONT / abs(c)
    return t * s, t * c  # (R, z)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--position", nargs=3, type=float, required=True, metavar=("X", "Y", "Z"), help="gun 위치 [mm]")
    ap.add_argument("--direction", nargs=3, type=float, required=True, metavar=("DX", "DY", "DZ"), help="gun 방향")
    ap.add_argument("--tower", type=int, default=None, help="조준하려던 tower 번호 (주면 맞았는지 알려 준다)")
    args = ap.parse_args()

    x0, y0, z0 = args.position
    norm = math.sqrt(sum(v * v for v in args.direction))
    if norm == 0:
        sys.exit("direction 이 0 벡터이다")
    dx, dy, dz = (v / norm for v in args.direction)
    if abs(norm - 1) > 1e-3:
        print(f"참고: direction 의 크기가 {norm:.4f} 이다 (ddsim 은 방향만 쓰므로 괜찮다). 단위벡터로 바꿔서 계산한다.")

    # barrel 원통 R = R_FRONT 과 만나는 t (t > 0)
    a = dx * dx + dy * dy
    b = 2 * (x0 * dx + y0 * dy)
    c = x0 * x0 + y0 * y0 - R_FRONT ** 2
    t_hit = None
    if a > 0 and b * b - 4 * a * c >= 0:
        t = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)
        if t > 0 and abs(z0 + t * dz) <= Z_FRONT:
            t_hit, where = t, "barrel"
    if t_hit is None and dz != 0:
        t = (math.copysign(Z_FRONT, dz) - z0) / dz
        if t > 0:
            t_hit, where = t, "endcap"
    if t_hit is None:
        sys.exit("DRC 앞면과 만나지 않는다")

    hx, hy, hz = x0 + t_hit * dx, y0 + t_hit * dy, z0 + t_hit * dz
    r = math.hypot(hx, hy)
    theta = math.atan2(r, hz)
    phi = math.atan2(hy, hx)
    n, theta_c = tower_of(theta)
    if n is None:
        sys.exit(f"theta = {math.degrees(theta):.2f} deg: DRC 가 덮지 않는 영역 (beam pipe 쪽) 이다")
    dphi = 2 * math.pi / N_PHI
    iphi = int(round(phi / dphi)) % N_PHI
    phi_c = iphi * dphi

    # tower 중심: pointing axis (theta_c, phi_c) 가 앞면과 만나는 점
    rc, zc = front_point(theta_c)
    cx, cy = rc * math.cos(phi_c), rc * math.sin(phi_c)
    dist = math.sqrt((hx - cx) ** 2 + (hy - cy) ** 2 + (hz - zc) ** 2)
    ax, ay, az = math.sin(theta_c) * math.cos(phi_c), math.sin(theta_c) * math.sin(phi_c), math.cos(theta_c)
    angle = math.degrees(math.acos(max(-1.0, min(1.0, dx * ax + dy * ay + dz * az))))

    print(f"DRC 앞면 ({where}) 에 맞는 점: ({hx:.1f}, {hy:.1f}, {hz:.1f}) mm,  "
          f"theta = {math.degrees(theta):.3f} deg, phi = {math.degrees(phi):.3f} deg")
    print(f"그 점이 속한 tower: eta 번호 {n} (중심 theta = {math.degrees(theta_c):.4f} deg), "
          f"phi 번호 {iphi} (중심 phi = {math.degrees(phi_c):.1f} deg)")
    print(f"tower 중심에서 떨어진 거리: {dist:.1f} mm")
    print(f"beam 과 tower 축 사이의 각도: {angle:.3f} deg")
    if args.tower is not None:
        ok = n == args.tower and dist < 5.0
        print("=> " + (f"OK: tower {args.tower} 의 중심을 맞힌다." if ok else
                       f"다시 확인: tower {args.tower} 를 조준했는데 tower {n} 의 중심에서 {dist:.1f} mm 떨어진 곳에 맞는다."))


if __name__ == "__main__":
    main()
