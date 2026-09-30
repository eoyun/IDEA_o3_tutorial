## =====================================================================================
## IDEA_o3 digitization + reconstruction (noOpt Sim 출력용)
##
##   k4run $IDEA_TUTORIAL_ROOT/digi/run_digi_reco.py \
##         --IOSvc.Input  test_sim.root  --IOSvc.Output test_digi.root \
##         --RootHistoSink.FileName test_trackhits.root
##
## 환경변수 (setup_env.sh 를 source 한 뒤에 설정):
##   DIGI_COMPACT_XML          (필수) Sim 에 쓴 compact XML 과 같은 것. $K4GEO_LOCAL 기준 상대경로.
##        gun, full geometry, noField : FCCee/IDEA/compact/IDEA_o3_v01/IDEA_o3_v01_noField.xml
##        gun, DRC only,      noField : FCCee/IDEA/compact/IDEA_o3_v01/IDEA_o3_v01_DRConly_noField.xml
##        physics (Z->ee, Z->qq)      : FCCee/IDEA/compact/IDEA_o3_v01/IDEA_o3_v01.xml
##   DIGI_SKIP_HELIX_TRACKING  자기장이 0 인 geometry (noField) 는 반드시 1 로 설정.
##        (TracksFromGenParticles 가 "Helix, invalid parameter: bField 0" 로 죽는다. calorimeter
##         분석에는 필요 없는 diagnostic 이라 건너뛴다.)
##
## 이 script 가 하는 일 (calorimeter 관점):
##   DRC S channel : SimulateSiPMwithEdep          DRcaloSiPMreadout_scint  -> DRcaloSiPMreadoutDigiHit_scint
##   DRC C channel : SimulateSiPMwithOpticalPhoton DRcaloSiPMreadoutSimHit  -> DRcaloSiPMreadoutDigiHit
##   SCEPCal (crystal ECAL) 은 digitizer 가 없다: crystal S/C 는 Sim 의 SCEPCal_MainScounts /
##   SCEPCal_MainCcounts (photo-electron 수) 를 그대로 쓴다 (Digi 출력 파일에도 그대로 복사되어 있음).
##   scaleADC = 1.0 으로 고정: 이 tutorial 의 calibration constant 는 이 값을 전제로 한다.
##
## !! fullSim (full optical Sim) 출력의 Digi 는 현재 지원하지 않는다 !!
##   full optical Sim 의 Digi 에는 별도로 받은 k4RecCalorimeter 와 작은 수정이 필요하다 (방법은 따로
##   안내). README 의 "fullSim Digi 미지원" 절 참고. 이 script 를 fullSim 출력에 쓰면 안 된다.
## =====================================================================================
import os

from Gaudi.Configuration import *

# Loading the input SIM file, defining output file
# (IOSvc.Input / IOSvc.Output are overridden from the command line by the condor wrapper)
from k4FWCore import IOSvc
from Configurables import EventDataSvc
io_svc = IOSvc("IOSvc")
io_svc.Input = "IDEA_sim.root"
io_svc.Output = "IDEA_sim_digi_reco.root"


################## Simulation setup
# Detector geometry
#
# Shared across all (geometry x simulation-mode x particle) condor combinations: which
# compact file to load is *not* hardcoded here, it must match whatever compact file was
# used for the Sim step that produced the input file (e.g. IDEA_o1_v03.xml for o1 no-opt,
# IDEA_o3_v01_opticalSiPM.xml for o3 fast-sim, etc). Set by the condor wrapper script via
# the DIGI_COMPACT_XML environment variable (path relative to $K4GEO).
from Configurables import GeoSvc
geoservice = GeoSvc("GeoSvc")
path_to_detector = os.environ["K4GEO_LOCAL"]  # setup_env.sh 가 설정 (로컬 k4geo 소스 디렉터리)
compact_xml = os.environ["DIGI_COMPACT_XML"]  # no silent fallback: must be set explicitly
print(path_to_detector, compact_xml)
detectors_to_use=[
                    compact_xml
                  ]
# prefix all xmls with path_to_detector
geoservice.detectors = [os.path.join(path_to_detector, _det) for _det in detectors_to_use]
geoservice.OutputLevel = INFO

