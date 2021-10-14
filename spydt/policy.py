import logging
from abc import ABC
from dataclasses import dataclass, field
from types import MethodWrapperType
from typing import Tuple

from spydt.naive import NaivePolicy

from .aux_func import ScalingIntervals
from .mock_storage import RetrieveCurrentState
from .model import (Const, Error, Forecast, Limit_, Policy, ProcessedForecast,
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
    
    log.debug(f"Current state -> {currentState}")
    # TODO
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


def SelectPolicy(policies, sysConfiguration, vmProfiles, forecast) -> Tuple[Policy, Error]:
    log.warning("SelectPolicy() still NOT IMPLEMENTED, returning emtpy Policy")
    return Policy(), Error() # Error("SelectPolicy() not implemented")
  

# planner/derivation/policies_derivation.go:545
def validateVMProfilesAvailable(vmSet: VMScale, mapVMProfiles: dict[str, VmProfile] ) -> Tuple[bool, str]:
    for k in vmSet:
        if k not in mapVMProfiles:
            return False, k
    return True, ""
