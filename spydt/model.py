from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import NewType

@dataclass
class Error:
    error: str = ""

# Enums

class Const(Enum):
    ISUNDERPROVISION = "underprovisioning-allowed"
    MAXUNDERPROVISION= "max-percentage-underprovision"
    METHOD = "scaling-method"
    ISHETEREOGENEOUS= "heterogeneous-vms-allowed"
    ISRESIZEPODS= "pods-resize-allowed"
    VMTYPES= "vm-types"
    DISCARTED = "discarted"
    SCHEDULED = "scheduled"
    SELECTED = "selected"
    HOUR = "h"
    MINUTE = "m"
    SECOND = "s"
    NAIVE_ALGORITHM = "naive"
    BEST_RESOURCE_PAIR_ALGORITHM = "best-resource-pair"
    ONLY_DELTA_ALGORITHM = "only-delta-load"
    ALWAYS_RESIZE_ALGORITHM = "always-resize"
    RESIZE_WHEN_BENEFICIAL = "resize-when-beneficial"
    SCALE_METHOD_HORIZONTAL = "horizontal"
    SCALE_METHOD_VERTICAL = "vertical"
    SCALE_METHOD_HYBRID = "hybrid"
    COST = "cost"
    DERIVATION_TIME = "derivation-time"
    TRANSITION_TIME = "transition-time"
    UTC_TIME_LAYOUT = "2006-01-02T15:04:00Z"
    CONFIG_FILE = "config.yml"
    DEFAULT_LOGFILE = "Logs.log"
    DEFAULT_VM_SHUTDOWN_TIME = 35
    DEFAULT_VM_BOOT_TIME = 20
    DEFAULT_POD_BOOT_TIME = 20
    PERCENTAGE_REQUIRED_k8S_INSTALLATION_CPU = 0.06
    PERCENTAGE_REQUIRED_k8S_INSTALLATION_MEM = 0.25
    TIME_ADD_NODE_TO_K8S = 120
    TIME_CONTAINER_START = 10
    ENDPOINT_FORECAST = "/predict"
    ENDPOINT_VMS_PROFILES = "/api/vms"
    ENDPOINT_STATES = "/api/states"
    ENDPOINT_INVALIDATE_STATES = "/api/invalidate/{timestamp}"
    ENDPOINT_CURRENT_STATE = "/api/current"
    ENDPOINT_SERVICE_PROFILES = "/getRegressionTRNsMongoDBAll/{apptype}/{appname}/{mainservicename}"
    ENDPOINT_VM_TIMES = "/getPerVMTypeOneBootShutDownData"
    ENDPOINT_ALL_VM_TIMES = "/getPerVMTypeAllBootShutDownData"
    ENDPOINT_SERVICE_PROFILE_BY_MSC = "/getPredictedRegressionReplicas/{apptype}/{appname}/{mainservicename}/{msc}/{numcoresutil}/{numcoreslimit}/{nummemlimit}"
    ENDPOINT_SERVICE_PROFILE_BY_REPLICAS = "/getPredictedRegressionTRN/{apptype}/{appname}/{mainservicename}/{replicas}/{numcoresutil}/{numcoreslimit}/{nummemlimit}"
    ENDPOINT_SUBSCRIBE_NOTIFICATIONS = "/subscribe"
    ENDPOINT_RECIVE_NOTIFICATIONS = "/api/forecast"


@dataclass
class Pricing: # types/types_performance_profiles.go:5
    Price: float = 0.0  # `json:"price" bson:"price"`
    Unit: str = ""      # `json:"unit" bson:"unit"`


@dataclass
class VmProfile:  # types/type_performance_profiles.go:10
    Type: str = ""                  # `json:"type" bson:"type"`
    CPUCores: float = 0.0           # `json:"cpu_cores" bson:"cpu_cores"`
    Memory: float = 0.0             # `json:"mem_gb" bson:"mem_gb"`
    OS:  str = ""                   # `json:"os" bson:"os"`
    _Pricing: Pricing = Pricing()   # `json:"pricing" bson:"pricing"`
    ReplicasCapacity: int=0	        # `json:"replicas_capacity" bson:"replicas_capacity"`

@dataclass
class ServiceInfo: # types/type_policies.go#111
    Scale: int=0       # `json:"Replicas"`
    CPU: float=0.0	    # `json:"Cpu_cores"`
    Memory: float=0.0   # `json:"Mem_gb"`


VMScale = NewType("VMScale", dict[str, int]) # types/types_policies.go:15
# Number of VMs of each type


Service = NewType("Service", dict[str, ServiceInfo]) # types/types_policies.go:12
# Service keeps the name and scale of the scaled service