############### Vertex Digitizer
from Configurables import DDPlanarDigi
import math
innerVertexResolution_x = 0.003 # [mm], assume 3 µm resolution for ARCADIA sensor
innerVertexResolution_y = 0.003 # [mm], assume 3 µm resolution for ARCADIA sensor
innerVertexResolution_t = 1000 # [ns]
outerVertexResolution_x = 0.050/math.sqrt(12) # [mm], assume ATLASPix3 sensor with 50 µm pitch
outerVertexResolution_y = 0.150/math.sqrt(12) # [mm], assume ATLASPix3 sensor with 150 µm pitch
outerVertexResolution_t = 1000 # [ns]

# CellIDBits=32 (2026-09-23): DDPlanarDigi (k4Reco) looks up surfaces via
# `surfaceMap->find(hit.getCellID() & mask)`, where `mask` comes from the CellIDBits
# property (default 64 = no masking at all). Surfaces are registered at the 32-bit
# system/side/layer/module/sensor hierarchy level, but IDEA_o1_v04's vertex/silicon-
# wrapper readouts (shared by o2 and o3 -- see VertexComplete_o1_v04.xml,
# SiliconWrapper_o1_v02.xml) add 48 more bits of x/y grid segmentation on top
# ("${GlobalTrackerReadoutID},x:32:-16,y:-16" = 64 bits total). Without masking those
# off, every lookup misses and DDPlanarDigi throws "no surface found for cellID" --
# this silently killed every o3 (and would-be o2) Digi job, producing an empty-shell
# output file despite the job's own exit code looking fine up to that point. o1_v03's
# vertex readout has no x/y segmentation at all (fits in 32 bits already), which is
# why this was never noticed there. Confirmed against the working reference
# ALLEGRO_o2_v01/run_digi_reco.py, which sets CellIDBits=32 on the equivalent 4
# instances for the exact same shared geometry. See DIGI_PIPELINE_NOTES.md section 3.
vtxb_digitizer = DDPlanarDigi("VTXBdigitizer")
vtxb_digitizer.SubDetectorName = "Vertex"
vtxb_digitizer.IsStrip = False
vtxb_digitizer.ResolutionU = [innerVertexResolution_x, innerVertexResolution_x, innerVertexResolution_x, outerVertexResolution_x, outerVertexResolution_x]
vtxb_digitizer.ResolutionV = [innerVertexResolution_y, innerVertexResolution_y, innerVertexResolution_y, outerVertexResolution_y, outerVertexResolution_y]
vtxb_digitizer.ResolutionT = [innerVertexResolution_t, innerVertexResolution_t, innerVertexResolution_t, outerVertexResolution_t, outerVertexResolution_t]
vtxb_digitizer.SimTrackHitCollectionName = ["VertexBarrelCollection"]
vtxb_digitizer.SimTrkHitRelCollection = ["VTXBSimDigiLinks"]
vtxb_digitizer.TrackerHitCollectionName = ["VTXBDigis"]
vtxb_digitizer.ForceHitsOntoSurface = True
vtxb_digitizer.CellIDBits = 32

vtxd_digitizer = DDPlanarDigi("VTXDdigitizer")
vtxd_digitizer.SubDetectorName = "Vertex"
vtxd_digitizer.IsStrip = False
vtxd_digitizer.ResolutionU = [outerVertexResolution_x, outerVertexResolution_x, outerVertexResolution_x]
vtxd_digitizer.ResolutionV = [outerVertexResolution_y, outerVertexResolution_y, outerVertexResolution_y]
vtxd_digitizer.ResolutionT = [outerVertexResolution_t, outerVertexResolution_t, outerVertexResolution_t]
vtxd_digitizer.SimTrackHitCollectionName = ["VertexEndcapCollection"]
vtxd_digitizer.SimTrkHitRelCollection = ["VTXDSimDigiLinks"]
vtxd_digitizer.TrackerHitCollectionName = ["VTXDDigis"]
vtxd_digitizer.ForceHitsOntoSurface = True
vtxd_digitizer.CellIDBits = 32

############### Wrapper Digitizer
siWrapperResolution_x   = 0.050/math.sqrt(12) # [mm]
siWrapperResolution_y   = 1.0/math.sqrt(12) # [mm]
siWrapperResolution_t   = 0.040 # [ns], assume 40 ps timing resolution for a single layer -> Should lead to <30 ps resolution when >1 hit

