from dataclasses import dataclass
import math
import logging
from datetime import datetime, timedelta
from typing import Tuple

from dataclasses_json.api import C
from .model import (
    CriticalInterval, Forecast, ForecastedValue, Limit_, ContainersConfig, Const, ProcessedForecast, ScalingAction, State, Const, VMScale, VmProfile,
    SystemConfiguration, Error, MSCSimpleSetting, ConfigMetrics
)

from .storage import GetPerformanceProfileDAO, GetPredictedReplicas


log = logging.getLogger("spydt")

systemConfiguration = SystemConfiguration()  # FIX: ¿Por qué esta global?


# planner/derivation/policies_derivation.go:217
def estimatePodsConfiguration(requests:float, limits:Limit_) -> Tuple[ContainersConfig, Error]:
    """
    Select the service profile for a given container limit resources
    in:
        @requests	float64 - number of requests that the service should serve
        @limits types.Limits	- resource limits (cpu cores and memory gb) configured in the container
    out:
        @ContainersConfig	- configuration with number of replicas and limits that best fit for the number of requests
    """

    containerConfig = ContainersConfig()
    err = Error()
    serviceProfileDAO = GetPerformanceProfileDAO(systemConfiguration.MainServiceName)

    performanceProfileBase,_ = serviceProfileDAO.FindByLimitsAndReplicas(limits.CPUCores, limits.MemoryGB, 1)
    estimatedReplicas = int(math.ceil(requests / performanceProfileBase.MSCSettings[0].MSCPerSecond))
    performanceProfileCandidate,err1 = serviceProfileDAO.FindByLimitsAndReplicas(limits.CPUCores, limits.MemoryGB, estimatedReplicas)

    if not err1.error and performanceProfileCandidate.MSCSettings[0].MSCPerSecond >= requests:
        containerConfig.MSCSetting.Replicas = performanceProfileCandidate.MSCSettings[0].Replicas
        containerConfig.MSCSetting.MSCPerSecond = performanceProfileCandidate.MSCSettings[0].MSCPerSecond
        containerConfig.Limits = limits
    else:
        url = systemConfiguration.PerformanceProfilesComponent.Endpoint + Const.ENDPOINT_SERVICE_PROFILE_BY_MSC.value
        appName = systemConfiguration.AppName
        appType = systemConfiguration.AppType
        mainServiceName = systemConfiguration.MainServiceName
        mscSetting,err = GetPredictedReplicas(url,appName,appType,mainServiceName,requests,limits.CPUCores, limits.MemoryGB)
        if err.error:
            return containerConfig, err

        newMSCSetting = MSCSimpleSetting()
        if not err.error:
            containerConfig.MSCSetting.Replicas = mscSetting.Replicas
            containerConfig.MSCSetting.MSCPerSecond = mscSetting.MSCPerSecond.RegBruteForce
            containerConfig.Limits = limits

            newMSCSetting.Replicas = mscSetting.Replicas
            newMSCSetting.MSCPerSecond = mscSetting.MSCPerSecond.RegBruteForce
            if mscSetting.BootTimeMs > 0:
                newMSCSetting.BootTimeSec = MillisecondsToSeconds(mscSetting.BootTimeMs)
            else:
                newMSCSetting.BootTimeSec = Const.DEFAULT_POD_BOOT_TIME.value
            profile, err3 = serviceProfileDAO.FindByLimitsAndReplicas(limits.CPUCores, limits.MemoryGB, mscSetting.Replicas)
            if not err3.error: 
                profile,_= serviceProfileDAO.FindProfileByLimits(limits)
                profile.MSCSettings.append(newMSCSetting)
                err3 = serviceProfileDAO.UpdateById(profile.ID, profile)
            else:
                log.error("Performance profile not updated")
        else:
            log.error(f"{err.error}")
            return containerConfig, err
    return containerConfig, err

# planner/derivation/policies_derivation.go:554
def adjustGranularity(granularity: str, capacityInSeconds: float) -> float:
    # planner/derivation/policies_derivation.go:554
    factor = 3600.0
    if granularity == Const.HOUR:
        factor = 3600
    elif granularity == Const.MINUTE:
        factor = 60
    elif granularity == Const.SECOND:
        factor = 1
    return factor*capacityInSeconds

# planner/derivation/miscellaneous.go:94
def DeltaVMSet(current:VMScale, candidate:VMScale) -> Tuple[VMScale,VMScale]:
    """
    compare the changes (vms added, vms removed) from one VM set to a candidate VM set
    in:
        @current	- Map with current VM cluster
        @candidate	- Map with candidate VM cluster
    out:
        @VMScale	- Map with VM cluster of the VMs that were added into the candidate VM set
        @VMScale	- Map with VM cluster of the VMs that were removed from the candidate VM set
    """
    delta = VMScale({})
    startSet = VMScale({})
    shutdownSet = VMScale({})
    sameSet = VMScale({})

    for k in current: 
        if k in candidate:
            delta[k] = current[k] - candidate[k]
            if delta[k] < 0:
                startSet[k] = -delta[k]
            elif delta[k] > 0:
                shutdownSet[k] = delta[k]
            else:
                sameSet[k] = current[k]   # ??? sameSet is never used
        else:
            shutdownSet[k] =  current[k]
    for k in candidate:
        if k in current:
            startSet[k] = candidate[k]
    return startSet, shutdownSet

