from dataclasses import dataclass
import math
from datetime import datetime, timedelta
from typing import Tuple
from .model import (
    Limit, ContainersConfig, Const, ScalingAction, State, Const, VMScale, VmProfile,
    SystemConfiguration, Error, MSCSimpleSetting
)

from .storage import GetPerformanceProfileDAO, GetPredictedReplicas

systemConfiguration = SystemConfiguration()  # TODO: ¿Por qué esta global?


# planner/derivation/policies_derivation.go:217
def estimatePodsConfiguration(requests:float, limits:Limit) -> Tuple[ContainersConfig, Error]:
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
                print("Performance profile not updated")  # FIX: Logging
        else:
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
    delta = VMScale()
    startSet = VMScale()
    shutdownSet = VMScale()
    sameSet = VMScale()

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

# planner/derivation/policies_derivation.go:349 TODO WIP
def setScalingSteps(scalingSteps: list[ScalingAction], 
                    currentState: State, newState: State, 
                    timeStart: datetime, timeEnd: datetime,
                    totalServicesBooting:float,
                    stateLoadCapacity:float) -> None:
    # This function returns None, because the scalingSteps are stored 
    # in-place in the first parameter

    if scalingSteps and newState == scalingSteps[-1].DesiredState:
        scalingSteps[-1].TimeEnd = timeEnd
    else:
        # var deltaTime int //time in seconds
        shutdownVMDuration = 0.0
        startTransitionTime = datetime.now()
        currentVMSet = VMScale()
        currentVMSet = currentState.VMs
        vmAdded, vmRemoved = DeltaVMSet(currentVMSet, newState.VMs)
        nVMRemoved = len(vmRemoved)
        nVMAdded = len(vmAdded)

        if vmRemoved and vmAdded:
            # case 1: There is an overlaping of configurations
            if  scalingSteps:
                shutdownVMDuration = computeVMTerminationTime(vmRemoved, systemConfiguration)
                previousTimeEnd = scalingSteps[-1].TimeEnd
                scalingSteps[-1].TimeEnd = previousTimeEnd + shutdownVMDuration
            startTransitionTime = computeScaleOutTransitionTime(vmAdded, True, timeStart, totalServicesBootingTime)
        """        
        } else if nVMRemoved > 0 && nVMAdded == 0 {
            //case 2:  Scale in,
            shutdownVMDuration = computeVMTerminationTime(vmRemoved, systemConfiguration)
            startTransitionTime = timeStart.Add(-1 * time.Duration(shutdownVMDuration) * time.Second)

        } else if (nVMRemoved == 0 && nVMAdded > 0) || ( nVMRemoved == 0 && nVMAdded == 0 ) {
            //case 3: Scale out
            startTransitionTime = computeScaleOutTransitionTime(vmAdded, true, timeStart, totalServicesBootingTime)
        }

        //newState.LaunchTime = startTransitionTime
        name,_ := structhash.Hash(newState, 1)
        newState.Hash = strings.Replace(name, "v1_", "", -1)
        *scalingSteps = append(*scalingSteps,
            types.ScalingAction{
                InitialState:currentState,
                DesiredState:        newState,
                TimeStart:           timeStart,
                TimeEnd:             timeEnd,
                Metrics:             types.ConfigMetrics{RequestsCapacity:stateLoadCapacity,},
                TimeStartTransition: startTransitionTime,
            })
    }
    """

def maxPodsCapacityInVM(vmProfile: VmProfile, resourceLimit: Limit) -> int:
    # For memory resources, Kubernetes Engine reserves aprox 6% of cores and 25% of Mem
    cpuCoresAvailable = vmProfile.CPUCores  * (1 - Const.PERCENTAGE_REQUIRED_k8S_INSTALLATION_CPU.value)
    memGBAvailable = vmProfile.Memory * (1 - Const.PERCENTAGE_REQUIRED_k8S_INSTALLATION_MEM.value)

    m = cpuCoresAvailable / resourceLimit.CPUCores
    n = memGBAvailable / resourceLimit.MemoryGB
    numReplicas = min(n,m)
    return int(numReplicas)

def MillisecondsToSeconds(m: float) -> float:
    return m/1000

