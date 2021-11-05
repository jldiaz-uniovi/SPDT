from dataclasses import dataclass
import math
import logging
from datetime import datetime, timedelta
from typing import Tuple

from dataclasses_json.api import C

from . import mock_storage
from .model import (
    CriticalInterval, Forecast, ForecastedValue, Limit_, ContainersConfig, Const, ProcessedForecast, ScalingAction, State, Const, VMScale, VmProfile,
    SystemConfiguration, Error, MSCSimpleSetting, ConfigMetrics
)

from .storage import GetPerformanceProfileDAO, GetPredictedReplicas, GetVMBootingProfileDAO


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
    if not performanceProfileBase.MSCSettings:
        errmsg = f"No MSCs available for reqouests={requests}, limits={limits}"
        log.error(errmsg)
        return containerConfig, Error(errmsg)
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
            errmsg = f"GetPredictedReplicas() returned empty {mscSetting=}"
            log.error(errmsg)
            return containerConfig, Error(errmsg)

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
        if k not in current:
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
    bootTime = 0.0
    # Check in db if already data is stored (TODO)    
    vmBootingProfileDAO = GetVMBootingProfileDAO()


    for vmType, n in vmsScale.items():
        times, err = vmBootingProfileDAO.BootingShutdownTime(vmType, n)
        if err.error:
            url = sysConfiguration.PerformanceProfilesComponent.Endpoint + Const.ENDPOINT_VM_TIMES.value
            csp = sysConfiguration.CSP
            region = sysConfiguration.Region
            times, err = mock_storage.GetBootShutDownProfileByType(url, vmType, n, csp, region)
            if err.error:
                log.error(f"Error in bootingTime query  type {vmType} {n} VMS. Details: {err.error}")
                times.BootTime = Const.DEFAULT_VM_BOOT_TIME.value
                log.warning(f"Takes the biggest time available {times.BootTime}")
            else:
                vmBootingProfile, err = vmBootingProfileDAO.FindByType(vmType)
                vmBootingProfile.InstancesValues.append(times)
                vmBootingProfileDAO.UpdateByType(vmType, vmBootingProfile)        
        bootTime += times.BootTime
    log.debug(f"computeVMBootingTime({vmsScale}) returning {bootTime}")
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
    terminationTime = 0.0
        # Check in db if already data is stored (TODO)    
    vmBootingProfileDAO = GetVMBootingProfileDAO()


    for vmType, n in vmsScale.items():
        times, err = vmBootingProfileDAO.BootingShutdownTime(vmType, n)
        if err.error:
            url = sysConfiguration.PerformanceProfilesComponent.Endpoint + Const.ENDPOINT_VM_TIMES.value
            csp = sysConfiguration.CSP
            region = sysConfiguration.Region
            times, err = mock_storage.GetBootShutDownProfileByType(url, vmType, n, csp, region)
            if err.error:
                log.error(f"Error in terminationTime query for type {vmType} {n} VMS. Details: {err.error}")
                times.ShutDownTime = Const.DEFAULT_VM_SHUTDOWN_TIME.value
                log.warning(f"Takes the default shutdown {times.ShutDownTime}")
            else:
                vmBootingProfile, err = vmBootingProfileDAO.FindByType(vmType)
                vmBootingProfile.InstancesValues.append(times)
                vmBootingProfileDAO.UpdateByType(vmType, vmBootingProfile)        
        terminationTime += times.ShutDownTime
    log.debug(f"computeVMTerminationime({vmsScale}) returning {terminationTime}")
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
        startTransitionTime = datetime.fromtimestamp(0)
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
        name,_ := structhash.Hash(newState, 1)  # TO-DO: compute appropriate hash (?) (what is it used for?)
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

    while i < lenValues-1:
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



# planner/derivation/policies_derivation.go:478
def buildHomogeneousVMSet(numberReplicas: int, limits: Limit_, mapVMProfiles: dict[str, VmProfile]) -> Tuple[VMScale,Error]:
    """/* Build Homogeneous cluster to deploy a number of replicas, each one with the defined constraint limits
        in:
            @numberReplicas	int - number of replicas
            @limits bool types.Limits - limits constraints(cpu cores and memory gb) per replica
            @mapVMProfiles - map with the profiles of VMs available
        out:
            @VMScale	- Map with the type of VM as key and the number of vms as value
    */"""
    err = Error()
    candidateVMSets: list[VMScale] = []
    for v in mapVMProfiles.values():
        vmScale =  VMScale({})
        replicasCapacity =  maxPodsCapacityInVM(v, limits)
        if replicasCapacity > 0:
            numVMs = math.ceil(numberReplicas / replicasCapacity)
            vmScale[v.Type] = int(numVMs)
            candidateVMSets.append(vmScale)

    if candidateVMSets:
        return min(candidateVMSets, key=lambda x: (VMScaleCost(x, mapVMProfiles), VMScaleTotalVms(x))), err
    else:
        return VMScale({}), Error("No VM Candidate")


