## =====================================================================================
## IDEA_o3 physics-event steering file (noOpt simulation, HepMC input)
##
## Pythia8 로 만든 HepMC 이벤트 (Z -> ee, Z -> qq, eCM = 91 GeV) 를 입력으로 받아 시뮬레이션한다.
##
##   ddsim --steeringFile $IDEA_TUTORIAL_ROOT/sim/SteeringFile_o3_physics.py \
##         --inputFiles my_gen.hepmc --numberOfEvents 20 \
##         --outputFile test_physics_sim.root --random.enableEventSeed --random.seed 1
##
## gun 이 아니라 physics event 를 쓴다는 점 (enableGun = False, 입력 파일은 명령행 --inputFiles),
## 그리고 실제 자기장이 켜진 (2 T) 전체 geometry 를 쓴다는 점이 SteeringFile_o3_gun.py 와 다르다.
## Vertex smearing 은 Pythia 쪽 (gen/pythia.py 의 GaussSmearVertex) 에서 이미 들어가므로 여기서는 0.
##
## noOpt 모드 설명 및 full optical 로 바꾸는 방법은 SteeringFile_o3_gun.py 와 같다
## ([FULL-OPTICAL n/4] 표시 4곳).
## =====================================================================================
import os

from DDSim.DD4hepSimulation import DD4hepSimulation
from g4units import MeV, mm

SIM = DD4hepSimulation()

## ---- USER SETTINGS ----
NUMBER_OF_EVENTS = 20
OUTPUT_FILE = "o3_physics_sim.root"

## 자기장 ON: IDEA_o3_v01.xml (Solenoid 2 T).
## 참고: 이 sungwon 샘플 (o3_{ee,qqbar}_eCM91_seedfix_noOpt_*) 도 이 XML 로 만들었다.
COMPACT_XML = "IDEA_o3_v01.xml"

## =====================================================================================

if "K4GEO_LOCAL" not in os.environ:
    raise RuntimeError("K4GEO_LOCAL 이 설정되지 않았다. 먼저 'source setup_env.sh' 를 실행하세요.")
COMPACT_DIR = os.path.join(os.environ["K4GEO_LOCAL"], "FCCee", "IDEA", "compact", "IDEA_o3_v01")

SIM.compactFile = [os.path.join(COMPACT_DIR, COMPACT_XML)]
SIM.numberOfEvents = NUMBER_OF_EVENTS
SIM.outputFile = OUTPUT_FILE
SIM.runType = "batch"
SIM.physicsList = "FTFP_BERT"
SIM.printLevel = 3

## ---- 입력: HepMC 파일은 명령행 --inputFiles 로 준다. gun 은 끈다. ----
SIM.enableGun = False
SIM.inputFiles = []
SIM.vertexOffset = [0.0, 0.0, 0.0, 0.0]
SIM.vertexSigma = [0.0, 0.0, 0.0, 0.0]

## ---- sensitive detector actions (SteeringFile_o3_gun.py 와 동일) ----
SIM.action.calo = "Geant4ScintillatorCalorimeterAction"
SIM.action.calorimeterSDTypes = ["calorimeter", "DRcaloSiPMSD"]
SIM.action.mapActions["SCEPCal_MainLayer"] = "SCEPCal_MainSDAction"
SIM.action.mapActions["SCEPCal_TimingLayer"] = "SCEPCal_TimingSDAction"

## [FULL-OPTICAL 1/4] full optical 로 바꿀 때는 아래 두 줄 (noOpt) 을 지우고 skipScint=false 로 교체
SIM.action.mapActions["DRcalo"] = ("DRCaloSDAction", {"skipScint": "true"})
SIM.geometry.regexSensitiveDetector["DRcalo"] = {"Match": ["(core|clad)"], "OutputLevel": 3}

SIM.filter.calo = ""
SIM.filter.mapDetFilter["SCEPCal_MainLayer"] = ""
SIM.filter.mapDetFilter["SCEPCal_TimingLayer"] = ""
SIM.filter.tracker = "edep1kev"

SIM.action.tracker = (
    "Geant4TrackerWeightedAction",
    {"HitPositionCombination": 2, "CollectSingleDeposits": False},
)
SIM.action.trackerSDTypes = ["tracker"]

SIM.part.userParticleHandler = "Geant4TCUserParticleHandler"
SIM.part.minimalKineticEnergy = 1.0 * MeV
SIM.part.saveProcesses = ["Decay"]
SIM.part.keepAllParticles = False
SIM.part.enableDetailedHitsAndParticleInfo = False


def Geant4Output2EDM4hep_DRC_plugin(dd4hepSimulation):
    from DDG4 import EventAction, Kernel

    evt_root = EventAction(Kernel(), "Geant4Output2EDM4hep_DRC/" + dd4hepSimulation.outputFile, True)
    evt_root.Control = True
    evt_root.Output = dd4hepSimulation.outputFile
    evt_root.enableUI()
    Kernel().eventAction().add(evt_root)
    return None


SIM.outputConfig.userOutputPlugin = Geant4Output2EDM4hep_DRC_plugin


def setupOpticalPhysics(kernel):
    from DDG4 import PhysicsList

    seq = kernel.physicsList()

    cerenkov = PhysicsList(kernel, "Geant4CerenkovPhysics/CerenkovPhys")
    cerenkov.TrackSecondariesFirst = True
    cerenkov.VerboseLevel = 1
    cerenkov.enableUI()
    seq.adopt(cerenkov)

    ## [FULL-OPTICAL 3/4] full optical 로 바꿀 때 아래 6줄의 주석을 해제
    # scint = PhysicsList(kernel, "Geant4ScintillationPhysics/ScintillationPhys")
    # scint.VerboseLevel = 1
    # scint.TrackSecondariesFirst = True
    # scint.BoundaryInvokeSD = True
    # scint.enableUI()
    # seq.adopt(scint)

    opt = PhysicsList(kernel, "Geant4OpticalPhotonPhysics/OpticalGammaPhys")
    opt.addParticleConstructor("G4OpticalPhoton")
    opt.VerboseLevel = 1
    ## [FULL-OPTICAL 4/4] full optical 에서는 아래 줄의 주석을 해제
    # opt.BoundaryInvokeSD = True
    opt.enableUI()
    seq.adopt(opt)
    return None


SIM.physics.setupUserPhysics(setupOpticalPhysics)

## [FULL-OPTICAL 2/4] compactFile 교체 (SiPM wafer 가 sensitive 인 XML). 이 파일은 자기장 ON 이므로
##                   physics 샘플에는 그대로 쓸 수 있다.
# SIM.compactFile = [os.path.join(COMPACT_DIR, "IDEA_o3_v01_opticalSiPM.xml")]
## 주의: full optical 출력 (Sim) 의 Digi 는 현재 이 tutorial 에서 지원하지 않는다 (README 참고).

SIM.random.enableEventSeed = False
SIM.random.seed = None
