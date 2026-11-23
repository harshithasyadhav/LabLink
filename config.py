import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "lablink.db")
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