# planner/derivation/policies_derivation.go:526
def  computeScaleOutTransitionTime(vmAdded: VMScale, podResize: bool, timeStart: datetime, podsBootingTime: float) -> datetime:
    """
    Calculate base on the expected start time for the new state, when the launch should start
    in:
        @vmAdded types.VMScale
                            - map of VM that were added
        @timeStart time.Time
                            - time when the desired state should start
    out:
        @time.Time	- Time when the launch should start
    """
    transitionTime = timeStart
    # Time to boot new VMS
    if vmAdded:
        # Case 1: New VMs
        bootTimeVMAdded = computeVMBootingTime(vmAdded, systemConfiguration)
        transitionTime = timeStart - timedelta(seconds=bootTimeVMAdded)
        # Time for add new VMS into k8s cluster
        transitionTime = transitionTime - timedelta(seconds=Const.TIME_ADD_NODE_TO_K8S.value)
        # Time to boot pods assuming worst scenario, when image has to be pulled
        transitionTime = transitionTime - timedelta(seconds=podsBootingTime)
    else:
        # Case: Only replication of pods
        transitionTime = transitionTime - timedelta(seconds=Const.TIME_CONTAINER_START.value)
    return transitionTime

# planner/derivation/policies_derivation.go:128 TODO: access to database or mock it
def computeVMBootingTime(vmsScale: VMScale, sysConfiguration: SystemConfiguration) -> float:
    """
    Compute the booting time that will take a set of VMS
    in:
        @vmsScale types.VMScale
        @sysConfiguration SystemConfiguration
    out:
        @int	Time in seconds that the booting wil take
    """
    log.warning(f"computeVMBootingTime() NOT IMPLEMENTED, returning booting time = 0 for {vmsScale}")
    bootTime = 0.0
    """
    # Check in db if already data is stored
    vmBootingProfileDAO := storage.GetVMBootingProfileDAO()

    //Call API
    for vmType, n := range vmsScale {
        times, err := vmBootingProfileDAO.BootingShutdownTime(vmType, n)
        if err != nil {
            url := sysConfiguration.PerformanceProfilesComponent.Endpoint + util.ENDPOINT_VM_TIMES
            csp := sysConfiguration.CSP
            region := sysConfiguration.Region
            times, err = performance_profiles.GetBootShutDownProfileByType(url,vmType, n, csp, region)
            if err != nil {
                log.Error("Error in bootingTime query  type %s %d VMS. Details: %s", vmType, n, err.Error())
                log.Warning("Takes the biggest time available")
                times.BootTime = util.DEFAULT_VM_BOOT_TIME
            }else {
                vmBootingProfile,_ := vmBootingProfileDAO.FindByType(vmType)
                vmBootingProfile.InstancesValues = append(vmBootingProfile.InstancesValues, times)
                vmBootingProfileDAO.UpdateByType(vmType, vmBootingProfile)
            }
        }
        bootTime += times.BootTime
    }
    """
    return bootTime

# planner/derivation/policies_derivation.go:164 TODO: access database or mock it
def computeVMTerminationTime(vmsScale: VMScale, sysConfiguration: SystemConfiguration) -> float:
    """
    Compute the termination time of a set of VMs
    in:
        @vmsScale types.VMScale
        @sysConfiguration SystemConfiguration
    out:
        @int	Time in seconds that the termination wil take
    """
    log.warning("NOT IMPLEMENTED, returning termination time = 0")
    terminationTime = 0.0
    # Check in db if already data is stored
    """
    vmBootingProfileDAO := storage.GetVMBootingProfileDAO()

    //Call API
    for vmType, n := range vmsScale {
        times, err := vmBootingProfileDAO.BootingShutdownTime(vmType, n)
        if err != nil {
            url := sysConfiguration.PerformanceProfilesComponent.Endpoint + util.ENDPOINT_VM_TIMES
            csp := sysConfiguration.CSP
            region := sysConfiguration.Region
            times, err = performance_profiles.GetBootShutDownProfileByType(url,vmType, n, csp, region)
            if err != nil {
                log.Error("Error in terminationTime query for type %s %d VMS. Details: %s", vmType, n, err.Error())
                log.Warning("Takes default shutdown")
                times.ShutDownTime = util.DEFAULT_VM_SHUTDOWN_TIME
            } else {
                vmBootingProfile,_ := vmBootingProfileDAO.FindByType(vmType)
                vmBootingProfile.InstancesValues = append(vmBootingProfile.InstancesValues, times)
                vmBootingProfileDAO.UpdateByType(vmType, vmBootingProfile)
            }
        }
        terminationTime += times.ShutDownTime
    }
    """
    return terminationTime

