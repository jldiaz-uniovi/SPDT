from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, NewType
from bson.objectid import ObjectId  # type: ignore
from dataclasses_json import dataclass_json, config, Undefined
from dateutil.parser import isoparse
from marshmallow import fields

def _f(fn=None, dv=None, df=None):
    if df:
        return field(metadata=config(field_name=fn), default_factory=df)
    else:
        return field(metadata=config(field_name=fn), default=dv)

def parse_date(isodate: str) -> datetime:
    return isoparse(isodate)

def parse_date2(isodate: str) -> datetime:
    return datetime.fromisoformat(isodate.replace("Z", "+00:00"))

def date_to_iso(date: datetime) -> str:
    return datetime.isoformat(date) + "Z"

def _isodate(fn=None):
    return field(metadata=config(
                    field_name=fn, 
                    encoder=date_to_iso, 
                    decoder=parse_date,  
                    mm_field=fields.DateTime(format="iso", data_key=fn)),
                default_factory=lambda: datetime.fromtimestamp(0)
                )


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
    Price: float = _f("price", 0.0)         # price per hour
    Unit: str = _f("unit" , "")             # Currently not used by spdt


@dataclass_json
@dataclass
class VmProfile:  # types/type_performance_profiles.go:10
    Type: str = _f("type", "")                          # eg: t2.large
    CPUCores: float = _f("cpu_cores", 0.0)              # eg: 2
    Memory: float = _f("mem_gb", 0.0)                   # eg: 8
    OS:  str = _f("os", "")                             # currently not used by sptd
    _Pricing: Pricing = _f("pricing", df=Pricing)       # pricer per hour
    ReplicasCapacity: int = _f("replicas_capacity", 0)  # computed? depending on the Limits of the container

@dataclass_json
@dataclass
class ServiceInfo: # types/type_policies.go#111
    Scale: int = _f("scale", 0)                         # Number of identical replicas of the service (eg: 7)
    CPU: float = _f("cpu", 0.0)                         # CPU of each replica (eg: 0.2)
    Memory: float = _f("memory", 0.0)                   # Memory in GB of each replica (eg: 0.2)


# Dictionary with the number of VM of each type
# The key is the VM type, and the value the number of instances
VMScale = NewType("VMScale", dict[str, int]) # types/types_policies.go:15
# Number of VMs of each type

# Dictionary which maps each service (app) name with a ServiceInfo structure
Service = NewType("Service", dict[str, ServiceInfo]) # types/types_policies.go:12
# Service keeps the name and scale of the scaled service

@dataclass_json
@dataclass
class ForecastComponent_:
    """Struct that models the external components to which SPDT should be connected"""
    Endpoint: str = _f("endpoint", "")
    Granularity:  str = _f("granularity", "")       # eg: "h". "m", "s"


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
    """Start and end time for the scaling actions, given in a config file"""
    StartTime: datetime	= _isodate("start-time")
    EndTime: datetime = _isodate("end-time")

@dataclass_json
@dataclass
class PricingModel_:
    """Budget used in policy selection, given in a config file"""
    Budget: float = _f("monthly-budget", 0.0)
    BillingUnit: str = _f("billing-unit", "")

@dataclass_json
@dataclass
class PolicySettings_:
    """Given in a config file, currently not used"""
    ScalingMethod: str = _f("vm-scaling-method", "")    # Currently not used by sptd (always "horizontal")
    PreferredMetric: str = _f("preferred-metric", "")   # Currently not used by sptd


