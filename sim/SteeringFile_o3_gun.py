## =====================================================================================
## IDEA_o3 single-particle gun steering file (noOpt simulation)
##
##   ddsim --steeringFile $IDEA_TUTORIAL_ROOT/sim/SteeringFile_o3_gun.py \
##         --numberOfEvents 10 --outputFile test_sim.root --random.seed 1
##
## 이 파일 하나로 다음 샘플을 모두 만들 수 있다. 위쪽 "USER SETTINGS" 블록만 고치면 된다.
##   - ECAL EM calibration / EM resolution : e-,  GEOMETRY="full"    (ECAL + DRC)
##   - DRC  EM calibration                 : e-,  GEOMETRY="DRConly" (ECAL, solenoid 없음)
##   - hadron calibration (chi)/resolution : pi-, GEOMETRY="full"
##
## 시뮬레이션 모드: "noOpt" (no optical). DRC fiber 의 scintillation photon 은 만들지 않고
## fiber 안의 energy deposit 을 합산 (S channel), Cherenkov photon 은 SD action 안의 shortcut
## 으로 fiber 끝까지 전달한다 (C channel). 가장 빠른 모드이고, 이 tutorial 은 noOpt 만 쓴다.
## full optical simulation 으로 바꾸는 방법은 파일 아래쪽 "FULL OPTICAL SIMULATION" 절 참고.
##
## 참고: 여기 적힌 값은 sungwon 이 미리 만들어 둔 샘플 (condor_output/o3_res_*, o3_calibB_*)
## 을 만들 때 쓴 설정과 동일하다. (ddsim 명령행 옵션은 steering file 값을 덮어쓴다.)
## =====================================================================================
import os

from DDSim.DD4hepSimulation import DD4hepSimulation
from g4units import GeV, MeV, mm

SIM = DD4hepSimulation()

## =====================================================================================
## USER SETTINGS  (여기만 수정)
## =====================================================================================

## 1) Geometry
##   "full"    : IDEA_o3_v01_noField.xml
##               전체 IDEA o3 (tracker + SCEPCal crystal ECAL + solenoid + fiber DRC + muon),
##               자기장 OFF. ECAL 과 DRC 를 모두 쓰는 샘플 (ECAL calibration, resolution).
##   "DRConly" : IDEA_o3_v01_DRConly_noField.xml
##               SCEPCal 과 solenoid 를 뺀 geometry. beam 이 ECAL/solenoid 에서 에너지를 잃지
##               않고 DRC 에 바로 도달한다 -> DRC EM calibration 용.
GEOMETRY = "full"

## 2) Particle & energy
##   EM calibration/resolution : "e-",  hadron : "pi-"
##   energy scan (resolution)  : 10, 20, 40, 60, 80 GeV 를 각각 따로 만든다.
##   (calibration 은 40 GeV)
PARTICLE = "e-"
ENERGY = 40 * GeV

## 3) Beam 위치 (p0 ~ p3): calibration 용 4개의 입사 위치/각도
##   각 점은 DRC 의 특정 tower 의 중심을 조준한다. gun 을 tower 의 pointing axis 에서 x 방향으로
##   약 50 mm 떨어뜨려 놓고 같은 tower 중심을 향해 쏘기 때문에 beam 이 약 1 deg 기울어져
##   (direction 의 x 성분 -0.017452 = -sin 1deg) 입사한다. 즉 fiber 방향과 정확히 평행하지 않다.
##     point  theta[deg]  조준하는 곳                          position [mm]      direction (x y z)
##     p0     89.44       barrel 첫 tower (equator, tower 0)   48.9638 0 0        -0.017452 0.999800 0.009816
##     p1     66.94       barrel 중간 (tower 20)               53.2145 0 0        -0.017452 0.919938 0.391675
##     p2     44.44       endcap 첫 tower (barrel/endcap 경계)  68.5720 0 0        -0.017452 0.700024 0.713906
##     p3     25.31       endcap 중간                          54.1616 0 0        -0.017452 0.427490 0.903852
POINT = "p0"

## 4) Vertex smearing: x y z t  (모든 sungwon 샘플에서 8 mm)
VERTEX_SIGMA = [8 * mm, 8 * mm, 8 * mm, 0]

## 5) 기본 이벤트 수, 출력 파일 (명령행 --numberOfEvents, --outputFile 이 우선)
NUMBER_OF_EVENTS = 10
OUTPUT_FILE = "o3_gun_sim.root"

## =====================================================================================
## 아래는 보통 수정할 필요 없음
## =====================================================================================