@dataclass
class ForecastComponent:
    """Struct that models the external components to which SPDT should be connected"""
    Endpoint: str=""	    # `yaml:"endpoint"`
    Granularity:  str=""	# `yaml:"granularity"`


@dataclass
class Component:
    """Struct that models the external components to which SPDT should be connected"""
    Endpoint:str=""	        # `yaml:"endpoint"`
    Username:str=""	        # `yaml:"username"`
    Password:str=""	        # `yaml:"password"`
    ApiKey:str=""	        # `yaml:"api-key"`


@dataclass
class SystemConfiguration:  # util/config.go:42  TODO: Implemented only the fields requiered for the naive strategy
    # Host                         string            # `yaml:"host"`
    # CSP                          string            # `yaml:"CSP"`
    # Region                       string            # `yaml:"region"`
    AppName: str = ""                                # `yaml:"app-name"`
    MainServiceName: str = ""                        # `yaml:"main-service-name"`
    AppType: str = ""                                # `yaml:"app-type"`
    # PricingModel                 PricingModel      # `yaml:"pricing-model"`
    ForecastComponent: ForecastComponent = ForecastComponent()            # `yaml:"forecasting-component"`
    PerformanceProfilesComponent: Component = Component()        # `yaml:"performance-profiles-component"`
    # SchedulerComponent           Component         # `yaml:"scheduler-component"`
    # ScalingHorizon               ScalingHorizon    # `yaml:"scaling-horizon"`
    # PreferredAlgorithm           string            # `yaml:"preferred-algorithm"`
    # PolicySettings               PolicySettings    # `yaml:"policy-settings"`
    # PullingInterval              int               # `yaml:"pulling-interval"`
    # StorageInterval              string            # `yaml:"storage-interval"`

@dataclass
class StateLoadCapacity: # types/type_policies.go:111
    " Represent the number of requests for a time T"
    TimeStamp: datetime            # `json:"timestamp"`
    Requests: float                # `json:"requests"`

@dataclass
class State: # types/type_policies.go:98
    "DesiredState is the metadata of the state expected to scale to"
    Services: Service = Service({})  # `json:"Services"`
    Hash: str = ""                   # `json:"Hash"`
    VMs: VMScale = VMScale({})       # `json:"VMs"`    

@dataclass
class CriticalInterval: # types/types_forecasting.go:9
    """Critical Interval is the interval of time analyzed to take a scaling decision"""
    TimeStart: datetime = datetime.now() # `json:"TimeStart"`
    Requests: float=0.0	                 # `json:"Requests"`	//max/min point in the interval
    TimeEnd: datetime = datetime.now()	 # `json:"TimeEnd"`
    TimePeak: datetime = datetime.now()

@dataclass
class MSCSimpleSetting: # types/types_performance_profiles.go:51
    Replicas: int=0                     # `json:"replicas" bson:"replicas"`
    MSCPerSecond: float=0.0             # `json:"maximum_service_capacity_per_sec" bson:"maximum_service_capacity_per_sec"`
    BootTimeSec: float=0.0              # `json:"pod_boot_time_sec" bson:"pod_boot_time_sec"`
    StandDevBootTimeSec: float=0.0      # `json:"sd_pod_boot_time_ms" bson:"sd_pod_boot_time_ms"`


@dataclass 
class Limit: # types/types_performance_profiles.go:32
    CPUCores: float=0.0                  # `json:"Cpu_cores" bson:"cpu_cores"`
    MemoryGB: float=0.0                  # `json:"Mem_gb" bson:"mem_gb"`
    RequestPerSecond: int=0              # `json:"Request_per_second" bson:"request_per_second"`

@dataclass
class ContainersConfig: # types/types_policies.go:224
    Limits: Limit=Limit()              # `json:"limits" bson:"limits"`
    MSCSetting: MSCSimpleSetting =MSCSimpleSetting() # `json:"mscs" bson:"mscs"`
    VMSet: VMScale=VMScale({})           # `json:"vms" bson:"vms"`
    Cost: float=0.0                      # `json:"cost" bson:"cost"`


@dataclass
class ProcessedForecast: # types/types_forecasting.go:33
    """ProcessedForecast metadata after processing the time serie"""
    CriticalIntervals: list[CriticalInterval] = field(default_factory=list)