@dataclass_json
@dataclass
class SystemConfiguration:  # util/config.go:42
    """Parameters read from config.yml"""
    Host: str = _f("host", "")          # Used for subscribing to updates
    CSP:  str = _f("CSP", "")           # Related with the retrieving of booting times of instances and containers
    Region: str = _f("region", "")      # Related with the retrieving of booting times of instances and containers
    AppName: str = _f("app-name", "")   # For retrieving information about performance profiles
    MainServiceName: str = _f("main-service-name", "")  # Used in lots of places, unsure about the difference with AppName
    AppType: str = _f("app-type", "")   # For retrieving information about performance profiles
    PricingModel: PricingModel_ = _f("pricing-model", df=PricingModel_) # Budget and billing unit
    ForecastComponent: ForecastComponent_ = _f("forecasting-component", df=ForecastComponent_)  # Endpoint for forecast API
    PerformanceProfilesComponent: Component = _f("performance-profiles-component", df=Component) # Endpoint for profiles API 
    SchedulerComponent: Component = _f("scheduler-component", df=Component)                     # Endpoint for scheduler API
    ScalingHorizon: ScalingHorizon_ = _f("scaling-horizon", df=ScalingHorizon_)                 # Time window
    PreferredAlgorithm: str = _f("preferred-algorithm", "")                                     # "naive", etc... or "all"
    PolicySettings: PolicySettings_ = _f("policy-settings", df=PolicySettings_)                 # Currently not used
    PullingInterval: int = _f("pulling-interval", "")           # Timeslot between policies derivations
    StorageInterval: str = _f("storage-interval", "")           # Related to removal of temporal data

@dataclass_json
@dataclass
class StateLoadCapacity: # types/type_policies.go:111
    " Represent the number of requests for a time T"  # Still unused
    TimeStamp: datetime = _isodate("timestamp")
    Requests: float = _f("requests", 0.0)

@dataclass_json
@dataclass
class State: # types/type_policies.go:98
    "DesiredState is the metadata of the state expected to scale to"
    Services: Service = _f("services", df=lambda: Service({}))  # dictionary app-> ServiceInfo (CPUs, Mem, Replicas)
    Hash: str = _f("hash", "")                                  # ???
    VMs: VMScale = _f("vms", df=lambda: VMScale({}))            # Number of vms of each type
    # NOTE: apparently the particular mapping of containers to VMs is not stored anywhere
    # only the number of containers of each type (replicas) and the number of VMs of each type

@dataclass_json
@dataclass
class CriticalInterval: # types/types_forecasting.go:9
    """Critical Interval is the interval of time analyzed to take a scaling decision"""
    # These critical intervals are derived from the forecast
    # by the function aux_func.ScalingIntervals()
    TimeStart: datetime = _isodate("TimeStart")  
    Requests: float= _f("Requests", 0.0)  # //max/min point in the interval
    TimeEnd: datetime = _isodate("TimeEnd")
    TimePeak: datetime = _isodate(None)     # Not used/set?

@dataclass_json
@dataclass
class MSCSimpleSetting: # types/types_performance_profiles.go:51
    """This class gives the performance of a replicaset of containers of the same kind"""
    
    # Note that the number of replicas in the replicaset is another parameter
    # i.e. A replicaset with N replicas does not simply provides N times the performance
    # of a single replica (indeed, I --JLD-- checked that in the test data the rps
    # of a replicaset with N replicas is more than N times one replica, which does
    # not make much sense)

    # Retrieved from performance profiles endpoint
    Replicas: int = _f("replicas", 0)              # Number of containers in the replicaset
    MSCPerSecond: float = _f("maximum_service_capacity_per_sec", 0.0) # Performance
    BootTimeSec: float =  _f("pod_boot_time_sec", 0.0)                # Time required to boot
    StandDevBootTimeSec: float = _f("sd_pod_boot_time_ms", 0.0)       # std_dev of the booting time


@dataclass_json
@dataclass 
class Limit_: # types/types_performance_profiles.go:32
    # Limits for a container/pod
    CPUCores: float = _f("Cpu_cores", 0.0)  # Limit on the cpu usage, expressed in cores, eg: 0.2
    MemoryGB: float = _f("Mem_gb", 0.0)     # Limit on memory usage
    RequestPerSecond: int = _f("Request_per_second", 0) # Limit on rps? Apparently this field is never used and always 0

