## =====================================================================================
## [advanced 01] particle gun steering file (정답) (noOpt)
##
## 빈칸 각각의 설명은 advanced/01_steering_gun/README.md 에 있다.
## 시뮬레이션 없이 최종 설정만 출력해서 확인한다 (몇 초, 로컬에서 해도 됨):
##
##   ddsim --steeringFile SteeringFile_o3_gun.py --dumpSteeringFile > dump.txt
## =====================================================================================
import os

from DDSim.DD4hepSimulation import DD4hepSimulation
from g4units import GeV, MeV, mm

SIM = DD4hepSimulation()

if "K4GEO_LOCAL" not in os.environ:
    raise RuntimeError("K4GEO_LOCAL 이 설정되지 않았다. 먼저 'source setup_env.sh' 를 실행하세요.")
COMPACT_DIR = os.path.join(os.environ["K4GEO_LOCAL"], "FCCee", "IDEA", "compact", "IDEA_o3_v01")

## ---- geometry: 전체 o3, 자기장 OFF ----
SIM.compactFile = [os.path.join(COMPACT_DIR, "IDEA_o3_v01_noField.xml")]
SIM.numberOfEvents = 10
SIM.outputFile = "o3_gun_sim.root"
SIM.runType = "batch"
SIM.physicsList = "FTFP_BERT"
SIM.printLevel = 3

## ---- particle gun: e- 40 GeV, barrel tower 0 (README 의 p0) ----
SIM.enableGun = True
SIM.gun.particle = "e-"
SIM.gun.energy = 40 * GeV
SIM.gun.position = (48.9638 * mm, 0.0 * mm, 0.0 * mm)
SIM.gun.direction = (-0.017452, 0.999800, 0.009816)
SIM.gun.multiplicity = 1
SIM.gun.isotrop = False
SIM.gun.distribution = None
SIM.vertexOffset = [0.0, 0.0, 0.0, 0.0]
SIM.vertexSigma = [8 * mm, 8 * mm, 8 * mm, 0]

## ---- sensitive detector actions ----
SIM.action.calo = "Geant4ScintillatorCalorimeterAction"
SIM.action.calorimeterSDTypes = ["calorimeter", "DRcaloSiPMSD"]
SIM.action.mapActions["SCEPCal_MainLayer"] = "SCEPCal_MainSDAction"
SIM.action.mapActions["SCEPCal_TimingLayer"] = "SCEPCal_TimingSDAction"
SIM.action.mapActions["DRcalo"] = ("DRCaloSDAction", {"skipScint": "true"})
SIM.geometry.regexSensitiveDetector["DRcalo"] = {"Match": ["(core|clad)"], "OutputLevel": 3}

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

    evt_root = EventAction(Kernel(), "Geant4Output2EDM4hep_DRC" + "/" + dd4hepSimulation.outputFile, True)
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

    cerenkov = PhysicsList(kernel, "Geant4CerenkovPhysics" + "/CerenkovPhys")
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
