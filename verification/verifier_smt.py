import z3
from components import Task, TaskType

def verify_no_memory_conflicts(tasks, scenario_name=""):
    if scenario_name:
        print(f"\nСценарий: {scenario_name}")
    else:
        print("\nПроверка памяти:")

    solver = z3.Solver()

    # Создаем переменные для каждой задачи
    task_vars = []
    for i, t in enumerate(tasks):
        s = z3.Int(f"s_{i}")
        e = z3.Int(f"e_{i}")
        active = z3.Bool(f"active_{i}")
        task_vars.append((s, e, active))

        # Ограничения по адресам
        solver.add(s == t.addr_start)
        solver.add(e == t.addr_end)
        solver.add(active == True)

    # Ограничения на отсутствие пересечений
    n = len(tasks)
    for i in range(n):
        for j in range(i + 1, n):
            s_i, e_i, active_i = task_vars[i]
            s_j, e_j, active_j = task_vars[j]
            solver.add(z3.Or(s_i >= e_j, s_j >= e_i, z3.Not(active_i), z3.Not(active_j)))

    # Проверка
    if solver.check() == z3.sat:
        print("Конфликтов памяти не найдено")
    else:
        print("Error: Найден конфликт памяти!")
        for i in range(n):
            for j in range(i + 1, n):
                t1, t2 = tasks[i], tasks[j]
                if t1.addr_end > t2.addr_start and t2.addr_end > t1.addr_start:
                    print(f"Task {i}: {t1}")
                    print(f"Task {j}: {t2}\n")

    print('='*70)


def main():
    # Сценарий 1: простые пересечения
    tasks1 = [
        Task(0, 10, TaskType.VPU),
        Task(5, 15, TaskType.VPU),
        Task(20, 30, TaskType.ME),
    ]
    verify_no_memory_conflicts(tasks1, "Пересечение 1")

    # Сценарий 2: пересечения между разными типами задач
    tasks2 = [
        Task(0, 10, TaskType.VPU),
        Task(8, 12, TaskType.ME),
        Task(12, 20, TaskType.FE),
    ]
    verify_no_memory_conflicts(tasks2, "Пересечение между типами")

    # Сценарий 3: без пересечений
    tasks3 = [
        Task(0, 10, TaskType.VPU),
        Task(10, 20, TaskType.VPU),
        Task(20, 30, TaskType.ME),
    ]
    verify_no_memory_conflicts(tasks3, "Без пересечений")

    # Сценарий 4: полный конфликт
    tasks4 = [
        Task(0, 50, TaskType.VPU),
        Task(0, 50, TaskType.ME),
        Task(0, 50, TaskType.FE),
    ]
    verify_no_memory_conflicts(tasks4, "Полный конфликт")


if __name__ == "__main__":
    main()
