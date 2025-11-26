from components import CommandExecutor, Task, TaskType, TaskExporter, PlotGenerator


def main():
    print("Start program")

    executor = CommandExecutor(tpc_count=2)

    # tasks = [
    #     Task(0, 10, TaskType.VPU),
    #     Task(15, 50, TaskType.ME),
    #     Task(15, 50, TaskType.ME),
    #     Task(0, 50, TaskType.VPU),
    #     Task(20, 70, TaskType.ME),
    #     Task(15, 50, TaskType.ME),
    #     Task(70, 80, TaskType.VPU),
    #     Task(88, 90, TaskType.ME),
    #     Task(40, 50, TaskType.FE),
    # ]

    tasks = [
        Task(0, 10, TaskType.VPU),
        Task(11, 20, TaskType.VPU),
        Task(21, 30, TaskType.VPU),
        Task(31, 40, TaskType.VPU),
        Task(41, 50, TaskType.VPU),
        Task(51, 60, TaskType.VPU),
        Task(61, 70, TaskType.VPU),
        Task(71, 80, TaskType.VPU),
    ]

    print("\nInitial tasks:")
    for t in tasks:
        print(t)

    completed_tasks, total_ticks = executor.execute(tasks)

    executor.print_summary()

    print("\n" + "=" * 60)
    print("Completed tasks with timing information:")
    print("=" * 60)
    for t in completed_tasks:
        print(t)

    print("\n" + "=" * 60)
    print("Exporting results to tasks.json...")
    print("=" * 60)
    TaskExporter.export_to_json(completed_tasks, "tasks.json")

    print("\n" + "=" * 60)
    print("Generating visualization plots...")
    print("=" * 60)
    PlotGenerator.generate_all_plots(completed_tasks, total_ticks, output_dir=".")

    print("End program")


if __name__ == "__main__":
    import sys

    try:
        import pytest
    except Exception:
        print(
            "pytest is required to run tests before starting. Install it with: python -m pip install pytest"
        )
        sys.exit(1)

    rc = pytest.main(["-q", "TestCommandExecutor.py"])
    if rc != 0:
        print(f"Tests failed (exit code={rc}). Aborting run.")
        sys.exit(rc)

    main()
