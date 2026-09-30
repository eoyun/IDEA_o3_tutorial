! [IDEA_o3 tutorial] eCM = 91 GeV, Z/gamma* -> qq (u,d,s,c)
! Random:seed 는 job 마다 달라야 한다: condor/gen_sim/wrapper_gen.sh 가 이 card 를 복사해 seed 를
! (ProcId+1) 로 바꿔서 쓴다. 그대로 여러 번 돌리면 항상 같은 event 가 나온다.
! main03.cmnd.
! This file contains commands to be read in for a Pythia8 run.
! Lines not beginning with a letter or digit are comments.
! Names are case-insensitive  -  but spellings-sensitive!
! The settings here are illustrative, not always physics-motivated.
!
! Copy of p8_ee_qq.cmd with Beams:eCM changed from 125 -> 91 GeV (on the Z pole),
! for the o3 noOpt physics-sample campaign (see o3 calibration+physics plan).

! 1) Settings used in the main program.
Random:setSeed = on
Random:seed = 1234567
Main:timesAllowErrors = 1          ! how many aborts before run stops
Stat:showProcessLevel = off
Stat:showErrors = off

! 2) Settings related to output in init(), next() and stat().
Init:showChangedSettings = on      ! list changed settings
Init:showChangedParticleData = off ! list changed particle data
Next:numberCount = 100             ! print message every n events
Next:numberShowInfo = 1            ! print event information n times
Next:numberShowProcess = 1         ! print process record n times
Next:numberShowEvent = 1           ! print event record n times

! 3) Beam parameter settings. Values below agree with default ones.
Beams:idA = 11                   ! first beam, e = 2212, pbar = -2212
Beams:idB = -11                   ! second beam, e = 2212, pbar = -2212

! 4) Hard process : Z->qqbar at Ecm=91 GeV (Z pole)
Beams:eCM = 91.  ! CM energy of collision

WeakSingleBoson:ffbar2gmZ = on
23:onMode = off
23:onIfAny = 1 2 3 4
22:onMode = off
22:onIfAny = 1 2 3 4
! light quarks only (u,d,s,c) -- no b for clean jets
! Use "1 2 3 4 5" to include b quarks
