from typing import List

from .model import Limit, Policy, ProcessedForecast, VMScale
from .policy import AbstractPolicy


class OnlyDeltaLoad(AbstractPolicy):
    def releaseVMs(self, vmSet: VMScale, numberPods: int, limits: Limit) -> VMScale:
        return VMScale()    

    def CreatePolicies(self, processedForecast: ProcessedForecast) -> List[Policy]:
        return []

    def FindSuitableVMs(self, numberPods: int, limits: Limit) -> VMScale:
        return VMScale()
