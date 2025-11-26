from enum import Enum


class TaskType(Enum):
    VPU = "vector"
    ME = "matrix"
    FE = "activation"
