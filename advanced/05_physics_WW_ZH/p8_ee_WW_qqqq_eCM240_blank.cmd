! [IDEA_o3 advanced] eCM = 240 GeV, e+e- -> W+W- -> qqqq (fully hadronic). 빈칸을 채운다.
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
Beams:eCM = ____TODO_1____

! 4) hard process: e+e- -> W+W-
____TODO_2____

! 5) W decay: quark 쌍으로만
____TODO_3____
____TODO_4____