# planner/derivation/policies_derivation.go:349
def setScalingSteps(scalingSteps: list[ScalingAction], 
                    currentState: State, newState: State, 
                    timeStart: datetime, timeEnd: datetime,
                    totalServicesBootingTime: float,
                    stateLoadCapacity:float) -> None:
    # This function returns None, because the scalingSteps are stored 
    # in-place in the first parameter

    if scalingSteps and newState == scalingSteps[-1].DesiredState:
        scalingSteps[-1].TimeEnd = timeEnd
    else:
        # var deltaTime int //time in seconds
        shutdownVMDuration = 0.0
        startTransitionTime = datetime.now()
        currentVMSet = VMScale({})
        currentVMSet = currentState.VMs
        vmAdded, vmRemoved = DeltaVMSet(currentVMSet, newState.VMs)
        nVMRemoved = len(vmRemoved)
        nVMAdded = len(vmAdded)

        if vmRemoved and vmAdded:
            # case 1: There is an overlaping of configurations
            if  scalingSteps:
                shutdownVMDuration = computeVMTerminationTime(vmRemoved, systemConfiguration)
                previousTimeEnd = scalingSteps[-1].TimeEnd
                scalingSteps[-1].TimeEnd = previousTimeEnd + timedelta(seconds=shutdownVMDuration)
            startTransitionTime = computeScaleOutTransitionTime(vmAdded, True, timeStart, totalServicesBootingTime)
        elif vmRemoved and not vmAdded:
            # case 2:  Scale in,
            shutdownVMDuration = computeVMTerminationTime(vmRemoved, systemConfiguration)
            startTransitionTime = timeStart - timedelta(seconds=shutdownVMDuration)
        elif (not vmRemoved and vmAdded) or (not vmRemoved and not vmAdded): # FIX: is this simply (not vmRemoved) ?
            # case 3: Scale out
            startTransitionTime = computeScaleOutTransitionTime(vmAdded, True, timeStart, totalServicesBootingTime)

        # // newState.LaunchTime = startTransitionTime
        # 
        """
        name,_ := structhash.Hash(newState, 1)  # TODO: compute appropriate hash (?) (what is it used for?)
        newState.Hash = strings.Replace(name, "v1_", "", -1)
        """
        scalingSteps.append(ScalingAction(
            InitialState=currentState,
            DesiredState=newState,
            TimeStart=timeStart,
            TimeEnd=timeEnd,
            Metrics=ConfigMetrics(RequestsCapacity=stateLoadCapacity),
            TimeStartTransition=startTransitionTime,
        ))

def maxPodsCapacityInVM(vmProfile: VmProfile, resourceLimit: Limit_) -> int:
    # For memory resources, Kubernetes Engine reserves aprox 6% of cores and 25% of Mem
    cpuCoresAvailable = vmProfile.CPUCores  * (1 - Const.PERCENTAGE_REQUIRED_k8S_INSTALLATION_CPU.value)
    memGBAvailable = vmProfile.Memory * (1 - Const.PERCENTAGE_REQUIRED_k8S_INSTALLATION_MEM.value)

    m = cpuCoresAvailable / resourceLimit.CPUCores
    n = memGBAvailable / resourceLimit.MemoryGB
    numReplicas = min(n,m)
    return int(numReplicas)

def MillisecondsToSeconds(m: float) -> float:
    return m/1000

def memBytesToGB(value: int) -> float:
    memFloat = float(value) / 1000000000
    return memFloat

def stringToCPUCores(value: str) -> float:
    try:
        return float(value.replace("m", ""))/1000
    except:
        return 0.0


# planner/forecast_processing/forecast-processing.go:9
def ScalingIntervals(forecast: Forecast, granularity: str) -> ProcessedForecast:
    factor = 3600.0

    if granularity == Const.MINUTE.value:
        factor = 60
    elif granularity == Const.SECOND.value:
        factor = 1

    intervals:list[CriticalInterval] = []
    i= 0
    lenValues = len(forecast.ForecastedValues)
    value = forecast.ForecastedValues[0]
    interval = CriticalInterval(
        Requests= value.Requests / factor,
        TimeStart=value.TimeStamp,
        TimeEnd=value.TimeStamp,
    )
    intervals.append(interval)

    for i in range(lenValues-1):
        value = forecast.ForecastedValues[i]
        startTimestamp = value.TimeStamp
        highestPeak = value.Requests
        nextValue: ForecastedValue
        endTimestamp: datetime

        while True:
            nextValue = forecast.ForecastedValues[i+1]
            aux = nextValue.TimeStamp - startTimestamp

            endTimestamp = forecast.ForecastedValues[i+1].TimeStamp
            if aux.total_seconds() < 300:
                highestPeak = (highestPeak + forecast.ForecastedValues[i+1].Requests)/2
            i+=1
            if aux.total_seconds() >= 300:
                break

        interval = CriticalInterval(
            Requests=highestPeak/factor,
            TimeStart=startTimestamp,
            TimeEnd=endTimestamp,
            )
        intervals.append(interval)

    processedForecast = ProcessedForecast(CriticalIntervals=intervals)
    return  processedForecast


# planner/derivation/miscellaneous.go:136
def MapKeysToString(keys: dict[str, bool]) -> str:
    return ",".join(keys)
