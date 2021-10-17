from datetime import datetime
import logging
from abc import ABC
from dataclasses import dataclass, field
import math
from types import MethodWrapperType
from typing import Tuple

from spydt.naive import NaivePolicy

from .aux_func import MapKeysToString, ScalingIntervals
from .mock_storage import RetrieveCurrentState
from .model import (ConfigMetrics, Const, Error, Forecast, ForecastedValue, Limit_, Policy, PolicyMetrics, ProcessedForecast, ScalingAction,
                    State, SystemConfiguration, VmProfile, VMScale)

log = logging.getLogger("spydt")


# planner/derivation/policies_derivation.go:40
def Policies(sortedVMProfiles: list[VmProfile], sysConfiguration: SystemConfiguration, forecast: Forecast) -> Tuple[list[Policy], Error]:
    policies: list[Policy] = []
    mapVMProfiles = { p.Type: p for p in sortedVMProfiles }

    log.info("Request current state" )
    currentState, err = RetrieveCurrentState(sysConfiguration.SchedulerComponent.Endpoint + Const.ENDPOINT_CURRENT_STATE.value)

    if err.error:
        log.error(f"Error to get current state {err.error}")
    else:
        log.info("Finish request for current state" )
    
    # log.debug(f"Current state -> {currentState}")
    if currentState.Services[sysConfiguration.MainServiceName].Scale == 0:
        return policies, Error(f"Service {sysConfiguration.MainServiceName } is not deployed")

    
    available, vmType = validateVMProfilesAvailable(currentState.VMs, mapVMProfiles)
    if not available:
        return policies, Error(f"Information not available for VM Type {vmType}")
    
    granularity = sysConfiguration.ForecastComponent.Granularity
    processedForecast = ScalingIntervals(forecast, granularity)
    initialState = currentState


    if sysConfiguration.PreferredAlgorithm == Const.NAIVE_ALGORITHM.value:
        naive = NaivePolicy(
            algorithm=Const.NAIVE_ALGORITHM.value,
            currentState=currentState, 
            mapVMProfiles=mapVMProfiles, 
            sysConfiguration=sysConfiguration
        )
        policies = naive.CreatePolicies(processedForecast=processedForecast)
        log.info(f"{len(policies)} policies generated")
        # print(policies[0].to_json())
    else:
        log.warning(f"Policies(). {sysConfiguration.PreferredAlgorithm} NOT IMPLEMENTED. Only naive strategy is implemented")
        return policies, Error(f"{sysConfiguration.PreferredAlgorithm} policy is not implemented")
 
    """
    switch sysConfiguration.PreferredAlgorithm {
    case util.NAIVE_ALGORITHM:
        naive := NaivePolicy {algorithm:util.NAIVE_ALGORITHM,
                             currentState:currentState, mapVMProfiles:mapVMProfiles, sysConfiguration: sysConfiguration}
        policies = naive.CreatePolicies(processedForecast)

    case util.BEST_RESOURCE_PAIR_ALGORITHM:
        base := BestResourcePairPolicy{algorithm:util.BEST_RESOURCE_PAIR_ALGORITHM,
            sortedVMProfiles:sortedVMProfiles,currentState:currentState,mapVMProfiles:mapVMProfiles, sysConfiguration: sysConfiguration}
        policies = base.CreatePolicies(processedForecast)

    case util.ALWAYS_RESIZE_ALGORITHM:
        alwaysResize := AlwaysResizePolicy{algorithm:util.ALWAYS_RESIZE_ALGORITHM,
                                    mapVMProfiles:mapVMProfiles, sortedVMProfiles:sortedVMProfiles, sysConfiguration: sysConfiguration, currentState:currentState}
        policies = alwaysResize.CreatePolicies(processedForecast)

    case util.ONLY_DELTA_ALGORITHM:
        tree := DeltaLoadPolicy{algorithm:util.ONLY_DELTA_ALGORITHM, currentState:currentState,
            mapVMProfiles:mapVMProfiles,sysConfiguration: sysConfiguration}
        policies = tree.CreatePolicies(processedForecast)

    case util.RESIZE_WHEN_BENEFICIAL:
        algorithm := ResizeWhenBeneficialPolicy{algorithm:util.RESIZE_WHEN_BENEFICIAL, currentState:currentState,
        sortedVMProfiles:sortedVMProfiles, mapVMProfiles:mapVMProfiles, sysConfiguration: sysConfiguration}
        policies = algorithm.CreatePolicies(processedForecast)
    default:
        //naive
        naive := NaivePolicy {algorithm:util.NAIVE_ALGORITHM,
            currentState:currentState, mapVMProfiles:mapVMProfiles, sysConfiguration: sysConfiguration}
        policies1 := naive.CreatePolicies(processedForecast)
        policies = append(policies, policies1...)
        //types
        base := BestResourcePairPolicy{algorithm:util.BEST_RESOURCE_PAIR_ALGORITHM,
            currentState:currentState, sortedVMProfiles:sortedVMProfiles, mapVMProfiles:mapVMProfiles, sysConfiguration: sysConfiguration}
        policies2 := base.CreatePolicies(processedForecast)
        policies = append(policies, policies2...)
        //always resize
        alwaysResize := AlwaysResizePolicy{algorithm:util.ALWAYS_RESIZE_ALGORITHM,
            mapVMProfiles:mapVMProfiles, sortedVMProfiles:sortedVMProfiles, sysConfiguration: sysConfiguration, currentState:currentState}
        policies3 := alwaysResize.CreatePolicies(processedForecast)
        policies = append(policies, policies3...)
        //resize when beneficial
        algorithm := ResizeWhenBeneficialPolicy{algorithm:util.RESIZE_WHEN_BENEFICIAL, currentState:currentState,
            sortedVMProfiles:sortedVMProfiles, mapVMProfiles:mapVMProfiles, sysConfiguration: sysConfiguration}
        policies4 := algorithm.CreatePolicies(processedForecast)
        policies = append(policies, policies4...)

        //delta load
        tree := DeltaLoadPolicy{algorithm:util.ONLY_DELTA_ALGORITHM, currentState:currentState,
            mapVMProfiles:mapVMProfiles,sysConfiguration: sysConfiguration}
        policies6 := tree.CreatePolicies(processedForecast)
        policies = append(policies, policies6...)
    }
    """
    return policies, err


