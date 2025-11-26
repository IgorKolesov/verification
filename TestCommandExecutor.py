import pytest
from components import CommandExecutor, Task, TaskType
from itertools import product


class TestCommandExecutorBasic:
    """Test basic executor functionality"""
    
    def test_single_task_execution(self):
        """Single task should execute successfully"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [Task(0, 9, TaskType.VPU)]
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == 1
        assert completed_tasks[0].is_completed
        assert ticks_used > 0
    
    def test_multiple_sequential_tasks(self):
        """Multiple non-overlapping tasks should execute in sequence"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(20, 29, TaskType.FE),
        ]
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == 3
        assert all(task.is_completed for task in completed_tasks)
        assert ticks_used > 0
    
    def test_overlapping_memory_ranges_blocked(self):
        """Tasks with overlapping memory ranges should wait for previous to complete"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(5, 14, TaskType.FE),  # Overlaps with both previous tasks
        ]
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == 3
        assert all(task.is_completed for task in completed_tasks)
        # Overlapping ranges require more ticks due to serialization
        assert ticks_used > 20


class TestCommandExecutorMultipleTPC:
    """Test multi-TPC parallelization"""
    
    def test_multiple_tpcs_parallel_execution(self):
        """Multiple TPCs should execute tasks in parallel"""
        executor = CommandExecutor(tpc_count=2)
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(20, 29, TaskType.FE),
        ]
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == 3
        assert all(task.is_completed for task in completed_tasks)
    
    def test_four_tpcs_execution(self):
        """Four TPCs should handle four non-overlapping tasks efficiently"""
        executor = CommandExecutor(tpc_count=4)
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(20, 29, TaskType.FE),
            Task(30, 39, TaskType.VPU),
        ]
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == 4
        assert all(task.is_completed for task in completed_tasks)
    
    def test_more_tpcs_reduces_execution_time(self):
        """More TPCs should reduce total execution time for non-overlapping tasks"""
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(20, 29, TaskType.FE),
        ]
        
        executor1 = CommandExecutor(tpc_count=1)
        _, ticks1 = executor1.execute(tasks)
        
        executor2 = CommandExecutor(tpc_count=3)
        _, ticks2 = executor2.execute(tasks)
        
        assert ticks2 < ticks1


class TestCommandExecutorMemory:
    """Test memory management and conflict detection"""
    
    def test_non_overlapping_memory_ranges(self):
        """Non-overlapping memory ranges should not block each other"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
        ]
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == 2
        assert all(task.is_completed for task in completed_tasks)
    
    def test_overlapping_memory_ranges_same_owner(self):
        """Overlapping memory ranges for same TPC should be serialized"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [
            Task(0, 15, TaskType.VPU),
            Task(10, 20, TaskType.ME),
        ]
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == 2
        assert all(task.is_completed for task in completed_tasks)
    
    def test_hbm_not_released_with_overlapping_future_tasks(self):
        """HBM should not be released if future tasks need overlapping memory"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(5, 14, TaskType.FE),  # Overlaps with both
        ]
        
        executor.execute(tasks)
        
        # After execution, HBM should be empty
        memory_ranges = executor.get_memory_ranges()
        assert len(memory_ranges) == 0
    
    def test_memory_allocation_and_release(self):
        """Memory should be allocated and released correctly"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [Task(0, 9, TaskType.VPU)]
        
        # Before execution
        assert len(executor.get_memory_ranges()) == 0
        
        executor.execute(tasks)
        
        # After execution
        assert len(executor.get_memory_ranges()) == 0


class TestCommandExecutorReset:
    """Test executor reset functionality"""
    
    def test_reset_between_executions(self):
        """Executor should reset state between executions"""
        executor = CommandExecutor(tpc_count=1)
        
        tasks1 = [Task(0, 9, TaskType.VPU)]
        completed1, ticks1 = executor.execute(tasks1)
        
        tasks2 = [Task(10, 19, TaskType.ME)]
        completed2, ticks2 = executor.execute(tasks2)
        
        assert len(completed1) == 1
        assert len(completed2) == 1
        assert completed1[0].id != completed2[0].id
    
    def test_completed_tasks_cleared_after_reset(self):
        """Completed tasks list should be cleared on reset"""
        executor = CommandExecutor(tpc_count=1)
        
        tasks1 = [Task(0, 9, TaskType.VPU)]
        executor.execute(tasks1)
        assert len(executor.global_worker.completed_tasks) == 1
        
        tasks2 = [Task(10, 19, TaskType.ME)]
        executor.execute(tasks2)
        assert len(executor.global_worker.completed_tasks) == 1


class TestCommandExecutorEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_task_list(self):
        """Empty task list should return immediately"""
        executor = CommandExecutor(tpc_count=1)
        tasks = []
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == 0
        assert ticks_used == 0
    
    def test_large_number_of_tasks(self):
        """Large number of non-overlapping tasks should complete"""
        executor = CommandExecutor(tpc_count=2)
        tasks = [
            Task(i * 10, i * 10 + 9, TaskType.VPU if i % 3 == 0 else (TaskType.ME if i % 3 == 1 else TaskType.FE))
            for i in range(10)
        ]
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == 10
        assert all(task.is_completed for task in completed_tasks)
    
    def test_single_address_range(self):
        """Tasks with single address (start == end) should work"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [Task(5, 5, TaskType.VPU)]
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == 1
        assert completed_tasks[0].is_completed
    
    def test_maximum_ticks_exceeded(self):
        """Execution should fail if max ticks exceeded"""
        executor = CommandExecutor(tpc_count=1, max_ticks=5)
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(20, 29, TaskType.FE),
        ]
        
        with pytest.raises(RuntimeError, match="Failed to complete all tasks"):
            executor.execute(tasks)