# planner/derivation/policies_derivation.go:273
def selectProfileUnderVMLimits(requests: float,  limits: Limit_) -> Tuple[ContainersConfig, Error]:
    """/* Select the service profile for any limit resources that satisfies the number of requests
        in:
            @requests	float64 - number of requests that the service should serve
        out:
            @ContainersConfig	- configuration with number of replicas and limits that best fit for the number of requests
    */
    """
    profiles: list[ContainersConfig] = []
    profile = ContainersConfig()
    serviceProfileDAO = GetPerformanceProfileDAO(systemConfiguration.MainServiceName)
    profiles,err2 = serviceProfileDAO.MatchProfileFitLimitsOver(limits.CPUCores, limits.MemoryGB, requests)
    if not profiles:
        msg = f"No profile found for {requests=}, {limits=}"
        log.error(msg)
        return profile, Error(msg)
    if err2.error:
        log.error(f"MatchProfileFitLimitsOver() returned error {err2.error!r}")
        return profile, err2
    
    return (min(profiles, key=lambda x: (abs(requests-x.MSCSetting.MSCPerSecond), 
                                            x.MSCSetting.Replicas * x.Limits.CPUCores + x.MSCSetting.Replicas * x.Limits.MemoryGB,
                                            x.MSCSetting.Replicas)),
            Error())
    """
        sort.Slice(profiles, func(i, j int) bool {
            utilizationFactori := float64(profiles[i].MSCSetting.Replicas) * profiles[i].Limits.CPUCores +  float64(profiles[i].MSCSetting.Replicas) * profiles[i].Limits.MemoryGB
            utilizationFactorj := float64(profiles[j].MSCSetting.Replicas) * profiles[j].Limits.CPUCores + float64(profiles[j].MSCSetting.Replicas) * profiles[j].Limits.MemoryGB
            msci := profiles[i].MSCSetting.MSCPerSecond
            mscj := profiles[j].MSCSetting.MSCPerSecond
            if msci == mscj {
                if utilizationFactori != utilizationFactorj {
                    return utilizationFactori < utilizationFactorj
                } else {
                    return 	profiles[i].MSCSetting.Replicas < profiles[j].MSCSetting.Replicas
                }
            }
            return   math.Abs(requests - msci) <  math.Abs(requests - mscj)
        })
    }
    """



def getStateLoadCapacity(numberReplicas: int, limits: Limit_) -> MSCSimpleSetting:
    """/* Select the service profile for any limit resources that satisfies the number of requests
        in:
            @numberReplicas	int - number of replicas
            @limits bool types.Limits - limits constraints(cpu cores and memory gb) per replica
        out:
            @float64	- Max number of request for this containers configuration
    */"""
    serviceProfileDAO = GetPerformanceProfileDAO(systemConfiguration.MainServiceName)
    profile,_ = serviceProfileDAO.FindByLimitsAndReplicas(limits.CPUCores, limits.MemoryGB, numberReplicas)
    if profile.MSCSettings:
        return profile.MSCSettings[0]
    else:
        # TODO
        log.warning(f"getStateLoadCapacity({numberReplicas=}, {limits=}) not found. INCOMPLETE IMPLEMENTATION, returning empty MSCSimpleSetting")
        return  MSCSimpleSetting()
        """
        url := systemConfiguration.PerformanceProfilesComponent.Endpoint + util.ENDPOINT_SERVICE_PROFILE_BY_REPLICAS
        appName := systemConfiguration.AppName
        appType := systemConfiguration.AppType
        mainServiceName := systemConfiguration.MainServiceName
        mscCompleteSetting,_ := performance_profiles.GetPredictedMSCByReplicas(url,appName,appType,mainServiceName,numberReplicas,limits.CPUCores, limits.MemoryGB)
        newMSCSetting = types.MSCSimpleSetting{
            MSCPerSecond:mscCompleteSetting.MSCPerSecond.RegBruteForce,
            BootTimeSec:mscCompleteSetting.BootTimeMs,
            Replicas:mscCompleteSetting.Replicas,
            StandDevBootTimeSec:mscCompleteSetting.StandDevBootTimeMS/1000,
        }
        if newMSCSetting.BootTimeSec == 0 {
            newMSCSetting.BootTimeSec = util.DEFAULT_POD_BOOT_TIME
        }
        //update in db

        profile,_:= serviceProfileDAO.FindByLimitsAndReplicas(limits.CPUCores, limits.MemoryGB, numberReplicas)
        if profile.ID == "" {
            profile,_= serviceProfileDAO.FindProfileByLimits(limits)
            profile.MSCSettings = append(profile.MSCSettings,newMSCSetting)
            err3 := serviceProfileDAO.UpdateById(profile.ID, profile)
            if err3 != nil{
                log.Error("Performance profile not updated")
            }
        }
    }
    //defer serviceProfileDAO.Session.Close()
    return newMSCSetting
    """


def computeVMsCapacity(limits: Limit_,  mapVMProfiles: dict[str, VmProfile]):
    """/* Compute the maximum capacity regarding the number of replicas hosted in each VM type
        in:
            @limits
            @mapVMProfiles
    */"""
    for k, v in mapVMProfiles.items():
        cap = maxPodsCapacityInVM(v, limits)
        mapVMProfiles[v.Type].ReplicasCapacity = cap



def VMScaleCost(vmScale: VMScale, mapVMProfiles: dict[str, VmProfile]) -> float:
    return sum(mapVMProfiles[k]._Pricing.Price * v for k,v in vmScale.items())

def VMScaleTotalVms(vmScale: VMScale) -> int:
    return sum(vmScale.values())

# /*Function that calculates the capacity to host service replicas for a VM Set*/
def ReplicasCapacity(vmSet: VMScale, mapVMProfiles: dict[str, VmProfile]) -> int:
    return sum(mapVMProfiles[k].ReplicasCapacity * v for k,v in vmSet.items())

