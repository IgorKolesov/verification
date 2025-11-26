from typing import List
from .TPC import TPC
from .Task import Task
from .GlobalWorker import GlobalWorker
from .Unit import Unit, _ENABLE_PRINTS
from .Time import Time


class CommandExecutor:
    def __init__(self, tpc_count: int = 1, max_ticks: int = 10000):
        self.tpc_count = tpc_count
        self.max_ticks = max_ticks
        self.time = Time()

        self.tpcs: List[TPC] = [TPC(name=f"TPC_{i+1}") for i in range(tpc_count)]

        self.global_worker = GlobalWorker("GlobalWorker", [], self.tpcs)

        self.units: List[Unit] = [self.global_worker, *self.tpcs]

        self._current_tick = 0
        self._all_completed = False

    def execute(self, tasks: List[Task]) -> tuple[List[Task], int]:
        self._reset()

        if not tasks:
            return [], 0

        for task in tasks:
            task.start_time = 0

        self.global_worker._queue = tasks.copy()

        while self._current_tick < self.max_ticks:
            for tpc in self.tpcs:
                tpc.set_current_tick(self._current_tick)
            
            for unit in self.units:
                unit.tick()
                if _ENABLE_PRINTS:
                    print(unit)

            self.time.tick()
            if _ENABLE_PRINTS:
                print(self.time)
            self._current_tick += 1

            if self._are_all_tasks_completed():
                self._all_completed = True
                break

        if not self._all_completed:
            raise RuntimeError(
                f"Failed to complete all tasks within {self.max_ticks} ticks"
            )

        completed_tasks = self.global_worker.completed_tasks.copy()
        for task in completed_tasks:
            task.end_time = self._current_tick

        self._cleanup_remaining_hbm(completed_tasks)

        ticks_used = self._current_tick

        return completed_tasks, ticks_used

    def get_memory_ranges(self) -> List[tuple]:
        return self.global_worker.hbm.copy()

    def _reset(self):
        self._current_tick = 0
        self._all_completed = False
        self.time.reset()

        self.global_worker.completed_tasks.clear()
        self.global_worker.hbm.clear()
        self.global_worker._queue.clear()

        for tpc in self.tpcs:
            tpc._TPC_CU._queue.clear()
            tpc._TPC_CU.noc.clear()
            tpc._TPC_CU._callback_on_complete_by_task.clear()
            tpc._TPC_CU.set_status(tpc._TPC_CU._status.__class__.WAIT)

            for executor in [tpc._VPU_executor, tpc._ME_executor, tpc._FE_executor]:
                executor._active_task = None
                executor._callback_on_complete = None
                executor.set_status(executor._status.__class__.WAIT)

    def _are_all_tasks_completed(self) -> bool:
        # Все задачи завершены если:
        # 1. Очередь GlobalWorker пуста
        # 2. Нет задач в очередях CU
        # 3. Нет активных задач в executors
        # 4. Нет задач в памяти NoC

        if self.global_worker._queue:
            return False

        for tpc in self.tpcs:
            if tpc._TPC_CU._queue:
                return False

            for executor in [tpc._VPU_executor, tpc._ME_executor, tpc._FE_executor]:
                if executor._active_task is not None:
                    return False

            if tpc._TPC_CU.noc:
                return False

        return True

    def _cleanup_remaining_hbm(self, completed_tasks: List[Task]):
        from .Memory import Memory

        for task in completed_tasks:
            if task.assigned_tpc is not None:
                cu = task.assigned_tpc._TPC_CU
                if not cu._queue and not cu.noc:
                    if any(
                        (s, e) == (task.addr_start, task.addr_end)
                        for s, e, _ in self.global_worker.hbm
                    ):
                        self.global_worker.log(
                            f"Final cleanup: Releasing HBM for {task}"
                        )
                        Memory.release(
                            self.global_worker.hbm, task.addr_start, task.addr_end
                        )

    def print_summary(self):
        if not _ENABLE_PRINTS:
            return

        print(f"Simulation completed in {self._current_tick} ticks")
        print(f"\nCompleted tasks: {len(self.global_worker.completed_tasks)}")
        print("\nCompleted tasks list:")
        for task in self.global_worker.completed_tasks:
            print(f"  {task}")

        print("\nOccupied HBM ranges:")
        if self.global_worker.hbm:
            for s, e, tpc in self.global_worker.hbm:
                print(f"  [{s}, {e}] -> {tpc.name if tpc else 'None'}")
        else:
            print("  No occupied ranges")
        print(f"{'='*60}\n")