siwrb_digitizer = DDPlanarDigi("SiWrBdigitizer")
siwrb_digitizer.SubDetectorName = "SiWrB"
siwrb_digitizer.IsStrip = False
siwrb_digitizer.ResolutionU = [siWrapperResolution_x, siWrapperResolution_x]
siwrb_digitizer.ResolutionV = [siWrapperResolution_y, siWrapperResolution_y]
siwrb_digitizer.ResolutionT = [siWrapperResolution_t, siWrapperResolution_t]
siwrb_digitizer.SimTrackHitCollectionName = ["SiWrBCollection"]
siwrb_digitizer.SimTrkHitRelCollection = ["SiWrBSimDigiLinks"]
siwrb_digitizer.TrackerHitCollectionName = ["SiWrBDigis"]
siwrb_digitizer.ForceHitsOntoSurface = True
siwrb_digitizer.CellIDBits = 32

siwrd_digitizer = DDPlanarDigi("SiWrDdigitizer")
siwrd_digitizer.SubDetectorName = "SiWrD"
siwrd_digitizer.IsStrip = False
siwrd_digitizer.ResolutionU = [siWrapperResolution_x, siWrapperResolution_x]
siwrd_digitizer.ResolutionV = [siWrapperResolution_y, siWrapperResolution_y]
siwrd_digitizer.ResolutionT = [siWrapperResolution_t, siWrapperResolution_t]
siwrd_digitizer.SimTrackHitCollectionName = ["SiWrDCollection"]
siwrd_digitizer.SimTrkHitRelCollection = ["SiWrDSimDigiLinks"]
siwrd_digitizer.TrackerHitCollectionName = ["SiWrDDigis"]
siwrd_digitizer.ForceHitsOntoSurface = True
siwrd_digitizer.CellIDBits = 32

############### DCH Digitizer
# DCHdigi_v01 outputs a custom extension::SenseWireHitCollection type that
# GGTFTrackFinder (renamed from GGTF_tracking in newer k4RecTracker) can no longer
# consume -- the upstream k4RecTracker reference
# (Tracking/test/testTrackFinder/runTestTrackFinder.py) uses DCHdigi_v02, which
# outputs the standard edm4hep::SenseWireHitCollection instead. (install.sh 가 로컬 k4RecTracker/
# genfit 을 빌드하는 이유: CVMFS 의 k4RecTracker 는 우리 k4geo fork 보다 오래되어 init 에서 죽는다.)
from Configurables import DCHdigi_v02
dch_digitizer = DCHdigi_v02("DCHdigi",
    InputSimHitCollection = ["DCHCollection"],
    OutputDigihitCollection = ["DCH_DigiCollection"],
    OutputLinkCollection = ["DCH_DigiSimAssociationCollection"],
    DCH_name = "DCH_v2",
    zResolution_mm = 30.0,  # in mm
    xyResolution_mm = 0.1,  # in mm
    Deadtime_ns = 400.0,  # in ns
    GasType = 0,  # 0: He(90%)-Isobutane(10%), 1: pure He, 2: Ar(50%)-Ethane(50%), 3: pure Ar
    ReadoutWindowStartTime_ns = 1.0,  # in ns (accounts for time of flight, drift, signal travel)
    ReadoutWindowDuration_ns = 450.0,  # in ns
    DriftVelocity_um_per_ns = -1.0,  # in um/ns; negative -> auto-chosen from GasType
    SignalVelocity_mm_per_ns = 200.0,  # in mm/ns (default: 2/3 speed of light)
    OutputLevel = INFO,
)

from Configurables import DDPlanarDigi

muon_digitizer = DDPlanarDigi()
muon_digitizer.SubDetectorName = "Muon-System"
muon_digitizer.EncodingStringParameterName = "MuonSystemReadoutID"
muon_digitizer.CellIDBits = "23"
muon_digitizer.IsStrip = False
muon_digitizer.ResolutionU = [0.4] # in mm, one value for all layers, or different values on the # of layers
muon_digitizer.ResolutionV = [0.4] # in mm, one value for all layers, or different values on the # of layers
muon_digitizer.ForceHitsOntoSurface = True
muon_digitizer.SimTrackHitCollectionName = ["MuonSystemCollection"]
muon_digitizer.SimTrkHitRelCollection = ["MSTrackerHitRelations"]
muon_digitizer.TrackerHitCollectionName = ["MSTrackerHits"]
#muon_digitizer.OutputLevel = 1  # DEBUG level

# Create tracks from gen particles
from Configurables import TracksFromGenParticles
tracksFromGenParticles = TracksFromGenParticles("CreateTracksFromGenParticles",
                                                InputGenParticles = ["MCParticles"],
                                                InputSimTrackerHits=[
                                                    "VertexBarrelCollection",
                                                    "VertexEndcapCollection",
                                                    "DCHCollection",
                                                    "SiWrBCollection",
                                                    "SiWrDCollection"
                                                ],
                                                OutputTracks = ["TracksFromGenParticles"],
                                                OutputMCRecoTrackParticleAssociation = ["TracksFromGenParticlesAssociation"],
                                                ExtrapolateToECal=False,
                                                OutputLevel = INFO)

