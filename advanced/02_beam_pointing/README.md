# 02. beam 이 원하는 tower 를 맞히도록 조준하기

01 에서는 p0 (barrel tower 0) 의 값을 그대로 썼습니다. 여기서는 **barrel tower n** 을 맞히는 gun 의
position 과 direction 을 직접 계산합니다 (n 은 각자 다르게 받습니다). 계산은 python 이나 계산기로 합니다.

## 좌표계와 치수

- z 축이 beam pipe 방향입니다. θ 는 +z 축에서 잰 각도 (polar angle), φ 는 x 축에서 잰 각도 (azimuth) 입니다.
- 이 tutorial 은 항상 **+y 방향 (φ = 90°)** 으로 쏩니다. φ = 90° 는 phi 번호 36 번 tower 의 중심입니다 (phi 는 2.5° 씩 144 개).
- DRC 앞면: barrel 은 반경 `R_in = 2805 mm` 원통, endcap 은 `z = 2805 mm` 평면입니다 (`DectDimensions_IDEA_o3_v01.xml`).
- tower 는 원점을 향하는 (projective) 모양이고, theta 방향 폭은 하나에 `Δθ = π/160 = 1.125°` 입니다.
  - barrel: tower 0 ~ 39. tower 0 은 θ = 90° 바로 옆 (θ = 90° ~ 88.875°) 이고 번호가 커질수록 θ 가 작아집니다. tower 39 의 끝이 θ = 45° 입니다.
  - endcap: tower 40 ~ 74. θ = 45° 에서 시작해서 작아집니다.
- beam 을 tower 축과 정확히 평행하게 쏘면 fiber 사이의 구리만 지나가거나 fiber 하나를 따라 가는 경우가 생깁니다
  (channeling). 그래서 tower 축에서 **x 방향으로 α = 1° 기울여** 쏩니다.

## 과제: barrel tower n 의 θ_n, position, direction

단계별 힌트입니다. 막히면 한 단계씩 펼쳐 보세요.

<details><summary>힌트 1: tower n 중심의 θ</summary>

tower 0 의 중심은 θ = 90° − ½Δθ 입니다. 하나씩 Δθ 만큼 작아집니다.
</details>

<details><summary>힌트 2: tower 축 방향과 앞면까지의 거리</summary>

φ = 90° 이므로 tower 축 방향은 (0, sin θ_n, cos θ_n) 입니다.
원점에서 이 방향으로 가다가 반경 R_in 에 닿는 거리 L 은? (반경 = L·sin θ_n)
</details>

<details><summary>힌트 3: 1° 기울인 방향</summary>

축 방향에 cos α 를 곱하고, x 성분에 −sin α 를 넣으면 크기 1 인 방향이 됩니다.
</details>

<details><summary>힌트 4: gun 을 어디에 놓아야 앞면에서 축과 만나나</summary>

gun 을 (x0, 0, 0) 에 두면, beam 은 x 방향으로 sin α 씩 줄어듭니다. 축 방향으로 L 만큼 갔을 때 x = 0 이 되려면
x0 와 L 사이에 어떤 관계가 있어야 할까요? (기울어진 직각삼각형을 그려 보세요.)
</details>

답을 구했으면 `check_beam.py` 로 확인합니다 (순수 python, 1초).

```bash
python3 advanced/02_beam_pointing/check_beam.py --position <x0> 0 0 --direction <dx> <dy> <dz> --tower <n>
```

```
DRC 앞면 (barrel) 에 맞는 점: (0.0, 2805.0, 586.6) mm,  theta = 78.188 deg, phi = 90.000 deg
그 점이 속한 tower: eta 번호 10 (중심 theta = 78.1875 deg), phi 번호 36 (중심 phi = 90.0 deg)
tower 중심에서 떨어진 거리: 0.0 mm
beam 과 tower 축 사이의 각도: 1.000 deg
=> OK: tower 10 의 중심을 맞힌다.
```

- 같은 tower 에 맞더라도 중심에서 수십 mm 떨어지면 "다시 확인" 이 나옵니다. tower 앞면의 theta 방향 폭은 tower 0 에서 약 55 mm 입니다.
- 직선으로만 계산합니다. 실제로는 ECAL 과 solenoid 에서 shower 가 시작하고 vertex smearing (8 mm) 도 있습니다.
- 검산: tower 0, 20 을 넣으면 `sim/SteeringFile_o3_gun.py` 의 p0, p1 과 같아야 합니다.
- **bonus**: endcap tower m (40 ~ 74). θ 는 45° 에서 시작하고, 앞면이 z = 2805 mm 평면이라 L 의 식이 바뀝니다.

정답 (모든 barrel tower 와 endcap 몇 개): `advanced/solutions/02_beam_pointing/answers.md`

## 시뮬레이션 결과로 확인: `find_hit_tower.py`

03 에서 계산한 값으로 Sim 을 돌린 뒤, DRC hit 이 실제로 어느 tower 에 모였는지 봅니다. Sim, Digi 파일 둘 다 됩니다.

```bash
python3 advanced/02_beam_pointing/find_hit_tower.py $TUTORIAL_OUTPUT/<TAG>_Sim/<TAG>_sim_0.root
```

sungwon 샘플 (p0, tower 0) 의 예:

```bash
python3 advanced/02_beam_pointing/find_hit_tower.py --max-events 50 \
    $TUTORIAL_SAMPLES/o3_calibB_drc_eminus_40GeV_p0_noOpt_Sim/o3_calibB_drc_eminus_40GeV_p0_noOpt_sim_0.root
```

```
1차 입자 (평균)   : 위치 = (49.7, -0.3, 0.2) mm,  방향 = (-0.017452, 0.999800, 0.009816)
                   방향의 theta = 89.438 deg, phi = 91.000 deg
DRC hit 중심 (평균): theta = 89.432 deg, phi = 90.059 deg
가장 에너지가 큰 tower 가 받은 비율 (평균): 0.93
가장 에너지가 큰 tower (eta 번호, phi 번호) 와 그런 event 수:
  eta    0, phi   36 : 50 events
```

- `1차 입자` 는 `MCParticles` 에서 읽은 gun 입자입니다. 방향이 내가 넣은 값과 같아야 합니다.
  방향의 phi 가 91° 인 것은 x 쪽으로 1° 기울였기 때문입니다.
- DRC hit 중심의 theta 가 tower 중심 θ_n 과 거의 같고, 가장 에너지가 큰 tower 의 eta 번호가 n, phi 번호가 36 이면 성공입니다.
- tower 번호는 hit 의 cellID 에서 읽습니다 (readout `system:5,assembly:1,eta:-8,phi:9,...`).
