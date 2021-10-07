from datetime import datetime
import math

from .model import (Const, Limit, Policy, PolicyMetrics, ProcessedForecast,
                    ScalingAction, ServiceInfo, Service, State, VMScale)
from .policy import AbstractPolicy
from .utils import (adjustGranularity, estimatePodsConfiguration,
                    setScalingSteps, maxPodsCapacityInVM)


class NaivePolicy(AbstractPolicy): # planner/derivation/algo_naive.go:12
    """
    It assumes that the current VM set where the microservice is deployed is a homogeneous set
    Based on the unique VM type and its capacity to host a number of replicas it increases or decreases the number of VMs
    """
    def currentVMType(self) -> str:
        """It selects teh VM with more resources in case there is more than onw vm type"""
        vmType = ""
        memGB = 0.0
        for k in self.currentState.VMs:
            if self.mapVMProfiles[k].Memory > memGB:
                vmType = k
                memGB =  self.mapVMProfiles[k].Memory
        if len(self.currentState.VMs) > 1:
            print("Current config has more than one VM type, type %s was selected to continue", vmType)  # FIX: use logging
        return vmType
    
    def CreatePolicies(self, processedForecast: ProcessedForecast) -> list[Policy]:
        policies: list[Policy] = []
        serviceToScale = self.currentState.Services[self.sysConfiguration.MainServiceName]
        currentPodLimits = Limit(CPUCores=serviceToScale.CPU, MemoryGB=serviceToScale.Memory)

        newPolicy = Policy()
        state = State()
        newPolicy.Metrics = PolicyMetrics(StartTimeDerivation=datetime.now())
        scalingActions: list[ScalingAction] = []
        for it in processedForecast.CriticalIntervals:
            resourceLimits = Limit()
            # Select the performance profile that fits better
            containerConfigOver, _ = estimatePodsConfiguration(it.Requests, currentPodLimits)
            newNumPods = containerConfigOver.MSCSetting.Replicas
            vmSet = self.FindSuitableVMs(newNumPods, containerConfigOver.Limits)
            stateLoadCapacity = containerConfigOver.MSCSetting.MSCPerSecond
            totalServicesBootingTime = containerConfigOver.MSCSetting.BootTimeSec
            resourceLimits = containerConfigOver.Limits

            services = Service({}) # make(map[string]types.ServiceInfo)
            services[self.sysConfiguration.MainServiceName] = ServiceInfo(
                Scale=  newNumPods,
                CPU=    resourceLimits.CPUCores,
                Memory= resourceLimits.MemoryGB,
            )
            state = State(
                Services= services,
                VMs=      vmSet,
            )

            # update state before next iteration
            timeStart = it.TimeStart
            timeEnd = it.TimeEnd
            systemConfiguration = self.sysConfiguration  # FIX: ¿sale de self? En el original parecía tomarlo de una variable global en el módulo util
            stateLoadCapacity = adjustGranularity(systemConfiguration.ForecastComponent.Granularity, stateLoadCapacity)
            setScalingSteps(scalingActions, self.currentState, state, timeStart, timeEnd, totalServicesBootingTime, stateLoadCapacity)
            self.currentState = state
        parameters = {}
        parameters[Const.METHOD.value] = Const.SCALE_METHOD_HORIZONTAL.value
        parameters[Const.ISHETEREOGENEOUS.value] = "false"
        parameters[Const.ISRESIZEPODS.value] = "false"
        # Add new policy
        numConfigurations = len(scalingActions)
        newPolicy.ScalingActions = scalingActions
        newPolicy.Algorithm = self.algorithm
        # newPolicy.ID = bson.NewObjectId()  # TODO: use pymongo.objectid
        newPolicy.Status = Const.DISCARTED.value  # State by default
        newPolicy.Parameters = parameters
        newPolicy.Metrics.NumberScalingActions = numConfigurations
        newPolicy.Metrics.FinishTimeDerivation = datetime.now()
        newPolicy.Metrics.DerivationDuration = (newPolicy.Metrics.FinishTimeDerivation- newPolicy.Metrics.StartTimeDerivation).total_seconds()
        newPolicy.TimeWindowStart = scalingActions[0].TimeStart
        newPolicy.TimeWindowEnd = scalingActions[numConfigurations-1].TimeEnd
        policies.append(newPolicy)
        return policies

    def FindSuitableVMs(self, numberPods: int, limits: Limit) -> VMScale:
        vmScale = VMScale({})
        vmType = self.currentVMType()
        profile = self.mapVMProfiles[vmType]
        podsCapacity = maxPodsCapacityInVM(profile, limits)
        if podsCapacity > 0:
            numVMs = math.ceil(numberPods/podsCapacity)
            vmScale[vmType] = int(numVMs)
        
        return vmScale

