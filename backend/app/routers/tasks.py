"""
Task Status API Endpoints
Provides endpoints to check status of async Celery tasks
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Any
from celery.result import AsyncResult
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["Task Status"])
limiter = Limiter(key_func=get_remote_address)


class TaskStatusResponse(BaseModel):
    """Response model for task status"""
    task_id: str
    state: str
    progress: Optional[int] = None
    current: Optional[int] = None
    total: Optional[int] = None
    result: Optional[Any] = None
    error: Optional[str] = None


@router.get("/{task_id}", response_model=TaskStatusResponse)
@limiter.limit("60/minute")  # 60 status checks per minute
async def get_task_status(request: Request, task_id: str):
    """
    Get the status of an async task

    Args:
        task_id: Celery task ID

    Returns:
        Task status information including state, progress, and result

    States:
        - PENDING: Task is waiting to be executed
        - STARTED: Task has been started
        - PROCESSING: Task is currently processing
        - SUCCESS: Task completed successfully
        - FAILURE: Task failed with an error
        - RETRY: Task is being retried
        - REVOKED: Task was cancelled
    """
    try:
        # Get task result object
        task_result = AsyncResult(task_id, app=celery_app)

        # Get task info
        state = task_result.state
        info = task_result.info if task_result.info else {}

        # Build response based on state
        response = {
            "task_id": task_id,
            "state": state,
        }

        # Add progress information if available
        if isinstance(info, dict):
            response["progress"] = info.get("progress")
            response["current"] = info.get("current")
            response["total"] = info.get("total")

        # Add result or error based on state
        if state == "SUCCESS":
            response["result"] = task_result.result
            response["progress"] = 100
        elif state == "FAILURE":
            response["error"] = str(task_result.info) if task_result.info else "Task failed"
        elif state == "PROCESSING":
            # Task is in progress, info contains progress metadata
            pass
        elif state == "PENDING":
            response["progress"] = 0

        return TaskStatusResponse(**response)

    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve task status: {str(e)}"
        )


@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a running task

    Args:
        task_id: Celery task ID

    Returns:
        Confirmation message
    """
    try:
        task_result = AsyncResult(task_id, app=celery_app)

        if task_result.state in ["SUCCESS", "FAILURE", "REVOKED"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task in state: {task_result.state}"
            )

        # Revoke the task
        task_result.revoke(terminate=True)

        logger.info(f"Task {task_id} cancelled")

        return {
            "message": "Task cancelled successfully",
            "task_id": task_id,
            "state": "REVOKED"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )


@router.get("/")
async def list_active_tasks():
    """
    List all active tasks

    Returns:
        List of active task IDs and their states

    Note: This requires Celery events to be enabled and may not
    show all tasks depending on worker configuration.
    """
    try:
        # Get active tasks from Celery
        inspect = celery_app.control.inspect()
        active = inspect.active()

        if not active:
            return {
                "message": "No active tasks found",
                "tasks": []
            }

        # Flatten active tasks from all workers
        all_tasks = []
        for worker, tasks in active.items():
            for task in tasks:
                all_tasks.append({
                    "task_id": task["id"],
                    "name": task["name"],
                    "worker": worker,
                    "time_start": task.get("time_start"),
                })

        return {
            "message": f"Found {len(all_tasks)} active tasks",
            "tasks": all_tasks
        }

    except Exception as e:
        logger.error(f"Failed to list active tasks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list active tasks: {str(e)}"
        )
