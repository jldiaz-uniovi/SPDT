from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, NewType
from dataclasses_json import dataclass_json, config

def _f(fn=None, dv=None, df=None):
    if df:
        return field(metadata=config(field_name=fn), default_factory=df)
    else:
        return field(metadata=config(field_name=fn), default=dv)

def parse_date(isodate: str) -> datetime:
    return datetime.fromisoformat(isodate.replace("Z", "+00:00"))

def date_to_iso(date: datetime) -> str:
    return datetime.isoformat(date) + "Z"

def _timestamp(fn=None):
    return field(metadata=config(field_name=fn, encoder=date_to_iso, decoder=parse_date),
        default_factory=datetime.now)

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


@dataclass_json
@dataclass
class Pricing: # types/types_performance_profiles.go:5
    Price: float = _f("price", 0.0)
    Unit: str = _f("unit" , "")


@dataclass_json
@dataclass
class VmProfile:  # types/type_performance_profiles.go:10
    Type: str = _f("type", "")
    CPUCores: float = _f("cpu_cores", 0.0)
    Memory: float = _f("mem_gb", 0.0)
    OS:  str = _f("os", "")
    _Pricing: Pricing = _f("pricing", df=Pricing)
    ReplicasCapacity: int = _f("replicas_capacity", 0)

@dataclass_json
@dataclass
class ServiceInfo: # types/type_policies.go#111
    Scale: int = _f("Replicas", 0)
    CPU: float = _f("Cpu_cores", 0.0)
    Memory: float = _f("Mem_gb", 0.0)


VMScale = NewType("VMScale", dict[str, int]) # types/types_policies.go:15
# Number of VMs of each type

Service = NewType("Service", dict[str, ServiceInfo]) # types/types_policies.go:12
# Service keeps the name and scale of the scaled service

@dataclass_json
@dataclass
class ForecastComponent_:
    """Struct that models the external components to which SPDT should be connected"""
    Endpoint: str = _f("endpoint", "")
    Granularity:  str = _f("granularity", "")


@dataclass_json
@dataclass
class Component:
    """Struct that models the external components to which SPDT should be connected"""
    Endpoint:str = _f("endpoint", "")
    Username:str = _f("username", "")
    Password:str = _f("password", "")
    ApiKey:str = _f("api-key", "")

@dataclass_json
@dataclass
class ScalingHorizon_:
    StartTime: datetime	= _timestamp("start-time")
    EndTime: datetime = _timestamp("end-time")

@dataclass_json
@dataclass
class PricingModel_:
    Budget: float = _f("monthly-budget", 0.0)
    BillingUnit: str = _f("billing-unit", "")

@dataclass_json
@dataclass
class PolicySettings_:
    ScalingMethod: str = _f("vm-scaling-method", "")
    PreferredMetric: str = _f("preferred-metric", "")


@dataclass_json
@dataclass
class SystemConfiguration:  # util/config.go:42
    Host: str = _f("host", "")
    CSP:  str = _f("CSP", "")
    Region: str = _f("region", "")
    AppName: str = _f("app-name", "")
    MainServiceName: str = _f("main-service-name", "")
    AppType: str = _f("app-type", "")
    PricingModel: PricingModel_ = _f("pricing-model", df=PricingModel_)
    ForecastComponent: ForecastComponent_ = _f("forecasting-component", df=ForecastComponent_)
    PerformanceProfilesComponent: Component = _f("performance-profiles-component", df=Component)
    SchedulerComponent: Component = _f("scheduler-component", df=Component)
    ScalingHorizon: ScalingHorizon_ = _f("scaling-horizon", df=ScalingHorizon_)
    PreferredAlgorithm: str = _f("preferred-algorithm", "")
    PolicySettings: PolicySettings_ = _f("policy-settings", df=PolicySettings_)
    PullingInterval: int = _f("pulling-interval", "")
    StorageInterval: str = _f("storage-interval", "")

@dataclass_json
@dataclass
class StateLoadCapacity: # types/type_policies.go:111
    " Represent the number of requests for a time T"
    TimeStamp: datetime = _timestamp("timestamp")
    Requests: float = _f("requests", 0.0)

@dataclass_json
@dataclass
class State: # types/type_policies.go:98
    "DesiredState is the metadata of the state expected to scale to"
    Services: Service = _f("Services", df=Service)
    Hash: str = _f("Hash", "")
    VMs: VMScale = _f("VMs", df=VMScale)

@dataclass_json
@dataclass
class CriticalInterval: # types/types_forecasting.go:9
    """Critical Interval is the interval of time analyzed to take a scaling decision"""
    TimeStart: datetime = _timestamp("TimeStart")
    Requests: float= _f("Requests", 0.0)  # //max/min point in the interval
    TimeEnd: datetime = _timestamp("TimeEnd")
    TimePeak: datetime = _timestamp(None)

@dataclass_json
@dataclass
class MSCSimpleSetting: # types/types_performance_profiles.go:51
    Replicas: int = _f("replicas", 0)
    MSCPerSecond: float = _f("maximum_service_capacity_per_sec", 0.0)
    BootTimeSec: float =  _f("pod_boot_time_sec", 0.0)
    StandDevBootTimeSec: float = _f("sd_pod_boot_time_ms", 0.0)


@dataclass_json
@dataclass 
class Limit_: # types/types_performance_profiles.go:32
    CPUCores: float = _f("Cpu_cores", 0.0)
    MemoryGB: float = _f("Mem_gb", 0.0)
    RequestPerSecond: int = _f("Request_per_second", 0)

