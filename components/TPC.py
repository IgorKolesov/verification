from .Unit import Unit
from .TaskType import TaskType
from .TPC_CU import TPC_CU
from .TPC_Executor import TPC_Executor
from typing import TYPE_CHECKING, Callable
from .BColors import BColors

if TYPE_CHECKING:
    from .Task import Task


class TPC(Unit):
    def __init__(self, name: str):
        super().__init__(name, BColors.OKGREEN, 1)
        self._VPU_executor = TPC_Executor(self, TaskType.VPU)
        self._ME_executor = TPC_Executor(self, TaskType.ME)
        self._FE_executor = TPC_Executor(self, TaskType.FE)
        self._TPC_CU = TPC_CU(self)
        self._current_tick = 0

    def set_current_tick(self, tick: int):
        self._current_tick = tick
        self._VPU_executor._current_tick = tick
        self._ME_executor._current_tick = tick
        self._FE_executor._current_tick = tick

    def get_total_task_count(self) -> int:
        return self._TPC_CU.get_queue_length()

    def get_workload(self) -> int:
        cu_queue_len = self._TPC_CU.get_queue_length()
        noc_used = len(self._TPC_CU.noc)
        active_executors = sum(1 for ex in (self._VPU_executor, self._ME_executor, self._FE_executor) if ex.get_active_task() is not None)
        return cu_queue_len + noc_used + active_executors

    def add_task(self, task: "Task", callback_on_complete: Callable[["Task"], None]):
        return self._TPC_CU.add_task(task, callback_on_complete)

    def _action(self):
        self._TPC_CU.tick()
        self._VPU_executor.tick()
        self._ME_executor.tick()
        self._FE_executor.tick()

    def __str__(self):
        return f"{super().__str__()}\n{f"{self._VPU_executor}"}\n{f"{self._ME_executor}"}\n{f"{self._FE_executor}"}\n{f"{self._TPC_CU}"}"
