
from typing import List, Tuple

from .model import (CriticalInterval, Limit_, Policy, ProcessedForecast,
                    VmProfile, VMScale)
from .policy import AbstractPolicy


class BestResourcePairPolicy(AbstractPolicy):
    def deriveCandidatePolicy(self, criticalIntervals: List[CriticalInterval],
        pod_Limits: Limit_, vmType: str ) -> Tuple[bool, Policy]:
        return (False, Policy())

    def findBestPair(self, forecastedValues: List[CriticalInterval]) -> Tuple[Limit_, VmProfile]:
        return (Limit_(), VmProfile())

    def CreatePolicies(self, processedForecast: ProcessedForecast) -> List[Policy]:
        return []

    def FindSuitableVMs(self, numberPods: int, limits: Limit_) -> VMScale:
        return VMScale({})
