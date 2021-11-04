import logging
import math
from dataclasses import field, dataclass
from datetime import datetime
from typing import Tuple

from bson.objectid import ObjectId  # type: ignore

from .abstract_classes import AbstractPolicy
from . import aux_func
from .model import (Const, CriticalInterval, Error, Limit_, Policy,
                    PolicyMetrics, ProcessedForecast, ScalingAction, Service,
                    ServiceInfo, State, VmProfile, VMScale)
from . import storage

log = logging.getLogger("spydt")

@dataclass
class AlwaysResizePolicy(AbstractPolicy):
    sortedVMProfiles: list[VmProfile] = field(default_factory=list)

    # planner/derivation/algo_always_resize.go:27
    def CreatePolicies(self, processedForecast: ProcessedForecast) -> list[Policy]:
        """/* Derive a list of policies using the best homogeneous cluster, change of type is possible
            in:
                @processedForecast
                @serviceProfile
            out:
                [] Policy. List of type Policy
        */"""
        log.info("Derive policies with %s algorithm", self.algorithm)
        policies: list[Policy] = []
        # //Compute results for cluster of each type
        biggestVM = self.sortedVMProfiles[-1]
        vmLimits = Limit_(MemoryGB=biggestVM.Memory, CPUCores=biggestVM.CPUCores)

        serviceToScale = self.currentState.Services[self.sysConfiguration.MainServiceName]
        currentPodLimits = Limit_(MemoryGB=serviceToScale.Memory, CPUCores=serviceToScale.CPU )
        newPolicy = self.deriveCandidatePolicy(processedForecast.CriticalIntervals, currentPodLimits, vmLimits)
        policies.append(newPolicy)
        return policies

    # planner/derivation/algo_always_resize.go:50
    def FindSuitableVMs(self, numberReplicas: int, limits: Limit_)  -> Tuple[VMScale, Error]:
        """/*Calculate VM set able to host the required number of replicas
            in:
                @numberReplicas = Amount of replicas that should be hosted
                @limits = Resources (CPU, Memory) constraints to configure the containers.
            out:
                @VMScale with the suggested number of VMs for that type
            */
        """
        vmSet,err = aux_func.buildHomogeneousVMSet(numberReplicas, limits, self.mapVMProfiles)
        # /*hetVMSet,_ := buildHeterogeneousVMSet(numberReplicas, limits, p.mapVMProfiles)
        # costi := hetVMSet.Cost(p.mapVMProfiles)
        # costj := vmSet.Cost(p.mapVMProfiles)
        # if costi < costj {
        #     vmSet = hetVMSet
        # }

        # if err!= nil {
        #     return vmSet,errors.New("No suitable VM set found")
        # }*/
        return vmSet,err

    # planner/derivation/algo_always_resize.go:66
    def deriveCandidatePolicy(self, criticalIntervals: list[CriticalInterval],
        podLimits: Limit_, vmLimits: Limit_) -> Policy:
        newPolicy = Policy()
        newPolicy.Metrics = PolicyMetrics(StartTimeDerivation=datetime.now())
        scalingSteps: list[ScalingAction] = []

        for it in criticalIntervals:
            totalLoad = it.Requests
            performanceProfile, _ = aux_func.selectProfileUnderVMLimits(totalLoad, vmLimits)
            vmSet, _ = self.FindSuitableVMs(performanceProfile.MSCSetting.Replicas, performanceProfile.Limits)
            newNumPods = performanceProfile.MSCSetting.Replicas
            stateLoadCapacity = performanceProfile.MSCSetting.MSCPerSecond
            totalServicesBootingTime = performanceProfile.MSCSetting.BootTimeSec
            limits = performanceProfile.Limits

            services = Service({})
            services[ self.sysConfiguration.MainServiceName] = ServiceInfo(
                Scale=newNumPods,
                CPU=limits.CPUCores,
                Memory=limits.MemoryGB,
            )

            state = State()
            state.Services = services
            state.VMs = vmSet

            timeStart = it.TimeStart
            timeEnd = it.TimeEnd
            stateLoadCapacity = aux_func.adjustGranularity(self.sysConfiguration.ForecastComponent.Granularity, stateLoadCapacity)
            aux_func.setScalingSteps(scalingSteps, self.currentState, state, timeStart, timeEnd, totalServicesBootingTime, stateLoadCapacity)
            self.currentState = state

        # //Add new policy
        parameters: dict[str, str] = {}
        parameters[Const.METHOD.value] = Const.SCALE_METHOD_HORIZONTAL.value
        parameters[Const.ISHETEREOGENEOUS.value] = str(True)
        parameters[Const.ISRESIZEPODS.value] = str(True)
        numConfigurations = len(scalingSteps)
        newPolicy.ScalingActions = scalingSteps
        newPolicy.Algorithm = self.algorithm
        newPolicy.ID = str(ObjectId())
        newPolicy.Status = Const.DISCARTED.value  # //State by default
        newPolicy.Parameters = parameters
        newPolicy.Metrics.NumberScalingActions = numConfigurations
        newPolicy.Metrics.FinishTimeDerivation = datetime.now()
        newPolicy.TimeWindowStart = scalingSteps[0].TimeStart
        newPolicy.TimeWindowEnd = scalingSteps[-1].TimeEnd
        newPolicy.Metrics.DerivationDuration = (newPolicy.Metrics.FinishTimeDerivation - newPolicy.Metrics.StartTimeDerivation).total_seconds()

        return newPolicy
