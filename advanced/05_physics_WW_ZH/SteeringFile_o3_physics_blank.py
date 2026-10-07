## =====================================================================================
## [advanced 05] physics event (HepMC 입력) steering file 빈칸 채우기 (noOpt)
##
## 01 의 gun steering 과 다른 곳만 빈칸이다 (sensitive detector, output plugin, optical physics
## 설정은 gun 과 같아서 채워 두었다). 확인:
##
##   ddsim --steeringFile SteeringFile_o3_physics.py --inputFiles x.hepmc --dumpSteeringFile > dump.txt
## =====================================================================================
import os

from DDSim.DD4hepSimulation import DD4hepSimulation
from g4units import MeV

SIM = DD4hepSimulation()

if "K4GEO_LOCAL" not in os.environ:
    raise RuntimeError("K4GEO_LOCAL 이 설정되지 않았다. 먼저 'source setup_env.sh' 를 실행하세요.")
COMPACT_DIR = os.path.join(os.environ["K4GEO_LOCAL"], "FCCee", "IDEA", "compact", "IDEA_o3_v01")

## ---- geometry: 전체 o3, 자기장 ON (2 T) ----
SIM.compactFile = [os.path.join(COMPACT_DIR, ____TODO_1____)]
SIM.numberOfEvents = 20
SIM.outputFile = "o3_physics_sim.root"
SIM.runType = "batch"
SIM.physicsList = "FTFP_BERT"
SIM.printLevel = 3

## ---- 입력: gun 대신 HepMC 파일 (파일 이름은 명령행 --inputFiles 로 준다) ----
SIM.enableGun = ____TODO_2____
SIM.inputFiles = ____TODO_3____
SIM.vertexOffset = [0.0, 0.0, 0.0, 0.0]
SIM.vertexSigma = ____TODO_4____

## ---- 아래는 gun steering 과 같다 ----
SIM.action.calo = "Geant4ScintillatorCalorimeterAction"
SIM.action.calorimeterSDTypes = ["calorimeter", "DRcaloSiPMSD"]
SIM.action.mapActions["SCEPCal_MainLayer"] = "SCEPCal_MainSDAction"
SIM.action.mapActions["SCEPCal_TimingLayer"] = "SCEPCal_TimingSDAction"
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

    opt = PhysicsList(kernel, "Geant4OpticalPhotonPhysics/OpticalGammaPhys")
    opt.addParticleConstructor("G4OpticalPhoton")
    opt.VerboseLevel = 1
    opt.enableUI()
    seq.adopt(opt)
    return None


SIM.physics.setupUserPhysics(setupOpticalPhysics)

SIM.random.enableEventSeed = False
SIM.random.seed = None
