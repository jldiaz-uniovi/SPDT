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
class BestResourcePairPolicy(AbstractPolicy):
    sortedVMProfiles: list[VmProfile] = field(default_factory=list)

    # planner/derivation/algo_best_resource_pair.go:26
    def CreatePolicies(self, processedForecast: ProcessedForecast) -> list[Policy]:
        """/* Derive a list of policies using the Best Instance Approach approach
            in:
                @processedForecast
                @serviceProfile
            out:
                [] Policy. List of type Policy
        */"""
        log.info(f"Derive policies with {self.algorithm} algorithm")
        policies: list[Policy] = []
        selectedLimits, selectedVMProfile = self.findBestPair(processedForecast.CriticalIntervals )

        _, newPolicy = self.deriveCandidatePolicy(processedForecast.CriticalIntervals,selectedLimits, selectedVMProfile.Type)
        policies.append(newPolicy)
        return policies

    # planner/derivation/algo_best_resource_pair.go:44
    def FindSuitableVMs(self, numberReplicas: int, resourcesLimit: Limit_, vmType: str)  -> Tuple[VMScale, Error]:
        """/*Calculate VM set able to host the required number of replicas
            in:
                @numberReplicas = Amount of replicas that should be hosted
                @resourcesLimit = Resources (CPU, Memory) constraints to configure the containers.
            out:
                @VMScale with the suggested number of VMs for that type
            */
        """
        vmScale = VMScale({})
        err = Error()
        profile = self.mapVMProfiles.get(vmType)
        if not profile:
            errmsg = f"No profile for vmType={vmType!r}"
            log.warning(errmsg)
            return vmScale, Error(errmsg)
        maxReplicas = aux_func.maxPodsCapacityInVM(profile, resourcesLimit)
        if maxReplicas > 0 :
            numVMs = math.ceil(numberReplicas/maxReplicas)
            vmScale[vmType] = int(numVMs)
        else:
            log.debug(f"No suitable VM set found for {numberReplicas=}, {resourcesLimit=}, {vmType=}")
            return vmScale, Error("No suitable VM set found")
        return vmScale, err

    # planner/derivation/algo_best_resource_pair.go:133
    def findBestPair(self, forecastedValues:  list[CriticalInterval] ) -> Tuple[Limit_, VmProfile]:
        _max = max(v.Requests for v in forecastedValues)
        biggestVMType = self.sortedVMProfiles[-1]
        allLimits, err = storage.GetPerformanceProfileDAO(self.sysConfiguration.MainServiceName).FindAllUnderLimits(biggestVMType.CPUCores, biggestVMType.Memory)
        if err.error:                    # Original go implementation discarded errors
            log.error(f"allLimits not found because {err.error}")         # but I want to at least report them, because it is not clear how to recover
            return Limit_(), VmProfile()

        bestLimit = Limit_()
        bestVMProfile = VmProfile()
        bestCost =  math.inf
        numberReplicas = 999
        for vmType in self.mapVMProfiles:
            for vl in allLimits:
                servicePerformanceProfile, _ = aux_func.estimatePodsConfiguration(_max, vl.Limit)
                replicas = servicePerformanceProfile.MSCSetting.Replicas
                vmSetCandidate,_ = self.FindSuitableVMs(replicas,vl.Limit, vmType)
                vmSetCost = 0.0
                if vmSetCandidate:
                    for v in vmSetCandidate.values():
                        vmSetCost += self.mapVMProfiles[vmType]._Pricing.Price + float(v)
                    if vmSetCost < bestCost:
                        bestLimit = vl.Limit
                        bestVMProfile = self.mapVMProfiles[vmType]
                        bestCost = vmSetCost
                        numberReplicas = replicas
                    elif vmSetCost == bestCost and replicas < numberReplicas:
                        bestLimit = vl.Limit
                        bestVMProfile = self.mapVMProfiles[vmType]
                        bestCost = vmSetCost
                        numberReplicas = replicas
        return bestLimit, bestVMProfile

    # planner/derivation/algo_best_resource_pair.go:68
    def deriveCandidatePolicy(self, criticalIntervals: list[CriticalInterval],
        podLimits: Limit_, vmType: str) -> Tuple[bool, Policy]:
        """/*
            Derive a policy
        */"""

        vmTypeSuitable = True
        scalingActions: list[ScalingAction] = []
        newPolicy = Policy()
        newPolicy.Metrics = PolicyMetrics(StartTimeDerivation=datetime.now())

        for it in criticalIntervals:
            servicePerformanceProfile,_ = aux_func.estimatePodsConfiguration(it.Requests, podLimits)
            vmSet, err = self.FindSuitableVMs(servicePerformanceProfile.MSCSetting.Replicas, servicePerformanceProfile.Limits, vmType)
            if err.error:
                vmTypeSuitable = False
            newNumPods = servicePerformanceProfile.MSCSetting.Replicas
            stateLoadCapacity = servicePerformanceProfile.MSCSetting.MSCPerSecond
            totalServicesBootingTime = servicePerformanceProfile.MSCSetting.BootTimeSec
            limits = servicePerformanceProfile.Limits

            services = Service({})
            services[self.sysConfiguration.MainServiceName] = ServiceInfo(
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
            aux_func.setScalingSteps(scalingActions, self.currentState, state, timeStart, timeEnd, totalServicesBootingTime, stateLoadCapacity)
            self.currentState = state
        

        if vmTypeSuitable and scalingActions:
            # Add new policy
            parameters: dict[str, str] = {}
            parameters[Const.METHOD.value] = Const.SCALE_METHOD_HORIZONTAL.value
            parameters[Const.ISHETEREOGENEOUS.value] = str(False)
            parameters[Const.ISRESIZEPODS.value] = str(True)
            newPolicy.ScalingActions = scalingActions
            newPolicy.Algorithm = self.algorithm
            newPolicy.ID = str(ObjectId())
            newPolicy.Status = Const.DISCARTED.value	# //State by default
            newPolicy.Parameters = parameters
            newPolicy.Metrics.NumberScalingActions = len(scalingActions)
            newPolicy.Metrics.FinishTimeDerivation = datetime.now()
            newPolicy.Metrics.DerivationDuration = (newPolicy.Metrics.FinishTimeDerivation - newPolicy.Metrics.StartTimeDerivation).total_seconds()
            newPolicy.TimeWindowStart = scalingActions[0].TimeStart
            newPolicy.TimeWindowEnd = scalingActions[-1].TimeEnd
        return vmTypeSuitable, newPolicy