@dataclass
class PolicyMetrics: # types/types_policies.go:156
    Cost: float=0.0                                 # `json:"cost" bson:"cost"`
    OverProvision: float=0.0                        # `json:"over_provision" bson:"over_provision"`
    UnderProvision: float=0.0                       # `json:"under_provision" bson:"under_provision"`
    NumberScalingActions: int=0                     # `json:"n_scaling_actions" bson:"n_scaling_actions"`
    StartTimeDerivation: datetime = datetime.now()  # `json:"start_derivation_time" bson:"start_derivation_time"`
    FinishTimeDerivation: datetime = datetime.now() # `json:"finish_derivation_time" bson:"finish_derivation_time"`
    DerivationDuration: float=0.0                   # `json:"derivation_duration" bson:"derivation_duration"`
    NumberVMScalingActions: int=0                   # `json:"num_scale_vms" bson:"num_scale_vms"`
    NumberContainerScalingActions: int=0            # `json:"num_scale_containers" bson:"num_scale_containers"`
    AvgShadowTime: float=0.0                        # `json:"avg_shadow_time_sec" bson:"avg_shadow_time_sec"`
    AvgTransitionTime: float=0.0                    # `json:"avg_transition_time_sec" bson:"avg_transition_time_sec"`
    AvgElapsedTime: float=0.0                       # `json:"avg_time_between_scaling_sec" bson:"avg_time_between_scaling_sec"`


@dataclass
class ConfigMetrics: # types/types_policies.go:144
    Cost: float=0.0                              # `json:"cost" bson:"cost"`
    OverProvision: float=0.0                     # `json:"over_provision" bson:"over_provision"`
    UnderProvision: float=0.0                    # `json:"under_provision" bson:"under_provision"`
    RequestsCapacity: float=0.0                  # `json:"requests_capacity" bson:"requests_capacity"`
    CPUUtilization: float=0.0                    # `json:"cpu_utilization" bson:"cpu_utilization"`
    MemoryUtilization: float=0.0                 # `json:"mem_utilization" bson:"mem_utilization"`
    ShadowTimeSec: float=0.0                     # `json:"shadow_time_sec" bson:"shadow_time_sec"`
    TransitionTimeSec: float=0.0                 # `json:"transition_time_sec" bson:"transition_time_sec"`
    ElapsedTimeSec: float=0.0                    # `json:"elapsed_time_sec" bson:"elapsed_time_sec"`


@dataclass
class ScalingAction: # types/types_policies.go
    TimeStartTransition: datetime=datetime.now()    # `json:"time_start_transition" bson:"time_start_transition"`
    InitialState: State=State()		                # `json:"initial_state" bson:"initial_state"`
    DesiredState: State=State()                     # `json:"desired_state" bson:"desired_state"`
    TimeStart: datetime=datetime.now()              # `json:"time_start" bson:"time_start"`
    TimeEnd: datetime=datetime.now()                # `json:"time_end" bson:"time_end"`
    Metrics: ConfigMetrics=ConfigMetrics()          # `json:"metrics" bson:"metrics"`


@dataclass
class Policy: # types/types_policies.go:201
    # ID              bson.ObjectId     ` bson:"_id" json:"id"`
    Algorithm:str = ""                       # `json:"algorithm" bson:"algorithm"`
    Metrics: PolicyMetrics = PolicyMetrics() # `json:"metrics" bson:"metrics"`
    Status: str = ""                         # `json:"status" bson:"status"`
    Parameters: dict[str,str]=field(default_factory=dict)        # `json:"parameters" bson:"parameters"`
    ScalingActions: list[ScalingAction]=field(default_factory=list) # `json:"scaling_actions" bson:"scaling_actions"`
    TimeWindowStart: datetime = datetime.now()    # `json:"window_time_start"  bson:"window_time_start"`
    TimeWindowEnd:   datetime = datetime.now()    # `json:"window_time_end"  bson:"window_time_end"`


@dataclass
class PerformanceProfile:
	ID: str=""                                                          # `bson:"_id" json:"id"`
	MSCSettings: list[MSCSimpleSetting] = field(default_factory=list)   # `json:"mscs" bson:"mscs"`
	_Limit: Limit = Limit()                                             # `json:"limits" bson:"limits"`

@dataclass
class MaxServiceCapacity: # types/types_performance_profiles.go:58
    Experimental   : float=0.0          # `json:"Experimental" bson:"experimental"`
    RegBruteForce  : float=0.0          # `json:"RegBruteForce" bson:"reg_brute_force"`
    RegSmart       : float=0.0          # `json:"RegSmart" bson:"reg_smart"`


@dataclass
class MSCCompleteSetting: # types/types_performance_profiles.go:77
    Replicas      		: int = 0                   # `json:"Replicas"`
    BootTimeMs         	: float = 0.0               # `json:"Pod_boot_time_ms"`
    StandDevBootTimeMS 	: float = 0.0               # `json:"Sd_Pod_boot_time_ms"`
    MSCPerSecond        : MaxServiceCapacity = MaxServiceCapacity()  # `json:"Maximum_service_capacity_per_sec"`
    MSCPerMinute        : MaxServiceCapacity = MaxServiceCapacity()  # `json:"Maximum_service_capacity_per_min"`