@dataclass_json
@dataclass
class ContainersConfig: # types/types_policies.go:224
    Limits: Limit_ = _f("limits", df=Limit_)
    MSCSetting: MSCSimpleSetting = _f("mscs", df=MSCSimpleSetting)
    VMSet: VMScale = _f("vms", df=VMScale)
    Cost: float = _f("cost", 0.0)


@dataclass
class ProcessedForecast: # types/types_forecasting.go:33
    """ProcessedForecast metadata after processing the time serie"""
    CriticalIntervals: list[CriticalInterval] = field(default_factory=list)


@dataclass_json
@dataclass
class PolicyMetrics: # types/types_policies.go:156
    Cost: float = _f("cost", 0.0)
    OverProvision: float = _f("over_provision", 0.0)
    UnderProvision: float = _f("under_provision", 0.0)
    NumberScalingActions: int = _f("n_scaling_actions", 0)
    StartTimeDerivation: datetime = _timestamp("start_derivation_time")
    FinishTimeDerivation: datetime = _timestamp("finish_derivation_time")
    DerivationDuration: float = _f("derivation_duration", 0.0)
    NumberVMScalingActions: int = _f("num_scale_vms", 0)
    NumberContainerScalingActions: int = _f("num_scale_containers", 0)
    AvgShadowTime: float = _f("avg_shadow_time_sec", 0.0)
    AvgTransitionTime: float = _f("avg_transition_time_sec", 0.0)
    AvgElapsedTime: float = _f("avg_time_between_scaling_sec", 0.0)


@dataclass_json
@dataclass
class ConfigMetrics: # types/types_policies.go:144
    Cost: float = _f("cost", 0.0)
    OverProvision: float = _f("over_provision", 0.0)
    UnderProvision: float = _f("under_provision", 0.0)
    RequestsCapacity: float = _f("requests_capacity", 0.0)
    CPUUtilization: float = _f("cpu_utilization", 0.0)
    MemoryUtilization: float = _f("mem_utilization", 0.0)
    ShadowTimeSec: float = _f("shadow_time_sec", 0.0)
    TransitionTimeSec: float = _f("transition_time_sec", 0.0)
    ElapsedTimeSec: float = _f("elapsed_time_sec", 0.0)


@dataclass_json
@dataclass
class ScalingAction: # types/types_policies.go
    TimeStartTransition: datetime = _timestamp("time_start_transition")
    InitialState: State = _f("initial_state", df=State)
    DesiredState: State = _f("desired_state", df=State)
    TimeStart: datetime = _f("time_start")
    TimeEnd: datetime = _f("time_end")
    Metrics: ConfigMetrics = _f("metrics", df=ConfigMetrics)


@dataclass_json
@dataclass
class Policy: # types/types_policies.go:201
    # ID              bson.ObjectId     ` bson:"_id" json:"id"`
    Algorithm: str = _f("algorithm", "")
    Metrics: PolicyMetrics = _f("metrics", df=PolicyMetrics)
    Status: str = _f("status", "")
    Parameters: dict[str,str] = _f("parameters", df=dict)
    ScalingActions: list[ScalingAction] = _f("scaling_actions", df=list)
    TimeWindowStart: datetime = _timestamp("window_time_start")
    TimeWindowEnd:   datetime = _timestamp("window_time_end")


@dataclass_json
@dataclass
class PerformanceProfile:
    ID: str = _f("_id", "")
    MSCSettings: list[MSCSimpleSetting] = _f("mscs", df=list)
    Limit: Limit_ = _f("limits", df=Limit_)

@dataclass_json
@dataclass
class MaxServiceCapacity: # types/types_performance_profiles.go:58
    Experimental   : float = _f("Experimental", 0.0)
    RegBruteForce  : float = _f("RegBruteForce", 0.0)
    RegSmart       : float = _f("RegSmart", 0.0)

@dataclass_json
@dataclass
class MSCCompleteSetting: # types/types_performance_profiles.go:77
    Replicas: int = _f("Replicas", 0)
    BootTimeMs: float = _f("Pod_boot_time_ms", 0.0)
    StandDevBootTimeMS: float = _f("Sd_Pod_boot_time_ms", 0.0)
    MSCPerSecond: MaxServiceCapacity = _f("Maximum_service_capacity_per_sec", df=MaxServiceCapacity)
    MSCPerMinute: MaxServiceCapacity = _f("Maximum_service_capacity_per_min", df=MaxServiceCapacity)


# types/types_forecasting.go:17
@dataclass_json
@dataclass
class ForecastedValue:
    """/*Represent the number of requests for a time T*/"""
    TimeStamp: datetime = _timestamp("timestamp")
    Requests: float = _f("requests", 0.0)


# types/types_forecasting.go:23
@dataclass_json
@dataclass
class Forecast:
    """/*Set of values received from the Forecasting component*/"""
    # IDdb: str=""                                # `bson:"_id"`
    ServiceName: str = _f("service_name", "")
    ForecastedValues: list[ForecastedValue] = _f("values", df=list)
    TimeWindowStart: datetime = _timestamp("start_time")
    TimeWindowEnd: datetime = _timestamp("end_time")
    IDPrediction: str = _f("id_predictions", "")


# types/types_performance_profiles.go:19
@dataclass_json
@dataclass
class BootShutDownTime:
    """//Times in seconds"""
    NumInstances: int = _f("NumInstances", 0)
    BootTime: float = _f("BootTime", 0.0)
    ShutDownTime: float = _f("ShutDownTime", 0.0)


# types/types_performance_profiles.go:27
@dataclass_json
@dataclass
class InstancesBootShutdownTime:
    """//Times in seconds"""
    InstancesValues: list[BootShutDownTime] = _f("InstanceValues", df=BootShutDownTime)
    VMType: str = _f("VMType", "")