# produce a TH1 with distances between gen tracks and simTrackerHits
from Configurables import PlotTrackHitDistances, RootHistSvc
from Configurables import Gaudi__Histograming__Sink__Root as RootHistoSink
plotTrackDCHHitDistances = PlotTrackHitDistances("PlotTrackDCHHitDistances",
                                             InputSimTrackerHits = ["DCHCollection"],
                                             InputTracksFromGenParticlesAssociation = tracksFromGenParticles.OutputMCRecoTrackParticleAssociation,
                                             Bz = 2.0)

hps = RootHistSvc("HistogramPersistencySvc")
root_hist_svc = RootHistoSink("RootHistoSink")
root_hist_svc.FileName = "TrackHitDistances.root"

# Calculate dNdx from tracks
from Configurables import TrackdNdxDelphesBased
dNdxFromTracks = TrackdNdxDelphesBased("dNdxFromTracks",
                                  InputLinkCollection=tracksFromGenParticles.OutputMCRecoTrackParticleAssociation,
                                  OutputCollection=["DCHdNdxCollection"],
                                  ZmaxParameterName="DCH_gas_Lhalf",
                                  ZminParameterName="DCH_gas_Lhalf",
                                  RminParameterName="DCH_gas_inner_cyl_R",
                                  RmaxParameterName="DCH_gas_outer_cyl_R",
                                  FillFactor=1.0,
                                  OutputLevel=ERROR)


# Load the Geometric Graph Track Finder (GGTF), following example from:
# k4RecTracker/Tracking/test/testTrackFinder/runTestTrackFinder.py
# Renamed from GGTF_tracking to GGTFTrackFinder in newer k4RecTracker.
from Configurables import GGTFTrackFinder

GGTF = GGTFTrackFinder(
    "GGTF_tracking",
    InputPlanarHitCollections=["VTXBDigis", "VTXDDigis", "SiWrDDigis", "SiWrBDigis"],
    InputWireHitCollections=["DCH_DigiCollection"],
    OutputTracksGGTF=["CDCHTracks"],
    # install.sh 가 내려받는 ONNX 모델 (IDEA_o1_v03 용 파일; drift chamber geometry 가
    # IDEA_o3_v01 과 같아서 그대로 사용).
    ModelPath=os.path.join(os.environ["IDEA_TUTORIAL_ROOT"], "digi", "SimpleGatrIDEAv3o1.onnx"),
    Tbeta=0.6,    # default clustering parameters
    Td=0.3,       # form the example in k4RecTracker
    OutputLevel=INFO,
)

