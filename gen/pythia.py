# Pythia8 event generation (k4run). Pythia card, HepMC/ROOT 출력 파일, event 수는 명령행으로 준다:
#   k4run pythia.py -n 20 --Pythia8.PythiaInterface.pythiacard p8_ee_Zqq_eCM91.cmd \
#         --HepMCFileWriter.Filename out.hepmc --IOSvc.Output out.root \
#         --RndmGenSvc.Engine.Seeds 1
# 주의: Gaudi 의 --RndmGenSvc.Engine.Seeds 는 vertex smearing 의 seed 만 바꾼다. Pythia 자체의 seed 는
#       card 안의 "Random:seed" 이므로 job 마다 다르게 하려면 card 를 복사해서 이 줄을 바꿔야 한다
#       (condor/gen_sim/wrapper_gen.sh 가 그렇게 한다).
"""
Pythia8, integrated in the FCCSW framework.

Generates according to a pythia .cmd file and saves them in fcc edm format.

"""

import os
from GaudiKernel import SystemOfUnits as units
from Gaudi.Configuration import *

# RNG engine
from Configurables import HepRndm__Engine_CLHEP__RanluxEngine_ as RndmEngine
rndmEngine = RndmEngine('RndmGenSvc.Engine',
  SetSingleton = True,
  Seeds = [ 1234567 ] # default seed is 1234567
)

from Configurables import RndmGenSvc
rndmGenSvc = RndmGenSvc("RndmGenSvc",
  Engine = rndmEngine.name()
)

# Event service
from k4FWCore import IOSvc
from Configurables import EventDataSvc
io_svc = IOSvc("IOSvc")
io_svc.Output = "output.root"
io_svc.OutputLevel = INFO

from Configurables import GaussSmearVertex
smeartool = GaussSmearVertex()
smeartool.xVertexSigma =   0.5*units.mm
smeartool.yVertexSigma =   0.5*units.mm
smeartool.zVertexSigma =  40.0*units.mm
smeartool.tVertexSigma = 180.0*units.picosecond

from Configurables import PythiaInterface
pythia8gentool = PythiaInterface()
### Example of pythia configuration file to generate events
# take from $K4GEN if defined, locally if not
path_to_pythiafile = os.environ.get("K4GEN", "")
# pythiafilename = "Pythia_standard.cmd"
pythiafilename = "Pythia_standard.cmd"
pythiafile = os.path.join(path_to_pythiafile, pythiafilename)
# Example of pythia configuration file to read LH event file
#pythiafile="options/Pythia_LHEinput.cmd"
pythia8gentool.pythiacard = pythiafile
pythia8gentool.doEvtGenDecays = False
pythia8gentool.printPythiaStatistics = True
pythia8gentool.pythiaExtraSettings = [""]

from Configurables import GenAlg
pythia8gen = GenAlg("Pythia8")
pythia8gen.SignalProvider = pythia8gentool
pythia8gen.VertexSmearingTool = smeartool
pythia8gen.hepmc.Path = "hepmc"

from Configurables import HepMCFileWriter
writer = HepMCFileWriter()
writer.hepmc.Path="hepmc"
writer.Filename = "output.hepmc"

### Reads an HepMC::GenEvent from the data service and writes a collection of EDM Particles
from Configurables import HepMCToEDMConverter
hepmc_converter = HepMCToEDMConverter()
hepmc_converter.hepmc.Path="hepmc"
hepmc_converter.hepmcStatusList = [] # convert particles with all statuses
hepmc_converter.GenParticles.Path="GenParticles"

### Filters generated particles
# accept is a list of particle statuses that should be accepted
from Configurables import GenParticleFilter
genfilter = GenParticleFilter("StableParticles")
genfilter.accept = [1]
genfilter.GenParticles.Path = "GenParticles"
genfilter.GenParticlesFiltered.Path = "MCParticles"

io_svc.outputCommands = [
  "keep *"
]

from k4FWCore import ApplicationMgr
application_mgr = ApplicationMgr(
    TopAlg = [
        pythia8gen,
        writer
        #hepmc_converter,
        #genfilter
    ],
    EvtSel = 'NONE',
    EvtMax = 100,
    ExtSvc = [
        EventDataSvc("EventDataSvc"),
        rndmEngine,
        rndmGenSvc,
    ],
    StopOnSignal = True,
)

