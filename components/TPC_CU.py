from .Unit import Unit
from .Status import Status
from .Memory import Memory
from .TaskType import TaskType
from .BColors import BColors
from typing import TYPE_CHECKING, List, Tuple, Callable, Dict

if TYPE_CHECKING:
    from .Task import Task
    from .TPC import TPC
    from .TPC_Executor import TPC_Executor


class TPC_CU(Unit):
    def __init__(self, tpc: "TPC"):
        super().__init__(f"{tpc.name}_CU", BColors.WARNING, 2)
        self._queue: List["Task"] = []
        self._tpc: "TPC" = tpc
        self.noc: List[Tuple[int, int, "TPC_Executor" | None]] = []
        self._callback_on_complete_by_task: Dict["Task", Callable[["Task"], None]] = {}
        self._max_queue_len: int = 20
        self._send_queue: List["Task"] = []

    def get_queue_length(self) -> int:
        return len(self._queue)

    def add_task(self, task: "Task", callback_on_complete: Callable[["Task"], None]):
        self.log(f"Adding {task} to CU queue (len={len(self._queue)})")
        if len(self._queue) >= self._max_queue_len:
            self.log(f"CU queue full (limit={self._max_queue_len}), rejecting {task}")
            return False

        self._queue.append(task)
        self._callback_on_complete_by_task[task] = callback_on_complete
        return True

    def _on_complete_task(self, task: "Task"):
        self.log(f"Scheduling send-to-global for completed task {task}")
        Memory.free_owner(self.noc, task.addr_start, task.addr_end)
        self._send_queue.append(task)

        busy = (
            self._tpc._VPU_executor.get_active_task() is not None or
            self._tpc._ME_executor.get_active_task() is not None or
            self._tpc._FE_executor.get_active_task() is not None
        )

        if busy or self._queue:
                self.log("Executors busy or CU queue not empty — staying in WAIT")
                self.set_status(Status.WAIT)
                return

        self.set_status(Status.SEND_TO_GLOBAL)

    def _is_in_noc(self, task: "Task") -> bool:
        return Memory.is_contained(self.noc, task.addr_start, task.addr_end)

    def _action(self):
        self.log(f"Queue length: {len(self._queue)}")

        if self.noc:
            for s, e, tpc in self.noc:
                self.log(f"Occupied NOC range: [{s}, {e}] -> {tpc.name if tpc else 'None'}")

        self.log(f"Status: {self._status.name}")

        match self._status:
            case Status.WAIT:
                self._wait()
            case Status.SEND_TO_GLOBAL:
                self._send_to_global()
            case Status.COLLECT_TO_LOCAL:
                self._collect_to_local()

    def _wait(self):
        self.log("Checking for tasks in CU queue")

        if not self._queue:
            self.log("No tasks in queue")
            return

        task = self._queue[0]
        if not self._is_in_noc(task):
            self.set_status(Status.COLLECT_TO_LOCAL)
            return

        task = self._queue[0]
        executor = self._get_executor(task.task_type)

        if Memory.check_conflict(self.noc, task.addr_start, task.addr_end, executor, ignore_none=True):
            self.log("Memory conflict detected")
            return

        if executor.get_active_task() is not None:
            self.log("Executor is busy")
            return

        Memory.allocate(self.noc, task.addr_start, task.addr_end, executor, ignore_none=True)
        executor.set_active_task(self._queue.pop(0), self._on_complete_task)
        self.set_status(Status.WAIT)

    def _collect_to_local(self):
        task = self._queue[0]
        self.log(f"Loading {task} from global memory")
        self.noc.append((task.addr_start, task.addr_end, None))
        self.set_status(Status.WAIT)

    def _send_to_global(self):
        self.log("Processing send-to-global queue")

        if not self._send_queue:
            self.set_status(Status.WAIT)
            return

        tasks_to_send = self._send_queue[:]
        self._send_queue.clear()

        for task in tasks_to_send:
            self.log(f"Sending results of {task} to global memory")

            still_queued = any(
                t != task and t.addr_start == task.addr_start and t.addr_end == task.addr_end
                for t in self._queue
            )

            active_same_range = False
            for exec_ in (self._tpc._VPU_executor, self._tpc._ME_executor, self._tpc._FE_executor):
                active = exec_.get_active_task()
                if active and active.addr_start == task.addr_start and active.addr_end == task.addr_end:
                    active_same_range = True
                    break

            if still_queued or active_same_range:
                self.log(f"Skipping memory release for {task}: range still in use")
            else:
                try:
                    Memory.release(self.noc, task.addr_start, task.addr_end)
                except Exception:
                    self.log(f"Warning: failed to release NoC range for {task}")

            callback = self._callback_on_complete_by_task.pop(task, None)
            if callback:
                callback(task)

        self.set_status(Status.WAIT)

    def _get_executor(self, task_type: "TaskType") -> "TPC_Executor":
        match task_type:
            case TaskType.VPU:
                return self._tpc._VPU_executor
            case TaskType.ME:
                return self._tpc._ME_executor
            case TaskType.FE:
                return self._tpc._FE_executor
