from .model import Limit_, Policy, ProcessedForecast, VMScale
from .policy import AbstractPolicy


class OnlyDeltaLoad(AbstractPolicy):
    def releaseVMs(self, vmSet: VMScale, numberPods: int, limits: Limit_) -> VMScale:
        return VMScale({})    

    def CreatePolicies(self, processedForecast: ProcessedForecast) -> list[Policy]:
        return []

    def FindSuitableVMs(self, numberPods: int, limits: Limit_) -> VMScale:
        return VMScale({})
