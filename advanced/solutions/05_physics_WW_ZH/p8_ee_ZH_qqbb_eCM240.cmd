! [IDEA_o3 advanced] eCM = 240 GeV, e+e- -> ZH, Z -> qq, H -> bb (fully hadronic)
! Random:seed 는 job 마다 wrapper 가 card 사본에서 바꾼다.

! 1) main program
Random:setSeed = on
Random:seed = 1234567
Main:timesAllowErrors = 1
Stat:showProcessLevel = off
Stat:showErrors = off

! 2) 출력
Init:showChangedSettings = on
Init:showChangedParticleData = off
Next:numberCount = 100
Next:numberShowInfo = 1
Next:numberShowProcess = 1
Next:numberShowEvent = 1

! 3) beam: e- (11) 과 e+ (-11)
Beams:idA = 11
Beams:idB = -11
Beams:eCM = 240.

! 4) hard process: e+e- -> Z* -> ZH (Higgsstrahlung)
HiggsSM:ffbar2HZ = on

! 5) Z decay: quark 쌍으로만
23:onMode = off
23:onIfAny = 1 2 3 4 5

! 6) H decay: b bbar 만
25:onMode = off
25:onIfAny = 5
