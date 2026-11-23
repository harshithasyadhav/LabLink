import os
import tempfile

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Check if running in a serverless or containerized environment (Vercel / AWS Lambda)
IS_SERVERLESS = bool(
    os.environ.get("VERCEL")
    or os.environ.get("VERCEL_ENV")
    or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    or os.environ.get("LAMBDA_TASK_ROOT")
    or os.path.exists("/var/task")
)

def determine_database_path():
    """
    Determines a writable location for SQLite.
    On Vercel and AWS Lambda, the root deployment directory is strictly read-only.
    Only /tmp (tempfile.gettempdir()) is writable.
    """
    # 1. Custom explicit path from environment variable
    if os.environ.get("DATABASE_PATH"):
        return os.environ.get("DATABASE_PATH")

    # 2. Serverless environment -> always use /tmp
    if IS_SERVERLESS:
        return os.path.join(tempfile.gettempdir(), "lablink.db")

    # 3. Check writability of local project root; if read-only, fallback to /tmp
    local_db = os.path.join(BASE_DIR, "lablink.db")
    try:
        test_file = os.path.join(BASE_DIR, ".write_test")
        with open(test_file, "w") as f:
            f.write("1")
        os.remove(test_file)
        return local_db
    except (OSError, IOError, PermissionError):
        return os.path.join(tempfile.gettempdir(), "lablink.db")

DATABASE_PATH = determine_database_path()
IS_VERCEL = IS_SERVERLESS

SECRET_KEY = os.environ.get("SECRET_KEY", "lablink-secure-session-key-2026")

# Academic time slots for lab bookings
STANDARD_SLOTS = [
    "09:00 - 11:00",
    "11:30 - 13:30",
    "14:00 - 16:00",
    "16:30 - 18:30",
    "19:00 - 21:00"
]

DEPARTMENTS = [
    "Computer Science",
    "Electronics & Communication",
    "Robotics & Automation",
    "Mechanical Engineering",
    "Artificial Intelligence & Data Science",
    "Physics & Instrumentation"
]

CATEGORIES = [
    "Development Kits",
    "AI/GPU Workstations",
    "Sensors & IoT",
    "Robotics",
    "3D Printing & Fabrication",
    "Test & Measurement",
    "FPGA Boards"
]

# Optional Gemini API key for natural language explanation enhancement
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