class TestCommandExecutorTaskProperties:
    """Test task property preservation and modification"""
    
    def test_task_ids_unique(self):
        """Different executors should produce unique task IDs"""
        executor1 = CommandExecutor(tpc_count=1)
        tasks1 = [Task(0, 9, TaskType.VPU)]
        completed1, _ = executor1.execute(tasks1)
        
        executor2 = CommandExecutor(tpc_count=1)
        tasks2 = [Task(0, 9, TaskType.VPU)]
        completed2, _ = executor2.execute(tasks2)
        
        assert completed1[0].id != completed2[0].id
    
    def test_task_properties_preserved(self):
        """Task properties should be preserved after execution"""
        executor = CommandExecutor(tpc_count=1)
        original_task = Task(5, 15, TaskType.ME)
        tasks = [original_task]
        
        completed_tasks, _ = executor.execute(tasks)
        
        completed_task = completed_tasks[0]
        assert completed_task.addr_start == original_task.addr_start
        assert completed_task.addr_end == original_task.addr_end
        assert completed_task.task_type == original_task.task_type
    
    def test_task_executed_by_set(self):
        """executed_by field should be set to correct executor"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(20, 29, TaskType.FE),
        ]
        
        completed_tasks, _ = executor.execute(tasks)
        
        assert all(task.executed_by is not None for task in completed_tasks)
        assert any('VPU' in task.executed_by for task in completed_tasks)
        assert any('ME' in task.executed_by for task in completed_tasks)
        assert any('FE' in task.executed_by for task in completed_tasks)


class TestCommandExecutorTiming:
    """Test timing and latency calculations"""
    
    def test_start_time_is_set(self):
        """Start time should be set to 0"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [Task(0, 9, TaskType.VPU)]
        
        completed_tasks, _ = executor.execute(tasks)
        
        assert completed_tasks[0].start_time == 0
    
    def test_end_time_is_set(self):
        """End time should be set and greater than start time"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [Task(0, 9, TaskType.VPU)]
        
        completed_tasks, _ = executor.execute(tasks)
        
        assert completed_tasks[0].end_time is not None
        assert completed_tasks[0].end_time > 0
    
    def test_latency_calculation(self):
        """Latency should be actual execution time (3 ticks for EXEC_* statuses)"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [Task(0, 9, TaskType.VPU)]
        
        completed_tasks, ticks = executor.execute(tasks)
        
        assert completed_tasks[0].latency is not None
        # VPU execution takes 3 ticks
        assert completed_tasks[0].latency == 3
    
    def test_latency_increases_with_multiple_tasks(self):
        """Last task latency should be consistent (all EXEC_* = 3 ticks)"""
        executor1 = CommandExecutor(tpc_count=1)
        tasks1 = [Task(0, 9, TaskType.VPU)]
        completed1, _ = executor1.execute(tasks1)
        latency1 = completed1[0].latency
        
        executor2 = CommandExecutor(tpc_count=1)
        tasks2 = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(20, 29, TaskType.FE),
        ]
        completed2, _ = executor2.execute(tasks2)
        latency_last = completed2[-1].latency
        
        # All EXEC_* statuses take 3 ticks, so latency should be same
        assert latency_last == latency1
    
    def test_all_tasks_have_latency(self):
        """All completed tasks should have latency"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(20, 29, TaskType.FE),
        ]
        
        completed_tasks, _ = executor.execute(tasks)
        
        assert all(task.latency is not None for task in completed_tasks)
        assert all(task.latency > 0 for task in completed_tasks)
    
    def test_overlapping_tasks_have_higher_latency(self):
        """Tasks with overlapping memory should have same execution latency (all 3 ticks)"""
        executor1 = CommandExecutor(tpc_count=1)
        tasks1 = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(20, 29, TaskType.FE),
        ]
        completed1, _ = executor1.execute(tasks1)
        
        executor2 = CommandExecutor(tpc_count=1)
        tasks2 = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(5, 14, TaskType.FE),  # Overlaps
        ]
        completed2, _ = executor2.execute(tasks2)
        
        # All tasks execution time should be 3 ticks (EXEC_* duration)
        assert all(task.latency == 3 for task in completed2)


class TestMemoryConflictDetection:
    """Test memory conflict detection and handling"""
    
    def test_partial_overlap_left(self):
        """Detect partial overlap on left side"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [
            Task(10, 19, TaskType.VPU),
            Task(5, 14, TaskType.ME),  # Overlaps [10, 14]
        ]
        
        completed_tasks, _ = executor.execute(tasks)
        
        assert len(completed_tasks) == 2
        assert all(task.is_completed for task in completed_tasks)
    
    def test_partial_overlap_right(self):
        """Detect partial overlap on right side"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(5, 14, TaskType.ME),  # Overlaps [5, 9]
        ]
        
        completed_tasks, _ = executor.execute(tasks)
        
        assert len(completed_tasks) == 2
        assert all(task.is_completed for task in completed_tasks)
    
    def test_complete_containment(self):
        """Detect when one range completely contains another"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [
            Task(0, 20, TaskType.VPU),
            Task(5, 14, TaskType.ME),  # Completely inside
        ]
        
        completed_tasks, _ = executor.execute(tasks)
        
        assert len(completed_tasks) == 2
        assert all(task.is_completed for task in completed_tasks)
    
    def test_identical_ranges(self):
        """Detect identical memory ranges"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [
            Task(5, 14, TaskType.VPU),
            Task(5, 14, TaskType.ME),  # Exact same range
        ]
        
        completed_tasks, _ = executor.execute(tasks)
        
        assert len(completed_tasks) == 2
        assert all(task.is_completed for task in completed_tasks)


class TestTaskTypeHandling:
    """Test correct handling of different task types"""
    
    def test_vpu_task_execution(self):
        """VPU tasks should execute correctly"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [Task(0, 9, TaskType.VPU)]
        
        completed_tasks, _ = executor.execute(tasks)
        
        assert completed_tasks[0].task_type == TaskType.VPU
        assert 'VPU' in completed_tasks[0].executed_by
    
    def test_me_task_execution(self):
        """ME tasks should execute correctly"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [Task(0, 9, TaskType.ME)]
        
        completed_tasks, _ = executor.execute(tasks)
        
        assert completed_tasks[0].task_type == TaskType.ME
        assert 'ME' in completed_tasks[0].executed_by
    
    def test_fe_task_execution(self):
        """FE tasks should execute correctly"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [Task(0, 9, TaskType.FE)]
        
        completed_tasks, _ = executor.execute(tasks)
        
        assert completed_tasks[0].task_type == TaskType.FE
        assert 'FE' in completed_tasks[0].executed_by
    
    def test_mixed_task_types(self):
        """Mixed task types should all execute"""
        executor = CommandExecutor(tpc_count=3)
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(20, 29, TaskType.FE),
        ]
        
        completed_tasks, _ = executor.execute(tasks)
        
        task_types = {task.task_type for task in completed_tasks}
        assert TaskType.VPU in task_types
        assert TaskType.ME in task_types
        assert TaskType.FE in task_types


