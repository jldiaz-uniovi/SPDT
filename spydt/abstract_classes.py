from abc import ABC
from dataclasses import dataclass, field

from .model import (Limit_, Policy, ProcessedForecast, State,
                    SystemConfiguration, VmProfile, VMScale)


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
