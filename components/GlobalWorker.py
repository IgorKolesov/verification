from .Unit import Unit
from .Memory import Memory
from typing import TYPE_CHECKING, List, Tuple, Optional
from .BColors import BColors

if TYPE_CHECKING:
    from .Task import Task
    from .TPC import TPC


class GlobalWorker(Unit):
    def __init__(self, name: str, tasks: List["Task"], tpcs: List["TPC"]):
        super().__init__(name, BColors.OKBLUE, 1)
        self._queue: List["Task"] = tasks
        self._tpcs: List["TPC"] = tpcs
        self.completed_tasks: List["Task"] = []
        self.hbm: List[Tuple[int, int, "TPC"]] = []

    def _action(self):
        self.log(f"Queue length: {len(self._queue)}")

        if self.hbm:
            for s, e, tpc in self.hbm:
                self.log(
                    f"Occupied HBM range: [{s}, {e}] -> {tpc.name if tpc else 'None'}"
                )

        if not self._queue:
            return

        while self._queue:
            candidate_task = self._queue[0]

            assigned_tpc = self._find_tpc_by_hbm_range(candidate_task)
            self.log(f"Assigned TPC from HBM range: {assigned_tpc}")

            if assigned_tpc is None:
                for tpc in sorted(self._tpcs, key=lambda t: (t.get_workload(), t.get_total_task_count())):
                    if not any(
                        Memory.ranges_overlap(candidate_task.addr_start, candidate_task.addr_end, s, e)
                        for s, e, _ in self.hbm
                    ):
                        assigned_tpc = tpc
                        break

                if assigned_tpc is None:
                    self.log("All TPCs are busy or memory ranges conflict, waiting...")
                    break

            self.log(f"Attempting to assign {candidate_task} to {assigned_tpc.name}")

            accepted = assigned_tpc.add_task(candidate_task, self._on_complete_task)
            if not accepted:
                self.log(f"{assigned_tpc.name} rejected task (CU full). Will retry later.")
                break

            Memory.allocate(self.hbm, candidate_task.addr_start, candidate_task.addr_end, assigned_tpc)
            candidate_task.assigned_tpc = assigned_tpc
            self._queue.pop(0)

    def _on_complete_task(self, task: "Task"):
        self.log(f"{task} completed and collected")
        self.completed_tasks.append(task)

        if task.assigned_tpc is not None:
            cu = task.assigned_tpc._TPC_CU
            
            has_overlapping_tasks = any(
                Memory.ranges_overlap(task.addr_start, task.addr_end, t.addr_start, t.addr_end)
                for t in cu._queue
            )
            
            has_overlapping_in_noc = any(
                Memory.ranges_overlap(task.addr_start, task.addr_end, s, e)
                for s, e, _ in cu.noc
            )
            
            if not has_overlapping_tasks and not has_overlapping_in_noc:
                self.log(f"Releasing HBM for {task}")
                Memory.release(self.hbm, task.addr_start, task.addr_end)
            else:
                self.log(
                    f"HBM not released (overlapping_tasks={has_overlapping_tasks}, overlapping_noc={has_overlapping_in_noc})"
                )
        else:
            self.log(f"Task has no assigned_tpc, cannot release HBM")

    def _select_least_loaded_tpc(self) -> "TPC":
        return min(self._tpcs, key=lambda t: t.get_total_task_count())

    def _find_tpc_by_hbm_range(self, task: "Task") -> Optional["TPC"]:
        for s, e, tpc in self.hbm:
            if task.addr_start >= s and task.addr_end <= e:
                return tpc
        return None