BEAM_POINTS = {
    "p0": {"position": (48.9638 * mm, 0.0 * mm, 0.0 * mm), "direction": (-0.017452, 0.999800, 0.009816)},
    "p1": {"position": (53.2145 * mm, 0.0 * mm, 0.0 * mm), "direction": (-0.017452, 0.919938, 0.391675)},
    "p2": {"position": (68.5720 * mm, 0.0 * mm, 0.0 * mm), "direction": (-0.017452, 0.700024, 0.713906)},
    "p3": {"position": (54.1616 * mm, 0.0 * mm, 0.0 * mm), "direction": (-0.017452, 0.427490, 0.903852)},
}

COMPACT_XML = {
    "full": "IDEA_o3_v01_noField.xml",
    "DRConly": "IDEA_o3_v01_DRConly_noField.xml",
}

if "K4GEO_LOCAL" not in os.environ:
    raise RuntimeError("K4GEO_LOCAL 이 설정되지 않았다. 먼저 'source setup_env.sh' 를 실행하세요.")
COMPACT_DIR = os.path.join(os.environ["K4GEO_LOCAL"], "FCCee", "IDEA", "compact", "IDEA_o3_v01")

SIM.compactFile = [os.path.join(COMPACT_DIR, COMPACT_XML[GEOMETRY])]
SIM.numberOfEvents = NUMBER_OF_EVENTS
SIM.outputFile = OUTPUT_FILE
SIM.runType = "batch"
SIM.physicsList = "FTFP_BERT"
SIM.printLevel = 3

## ---- particle gun ----
SIM.enableGun = True
SIM.gun.particle = PARTICLE
SIM.gun.energy = ENERGY
SIM.gun.position = BEAM_POINTS[POINT]["position"]
SIM.gun.direction = BEAM_POINTS[POINT]["direction"]
SIM.gun.multiplicity = 1
SIM.gun.isotrop = False
SIM.gun.distribution = None
SIM.vertexOffset = [0.0, 0.0, 0.0, 0.0]
SIM.vertexSigma = VERTEX_SIGMA

## ---- sensitive detector actions ----
## 기본 calorimeter action. "DRcaloSiPMSD" 는 fiber DRC (DRcalo) 를 calorimeter SD 로 취급하게 한다.
SIM.action.calo = "Geant4ScintillatorCalorimeterAction"
SIM.action.calorimeterSDTypes = ["calorimeter", "DRcaloSiPMSD"]

## SCEPCal (crystal ECAL) 전용 SD action. Main layer 는 crystal 마다 S/C photo-electron 수를 센다.
SIM.action.mapActions["SCEPCal_MainLayer"] = "SCEPCal_MainSDAction"
SIM.action.mapActions["SCEPCal_TimingLayer"] = "SCEPCal_TimingSDAction"

## DRC fiber SD action.
##   skipScint=true : scintillation photon 을 만들지 않고 fiber 의 energy deposit 을 합산 (noOpt).
##                    dd4hep 의 Birks law 가 적용되고, 중성 입자/길이 0 step 은 S channel 에서 제외된다.
##   regexSensitiveDetector : fiber core/clad 가 sensitive volume.
## [FULL-OPTICAL 1/4] full optical 로 바꿀 때는 아래 두 줄 (noOpt) 을 지우고, 파일 아래쪽의
##                   해당 블록을 켠다.
SIM.action.mapActions["DRcalo"] = ("DRCaloSDAction", {"skipScint": "true"})
SIM.geometry.regexSensitiveDetector["DRcalo"] = {"Match": ["(core|clad)"], "OutputLevel": 3}

## ---- filters ----
## SCEPCal 은 hit 을 SD action 안에서 직접 처리하므로 edep filter 를 쓰지 않는다.
SIM.filter.calo = ""
SIM.filter.mapDetFilter["SCEPCal_MainLayer"] = ""
SIM.filter.mapDetFilter["SCEPCal_TimingLayer"] = ""
SIM.filter.tracker = "edep1kev"

## ---- tracker ----
SIM.action.tracker = (
    "Geant4TrackerWeightedAction",
    {"HitPositionCombination": 2, "CollectSingleDeposits": False},
)
SIM.action.trackerSDTypes = ["tracker"]

## ---- MC truth (MCParticles) ----
SIM.part.userParticleHandler = "Geant4TCUserParticleHandler"
SIM.part.minimalKineticEnergy = 1.0 * MeV
SIM.part.saveProcesses = ["Decay"]
SIM.part.keepAllParticles = False
SIM.part.enableDetailedHitsAndParticleInfo = False

