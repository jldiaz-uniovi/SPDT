from dataclasses import dataclass, field
from typing import Mapping, List
from abc import ABC
from .model import (
    State, VmProfile, SystemConfiguration, ProcessedForecast, Policy, Limit, VMScale
)

@dataclass
class AbstractPolicy(ABC): # planner/derivation/policies_derivation.go:25
    """//Interface for strategies of how to scale"""
    algorithm: str = ""
    currentState: State = State()
    mapVMProfiles: Mapping[str, VmProfile] = field(default_factory=dict)
    sysConfiguration: SystemConfiguration = SystemConfiguration()    

    def CreatePolicies(self, processedForecast: ProcessedForecast) -> List[Policy]:
        ...

    def FindSuitableVMs(self, numberPods: int, limits: Limit) -> VMScale:
        ...
        