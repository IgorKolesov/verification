from .Unit import Unit
from .Status import Status, TICK_COUNT_BY_STATUS
from typing import TYPE_CHECKING, Callable, Optional
from .TaskType import TaskType
from .BColors import BColors


if TYPE_CHECKING:
    from .Task import Task
    from .TPC import TPC


class TPC_Executor(Unit):
    def __init__(self, tpc: "TPC", task_type: "TaskType"):
        super().__init__(f"{tpc.name}_{task_type.name}_Executor", BColors.FAIL, 2)
        self._tpc: "TPC" = tpc
        self._task_type: "TaskType" = task_type
        self._active_task: Optional["Task"] = None
        self._callback_on_complete: Optional[Callable[["Task"], None]] = None
        self._current_tick: int = 0

    def get_active_task(self) -> Optional["Task"]:
        return self._active_task

    def set_active_task(
        self,
        task: "Task",
        callback_on_complete: Optional[Callable[["Task"], None]] = None,
        current_tick: int = 0,
    ):
        self._active_task = task
        self._callback_on_complete = callback_on_complete
        self._current_tick = current_tick

    def _action(self):
        match self._status:
            case Status.WAIT:
                self._wait()
            case Status.EXEC_VPU | Status.EXEC_ME | Status.EXEC_FE:
                self._exec()

    def _wait(self):
        if not self._active_task:
            return

        match self._task_type:
            case TaskType.VPU:
                self.set_status(Status.EXEC_VPU)
            case TaskType.ME:
                self.set_status(Status.EXEC_ME)
            case TaskType.FE:
                self.set_status(Status.EXEC_FE)

    def _exec(self):
        self.log(f"Executing task {self._active_task}")


        executing_task = self._active_task
        self._active_task = None

        executing_task.executed_by = self.name
        executing_task.is_completed = True

        exec_duration = TICK_COUNT_BY_STATUS.get(self._status, 1)
        executing_task.actual_start_time = self._current_tick - exec_duration
        executing_task.actual_end_time = self._current_tick

        self._callback_on_complete(executing_task)
        self._callback_on_complete = None

        self.set_status(Status.WAIT)