## ---- output: DRC 용 EDM4hep output plugin ----
## 일반 edm4hep output 대신 Geant4Output2EDM4hep_DRC 를 써야 DRC 의 hit collection
## (DRcaloSiPMreadout_scint, DRcaloSiPMreadoutSimHit 등) 이 저장된다.
def Geant4Output2EDM4hep_DRC_plugin(dd4hepSimulation):
    from DDG4 import EventAction, Kernel

    evt_root = EventAction(Kernel(), "Geant4Output2EDM4hep_DRC/" + dd4hepSimulation.outputFile, True)
    evt_root.Control = True
    evt_root.Output = dd4hepSimulation.outputFile
    evt_root.enableUI()
    Kernel().eventAction().add(evt_root)
    return None


SIM.outputConfig.userOutputPlugin = Geant4Output2EDM4hep_DRC_plugin


## ---- optical physics ----
## noOpt : Cherenkov photon 만 생성 (Scintillation physics 없음).
def setupOpticalPhysics(kernel):
    from DDG4 import PhysicsList

    seq = kernel.physicsList()

    cerenkov = PhysicsList(kernel, "Geant4CerenkovPhysics/CerenkovPhys")
    cerenkov.TrackSecondariesFirst = True
    cerenkov.VerboseLevel = 1
    cerenkov.enableUI()
    seq.adopt(cerenkov)

    ## [FULL-OPTICAL 3/4] full optical 로 바꿀 때 아래 6줄의 주석을 해제 (scintillation photon 생성)
    # scint = PhysicsList(kernel, "Geant4ScintillationPhysics/ScintillationPhys")
    # scint.VerboseLevel = 1
    # scint.TrackSecondariesFirst = True
    # scint.BoundaryInvokeSD = True
    # scint.enableUI()
    # seq.adopt(scint)

    opt = PhysicsList(kernel, "Geant4OpticalPhotonPhysics/OpticalGammaPhys")
    opt.addParticleConstructor("G4OpticalPhoton")
    opt.VerboseLevel = 1
    ## [FULL-OPTICAL 4/4] full optical 에서는 SiPM wafer 가 SD 이므로 아래 줄의 주석을 해제
    # opt.BoundaryInvokeSD = True
    opt.enableUI()
    seq.adopt(opt)
    return None


SIM.physics.setupUserPhysics(setupOpticalPhysics)

## =====================================================================================
## FULL OPTICAL SIMULATION (기본 OFF, 이 tutorial 에서는 사용하지 않음)
##
## 모든 scintillation/Cherenkov photon 을 Geant4 가 SiPM 까지 직접 추적한다 (기준이 되는 모드,
## 가장 느림). 켜려면 파일 안의 [FULL-OPTICAL n/4] 표시 4곳을 수정:
##
##  [1/4] 위쪽 DRcalo SD 설정 (noOpt 2줄) 을 주석 처리하고 아래 두 줄로 교체
##            SIM.action.mapActions["DRcalo"] = ("DRCaloSDAction", {"skipScint": "false"})
##        (regexSensitiveDetector 는 설정하지 않는다: SiPM wafer 가 SD 이고 fiber 는 SD 가 아니어야 함)
##  [2/4] compactFile 을 SiPM wafer 가 sensitive 인 XML 로 교체 (이 파일 안 아래쪽 줄을 켠다)
##  [3/4] setupOpticalPhysics 의 Scintillation physics 블록 주석 해제
##  [4/4] setupOpticalPhysics 의 opt.BoundaryInvokeSD = True 주석 해제
##
## 주의 1) IDEA_o3_v01_opticalSiPM.xml 은 자기장 ON 인 전체 o3 geometry 이다. calibration 처럼
##         자기장 OFF 가 필요하면 IDEA_o3_v01_noField.xml 을 복사해 DRC include 를
##         FiberDualReadoutCalo_o1_v01_opticalSiPM.xml 로 바꾼 XML 을 만들어 쓴다.
## 주의 2) full optical 출력 (Sim) 의 Digi 는 현재 이 tutorial 에서 지원하지 않는다.
##         (README 의 "fullSim Digi 미지원" 절 참고)
## =====================================================================================
## [FULL-OPTICAL 2/4]
# SIM.compactFile = [os.path.join(COMPACT_DIR, "IDEA_o3_v01_opticalSiPM.xml")]

## ---- random ----
## seed 는 명령행으로 준다:  --random.enableEventSeed --random.seed <N>
## enableEventSeed: event 번호로 seed 를 다시 계산 -> 같은 seed 면 항상 같은 결과 (재현 가능)
SIM.random.enableEventSeed = False
SIM.random.seed = None
