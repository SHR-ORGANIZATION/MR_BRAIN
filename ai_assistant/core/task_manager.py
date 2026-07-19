"""
AMAZON AI - Task Manager
Async task execution tracking with progress reporting and cancellation.
"""
import uuid
import threading
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class Task:
    """Represents an executable task."""
    id: str
    name: str
    command: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancel_requested: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
    
    @property
    def duration(self) -> Optional[float]:
        """Get task duration in seconds."""
        if self.started_at is None:
            return None
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()


class TaskManager:
    """
    Manages async task execution with progress tracking.
    
    Features:
    - Task queue management
    - Progress reporting
    - Cancellation support
    - Thread-safe execution
    """
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.current_task: Optional[str] = None
        self._lock = threading.Lock()
        self._callbacks: Dict[str, List[Callable]] = {}
    
    def create_task(
        self, 
        name: str, 
        command: str,
        callback: Optional[Callable] = None
    ) -> str:
        """Create a new task and return its ID."""
        task_id = str(uuid.uuid4())[:8]
        
        task = Task(
            id=task_id,
            name=name,
            command=command
        )
        
        with self._lock:
            self.tasks[task_id] = task
            if callback:
                self._callbacks[task_id] = [callback]
        
        logger.info(f"Task created: {task_id} - {name}")
        return task_id
    
    def start_task(self, task_id: str) -> bool:
        """Mark a task as started."""
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status != TaskStatus.PENDING:
                return False
            
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            self.current_task = task_id
            
        self._notify_callbacks(task_id, "started")
        return True
    
    def update_progress(self, task_id: str, progress: float, message: str = ""):
        """Update task progress (0.0 to 1.0)."""
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].progress = min(1.0, max(0.0, progress))
        
        self._notify_callbacks(task_id, "progress", {"progress": progress, "message": message})
    
    def complete_task(self, task_id: str, result: Optional[Dict] = None):
        """Mark a task as completed."""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = TaskStatus.COMPLETED
                task.progress = 1.0
                task.result = result
                task.completed_at = datetime.now()
                
                if self.current_task == task_id:
                    self.current_task = None
        
        self._notify_callbacks(task_id, "completed", result)
        logger.info(f"Task completed: {task_id}")
    
    def fail_task(self, task_id: str, error: str):
        """Mark a task as failed."""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = TaskStatus.FAILED
                task.error = error
                task.completed_at = datetime.now()
                
                if self.current_task == task_id:
                    self.current_task = None
        
        self._notify_callbacks(task_id, "failed", {"error": error})
        logger.warning(f"Task failed: {task_id} - {error}")
    
    def cancel_task(self, task_id: str) -> bool:
        """Request cancellation of a task."""
        with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                return False
            
            task.cancel_requested = True
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            
            if self.current_task == task_id:
                self.current_task = None
        
        self._notify_callbacks(task_id, "cancelled")
        logger.info(f"Task cancelled: {task_id}")
        return True
    
    def is_cancel_requested(self, task_id: str) -> bool:
        """Check if cancellation was requested for a task."""
        with self._lock:
            if task_id in self.tasks:
                return self.tasks[task_id].cancel_requested
        return False
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task details."""
        with self._lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        """Get all tasks, optionally filtered by status."""
        with self._lock:
            tasks = list(self.tasks.values())
            if status:
                tasks = [t for t in tasks if t.status == status]
            return tasks
    
    def get_current_task(self) -> Optional[Task]:
        """Get the currently running task."""
        with self._lock:
            if self.current_task:
                return self.tasks.get(self.current_task)
        return None
    
    def register_callback(self, task_id: str, callback: Callable):
        """Register a callback for task events."""
        with self._lock:
            if task_id not in self._callbacks:
                self._callbacks[task_id] = []
            self._callbacks[task_id].append(callback)
    
    def _notify_callbacks(self, task_id: str, event: str, data: Any = None):
        """Notify registered callbacks of a task event."""
        with self._lock:
            callbacks = self._callbacks.get(task_id, [])
        
        for callback in callbacks:
            try:
                callback(task_id, event, data)
            except Exception as e:
                logger.warning(f"Callback error: {e}")
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove completed tasks older than max_age_hours."""
        now = datetime.now()
        to_remove = []
        
        with self._lock:
            for task_id, task in self.tasks.items():
                if task.completed_at:
                    age = (now - task.completed_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.tasks[task_id]
                self._callbacks.pop(task_id, None)


# Singleton instance
_task_manager_instance = None

def get_task_manager() -> TaskManager:
    """Get or create the singleton task manager."""
    global _task_manager_instance
    if _task_manager_instance is None:
        _task_manager_instance = TaskManager()
    return _task_manager_instance
