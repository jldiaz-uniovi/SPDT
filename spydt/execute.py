from typing import Tuple
import logging
from .model import Policy, StateToSchedule, Error

log = logging.getLogger("spytd")

# planner/execution/trigger_scheduler.go:10
def TriggerScheduler(policy: Policy, endpoint: str) -> Tuple[list[StateToSchedule], Error]:
    statesToSchedule: list[StateToSchedule] = []
    log.warning("TriggerScheduler() NOT IMPLEMENTED, returning empty list and error")  # TO-DO
    log.warning(f"The schedule was {policy.to_json()}")  # type: ignore
    return statesToSchedule, Error("TriggerScheduler() not implemented")

    """
    for _, conf := range policy.ScalingActions {
        mapServicesToSchedule := make(map[string]scheduler.ServiceToSchedule)
        state := conf.DesiredState

        for k,v := range state.Services {
            cpu := CPUToString(v.CPU)
            memory := memGBToBytes(v.Memory)
            replicas := v.Scale
            mapServicesToSchedule[k] = scheduler.ServiceToSchedule{
                Scale:replicas,
                CPU:cpu,
                Memory:memory,
            }
        }
        vms := addRemovedKeys(conf.InitialState.VMs, conf.DesiredState.VMs)
        stateToSchedule := scheduler.StateToSchedule{
            LaunchTime:conf.TimeStartTransition,
            Services:mapServicesToSchedule,
            Name:state.Hash,
            VMs:vms,
            ExpectedStart:conf.TimeStart,
        }
        statesToSchedule = append(statesToSchedule, stateToSchedule)

        err := scheduler.CreateState(stateToSchedule, endpoint)
        if err != nil {
            return statesToSchedule,err
        }
    }
    return statesToSchedule,nil
    """
