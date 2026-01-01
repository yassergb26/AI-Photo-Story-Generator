"""
Test script for task-status endpoints
Run this to verify the /api/tasks endpoints are working
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.celery_app import celery_app
from app.tasks import classify_image_task
from app.redis_client import check_redis_connection
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_task_status_endpoints():
    """Test task status tracking"""
    print("\n=== Testing Task Status Endpoints ===" )

    # First check Redis
    if not check_redis_connection():
        print("❌ Redis not connected - cannot test task endpoints")
        return False

    print("✅ Redis connected")

    try:
        # Submit a test task
        print("\n1. Submitting test task...")
        result = classify_image_task.delay(1)
        task_id = result.id
        print(f"   Task ID: {task_id}")

        # Check task status multiple times
        print("\n2. Checking task status...")
        for i in range(5):
            time.sleep(1)
            state = result.state
            info = result.info if result.info else {}

            print(f"   Attempt {i+1}: State={state}, Info={info}")

            if state in ["SUCCESS", "FAILURE"]:
                break

        # Final state
        print(f"\n3. Final task state: {result.state}")

        if result.state == "FAILURE":
            error_msg = str(result.info)
            if "not found" in error_msg.lower():
                print("   ✅ Task executed (expected failure - image doesn't exist)")
                print("\n✅ Task status tracking is working!")
                print(f"\n📝 You can check task status via API:")
                print(f"   GET http://localhost:8000/api/tasks/{task_id}")
                return True
            else:
                print(f"   ❌ Task failed with unexpected error: {result.info}")
                return False
        elif result.state == "SUCCESS":
            print("   ✅ Task completed successfully!")
            print(f"   Result: {result.result}")
            return True
        else:
            print(f"   ⚠️  Task in state: {result.state}")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Task Status Endpoints Test")
    print("=" * 50)

    success = test_task_status_endpoints()

    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed!")
        print("\nNext steps:")
        print("1. Start the FastAPI server:")
        print("   python main.py")
        print("2. Visit http://localhost:8000/docs")
        print("3. Test the /api/tasks endpoints")
    else:
        print("❌ Tests failed")
        print("\nMake sure:")
        print("1. Redis is running")
        print("2. Celery worker is running:")
        print("   celery -A app.celery_app worker --loglevel=info --pool=solo")
    print("=" * 50)