################ Dual-readout calorimeter
# SiPM emulation
from Configurables import SimulateSiPMwithEdep
sipmEdep = SimulateSiPMwithEdep("SimulateSiPMwithEdep",
    OutputLevel=DEBUG,
    inputHitCollection = "DRcaloSiPMreadout_scint",
    outputHitCollection = "DRcaloSiPMreadoutDigiHit_scint",
    outputTimeStructCollection = "DRcaloSiPMreadoutDigiWaveform_scint",
    readoutName = "DRcaloSiPMreadout",
    # wavelength in nm (decreasing order)
    wavelength = [
        900., 850., 800., 750., 725.,
        700., 675., 650., 625., 600.,
        590., 580., 570., 560., 550.,
        540., 530., 520., 510., 500.,
        490., 480., 470., 460., 450.,
        440., 430., 420., 400., 350.,
        300.
    ],
    # Hamamatsu S14160-1310PS
    sipmEfficiency = [
        0.02, 0.025, 0.045, 0.06, 0.0675,
        0.075, 0.0925, 0.11, 0.125, 0.14,
        0.146, 0.152, 0.158, 0.164, 0.17,
        0.173, 0.176, 0.178, 0.179, 0.18,
        0.181, 0.182, 0.183, 0.184, 0.18,
        0.173, 0.166, 0.158, 0.15, 0.12,
        0.05
    ],
    # Kuraray SCSF-78
    scintSpectrum = [
        0., 0., 0., 0., 0.,
        0., 0., 0.0003, 0.0008, 0.0032,
        0.0057, 0.0084, 0.0153, 0.0234, 0.0343,
        0.0604, 0.0927, 0.1398, 0.2105, 0.2903,
        0.4122, 0.5518, 0.7086, 0.8678, 1.,
        0.8676, 0.2311, 0.0033, 0.0012, 0.,
        0.
    ],
    # Kuraray SCSF-78
    absorptionLength = [
        2.714, 3.619, 5.791, 4.343, 7.896,
        5.429, 36.19, 17.37, 36.19, 5.429,
        13., 14.5, 16., 18., 16.5,
        17., 14., 16., 15., 14.5,
        13., 12., 10., 8., 7.238,
        4., 1.2, 0.5, 0.2, 0.2,
        0.1
    ],
    # Kodak Wratten 9
    filterEfficiency = [
        0.903, 0.903, 0.903, 0.903, 0.903,
        0.903, 0.902, 0.901, 0.898, 0.895,
        0.893, 0.891, 0.888, 0.883, 0.87,
        0.838, 0.76, 0.62, 0.488, 0.345,
        0.207, 0.083, 0.018, 0., 0.,
        0., 0., 0., 0., 0.,
        0.
    ],
    # empirical value to keep (scint npe / ceren npe) =~ 5
    scintYield = 0.565, # effective scintillation yield (k*13.6/keV)
                        # k responsible for numerical aperture
    scaleADC = 1.0, # equalization constant from ADC to GeV -- pinned to 1.0 (nominal
                    # convention, 2026-09-29): our own S_fiber/C_fiber calib constants
                    # (analysis/calib_constants_digi_*.json) absorb the real ADC-to-GeV
                    # scale instead. Was 0.0003897 (o1-derived, unused since); do not
                    # revert without updating the nominal calib constants to match.
    threshold = 1.5, # ADC integration threshold
    params = {"ccgv" : 0.25}, # cell-to-cell gain variation (and others if needed)
    gateLength = 80., # ns
    SNR = 14., # gain(10um)/gain(15um) = 0.5
)

from Configurables import SimulateSiPMwithOpticalPhoton
sipmOptical = SimulateSiPMwithOpticalPhoton("SimulateSiPMwithOpticalPhoton",
    OutputLevel=DEBUG,
    inputHitCollection = "DRcaloSiPMreadoutSimHit",
    inputTimeStructCollection = "DRcaloSiPMreadoutTimeStruct",
    inputWavlenCollection = "DRcaloSiPMreadoutWaveLen",
    outputHitCollection = "DRcaloSiPMreadoutDigiHit",
    outputTimeStructCollection = "DRcaloSiPMreadoutDigiWaveform",
    # wavelength in nm (decreasing order)
    wavelength = [
        900., 850., 800., 750., 725.,
        700., 675., 650., 625., 600.,
        590., 580., 570., 560., 550.,
        540., 530., 520., 510., 500.,
        490., 480., 470., 460., 450.,
        440., 430., 420., 400., 350.,
        300., 280.
    ],
    # Hamamatsu S14160-1315PS
    sipmEfficiency = [
        0.03, 0.05, 0.07, 0.1, 0.13,
        0.14, 0.16, 0.19, 0.21, 0.23,
        0.238, 0.246, 0.254, 0.262, 0.27,
        0.28, 0.29, 0.3, 0.31, 0.32,
        0.322, 0.324, 0.326, 0.328, 0.33,
        0.33, 0.32, 0.30, 0.27, 0.22,
        0.12, 0.
    ],
    scaleADC = 1.0, # equalization constant from ADC to GeV -- pinned to 1.0, see the
                    # SimulateSiPMwithEdep.scaleADC comment above for why.
    threshold = 1.5,
    cellpitch = 15., # um
    falltimeFast = 1.7, # ns
    gateLength = 80., # ns
    params = {
        "ccgv" : 0.15, # cell-to-cell gain variation
                       # responsible for a single photon peak std. dev.
        "falltimeslow" : 15., # ns
        "slowcomponentfraction" : 0.5 # signal = (1-f)*fast + f*slow
    },
)

# RNG for sipm emulation (TODO harmonize RNG with other modules)
from Configurables import HepRndm__Engine_CLHEP__RanluxEngine_ as RndmEngine
rndmEngine = RndmEngine('RndmGenSvc.Engine',
  SetSingleton = True,
  Seeds = [ 1234567 ] # default seed is 1234567
)

