
from typing import List, Tuple

from .model import (CriticalInterval, Limit, Policy, ProcessedForecast,
                    VmProfile, VMScale)
from .policy import AbstractPolicy


class BestResourcePairPolicy(AbstractPolicy):
    def deriveCandidatePolicy(self, criticalIntervals: List[CriticalInterval],
        podLimits: Limit, vmType: str ) -> Tuple[bool, Policy]:
        return (False, Policy())

    def findBestPair(self, forecastedValues: List[CriticalInterval]) -> Tuple[Limit, VmProfile]:
        return (Limit(), VmProfile())

    def CreatePolicies(self, processedForecast: ProcessedForecast) -> List[Policy]:
        return []

    def FindSuitableVMs(self, numberPods: int, limits: Limit) -> VMScale:
        return VMScale()
