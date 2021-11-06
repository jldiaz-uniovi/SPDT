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
                    ServiceInfo, State, StateLoadCapacity, VmProfile, VMScale)
from . import storage

log = logging.getLogger("spydt")

@dataclass
class DeltaLoadPolicy(AbstractPolicy):
    def FindSuitableVMs(self, numberReplicas:int, limits: Limit_) -> VMScale:
        vmSet, _ = aux_func.buildHomogeneousVMSet(numberReplicas, limits, self.mapVMProfiles)
        # log.info(f"FindSuitableVMs({numberReplicas=}, {limits=}")
        # log.info(f" {self.mapVMProfiles=}---> {vmSet=}")
        return vmSet

    def CreatePolicies(self, processedForecast: ProcessedForecast) -> list[Policy]:
        log.info(f"Derive policies with {self.algorithm} algorithm")
        policies: list[Policy] = []
        scalingActions: list[ScalingAction] = []
        newPolicy = Policy()
        newPolicy.Metrics = PolicyMetrics (StartTimeDerivation=datetime.now())

        for n, it in enumerate(processedForecast.CriticalIntervals):
            vmSet = VMScale({})
            newNumPods:int = 0
            podLimits  = Limit_()
            totalServicesBootingTime:float = 0.0
            stateLoadCapacity:float = 0.0

            # //Current configuration
            totalLoad = it.Requests
            serviceToScale = self.currentState.Services[self.sysConfiguration.MainServiceName]
            currentPodLimits = Limit_(MemoryGB=serviceToScale.Memory, CPUCores=serviceToScale.CPU)
            currentNumPods = serviceToScale.Scale
            currentLoadCapacity = aux_func.getStateLoadCapacity(currentNumPods, currentPodLimits).MSCPerSecond
            deltaLoad = totalLoad - currentLoadCapacity

            if deltaLoad == 0:
                # //case 0: Resource configuration do not change
                vmSet = self.currentState.VMs
                newNumPods = currentNumPods
                podLimits = currentPodLimits
                stateLoadCapacity = currentLoadCapacity
            else:
                # //Alternative configuration to handle the total load
                profileCurrentLimits,_ = aux_func.estimatePodsConfiguration(totalLoad, currentPodLimits)
                newNumPods = profileCurrentLimits.MSCSetting.Replicas
                podLimits = profileCurrentLimits.Limits
                stateLoadCapacity = profileCurrentLimits.MSCSetting.MSCPerSecond
                totalServicesBootingTime = profileCurrentLimits.MSCSetting.BootTimeSec

                if deltaLoad > 0:
                    # //case 1: Increase resources
                    aux_func.computeVMsCapacity(profileCurrentLimits.Limits, self.mapVMProfiles)
                    currentPodsCapacity = aux_func.VMScaleReplicasCapacity(self.currentState.VMs, self.mapVMProfiles)
                    if currentPodsCapacity >= newNumPods:
                        # //case 1.1: Increases number of replicas with the current limit resources but VMS remain the same
                        vmSet = self.currentState.VMs
                    else:
                        # //case 1.2: Increases number of VMS. Find new suitable Vm(s) to cover the number of replicas missing.
                        deltaNumPods = newNumPods - currentPodsCapacity
                        vmSet = self.FindSuitableVMs(deltaNumPods, profileCurrentLimits.Limits)
                        aux_func.VMScaleMerge(vmSet, self.currentState.VMs)
                else:
                    # //case 2: delta load is negative, some resources should be terminated
                    # //deltaNumPods := currentNumPods - newNumPods
                    vmSet = self.releaseVMs(self.currentState.VMs, newNumPods, currentPodLimits)
                    # log.info(f"timeslot {n}: {vmSet=}")

            services = Service({})
            services[self.sysConfiguration.MainServiceName] = ServiceInfo(
                Scale=newNumPods,
                CPU=podLimits.CPUCores,
                Memory=podLimits.MemoryGB,
            )
            state = State()
            state.Services = services
            vmSet = VMScale({ k: v for k,v in vmSet.items() if v != 0 })
            state.VMs = vmSet
            timeStart = it.TimeStart
            timeEnd = it.TimeEnd
            stateLoadCapacity = aux_func.adjustGranularity(self.sysConfiguration.ForecastComponent.Granularity, stateLoadCapacity)
            aux_func.setScalingSteps(scalingActions, self.currentState, state, timeStart, timeEnd, totalServicesBootingTime, stateLoadCapacity)
            self.currentState = state

        # //Add new policy
        parameters:dict[str, str] = {}
        parameters[Const.METHOD.value] = Const.SCALE_METHOD_HORIZONTAL.value
        parameters[Const.ISHETEREOGENEOUS.value] = str(True)
        parameters[Const.ISRESIZEPODS.value] = str(False)
        numConfigurations = len(scalingActions)
        newPolicy.ScalingActions = scalingActions
        newPolicy.Algorithm = self.algorithm
        newPolicy.ID = str(ObjectId)
        newPolicy.Status = Const.DISCARTED.value	# //State by default
        newPolicy.Parameters = parameters
        newPolicy.Metrics.NumberScalingActions = numConfigurations
        newPolicy.Metrics.FinishTimeDerivation = datetime.now()
        newPolicy.Metrics.DerivationDuration = (newPolicy.Metrics.FinishTimeDerivation - newPolicy.Metrics.StartTimeDerivation).total_seconds()
        newPolicy.TimeWindowStart = scalingActions[0].TimeStart
        newPolicy.TimeWindowEnd = scalingActions[-1].TimeEnd
        policies.append(newPolicy)
        return policies

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