# DRC topoclustering
# use const noise tool for the moment
from Configurables import ConstNoiseTool
constNoiseTool = ConstNoiseTool("ConstNoiseTool",
    detectors = ["FiberDRCalo"],
    systemEncoding = "system:5",
    detectorsNoiseRMS = [0.001], # ad-hoc small value
    detectorsNoiseOffset = [0.],
    OutputLevel = INFO
)

from Configurables import CaloTopoClusterFCCee
topoClusterAll = CaloTopoClusterFCCee("topoClusterAll",
    cells = ["DRcaloSiPMreadoutDigiHit","DRcaloSiPMreadoutDigiHit_scint"],
    clusters = "TopoClusterAll",
    clusterCells = "TopoClusterAllCells",
    useNeighborMap = False,
    readoutName = "DRcaloSiPMreadout",
    neigboursTool = None,
    noiseTool = constNoiseTool,
    systemEncoding = "system:5",
    seedSigma = 4,
    neighbourSigma = 2,
    lastNeighbourSigma = 0,
    calorimeterIDs=[25],
    createClusterCellCollection=True,
    OutputLevel = INFO
)

from Configurables import CreateTruthLinks
createTruthLinks = CreateTruthLinks("CreateTruthLinks",
    cell_hit_links=["DRcaloSiPMreadoutDigiHit_scint_link"],
    clusters=["TopoClusterAll"],
    mcparticles="MCParticles",
    cell_mcparticle_links="CaloHitMCParticleLinks_scint",
    cluster_mcparticle_links="ClusterMCParticleLinks",
    OutputLevel=INFO
)

from Configurables import RndmGenSvc
rndmGenSvc = RndmGenSvc("RndmGenSvc",
  Engine = rndmEngine.name()
)

################ Output
io_svc.outputCommands = [
  "keep *",
  "drop *scintContrib*",
  "drop *Waveform*",
  "drop *DRcaloSiPMreadoutTimeStruct*",
  "drop *DRcaloSiPMreadoutWaveLen*"
]

# Profiling
from Configurables import AuditorSvc, ChronoAuditor, UniqueIDGenSvc
chra = ChronoAuditor()
audsvc = AuditorSvc()
audsvc.Auditors = [chra]

# DIGI_SKIP_HELIX_TRACKING=1 (set by the calibration-campaign condor wrappers for the
# no-field / 1e-3-tesla-field compact variants): TracksFromGenParticles reads the
# magnetic field straight from the compact geometry at runtime and helix-parameterizes
# GenParticle trajectories with it; below some (undetermined, seemingly independent of
# the actual field magnitude we tried: 1e-9 and 1e-3 tesla both hit this) internal
# threshold it throws "Helix, invalid parameter: bField 0" and aborts the whole event
# loop (0 events processed). tracksFromGenParticles/plotTrackDCHHitDistances/
# dNdxFromTracks are diagnostic-only (hit-distance histogram, dE/dx) and nothing else
# downstream depends on their output -- GGTFTrackFinder uses its own ML model on raw
# digitized hits directly, and CreateTruthLinks only needs calo hits/clusters/MCParticles
# -- so skipping all three is safe. Discovered while smoke-testing the o3 calibration
# campaign; see O3_GEOMETRY_AND_SIM_NOTES.md / calibration campaign plan for details.
skip_helix_tracking = os.environ.get("DIGI_SKIP_HELIX_TRACKING", "0") == "1"

top_alg = [
    vtxb_digitizer,
    vtxd_digitizer,
    siwrb_digitizer,
    siwrd_digitizer,
    dch_digitizer,
    muon_digitizer,
]
if not skip_helix_tracking:
    top_alg += [tracksFromGenParticles, plotTrackDCHHitDistances, dNdxFromTracks]
else:
    print("DIGI_SKIP_HELIX_TRACKING=1: skipping tracksFromGenParticles/"
          "plotTrackDCHHitDistances/dNdxFromTracks (helix propagation needs a "
          "non-degenerate B field; not needed for calorimeter-only calibration analysis)")
top_alg += [GGTF, sipmEdep, sipmOptical, topoClusterAll, createTruthLinks]

from k4FWCore import ApplicationMgr
application_mgr = ApplicationMgr(
    TopAlg = top_alg,
    EvtSel = 'NONE',
    EvtMax = -1,
    ExtSvc = [
        root_hist_svc,
        EventDataSvc("EventDataSvc"),
        geoservice,
        audsvc,
        UniqueIDGenSvc("uidSvc"),
        rndmEngine,
        rndmGenSvc
    ],
    StopOnSignal = True,
)

for algo in application_mgr.TopAlg:
    algo.AuditExecute = True