# planner/derivation/policy_selection.go:9
def SelectPolicy(policies: list[Policy], sysConfiguration: SystemConfiguration, vmProfiles: list[VmProfile], forecast: Forecast) -> Tuple[Policy, Error]:
    """
    /*Evaluates and select the most suitable policy for the given system configurations and forecast
    in:
        @policies *[]types.Policy
                    - List of derived policies
        @sysConfig config.SystemConfiguration
                    - Configuration specified by the user in the config file
        @vmProfiles []types.VmProfile
                    - List of virtual machines profiles
        @forecast types.Forecast
                    - Forecast of the expected load
    out:
        @types.Policy
                - Selected policy
        @error
                - Error in case of any
    */
    """
    log.warning("SelectPolicy() still NOT IMPLEMENTED, returning emtpy Policy")

    mapVMProfiles: dict[str, VmProfile] = {p.Type: p for p in vmProfiles}
    # //Calculate total cost of the policy
    for i, policy in enumerate(policies):
        policyMetrics, vmTypes = ComputePolicyMetrics(policy.ScalingActions,forecast.ForecastedValues, sysConfiguration, mapVMProfiles)
        policyMetrics.StartTimeDerivation = policy.Metrics.StartTimeDerivation
        policyMetrics.FinishTimeDerivation = policy.Metrics.FinishTimeDerivation
        duration =(policy.Metrics.FinishTimeDerivation - policy.Metrics.StartTimeDerivation).total_seconds()
        policyMetrics.DerivationDuration = round(duration, 2)
        policy.Metrics = policyMetrics
        policy.Parameters[Const.VMTYPES.value] = MapKeysToString(vmTypes)
        print(policy.to_json())
    """
    //Sort policies based on price
    sort.Slice(*policies, func(i, j int) bool {
        costi := (*policies)[i].Metrics.Cost
        costj := (*policies)[j].Metrics.Cost

        if costi < costj {
            return true
        }else  if costi == costj {
            return (*policies)[i].Metrics.NumberContainerScalingActions < (*policies)[j].Metrics.NumberContainerScalingActions
        }
        return false
    })

    if len(*policies) >0 {
        remainBudget, time := isEnoughBudget(sysConfig.PricingModel.Budget, (*policies)[0])
        if remainBudget {
            (*policies)[0].Status = types.SELECTED
            return (*policies)[0], nil
        } else {
            return (*policies)[0], errors.New("Budget is not enough for time window, you should increase the budget to ensure resources after " +time.String())
        }
    } else {
        return types.Policy{}, errors.New("No suitable policy found")
    }
    """
    return Policy(), Error() # Error("SelectPolicy() not implemented")
  

