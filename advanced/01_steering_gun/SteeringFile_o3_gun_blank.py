## =====================================================================================
## [advanced 01] particle gun steering file 빈칸 채우기 (noOpt)
##
## ____TODO_n____ 을 모두 채운다. 각 빈칸의 의미와 힌트는 같은 디렉터리의 README.md 에 있다.
## 다 채웠으면 시뮬레이션 없이 최종 설정만 출력해서 확인한다 (몇 초, 로컬에서 해도 됨):
##
##   ddsim --steeringFile SteeringFile_o3_gun.py --dumpSteeringFile > dump.txt
##
## 빈칸이 남아 있으면 "NameError: name ... is not defined" 로 어느 빈칸인지 알려 준다.
## =====================================================================================
import os

from DDSim.DD4hepSimulation import DD4hepSimulation
from g4units import GeV, MeV, mm

SIM = DD4hepSimulation()

if "K4GEO_LOCAL" not in os.environ:
    raise RuntimeError("K4GEO_LOCAL 이 설정되지 않았다. 먼저 'source setup_env.sh' 를 실행하세요.")
COMPACT_DIR = os.path.join(os.environ["K4GEO_LOCAL"], "FCCee", "IDEA", "compact", "IDEA_o3_v01")

## ---- geometry: 전체 o3, 자기장 OFF ----
SIM.compactFile = [os.path.join(COMPACT_DIR, ____TODO_1____)]
SIM.numberOfEvents = 10
SIM.outputFile = "o3_gun_sim.root"
SIM.runType = "batch"
SIM.physicsList = "FTFP_BERT"
SIM.printLevel = 3

## ---- particle gun: e- 40 GeV, barrel tower 0 (README 의 p0) ----
SIM.enableGun = ____TODO_2____
SIM.gun.particle = ____TODO_3____
SIM.gun.energy = ____TODO_4____
SIM.gun.position = ____TODO_5____
SIM.gun.direction = ____TODO_6____
SIM.gun.multiplicity = 1
SIM.gun.isotrop = False
SIM.gun.distribution = None
SIM.vertexOffset = [0.0, 0.0, 0.0, 0.0]
SIM.vertexSigma = ____TODO_7____

## ---- sensitive detector actions ----
SIM.action.calo = "Geant4ScintillatorCalorimeterAction"
SIM.action.calorimeterSDTypes = ____TODO_8____
SIM.action.mapActions["SCEPCal_MainLayer"] = "SCEPCal_MainSDAction"
SIM.action.mapActions["SCEPCal_TimingLayer"] = "SCEPCal_TimingSDAction"
SIM.action.mapActions["DRcalo"] = ("DRCaloSDAction", {"skipScint": ____TODO_9____})
SIM.geometry.regexSensitiveDetector["DRcalo"] = {"Match": ____TODO_10____, "OutputLevel": 3}

## ---- filters ----
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
## ddsim 은 이 파일을 exec(globals, locals 분리) 로 읽어서, 함수 안에서는 이 파일의 다른 변수가 보이지 않는다.
## 함수 안에서 쓰는 값은 함수 안에 직접 쓴다.


def Geant4Output2EDM4hep_DRC_plugin(dd4hepSimulation):
    from DDG4 import EventAction, Kernel

    evt_root = EventAction(Kernel(), ____TODO_11____ + "/" + dd4hepSimulation.outputFile, True)
    evt_root.Control = True
    evt_root.Output = dd4hepSimulation.outputFile
    evt_root.enableUI()
    Kernel().eventAction().add(evt_root)
    return None


SIM.outputConfig.userOutputPlugin = Geant4Output2EDM4hep_DRC_plugin

## ---- optical physics (noOpt: Cherenkov 만) ----


def setupOpticalPhysics(kernel):
    from DDG4 import PhysicsList

    seq = kernel.physicsList()

    cerenkov = PhysicsList(kernel, ____TODO_12____ + "/CerenkovPhys")
    cerenkov.TrackSecondariesFirst = True
    cerenkov.VerboseLevel = 1
    cerenkov.enableUI()
    seq.adopt(cerenkov)

    opt = PhysicsList(kernel, "Geant4OpticalPhotonPhysics/OpticalGammaPhys")
    opt.addParticleConstructor("G4OpticalPhoton")
    opt.VerboseLevel = 1
    opt.enableUI()
    seq.adopt(opt)
    return None


SIM.physics.setupUserPhysics(setupOpticalPhysics)

## ---- random: seed 는 명령행 --random.enableEventSeed --random.seed <N> 으로 준다 ----
SIM.random.enableEventSeed = False
SIM.random.seed = None
