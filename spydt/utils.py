from dataclasses import dataclass
import math
from datetime import datetime
from typing import List, Tuple
from .model import (
    Limit, ContainersConfig, Const, ScalingAction, State, Const, VMScale, VmProfile,
    SystemConfiguration, Error, MSCSimpleSetting
)

from .storage import GetPerformanceProfileDAO, GetPredictedReplicas

systemConfiguration = SystemConfiguration()  # TODO: ¿Por qué esta global?


# planner/derivation/policies_derivation.go:217
def estimatePodsConfiguration(requests:float, limits:Limit) -> Tuple[ContainersConfig, Error]:
    # return ContainersConfig(), Error()  # TODO
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
                print("Performance profile not updated")  # TODO: Logging
        else:
            return containerConfig, err
    return containerConfig, err

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


def setScalingSteps(scalingSteps: List[ScalingAction], 
                    currentState: State, newState: State, 
                    timeStart: datetime, timeEnd: datetime,
                    totalServicesBooting:float,
                    stateLoadCapacity:float) -> None:
    # This function returns None, because the scalingSteps are stored 
    # in-place in the first parameter
    # return None  # TODO

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
            ...
        """
        if  scalingSteps:
                shutdownVMDuration = computeVMTerminationTime(vmRemoved, systemConfiguration)
                previousTimeEnd = scalingSteps[-1].TimeEnd
                scalingSteps[-1].TimeEnd = previousTimeEnd + shutdownVMDuration
            startTransitionTime = computeScaleOutTransitionTime(vmAdded, True, timeStart, totalServicesBootingTime)
        
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


def DeltaVMSet(current: VMScale, candidate: VMScale) -> Tuple[VMScale, VMScale]:
    # TODO
    return (VMScale(), VMScale())
    """
	delta := types.VMScale{}
	startSet := types.VMScale{}
	shutdownSet := types.VMScale{}
	sameSet := types.VMScale{}

	for k,_ :=  range current {
		if _,ok := candidate[k]; ok {
			delta[k] = current[k] - candidate[k]
			if (delta[k] < 0) {
				startSet[k] = -1 * delta[k]
			} else if (delta[k] > 0) {
				shutdownSet[k] = delta[k]
			} else {
				sameSet[k] = current[k]
			}
		} else {
			shutdownSet[k] =  current[k]
		}
	}

	for k,_ :=  range candidate {
		if _,ok := current[k]; !ok {
			startSet[k] = candidate[k]
		}
	}
	return startSet, shutdownSet
    """