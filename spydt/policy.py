from dataclasses import dataclass, field
from abc import ABC
from typing import Tuple

from spydt.mock_storage import RetrieveCurrentState
from .model import (
    Const, Error, Forecast, State, VmProfile, SystemConfiguration, ProcessedForecast, Policy, Limit_, VMScale
)

@dataclass
class AbstractPolicy(ABC): # planner/derivation/policies_derivation.go:25
    """//Interface for strategies of how to scale"""
    algorithm: str = ""
    currentState: State = field(default_factory=State)
    mapVMProfiles: dict[str, VmProfile] = field(default_factory=dict)
    sysConfiguration: SystemConfiguration = SystemConfiguration()    

    def CreatePolicies(self, processedForecast: ProcessedForecast) -> list[Policy]:
        ...

    def FindSuitableVMs(self, numberPods: int, limits: Limit_) -> VMScale:
        ...


# planner/derivation/policies_derivation.go:40
def Policies(sortedVMProfiles: list[VmProfile], sysConfiguration: SystemConfiguration, forecast: Forecast) -> Tuple[list[Policy], Error]:
    policies: list[Policy] = []
    systemConfiguration = sysConfiguration
    mapVMProfiles = { p.Type: p for p in sortedVMProfiles }

    # log.Info("Request current state" )
    currentState, err = RetrieveCurrentState(sysConfiguration.SchedulerComponent.Endpoint + Const.ENDPOINT_CURRENT_STATE.value)

    """
    if err != nil {
        log.Error("Error to get current state %s", err.Error() )
    } else {
        log.Info("Finish request for current state" )
    }
    if currentState.Services[systemConfiguration.MainServiceName].Scale == 0 {
        return policies, errors.New("Service "+ systemConfiguration.MainServiceName +" is not deployed")
    }
    if available, vmType := validateVMProfilesAvailable(currentState.VMs, mapVMProfiles); !available{
        return policies, errors.New("Information not available for VM Type "+vmType )
    }

    granularity := systemConfiguration.ForecastComponent.Granularity
    processedForecast := forecast_processing.ScalingIntervals(forecast, granularity)
    initialState = currentState


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


def SelectPolicy(policies, sysConfiguration, vmProfiles, forecast):
    ...    