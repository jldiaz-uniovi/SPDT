import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from os import sysconf
from typing import Tuple

from bson.objectid import ObjectId  # type: ignore

from . import aux_func, storage
from .abstract_classes import AbstractPolicy
from .model import (Const, ContainersConfig, CriticalInterval, Error, Limit_,
                    MSCSimpleSetting, Policy, PolicyMetrics, ProcessedForecast,
                    ScalingAction, Service, ServiceInfo, State, VmProfile,
                    VMScale)

log = logging.getLogger("spydt")

@dataclass
class ResizeWhenBeneficialPolicy(AbstractPolicy):
    sortedVMProfiles: list[VmProfile] = field(default_factory=list)

    # planner/derivation/algo_resize_when_beneficial.go:135
    def FindSuitableVMs(self, numberReplicas:int, limits: Limit_) -> VMScale:
        vmSet, _ = aux_func.buildHomogeneousVMSet(numberReplicas, limits, self.mapVMProfiles)
        # log.info(f"FindSuitableVMs({numberReplicas=}, {limits=}")
        # log.info(f" {self.mapVMProfiles=}---> {vmSet=}")
        return vmSet    

    # planner/derivation/algo_resize_when_beneficial.go:33
    def CreatePolicies(self, processedForecast: ProcessedForecast) -> list[Policy]:
        """/* Derive a list of policies
        Add vmSet to handle delta load and compare the reconfiguration cost against the vmSet
        optimized for a total load.
            in:
                @processedForecast
                @serviceProfile
            out:
                [] Policy. List of type Policy
        */"""
        log.info(f"Derive policies with {self.algorithm} algorithm")
        policies: list[Policy] = []
        newPolicy = Policy()
        newPolicy.Metrics = PolicyMetrics (StartTimeDerivation=datetime.now())

        configurations: list[ScalingAction] = []
        biggestVM = self.sortedVMProfiles[-1]
        vmLimits = Limit_(MemoryGB=biggestVM.Memory, CPUCores=biggestVM.CPUCores)

        for i, it in enumerate(processedForecast.CriticalIntervals):
            resourcesConfiguration = ContainersConfig()

            # //Load in terms of number of requests
            totalLoad = it.Requests
            serviceToScale = self.currentState.Services[self.sysConfiguration.MainServiceName]
            currentPodLimits = Limit_(MemoryGB=serviceToScale.Memory, CPUCores=serviceToScale.CPU)
            currentNumPods = serviceToScale.Scale
            currentLoadCapacity = aux_func.getStateLoadCapacity(currentNumPods, currentPodLimits).MSCPerSecond
            deltaLoad = totalLoad - currentLoadCapacity

            if deltaLoad == 0: 
                # //case 0: Keep current resource configuration
                resourcesConfiguration.VMSet = self.currentState.VMs
                resourcesConfiguration.Limits = currentPodLimits
                resourcesConfiguration.MSCSetting = MSCSimpleSetting(MSCPerSecond=currentLoadCapacity, Replicas=currentNumPods)
            else:
                if deltaLoad > 0:
                    # //case 1: Need to increase resources
                    rConfigDeltaLoad = self.onlyDeltaScaleOut(totalLoad, currentPodLimits)
                    resourceConfigTLoad = self.resize(totalLoad, currentPodLimits, vmLimits)

                    # //Test if reconfigure the complete VM set for the totalLoad is better
                    newConfig, ok = self.shouldRepackVMSet(rConfigDeltaLoad, resourceConfigTLoad, i, processedForecast.CriticalIntervals)
                    if ok:
                        resourcesConfiguration = newConfig
                    else:
                        resourcesConfiguration = rConfigDeltaLoad
                elif deltaLoad < 0:
                    # case 2: Need to decrease resources
                    rConfigDeltaLoad = self.onlyDeltaScaleIn(totalLoad, currentPodLimits, currentNumPods)
                    resourceConfigTLoad = self.resize(totalLoad, currentPodLimits, vmLimits)

                    # //Test if reconfigure the complete VM set for the totalLoad is better
                    newConfig,ok = self.shouldRepackVMSet(rConfigDeltaLoad, resourceConfigTLoad, i, processedForecast.CriticalIntervals)
                    if ok:
                        resourcesConfiguration = newConfig
                    else:
                        resourcesConfiguration = rConfigDeltaLoad

            services = Service({})
            services[self.sysConfiguration.MainServiceName] = ServiceInfo(
                Scale=resourcesConfiguration.MSCSetting.Replicas,
                CPU=resourcesConfiguration.Limits.CPUCores,
                Memory=resourcesConfiguration.Limits.MemoryGB,
            )

            # //Create a new state
            state = State()
            state.Services = services
            vmSet = resourcesConfiguration.VMSet
            vmSet = VMScale({ k: v for k,v in vmSet.items() if v != 0 })
            state.VMs = vmSet
            timeStart = it.TimeStart
            timeEnd = it.TimeEnd
            totalServicesBootingTime = resourcesConfiguration.MSCSetting.BootTimeSec
            stateLoadCapacity = resourcesConfiguration.MSCSetting.MSCPerSecond
            stateLoadCapacity = aux_func.adjustGranularity(self.sysConfiguration.ForecastComponent.Granularity, stateLoadCapacity)
            aux_func.setScalingSteps(configurations, self.currentState, state, timeStart, timeEnd, totalServicesBootingTime, stateLoadCapacity)
            # //Update current state
            self.currentState = state

        # //Add new policy
        parameters: dict[str, str] = {}
        parameters[Const.METHOD.value] = Const.SCALE_METHOD_HORIZONTAL.value
        parameters[Const.ISHETEREOGENEOUS.value] = str(True)
        parameters[Const.ISRESIZEPODS.value] = str(True)
        numConfigurations = len(configurations)
        newPolicy.ScalingActions = configurations
        newPolicy.Algorithm = self.algorithm
        newPolicy.ID = str(ObjectId())
        newPolicy.Status = Const.DISCARTED.value     #//State by default
        newPolicy.Parameters = parameters
        newPolicy.Metrics.FinishTimeDerivation = datetime.now()
        newPolicy.TimeWindowStart = configurations[0].TimeStart
        newPolicy.TimeWindowEnd = configurations[-1].TimeEnd
        policies.append(newPolicy)

        return policies

    # planner/derivation/algo_resize_when_beneficial.go:146
    def releaseVMs(self, vmSet:VMScale, numberPods:int, limits:Limit_) -> VMScale:
        aux_func.computeVMsCapacity(limits, self.mapVMProfiles)

        currentVMSet = VMScale(vmSet)  # make a copy
        newVMSet =  VMScale({})

        # //Creates a list sorted by the number of machines per type
        listMaps: list[Tuple[str, int]] = sorted(currentVMSet.items(), key=lambda x: x[1])

        for key, value in listMaps:
            i=0
            cap = self.mapVMProfiles[key].ReplicasCapacity
            while i < value and numberPods > 0:
                numberPods = numberPods - cap
                if key not in newVMSet:
                    newVMSet[key] = 0
                newVMSet[key] = newVMSet[key] + 1
                i+=1            
            if numberPods <= 0:
                break

        return newVMSet

    # planner/derivation/algo_resize_when_beneficial.go:188
    def calculateReconfigurationCost(self, newSet: VMScale) -> float:
        """/* Calculate the cost of a reconfiguration
        in:
            @newSet =  Target VM set
        out:
            @float64 Cost of the transition from the  current vmSet to the newSet
        */"""
        # //Compute reconfiguration cost
        _, deletedVMS = aux_func.DeltaVMSet(self.currentState.VMs, newSet)
        reconfigTime = aux_func.computeVMTerminationTime(deletedVMS, self.sysConfiguration)

        return aux_func.VMScaleCost(deletedVMS, self.mapVMProfiles) * reconfigTime

    # planner/derivation/algo_resize_when_beneficial.go:214
    def  shouldRepackVMSet(self, currentOption: ContainersConfig, candidateOption: ContainersConfig, 
            indexTimeInterval: int, timeIntervals: list[CriticalInterval]) -> Tuple[ContainersConfig, bool]:
        """/* Evaluate if the current configuration of VMS should be changed to a new configuration
        in:
            @currentOption =  Configuration to handle extra delta load
            @candidateOption = Configuration to handle total load
            @indexTimeInterval = index in the time window
            @timeIntervals = forecasted values
        out:
            @ContainersConfig = chosen configuration
            @bool = flag to indicate whether reconfiguration should be performed
        */"""
        currentCost = aux_func.VMScaleCost(currentOption.VMSet, self.mapVMProfiles)
        candidateCost = aux_func.VMScaleCost(candidateOption.VMSet, self.mapVMProfiles)

        if candidateCost <= currentCost:
            # //By default the transition policy would be to shut down VMs after launch new ones
            # //Calculate reconfiguration time
            timeStart = timeIntervals[indexTimeInterval].TimeStart
            timeEnd:datetime = datetime.fromisoformat("1970-01-01 00:00:00+00:00")
            idx = indexTimeInterval
            lenInterval = len(timeIntervals)
            # //Compute duration for new set
            candidateLoadCapacity = candidateOption.MSCSetting.MSCPerSecond
            while idx < lenInterval:
                if timeIntervals[idx].Requests > candidateLoadCapacity:
                    timeEnd = timeIntervals[idx].TimeStart
                    break
                idx+=1
            durationNewVMSet =  (timeEnd - timeStart).total_seconds()
            reconfigCostNew = self.calculateReconfigurationCost(candidateOption.VMSet)

            # //Compute duration for current set
            jdx = indexTimeInterval
            currentLoadCapacity = currentOption.MSCSetting.MSCPerSecond
            while jdx < lenInterval:
                if timeIntervals[jdx].Requests > currentLoadCapacity:
                    timeEnd = timeIntervals[jdx].TimeStart
                    break
                jdx+=1
            durationCurrentVMSet =  (timeEnd-timeStart).total_seconds()
            reconfigCostCurrent = self.calculateReconfigurationCost(currentOption.VMSet)

            if candidateCost*durationNewVMSet + reconfigCostNew < currentCost * durationCurrentVMSet + reconfigCostCurrent:
                return candidateOption, True
        return ContainersConfig(), False

    # planner/derivation/algo_resize_when_beneficial.go:264
    def onlyDeltaScaleOut(self, totalLoad:float, currentPodLimits: Limit_) -> ContainersConfig:
        """/* Compute the resource configuration to handle extra delta load
        in:
            @totalLoad =  Configuration to handle extra delta load
            @currentPodLimits = Pod limits used in current configuration
        out:
            @ContainersConfig = Computed configuration
        */"""
        vmSet = VMScale({})
        containersResourceConfig =  ContainersConfig()

        profileCurrentLimits, _ = aux_func.estimatePodsConfiguration(totalLoad, currentPodLimits)
        aux_func.computeVMsCapacity(currentPodLimits, self.mapVMProfiles)
        currentPodsCapacity = aux_func.VMScaleReplicasCapacity(self.currentState.VMs, self.mapVMProfiles)
        newNumPods = profileCurrentLimits.MSCSetting.Replicas

        if currentPodsCapacity >= newNumPods:
            vmSet = self.currentState.VMs
        else:
            deltaNumPods = newNumPods - currentPodsCapacity
            vmSet = self.FindSuitableVMs(deltaNumPods, profileCurrentLimits.Limits)
            aux_func.VMScaleMerge(vmSet, self.currentState.VMs)

        containersResourceConfig.VMSet = vmSet
        containersResourceConfig.Limits = profileCurrentLimits.Limits
        containersResourceConfig.MSCSetting = profileCurrentLimits.MSCSetting

        return  containersResourceConfig

    # planner/derivation/algo_resize_when_beneficial.go:296
    def onlyDeltaScaleIn(self, totalLoad:float, currentPodLimits:Limit_, currentNumPods:int) -> ContainersConfig:
        """/* Compute the resource configuration to remove resources given a negative delta load
        in:
            @totalLoad =  Configuration to handle extra delta load
            @currentPodLimits = Pod limits used in current configuration
            @currentNumPods = Number of pods that should be hosted
        out:
            @ContainersConfig = Computed configuration
        */"""
        vmSet = VMScale({})
        containersResourceConfig = ContainersConfig()

        profileCurrentLimits, _ = aux_func.estimatePodsConfiguration(totalLoad, currentPodLimits)
        newNumPods = profileCurrentLimits.MSCSetting.Replicas
        deltaNumPods = currentNumPods - newNumPods
        if deltaNumPods > 0:
            vmSet = self.releaseVMs(self.currentState.VMs,newNumPods, currentPodLimits)
        else:
            vmSet = self.currentState.VMs
        containersResourceConfig.VMSet = vmSet
        containersResourceConfig.Limits = profileCurrentLimits.Limits
        containersResourceConfig.MSCSetting = profileCurrentLimits.MSCSetting
        return  containersResourceConfig

    # planner/derivation/algo_resize_when_beneficial.go:323
    def resize(self, totalLoad:float, currentPodLimits:Limit_, vmLimits:Limit_) -> ContainersConfig:
        """    /* Compute the resource configuration to by changing pod configurations and VM types
        in:
            @totalLoad =  Configuration to handle extra delta load
            @currentPodLimits = Pod limits used in current configuration
            @vmLimits = Limits of the biggest VM available
        out:
            @ContainersConfig = Computed configuration
        */
        """
        containersResourceConfig = ContainersConfig()
        performanceProfile, _ = aux_func.selectProfileUnderVMLimits(totalLoad, vmLimits)
        vmSet = self.FindSuitableVMs(performanceProfile.MSCSetting.Replicas, performanceProfile.Limits)

        containersResourceConfig.VMSet = vmSet
        containersResourceConfig.Limits = performanceProfile.Limits
        containersResourceConfig.MSCSetting = performanceProfile.MSCSetting

        return  containersResourceConfig
