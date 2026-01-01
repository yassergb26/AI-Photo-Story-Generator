"""
Test script for Celery+Redis setup
Run this to verify async task processing is working
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.celery_app import celery_app
from app.redis_client import check_redis_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_redis_connection():
    """Test Redis connection"""
    print("\n=== Testing Redis Connection ===")
    try:
        if check_redis_connection():
            print("✅ Redis connection successful!")
            return True
        else:
            print("❌ Redis connection failed!")
            return False
    except Exception as e:
        print(f"❌ Redis connection error: {e}")
        return False


def test_celery_task():
    """Test Celery with a registered task"""
    print("\n=== Testing Celery Task ===")

    from app.tasks import classify_image_task

    try:
        print("⚠️  Note: This will fail if no image exists with ID 1")
        print("   But it will prove Celery worker can receive and process tasks!")

        # Send task asynchronously
        result = classify_image_task.delay(1)
        print(f"📤 Task sent with ID: {result.id}")
        print(f"⏳ Waiting for result (10 seconds)...")

        # Wait for result (timeout 10 seconds)
        try:
            output = result.get(timeout=10)
            print(f"✅ Task completed! Result: {output}")
            return True
        except Exception as task_error:
            # Check if task was received and attempted
            error_msg = str(task_error).lower()
            if "not found" in error_msg or "image 1 not found" in error_msg:
                print(f"✅ Task was received and executed by worker!")
                print(f"   (Failed because image doesn't exist - that's OK for testing)")
                return True
            elif "timeout" in error_msg or "timed out" in error_msg:
                print(f"❌ Task timed out - worker may not be consuming from the queue")
                print(f"   Task state: {result.state}")
                return False
            else:
                raise

    except Exception as e:
        print(f"❌ Celery task failed: {e}")
        print("\nMake sure Celery worker is running:")
        print("  celery -A app.celery_app worker --loglevel=info --pool=solo")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Celery + Redis Test Script")
    print("=" * 50)

    # Test 1: Redis
    redis_ok = test_redis_connection()

    # Test 2: Celery
    celery_ok = test_celery_task() if redis_ok else False

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"  Redis:  {'✅ PASS' if redis_ok else '❌ FAIL'}")
    print(f"  Celery: {'✅ PASS' if celery_ok else '❌ FAIL'}")
    print("=" * 50)

    if redis_ok and celery_ok:
        print("\n🎉 All tests passed! Async processing is ready.")
    else:
        print("\n⚠️  Some tests failed. See above for details.")
        if not redis_ok:
            print("\n💡 Start Redis server:")
            print("   Windows: Download from https://github.com/microsoftarchive/redis/releases")
            print("   Mac: brew install redis && brew services start redis")
            print("   Linux: sudo service redis-server start")
