from enum import Enum


class Status(Enum):
    WAIT = 0
    COLLECT_TO_LOCAL = 1
    SEND_TO_GLOBAL = 2
    EXEC_VPU = 3
    EXEC_ME = 4
    EXEC_FE = 5


TICK_COUNT_BY_STATUS = {
    Status.WAIT: 0,
    Status.COLLECT_TO_LOCAL: 5,
    Status.SEND_TO_GLOBAL: 5,
    Status.EXEC_VPU: 3,
    Status.EXEC_ME: 3,
    Status.EXEC_FE: 3,
}