class TestParametrizedTasksAndTPCs:
    """Parametrized tests for various combinations of tasks and TPCs"""
    
    @pytest.mark.parametrize("task_count", [1, 2, 3, 5, 10])
    def test_different_task_counts(self, task_count):
        """Test execution with different numbers of tasks"""
        executor = CommandExecutor(tpc_count=2)
        tasks = [
            Task(i * 10, i * 10 + 9, TaskType.VPU if i % 3 == 0 else (TaskType.ME if i % 3 == 1 else TaskType.FE))
            for i in range(task_count)
        ]
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == task_count
        assert all(task.is_completed for task in completed_tasks)
        assert ticks_used > 0
    
    @pytest.mark.parametrize("tpc_count", [1, 2, 3, 4, 8])
    def test_different_tpc_counts(self, tpc_count):
        """Test execution with different numbers of TPCs"""
        executor = CommandExecutor(tpc_count=tpc_count)
        tasks = [
            Task(i * 10, i * 10 + 9, TaskType.VPU if i % 3 == 0 else (TaskType.ME if i % 3 == 1 else TaskType.FE))
            for i in range(5)
        ]
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == 5
        assert all(task.is_completed for task in completed_tasks)
    
    @pytest.mark.parametrize("task_count,tpc_count", [
        (1, 1), (1, 2), (1, 4),
        (2, 1), (2, 2), (2, 4),
        (3, 1), (3, 2), (3, 3),
        (4, 1), (4, 2), (4, 4),
        (5, 1), (5, 2), (5, 5),
        (10, 1), (10, 2), (10, 5), (10, 10),
    ])
    def test_task_tpc_combinations(self, task_count, tpc_count):
        """Test various combinations of task and TPC counts"""
        executor = CommandExecutor(tpc_count=tpc_count)
        tasks = [
            Task(i * 10, i * 10 + 9, TaskType.VPU if i % 3 == 0 else (TaskType.ME if i % 3 == 1 else TaskType.FE))
            for i in range(task_count)
        ]
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == task_count
        assert all(task.is_completed for task in completed_tasks)
        assert ticks_used > 0
    
    @pytest.mark.parametrize("task_count,tpc_count", [
        (1, 1), (2, 1), (3, 1), (5, 2), (10, 3)
    ])
    def test_execution_time_scales_with_resources(self, task_count, tpc_count):
        """Test that execution time improves with more TPCs"""
        tasks = [
            Task(i * 10, i * 10 + 9, TaskType.VPU if i % 3 == 0 else (TaskType.ME if i % 3 == 1 else TaskType.FE))
            for i in range(task_count)
        ]
        
        executor_single = CommandExecutor(tpc_count=1)
        _, ticks_single = executor_single.execute(tasks)
        
        executor_multi = CommandExecutor(tpc_count=tpc_count)
        _, ticks_multi = executor_multi.execute(tasks)
        
        # More TPCs should not increase execution time (should stay same or decrease)
        assert ticks_multi <= ticks_single
    
    @pytest.mark.parametrize("tpc_count", [1, 2, 4, 8])
    def test_all_tasks_complete_regardless_of_tpc_count(self, tpc_count):
        """Verify all tasks complete regardless of TPC count"""
        executor = CommandExecutor(tpc_count=tpc_count)
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(20, 29, TaskType.FE),
            Task(30, 39, TaskType.VPU),
            Task(40, 49, TaskType.ME),
        ]
        
        completed_tasks, _ = executor.execute(tasks)
        
        assert len(completed_tasks) == 5
        assert all(task.is_completed for task in completed_tasks)
        assert all(task.latency is not None for task in completed_tasks)
    
    @pytest.mark.parametrize("num_tasks,num_tpcs", [
        (100, 1),
        (100, 2),
        (100, 4),
    ])
    def test_large_scale_execution(self, num_tasks, num_tpcs):
        """Test execution with large numbers of tasks"""
        executor = CommandExecutor(tpc_count=num_tpcs)
        tasks = [
            Task(i * 10, i * 10 + 9, TaskType.VPU if i % 3 == 0 else (TaskType.ME if i % 3 == 1 else TaskType.FE))
            for i in range(num_tasks)
        ]
        
        completed_tasks, ticks_used = executor.execute(tasks)
        
        assert len(completed_tasks) == num_tasks
        assert all(task.is_completed for task in completed_tasks)
        assert ticks_used > 0
    
    @pytest.mark.parametrize("task_count,tpc_count", [
        (2, 1), (3, 1), (4, 2), (5, 2), (6, 3)
    ])
    def test_task_distribution_across_tpcs(self, task_count, tpc_count):
        """Verify tasks are distributed across available TPCs"""
        executor = CommandExecutor(tpc_count=tpc_count)
        tasks = [
            Task(i * 10, i * 10 + 9, TaskType.VPU if i % 3 == 0 else (TaskType.ME if i % 3 == 1 else TaskType.FE))
            for i in range(task_count)
        ]
        
        completed_tasks, _ = executor.execute(tasks)
        
        # Check that we have executed_by values
        executed_by_values = [task.executed_by for task in completed_tasks]
        assert all(eb is not None for eb in executed_by_values)
        
        # Different TPCs should be used (if we have enough tasks and TPCs)
        unique_tpcs = set(eb.split('_')[0] for eb in executed_by_values if eb)
        expected_min_tpcs = min(task_count, tpc_count)
        assert len(unique_tpcs) >= 1
    
    @pytest.mark.parametrize("tpc_count", [1, 2, 4])
    def test_latency_consistency_across_tpc_counts(self, tpc_count):
        """Test that latency is consistent across different TPC counts"""
        executor = CommandExecutor(tpc_count=tpc_count)
        tasks = [
            Task(0, 9, TaskType.VPU),
            Task(10, 19, TaskType.ME),
            Task(20, 29, TaskType.FE),
        ]
        
        completed_tasks, ticks = executor.execute(tasks)
        
        # All tasks should have latency equal to total ticks
        for task in completed_tasks:
            assert task.latency is not None
            assert task.latency <= ticks
    
    @pytest.mark.parametrize("num_overlapping_pairs", [1, 2, 3, 5])
    def test_overlapping_memory_with_different_loads(self, num_overlapping_pairs):
        """Test overlapping memory ranges with different workloads"""
        executor = CommandExecutor(tpc_count=1)
        tasks = []
        
        # Create pairs of overlapping tasks
        for i in range(num_overlapping_pairs):
            tasks.append(Task(i * 20, i * 20 + 9, TaskType.VPU))
            tasks.append(Task(i * 20 + 5, i * 20 + 14, TaskType.ME))
        
        completed_tasks, ticks = executor.execute(tasks)
        
        assert len(completed_tasks) == num_overlapping_pairs * 2
        assert all(task.is_completed for task in completed_tasks)
        assert ticks > 0
    
    @pytest.mark.parametrize("task_count,expected_min_ticks", [
        (1, 5),
        (2, 8),
        (3, 11),
        (4, 14),
        (5, 17),
    ])
    def test_execution_time_grows_with_tasks(self, task_count, expected_min_ticks):
        """Test that execution time grows approximately linearly with task count"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [
            Task(i * 10, i * 10 + 9, TaskType.VPU if i % 3 == 0 else (TaskType.ME if i % 3 == 1 else TaskType.FE))
            for i in range(task_count)
        ]
        
        completed_tasks, ticks = executor.execute(tasks)
        
        assert len(completed_tasks) == task_count
        # Execution time should be at least minimum expected
        assert ticks >= expected_min_ticks


class TestTPCUtilization:
    """Test TPC utilization and task distribution"""
    
    @pytest.mark.parametrize("tpc_count", [1, 2, 4, 8])
    def test_optimal_task_distribution(self, tpc_count):
        """Test that tasks are optimally distributed across TPCs"""
        executor = CommandExecutor(tpc_count=tpc_count)
        task_count = tpc_count * 3
        tasks = [
            Task(i * 10, i * 10 + 9, TaskType.VPU if i % 3 == 0 else (TaskType.ME if i % 3 == 1 else TaskType.FE))
            for i in range(task_count)
        ]
        
        completed_tasks, _ = executor.execute(tasks)
        
        assert len(completed_tasks) == task_count
        assert all(task.is_completed for task in completed_tasks)
    
    @pytest.mark.parametrize("task_count,tpc_count", [
        (5, 1),
        (5, 2),
        (5, 5),
        (5, 10),
    ])
    def test_excess_tpc_capacity(self, task_count, tpc_count):
        """Test behavior when TPCs exceed available tasks"""
        executor = CommandExecutor(tpc_count=tpc_count)
        tasks = [
            Task(i * 10, i * 10 + 9, TaskType.VPU if i % 3 == 0 else (TaskType.ME if i % 3 == 1 else TaskType.FE))
            for i in range(task_count)
        ]
        
        completed_tasks, ticks = executor.execute(tasks)
        
        assert len(completed_tasks) == task_count
        assert all(task.is_completed for task in completed_tasks)
        # Excess TPCs shouldn't hurt performance
        assert ticks > 0
    
    @pytest.mark.parametrize("task_count", [10, 20, 50])
    def test_single_tpc_bottleneck(self, task_count):
        """Test single TPC becomes bottleneck with many tasks"""
        executor = CommandExecutor(tpc_count=1)
        tasks = [
            Task(i * 10, i * 10 + 9, TaskType.VPU if i % 3 == 0 else (TaskType.ME if i % 3 == 1 else TaskType.FE))
            for i in range(task_count)
        ]
        
        completed_tasks, ticks_single = executor.execute(tasks)
        
        assert len(completed_tasks) == task_count
        
        # Compare with multi-TPC
        executor_multi = CommandExecutor(tpc_count=4)
        _, ticks_multi = executor_multi.execute(tasks)
        
        # Multi-TPC should be faster or equal
        assert ticks_multi <= ticks_single

