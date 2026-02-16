"""
Task Scheduler implementation
"""

import time
import logging
from typing import Callable, Optional, Dict, Any
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import sqlite3
import os
import json


logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Task scheduler with cron-like scheduling, priority management, and retry mechanism.
    """

    TASK_PRIORITIES = ["low", "normal", "high", "critical"]
    TASK_STATUSES = ["pending", "running", "completed", "failed", "cancelled"]

    def __init__(self, db_path: str = None):
        """
        Initialize task scheduler.

        Args:
            db_path: Path to SQLite database for task persistence.
        """
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "memory_system.db"
            )
            db_path = os.path.abspath(db_path)

        self.db_path = db_path
        self._init_db()

        jobstores = {"default": MemoryJobStore()}
        executors = {"default": ThreadPoolExecutor(10)}
        job_defaults = {"coalesce": True, "max_instances": 1}

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores, executors=executors, job_defaults=job_defaults
        )
        self.task_functions: Dict[str, Callable] = {}
        logger.info("TaskScheduler initialized")

    def _init_db(self):
        """Initialize database connection and tables if needed."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                schedule TEXT,
                retry_count INTEGER DEFAULT 3,
                max_retries INTEGER DEFAULT 3,
                status TEXT NOT NULL,
                last_run_at TEXT,
                next_run_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                error_message TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """
        )
        conn.commit()
        conn.close()

    def register_task_function(self, task_type: str, func: Callable):
        """
        Register a task function that can be scheduled.

        Args:
            task_type: Unique identifier for the task type
            func: Callable function to execute
        """
        self.task_functions[task_type] = func
        logger.info(f"Registered task function: {task_type}")

    def add_task(
        self,
        task_type: str,
        priority: str = "normal",
        schedule: str = None,
        retry_count: int = 3,
        max_retries: int = 3,
        manual_trigger: bool = False,
    ) -> int:
        """
        Add a task to the scheduler.

        Args:
            task_type: Type of task (must match registered function)
            priority: Task priority (low, normal, high, critical)
            schedule: Cron-like schedule string (e.g., "0 23 * * *" for 11 PM daily)
            retry_count: Current retry count
            max_retries: Maximum retry attempts
            manual_trigger: If True, task can be triggered manually without schedule

        Returns:
            Task ID
        """
        if priority not in self.TASK_PRIORITIES:
            raise ValueError(f"Invalid priority: {priority}")

        now = datetime.now(timezone.utc).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (task_type, priority, schedule, retry_count, max_retries,
                               status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (task_type, priority, schedule, retry_count, max_retries, now, now),
        )
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Added task {task_id}: {task_type} (priority={priority})")

        if schedule and not manual_trigger:
            self._schedule_task(task_id, task_type, schedule)

        return task_id

    def _schedule_task(self, task_id: int, task_type: str, schedule: str):
        """
        Schedule a task using APScheduler.

        Args:
            task_id: Database task ID
            task_type: Type of task
            schedule: Cron-like schedule string
        """
        if task_type not in self.task_functions:
            logger.warning(f"No function registered for task type: {task_type}")
            return

        trigger = self._parse_schedule(schedule)
        if not trigger:
            logger.error(f"Invalid schedule: {schedule}")
            return

        job_id = f"task_{task_id}"
        self.scheduler.add_job(
            self._execute_task,
            trigger=trigger,
            id=job_id,
            args=[task_id, task_type],
            name=f"{task_type}_{task_id}",
        )
        logger.info(f"Scheduled task {task_id} with schedule: {schedule}")

    def _parse_schedule(self, schedule: str):
        """
        Parse schedule string into APScheduler trigger.

        Args:
            schedule: Cron-like schedule string

        Returns:
            APScheduler Trigger object or None
        """
        parts = schedule.split()
        if len(parts) == 5:
            try:
                return CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                )
            except Exception as e:
                logger.error(f"Failed to parse cron schedule: {e}")
                return None
        elif schedule.startswith("interval "):
            try:
                interval = int(schedule.split()[1])
                return IntervalTrigger(seconds=interval)
            except Exception as e:
                logger.error(f"Failed to parse interval schedule: {e}")
                return None
        return None

    def _execute_task(self, task_id: int, task_type: str):
        """
        Execute a task with retry logic.

        Args:
            task_id: Database task ID
            task_type: Type of task to execute
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        started_at = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            UPDATE tasks SET status='running', last_run_at=?, updated_at=?
            WHERE id=?
            """,
            (started_at, started_at, task_id),
        )

        cursor.execute(
            "SELECT retry_count, max_retries FROM tasks WHERE id=?", (task_id,)
        )
        task_data = cursor.fetchone()
        retry_count, max_retries = task_data[0], task_data[1]

        success = False
        error_message = None

        try:
            if task_type in self.task_functions:
                self.task_functions[task_type]()
                success = True
                logger.info(f"Task {task_id} ({task_type}) completed successfully")
            else:
                error_message = f"No function registered for task type: {task_type}"
                logger.error(error_message)

        except Exception as e:
            error_message = str(e)
            logger.error(f"Task {task_id} failed: {error_message}")

        completed_at = datetime.now(timezone.utc).isoformat()
        status = "completed" if success else "failed"

        if not success and retry_count < max_retries:
            retry_count += 1
            status = "pending"
            cursor.execute(
                "UPDATE tasks SET retry_count=?, status=?, updated_at=? WHERE id=?",
                (retry_count, status, completed_at, task_id),
            )
            logger.info(
                f"Task {task_id} will retry (attempt {retry_count}/{max_retries})"
            )
        else:
            cursor.execute(
                "UPDATE tasks SET status=?, updated_at=? WHERE id=?",
                (status, completed_at, task_id),
            )

        cursor.execute(
            """
            INSERT INTO task_logs (task_id, status, started_at, completed_at, error_message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                task_id,
                "completed" if success else "failed",
                started_at,
                completed_at,
                error_message,
            ),
        )

        conn.commit()
        conn.close()

    def trigger_task(self, task_id: int) -> bool:
        """
        Manually trigger a task.

        Args:
            task_id: Database task ID

        Returns:
            True if task was triggered, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT task_type, status FROM tasks WHERE id=?", (task_id,))
        task_data = cursor.fetchone()
        conn.close()

        if not task_data:
            logger.warning(f"Task {task_id} not found")
            return False

        task_type, status = task_data[0], task_data[1]
        if status in ["cancelled", "completed"]:
            logger.warning(f"Task {task_id} is {status}, cannot trigger")
            return False

        self._execute_task(task_id, task_type)
        return True

    def cancel_task(self, task_id: int) -> bool:
        """
        Cancel a scheduled task.

        Args:
            task_id: Database task ID

        Returns:
            True if task was cancelled, False otherwise
        """
        job_id = f"task_{task_id}"
        try:
            self.scheduler.remove_job(job_id)
        except:
            pass

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET status='cancelled', updated_at=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(), task_id),
        )
        conn.commit()
        conn.close()

        logger.info(f"Task {task_id} cancelled")
        return True

    def get_task_status(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Get task status.

        Args:
            task_id: Database task ID

        Returns:
            Task status dict or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        task = cursor.fetchone()
        conn.close()

        if task:
            return dict(task)
        return None

    def get_all_tasks(self, status: str = None) -> list:
        """
        Get all tasks, optionally filtered by status.

        Args:
            status: Filter by status (pending, running, completed, failed, cancelled)

        Returns:
            List of task dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if status:
            cursor.execute("SELECT * FROM tasks WHERE status=? ORDER BY id", (status,))
        else:
            cursor.execute("SELECT * FROM tasks ORDER BY id")

        tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return tasks

    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("TaskScheduler started")

    def shutdown(self):
        """Shutdown the scheduler."""
        try:
            self.scheduler.shutdown()
        except:
            pass
        logger.info("TaskScheduler shutdown")
