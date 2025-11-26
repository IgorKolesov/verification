from typing import List
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
from .Task import Task


class PlotGenerator:
    TASK_COLORS = {
        'VPU': '#FF6B6B',
        'ME': '#4ECDC4',
        'FE': '#45B7D1',
    }
    
    @staticmethod
    def plot_gantt_chart(tasks: List[Task], filename: str = "gantt_chart.png") -> None:
        if not tasks:
            print("No tasks to plot")
            return
        
        executors = {}
        for task in tasks:
            executor = task.executed_by or "Unknown"
            if executor not in executors:
                executors[executor] = []
            executors[executor].append(task)
        
        executor_list = sorted(executors.keys())
        fig, ax = plt.subplots(figsize=(14, 6))
        
        y_pos = 0
        y_labels = []
        y_ticks = []
        
        for executor in executor_list:
            executor_tasks = executors[executor]
            y_labels.append(executor)
            y_ticks.append(y_pos)
            
            for task in executor_tasks:
                if task.actual_start_time is not None and task.latency is not None:
                    color = PlotGenerator.TASK_COLORS.get(task.task_type.name, '#95E1D3')
                    rect = Rectangle(
                        (task.actual_start_time, y_pos - 0.4),
                        task.latency,
                        0.8,
                        linewidth=2,
                        edgecolor='black',
                        facecolor=color,
                        alpha=0.8
                    )
                    ax.add_patch(rect)
                    
                    # Add task ID label
                    ax.text(
                        task.actual_start_time + task.latency / 2,
                        y_pos,
                        f"T{task.id}",
                        ha='center',
                        va='center',
                        fontsize=9,
                        fontweight='bold'
                    )
            
            y_pos += 1
        
        ax.set_ylim(-1, y_pos)
        ax.set_xlim(0, max(t.actual_end_time for t in tasks if t.actual_end_time is not None) + 1)
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_labels)
        ax.set_xlabel('Simulation Ticks', fontsize=12, fontweight='bold')
        ax.set_ylabel('TPC Executors', fontsize=12, fontweight='bold')
        ax.set_title('Task Execution Timeline (Gantt Chart)', fontsize=14, fontweight='bold')
        
        ax.grid(True, axis='x', alpha=0.3, linestyle='--')
        
        legend_elements = [
            mpatches.Patch(facecolor=PlotGenerator.TASK_COLORS['VPU'], edgecolor='black', label='VPU'),
            mpatches.Patch(facecolor=PlotGenerator.TASK_COLORS['ME'], edgecolor='black', label='ME'),
            mpatches.Patch(facecolor=PlotGenerator.TASK_COLORS['FE'], edgecolor='black', label='FE'),
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"[OK] Generated Gantt chart: {filename}")
        plt.close()
    
    @staticmethod
    def plot_tpc_utilization(tasks: List[Task], total_ticks: int, filename: str = "tpc_utilization.png") -> None:
        if not tasks:
            print("No tasks to plot")
            return
        
        executors_time = {}
        for task in tasks:
            executor = task.executed_by or "Unknown"
            if executor not in executors_time:
                executors_time[executor] = 0
            if task.latency is not None:
                executors_time[executor] += task.latency
        
        executor_names = sorted(executors_time.keys())
        utilization_percentages = [
            (executors_time[exe] / total_ticks) * 100 for exe in executor_names
        ]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bars = ax.bar(executor_names, utilization_percentages, color=['#FF6B6B', '#4ECDC4', '#45B7D1'], 
                     edgecolor='black', linewidth=2, alpha=0.8)
        
        for bar, pct in zip(bars, utilization_percentages):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height + 1,
                f'{pct:.1f}%',
                ha='center',
                va='bottom',
                fontsize=11,
                fontweight='bold'
            )
        
        ax.set_ylim(0, 110)
        ax.set_xlabel('TPC Executors', fontsize=12, fontweight='bold')
        ax.set_ylabel('Utilization (%)', fontsize=12, fontweight='bold')
        ax.set_title(f'TPC Utilization (Total Simulation: {total_ticks} ticks)', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"[OK] Generated utilization chart: {filename}")
        plt.close()
    
    @staticmethod
    def plot_task_progress(tasks: List[Task], filename: str = "task_progress.png") -> None:
        if not tasks:
            print("No tasks to plot")
            return
        
        sorted_tasks = sorted(
            [t for t in tasks if t.actual_end_time is not None],
            key=lambda t: t.actual_end_time
        )
        
        end_times = [t.actual_end_time for t in sorted_tasks]
        completed_count = list(range(1, len(sorted_tasks) + 1))
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(end_times, completed_count, marker='o', linewidth=2.5, markersize=8, 
               color='#4ECDC4', markerfacecolor='#FF6B6B', markeredgewidth=2, markeredgecolor='black')
        
        ax.step(end_times, completed_count, where='post', linewidth=2.5, 
               color='#45B7D1', alpha=0.5, linestyle='--')
        
        for end_time, count, task in zip(end_times, completed_count, sorted_tasks):
            ax.text(end_time, count + 0.05, f'T{task.id}', ha='center', va='bottom', 
                   fontsize=9, fontweight='bold')
        
        ax.set_xlabel('Simulation Ticks', fontsize=12, fontweight='bold')
        ax.set_ylabel('Number of Completed Tasks', fontsize=12, fontweight='bold')
        ax.set_title('Task Completion Progress', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_ylim(0, len(sorted_tasks) + 1)
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"[OK] Generated progress chart: {filename}")
        plt.close()
    
    @staticmethod
    def plot_memory_timeline(tasks: List[Task], filename: str = "memory_timeline.png") -> None:
        if not tasks:
            print("No tasks to plot")
            return
        
        sorted_tasks = sorted(
            [t for t in tasks if t.actual_start_time is not None],
            key=lambda t: t.actual_start_time
        )
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        min_addr = min(t.addr_start for t in sorted_tasks)
        max_addr = max(t.addr_end for t in sorted_tasks)
        memory_height = max_addr - min_addr + 1
        
        for i, task in enumerate(sorted_tasks):
            color = PlotGenerator.TASK_COLORS.get(task.task_type.name, '#95E1D3')
            
            rect = Rectangle(
                (task.actual_start_time, task.addr_start),
                task.latency,
                task.addr_end - task.addr_start + 1,
                linewidth=2,
                edgecolor='black',
                facecolor=color,
                alpha=0.7
            )
            ax.add_patch(rect)
            
            ax.text(
                task.actual_start_time + task.latency / 2,
                task.addr_start + (task.addr_end - task.addr_start) / 2,
                f"T{task.id}",
                ha='center',
                va='center',
                fontsize=10,
                fontweight='bold'
            )
        
        max_tick = max(t.actual_end_time for t in sorted_tasks if t.actual_end_time is not None) + 1
        ax.set_xlim(0, max_tick)
        ax.set_ylim(min_addr - 1, max_addr + 2)
        ax.set_xlabel('Simulation Ticks', fontsize=12, fontweight='bold')
        ax.set_ylabel('Memory Address Range', fontsize=12, fontweight='bold')
        ax.set_title('Memory Usage Timeline', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        
        legend_elements = [
            mpatches.Patch(facecolor=PlotGenerator.TASK_COLORS['VPU'], edgecolor='black', label='VPU'),
            mpatches.Patch(facecolor=PlotGenerator.TASK_COLORS['ME'], edgecolor='black', label='ME'),
            mpatches.Patch(facecolor=PlotGenerator.TASK_COLORS['FE'], edgecolor='black', label='FE'),
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"[OK] Generated memory timeline: {filename}")
        plt.close()
    
    @staticmethod
    def generate_all_plots(tasks: List[Task], total_ticks: int, output_dir: str = ".") -> None:
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print("\nGenerating plots...")
        print("-" * 60)
        
        PlotGenerator.plot_gantt_chart(
            tasks, 
            str(output_path / "gantt_chart.png")
        )
        PlotGenerator.plot_tpc_utilization(
            tasks, 
            total_ticks,
            str(output_path / "tpc_utilization.png")
        )
        PlotGenerator.plot_task_progress(
            tasks,
            str(output_path / "task_progress.png")
        )
        PlotGenerator.plot_memory_timeline(
            tasks,
            str(output_path / "memory_timeline.png")
        )
        
        print("-" * 60)
        print(f"[OK] All plots generated in: {output_dir}")