@dataclass_json
@dataclass
class ContainersConfig: # types/types_policies.go:224
    # This class is computed by aux_func.estimatePodsConfiguration() which returns
    # the configuration with number of replicas and limits that best fit for the number of requests
    Limits: Limit_ = _f("limits", df=Limit_)  # Limits for the CPUs and mem of the containers
    MSCSetting: MSCSimpleSetting = _f("mscs", df=MSCSimpleSetting)  # Performance data, number of replicas
    VMSet: VMScale = _f("vms", df=lambda: VMScale({}))              # Types and number of VMs
    Cost: float = _f("cost", 0.0)                                   # Unused (always zero)


@dataclass
class ProcessedForecast: # types/types_forecasting.go:33
    """ProcessedForecast metadata after processing the time series"""
    CriticalIntervals: list[CriticalInterval] = field(default_factory=list)


@dataclass_json
@dataclass
class PolicyMetrics: # types/types_policies.go:156
    # All this data is computed by policy.ComputePolicyMetrics()
    Cost: float = _f("cost", 0.0)                           # Cost of the VMs deployed in the interval
    OverProvision: float = _f("over_provision", 0.0)        # Average % per hour of overprovisioning
    UnderProvision: float = _f("under_provision", 0.0)      # Average % per hour of underprovisioning
    NumberScalingActions: int = _f("n_scaling_actions", 0)  # Number of changes in the VM type or number
    StartTimeDerivation: datetime = _isodate("start_derivation_time")   # timestamp of the starting of the solving algorithm
    FinishTimeDerivation: datetime = _isodate("finish_derivation_time") # timestamp of the ending of the solving algorithm
    DerivationDuration: float = _f("derivation_duration", 0.0)          # Number of seconds required by the solving algorithm
    NumberVMScalingActions: int = _f("num_scale_vms", 0)                # Same than NumberScalingActions (??)
    NumberContainerScalingActions: int = _f("num_scale_containers", 0)  # Number of changes in the type or number of containers
    AvgShadowTime: float = _f("avg_shadow_time_sec", 0.0)               # shadow time / number of scaling actions
    AvgTransitionTime: float = _f("avg_transition_time_sec", 0.0)       # transition time / number of scaling actions
    AvgElapsedTime: float = _f("avg_time_between_scaling_sec", 0.0)     # average time each scaling step is active


@dataclass_json
@dataclass
class ConfigMetrics: # types/types_policies.go:144
    # Metrics for each policy configuration (also computed by policy.ComputePolicyMetrics())
    Cost: float = _f("cost", 0.0)                           # Cost of the period the policy is active (rounded up to cents)
    OverProvision: float = _f("over_provision", 0.0)        # excess capacity divided by the number of hours with excess capacity
    UnderProvision: float = _f("under_provision", 0.0)      # capacity deficit divided by the number of hours with capacity deficit
    RequestsCapacity: float = _f("requests_capacity", 0.0)  # rph that the config can provide
    CPUUtilization: float = _f("cpu_utilization", 0.0)      # sum of cpus of the containers divided by the number of cpus of the VMs (%)
    MemoryUtilization: float = _f("mem_utilization", 0.0)   # sum of memory of the containers divided by the memory of the VMs (%)
    ShadowTimeSec: float = _f("shadow_time_sec", 0.0)       # amount of time overlap between one config and the next
    TransitionTimeSec: float = _f("transition_time_sec", 0.0) # amount of time in which previous config is still active while new config is booting
    ElapsedTimeSec: float = _f("elapsed_time_sec", 0.0)     # duration of the period


@dataclass_json
@dataclass
class ScalingAction: # types/types_policies.go
    TimeStartTransition: datetime = _isodate("time_start_transition")   # time in which the action must begin (taking into accout booting times)
    InitialState: State = _f("initial_state", df=State)                 # State (containers, vms) previous of the scaling action
    DesiredState: State = _f("desired_state", df=State)                 # State (containers, vms) after the scaling action
    TimeStart: datetime = _isodate("time_start")                        # Time in which the new state is operative
    TimeEnd: datetime = _isodate("time_end")                            # Time in which the new state should end
    Metrics: ConfigMetrics = _f("metrics", df=ConfigMetrics)            # Computed metrics (cost, utilization, etc)


