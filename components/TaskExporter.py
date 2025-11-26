import json
from typing import List
from datetime import datetime
from .Task import Task


class TaskExporter:
    @staticmethod
    def export_to_json(tasks: List[Task], filename: str) -> None:
        if not tasks:
            print("No tasks to export")
            return
        
        tasks_data = []
        for task in tasks:
            tasks_data.append({
                'id': task.id,
                'type': task.task_type.name,
                'memory': {
                    'start': task.addr_start,
                    'end': task.addr_end,
                    'size': task.addr_end - task.addr_start + 1
                },
                'timing': {
                    'actual_start': task.actual_start_time,
                    'actual_end': task.actual_end_time,
                    'exec_time': task.latency,
                    'total_time': task.total_latency,
                    'start_time': task.start_time,
                    'end_time': task.end_time
                },
                'executor': task.executed_by,
                'completed': task.is_completed
            })
        
        output = {
            'export_timestamp': datetime.now().isoformat(),
            'total_tasks': len(tasks),
            'tasks': tasks_data,
            'summary': {
                'min_actual_start': min((t['timing']['actual_start'] for t in tasks_data 
                                        if t['timing']['actual_start'] is not None), default=None),
                'max_actual_end': max((t['timing']['actual_end'] for t in tasks_data 
                                      if t['timing']['actual_end'] is not None), default=None),
                'total_execution_time': max((t['timing']['total_time'] for t in tasks_data 
                                            if t['timing']['total_time'] is not None), default=None),
                'avg_exec_time': (sum(t['timing']['exec_time'] for t in tasks_data 
                                      if t['timing']['exec_time'] is not None) / 
                                 len([t for t in tasks_data if t['timing']['exec_time'] is not None])
                                 if any(t['timing']['exec_time'] is not None for t in tasks_data) else None)
            }
        }
        
        with open(filename, 'w') as jsonfile:
            json.dump(output, jsonfile, indent=2)
        
        print(f"[OK] Exported {len(tasks)} tasks to JSON: {filename}")
    
    @staticmethod
    def export(tasks: List[Task], filename: str = "tasks.json") -> None:
        TaskExporter.export_to_json(tasks, filename)