# planner/derivation/policies_derivation.go:545
def validateVMProfilesAvailable(vmSet: VMScale, mapVMProfiles: dict[str, VmProfile] ) -> Tuple[bool, str]:
    for k in vmSet:
        if k not in mapVMProfiles:
            return False, k
    return True, ""


# planner/derivation/policy_selection.go:66
def ComputePolicyMetrics(scalingActions: list[ScalingAction], forecast: list[ForecastedValue],
    sysConfiguration: SystemConfiguration, mapVMProfiles: dict[str, VmProfile]) -> Tuple[PolicyMetrics, dict[str, bool]]:
    """//Compute the metrics related to the policy and its scaling actions"""

    log.warning("ComputePolicyMetrics() NOT IMPLEMENTED, returning emtpy PolicyMetrics and VmTypes")
    # return PolicyMetrics(), {}

    avgOverProvision: float
    avgUnderProvision: float
    avgElapsedTime: float
    avgTransitionTime: float
    avgShadowTime: float

    totalCost = 0.0
    numberVMScalingActions:int = 0
    numberContainerScalingActions:int = 0
    vmTypes: dict[str, bool] = {}
    totalOver = 0.0
    totalUnder = 0.0
    totalElapsedTime = 0.0
    totalTransitionTime = 0.0
    totalShadowTime = 0.0

    index:int = 0
    numberScalingActions = len(scalingActions)
    nPredictedValues = len(forecast)
    for i, scalingAction in enumerate(scalingActions):
        underProvision = 0.0
        overProvision = 0.0
        cost = 0.0
        transitionTime = 0.0
        elapsedTime = 0.0
        shadowTime = 0.0
        cpuUtilization = 0.0
        memUtilization = 0.0

        # //Capacity
        scaleActionOverProvision = 0.0
        scaleActionUnderProvision = 0.0
        numSamplesOver = 0.0
        numSamplesUnder = 0.0
        while index < nPredictedValues and scalingAction.TimeEnd > forecast[index].TimeStamp:
            deltaLoad = scalingAction.Metrics.RequestsCapacity - forecast[index].Requests
            if deltaLoad > 0:
                scaleActionOverProvision += deltaLoad*100.0/ forecast[index].Requests
                numSamplesOver+=1
            elif deltaLoad < 0:
                scaleActionUnderProvision += -1*deltaLoad*100.0/ forecast[index].Requests
                numSamplesUnder+=1
            index+=1

        if numSamplesUnder > 0:
            underProvision = round(scaleActionUnderProvision/numSamplesUnder, 2)
            totalUnder += scaleActionUnderProvision /numSamplesUnder

        if numSamplesOver > 0:
            overProvision = round(scaleActionOverProvision/numSamplesOver, 2)
            totalOver += scaleActionOverProvision /numSamplesOver

        # Other metrics
        vmSetDesired = scalingAction.DesiredState.VMs
        vmSetInitial = scalingAction.InitialState.VMs
        if vmSetDesired != vmSetInitial:
            numberVMScalingActions += 1

        desiredServiceReplicas = scalingAction.DesiredState.Services[sysConfiguration.MainServiceName]
        initialServiceReplicas = scalingAction.InitialState.Services[sysConfiguration.MainServiceName]
        if desiredServiceReplicas != initialServiceReplicas:
            numberContainerScalingActions += 1

        totalCPUCoresInVMSet = 0.0
        totalMemGBInVMSet = 0.0
        
        deltaTime = BilledTime(scalingAction.TimeStart, scalingAction.TimeEnd, sysConfiguration.PricingModel.BillingUnit)
        for k,v in vmSetDesired.items():
            vmTypes[k] = True
            totalCPUCoresInVMSet += mapVMProfiles[k].CPUCores * float(v)
            totalMemGBInVMSet += mapVMProfiles[k].Memory * float(v)
            totalPrice = mapVMProfiles[k]._Pricing.Price * float(v) * deltaTime
            cost +=  round(totalPrice, 2)       
        totalCost += cost
        if i>1:
            previousStateEndTime = scalingActions[i-1].TimeEnd
            shadowTime = (previousStateEndTime - scalingAction.TimeStart).total_seconds()
            totalShadowTime += shadowTime
            transitionTime = (previousStateEndTime - scalingAction.TimeStartTransition).total_seconds()
            totalTransitionTime += transitionTime

        memUtilization = desiredServiceReplicas.Memory * float(desiredServiceReplicas.Scale) * 100.0 / totalMemGBInVMSet
        cpuUtilization = desiredServiceReplicas.CPU * float(desiredServiceReplicas.Scale)  * 100.0 / totalCPUCoresInVMSet
        elapsedTime = (scalingAction.TimeEnd - scalingAction.TimeStart).total_seconds()
        totalElapsedTime += elapsedTime

        configMetrics = ConfigMetrics(
            UnderProvision=underProvision,
            OverProvision=overProvision,
            Cost=cost,
            TransitionTimeSec=transitionTime,
            ElapsedTimeSec=elapsedTime,
            ShadowTimeSec=shadowTime,
            RequestsCapacity=scalingAction.Metrics.RequestsCapacity,
            CPUUtilization=cpuUtilization,
            MemoryUtilization=memUtilization,
        )
        scalingAction.Metrics = configMetrics

    avgOverProvision = totalOver/ float(numberScalingActions)
    avgUnderProvision = totalUnder / float(numberScalingActions)
    avgElapsedTime = totalElapsedTime / float(numberScalingActions)
    avgTransitionTime = totalTransitionTime / float(numberScalingActions)
    avgShadowTime = totalShadowTime / float(numberScalingActions)

    return PolicyMetrics (
        Cost=round(totalCost, 2),
        OverProvision=round(avgOverProvision, 2),
        UnderProvision=round(avgUnderProvision, 2),
        NumberVMScalingActions=numberVMScalingActions,
        NumberContainerScalingActions=numberContainerScalingActions,
        NumberScalingActions=numberVMScalingActions,
        AvgElapsedTime=round(avgElapsedTime, 2),
        AvgShadowTime=round(avgShadowTime, 2),
        AvgTransitionTime=round(avgTransitionTime, 2),
    ), vmTypes

# planner/derivation/cost_calculation.go:33
def BilledTime(timeStart: datetime, timeEnd: datetime, unit: str) -> float:
    """//Calculate detlta time for a time window"""
    delta = (timeEnd-timeStart).total_seconds()/3600
    if unit == Const.SECOND.value:
        return max(0.01666666666, delta)                    # It charges at least 1 sec
    elif unit == Const.HOUR.value:
        return math.ceil(delta)								# It charges at least 1 hour
    return delta