@dataclass_json
@dataclass
class Policy: # types/types_policies.go:201
    """The policy is the output of the scaling algorithm"""
    ID: str = _f("id", df=lambda: str(ObjectId))                    # For storage in database
    Algorithm: str = _f("algorithm", "")                            # "naive", etc
    Metrics: PolicyMetrics = _f("metrics", df=PolicyMetrics)        # computed statistics about costs, overprovisioning, etc.
    Status: str = _f("status", "")                                  # "discarted", "scheduled", "selected"
    Parameters: dict[str,str] = _f("parameters", df=dict)           # extra parameters (vm types, scaling type, heterogeneus...)
    ScalingActions: list[ScalingAction] = _f("scaling_actions", df=list) # List of scaling actions
    TimeWindowStart: datetime = _isodate("window_time_start")       # time in which the policy begins to be applied
    TimeWindowEnd:   datetime = _isodate("window_time_end")         # time in which the policy ends


@dataclass_json
@dataclass
class PerformanceProfile:
    ID: str = _f("_id", df=lambda: str(ObjectId()))
    MSCSettings: list[MSCSimpleSetting] = _f("mscs", df=list)
    Limit: Limit_ = _f("limits", df=Limit_)

@dataclass_json
@dataclass
class MaxServiceCapacity: # types/types_performance_profiles.go:58
    Experimental   : float = _f("Experimental", 0.0)
    RegBruteForce  : float = _f("RegBruteForce", 0.0)
    RegSmart       : float = _f("RegSmart", 0.0)

@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class MSCCompleteSetting: # types/types_performance_profiles.go:77
    # Returned by GetPredictedReplicas()
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
    TimeStamp: datetime = _isodate("timestamp")
    Requests: float = _f("requests", 0.0)


# types/types_forecasting.go:23
@dataclass_json
@dataclass
class Forecast:
    """/*Set of values received from the Forecasting component*/"""
    IDdb: str = _f("id", df=lambda: str(ObjectId()))
    ServiceName: str = _f("service_name", "")
    ForecastedValues: list[ForecastedValue] = _f("values", df=list)
    TimeWindowStart: datetime = _isodate("start_time")
    TimeWindowEnd: datetime = _isodate("end_time")
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

@dataclass_json
@dataclass
class _Profile:
    Limits: Limit_ = _f("Limits", df=Limit_)
    MSCs: list[MSCCompleteSetting] = _f("MSCs", df=MSCCompleteSetting)


@dataclass_json
@dataclass
class ServicePerformanceProfile:
    HostInstanceType: str = _f("HostInstanceType", "")
    ServiceName: str = _f("ServiceName", "")
    MainServiceName: str = _f("MainServiceName", "")
    ServiceType: str = _f("ServiceType", "")
    TestAPI: str = _f("TestAPI", "")
    Profiles: list[_Profile] = _f("Profiles", df=_Profile)

@dataclass_json
@dataclass
class ServiceToSchedule:
    Scale: int = _f("Replicas", 0)
    CPU: str = _f("Cpu", "")
    Memory: int = _f("Memory")

ServicesSchedule = NewType("ServicesSchedule", dict[str, ServiceToSchedule])


@dataclass_json#(undefined=Undefined.EXCLUDE)
@dataclass
class StateToSchedule:
    LaunchTime: datetime = _isodate("ISODate")
    Services: ServicesSchedule = _f("Services", df=lambda: ServicesSchedule({}))
    Name: str = _f("Name", "")
    VMs: VMScale = _f("VMs", df=lambda: VMScale({}))
    ExpectedStart: datetime = _isodate("ExpectedTime")
    RealTime:  datetime = _isodate("RealTime")

@dataclass_json
@dataclass
class InfrastructureState:
    ActiveState: StateToSchedule = _f("active", df=StateToSchedule)
    LastDeployedState: StateToSchedule = _f("lastDeployed", df=StateToSchedule)
    isStateTrue: bool = _f("isStateTrue", False)
