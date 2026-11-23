from datetime import datetime, date, timedelta
from config import STANDARD_SLOTS
from models import init_db, execute_db, query_db

def seed():
    """Initializes and seeds the database with realistic campus lab data."""
    init_db()

    # Clear existing tables to ensure clean seed state
    conn = execute_db("DELETE FROM notifications")
    execute_db("DELETE FROM conflict_resolutions")
    execute_db("DELETE FROM project_requests")
    execute_db("DELETE FROM bookings")
    execute_db("DELETE FROM equipment")
    execute_db("DELETE FROM users")

    # 1. Seed Users
    users_data = [
        ("Prof. Aris Vance", "faculty@campus.edu", "faculty", "Electronics & Instrumentation", "FAC-9042"),
        ("Maya Patel", "maya.patel@campus.edu", "student", "Computer Science", "CS2023-4012"),
        ("Rahul Sharma", "rahul.sharma@campus.edu", "student", "Robotics & Automation", "RO2024-2108"),
        ("Priya Nair", "priya.nair@campus.edu", "student", "Electronics & Communication", "EC2023-1190"),
        ("David Kim", "david.kim@campus.edu", "student", "Mechanical Engineering", "ME2024-5541")
    ]

    user_ids = {}
    for name, email, role, dept, roll in users_data:
        uid = execute_db(
            "INSERT INTO users (name, email, role, department, roll_or_emp_id) VALUES (?, ?, ?, ?, ?)",
            (name, email, role, dept, roll)
        )
        user_ids[email] = uid

    # 2. Seed Realistic Laboratory Equipment
    equipment_data = [
        (
            "NVIDIA RTX 4090 Deep Learning Workstation Alpha",
            "GPU-CS-4090A",
            "AI/GPU Workstations",
            "Computer Science",
            "Room 402, AI Research Lab",
            "Intel Core i9-14900K, 24GB RTX 4090 GPU, 64GB DDR5, 2TB NVMe SSD. Pre-installed: PyTorch 2.3, CUDA 12.2, TensorRT.",
            "Bring university smart card for lab entry. Save all model checkpoints to designated scratch directory /mnt/scratch.",
            "available",
            "gpu"
        ),
        (
            "Dual NVIDIA RTX A6000 AI Cluster Node",
            "GPU-AI-A6000",
            "AI/GPU Workstations",
            "Artificial Intelligence & Data Science",
            "High-Compute Data Center 405",
            "2x 48GB NVIDIA RTX A6000 (96GB Total VRAM), Dual AMD EPYC 7763, 256GB ECC RAM, InfiniBand HDR 200Gb/s.",
            "Remote SSH access available via lab VPN. Slurm job scheduling support enabled.",
            "available",
            "server"
        ),
        (
            "Bambu Lab X1-Carbon Combo 3D Printer",
            "3DP-MECH-X1C",
            "3D Printing & Fabrication",
            "Mechanical Engineering",
            "MakerSpace & FabLab B04",
            "256x256x256mm build volume, AMS 4-spool multi-material auto-switching, up to 500mm/s print speed, AI LiDAR inspection.",
            "Clean build plate with IPA before each print. Wear safety goggles when removing finished parts.",
            "available",
            "printer"
        ),
        (
            "Keysight InfiniiVision 4-Channel 1GHz Digital Oscilloscope",
            "OSC-ECE-1004",
            "Test & Measurement",
            "Electronics & Communication",
            "VLSI & Embedded Systems Lab 208",
            "1 GHz bandwidth, 4 analog + 16 digital MSO channels, 5 GSa/s sampling, automated I2C/SPI/CAN protocol decoding.",
            "Calibrate probes before measurement. Do not exceed 50V input on high-impedance channels.",
            "available",
            "oscilloscope"
        ),
        (
            "Xilinx Zynq UltraScale+ MPSoC Development Board",
            "FPGA-ECE-ZYNQ",
            "FPGA Boards",
            "Electronics & Communication",
            "Digital Signal Processing Lab 210",
            "Quad ARM Cortex-A53, Dual Cortex-R5F, 16nm FinFET+ programmable logic, FMC expansion slot, Gigabit Ethernet.",
            "Use antistatic wrist strap while handling the board. Power down before swapping daughtercards.",
            "available",
            "circuit"
        ),
        (
            "ROS 2 TurtleBot 4 Mobile Robot Kit",
            "ROB-ROB-TB4",
            "Robotics",
            "Robotics & Automation",
            "Robotics Arena & Testing Lab 101",
            "iRobot Create 3 base, Raspberry Pi 4B companion computer, OAK-D-Pro stereo depth camera, RPLIDAR A1 2D LiDAR.",
            "Ensure battery is plugged into docking station after each test run. Verify emergency stop button is accessible.",
            "available",
            "robot"
        ),
        (
            "Raspberry Pi 5 AI Starter Kit with Hailo-8L",
            "DEV-CS-RPI5",
            "Development Kits",
            "Computer Science",
            "Embedded Systems Lab 305",
            "8GB LPDDR4X RAM, Broadcom BCM2712 Quad-Core 2.4GHz, Hailo-8L 13 TOPS M.2 AI acceleration HAT, Sony IMX708 camera.",
            "Use official 27W USB-C power supply. Do not hot-swap camera ribbon cable.",
            "available",
            "chip"
        ),
        (
            "LoRaWAN Industrial IoT Sensor Lab Kit",
            "IOT-ECE-LORA",
            "Sensors & IoT",
            "Electronics & Communication",
            "Smart Campus IoT Lab 204",
            "8-channel Outdoor LoRaWAN Gateway, 6 sensor nodes (temperature, humidity, CO2, soil moisture, GPS, RS485 Modbus).",
            "Antennas must be securely connected before powering on the RF transceivers.",
            "available",
            "wifi"
        ),
        (
            "Arduino Giga R1 WiFi & Touch Display Bundle",
            "DEV-ROB-GIGA",
            "Development Kits",
            "Robotics & Automation",
            "Mechatronics Lab 103",
            "Dual-core STM32H747XI (Cortex-M7 at 480MHz & Cortex-M4 at 240MHz), 4.3 inch 480x800 RGB touch shield, CAN bus.",
            "Connect via USB-C. Follow dual-core memory mapping documentation when flashing firmware.",
            "available",
            "cpu"
        ),
        (
            "Rohde & Schwarz Mixed Signal Oscilloscope 500MHz",
            "OSC-PHYS-500",
            "Test & Measurement",
            "Physics & Instrumentation",
            "Modern Physics & Optics Lab 112",
            "500 MHz, 4 analog channels, 2.5 GSa/s, 10.1 inch touchscreen, real-time spectrum analysis FFT.",
            "Use 50-ohm termination only when specified in experiment manual.",
            "maintenance",
            "activity"
        )
    ]

    eq_ids = {}
    for name, code, cat, dept, loc, specs, inst, status, icon in equipment_data:
        eid = execute_db(
            """
            INSERT INTO equipment (name, code, category, department, location, specs, instructions, status, image_icon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, code, cat, dept, loc, specs, inst, status, icon)
        )
        eq_ids[code] = eid

    # Calculate dates
    today = date.today()
    tomorrow = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    day_after = (today + timedelta(days=2)).strftime("%Y-%m-%d")
    five_days_later = (today + timedelta(days=5)).strftime("%Y-%m-%d")
    two_weeks_later = (today + timedelta(days=14)).strftime("%Y-%m-%d")

    # 3. Existing Historical & Approved Bookings
    # Priya Nair has an approved booking for Keysight Oscilloscope
    execute_db(
        """
        INSERT INTO bookings (user_id, equipment_id, booking_date, time_slot, purpose, status, reviewed_by, review_comments)
        VALUES (?, ?, ?, ?, ?, 'approved', ?, 'Approved for high-frequency RF filter characterization.')
        """,
        (user_ids['priya.nair@campus.edu'], eq_ids['OSC-ECE-1004'], tomorrow, "09:00 - 11:00",
         "High-frequency RF filter characterization experiment", user_ids['faculty@campus.edu'])
    )

    # David Kim has an approved 3D printer booking
    execute_db(
        """
        INSERT INTO bookings (user_id, equipment_id, booking_date, time_slot, purpose, status, reviewed_by, review_comments)
        VALUES (?, ?, ?, ?, ?, 'approved', ?, 'Approved for UAV chassis structural print.')
        """,
        (user_ids['david.kim@campus.edu'], eq_ids['3DP-MECH-X1C'], tomorrow, "11:30 - 13:30",
         "Fabricating carbon-fiber reinforced drone arm brackets", user_ids['faculty@campus.edu'])
    )

    # Give Rahul Sharma 2 prior completed bookings in past 14 days (establishes realistic history for fairness algorithm)
    execute_db(
        """
        INSERT INTO bookings (user_id, equipment_id, booking_date, time_slot, purpose, status, reviewed_by, created_at)
        VALUES (?, ?, ?, '14:00 - 16:00', 'Robotics sensor calibration lab', 'completed', ?, datetime('now', '-4 days'))
        """,
        (user_ids['rahul.sharma@campus.edu'], eq_ids['DEV-ROB-GIGA'], (today - timedelta(days=4)).strftime("%Y-%m-%d"), user_ids['faculty@campus.edu'])
    )
    execute_db(
        """
        INSERT INTO bookings (user_id, equipment_id, booking_date, time_slot, purpose, status, reviewed_by, created_at)
        VALUES (?, ?, ?, '16:30 - 18:30', 'TurtleBot ROS 2 mapping run', 'completed', ?, datetime('now', '-8 days'))
        """,
        (user_ids['rahul.sharma@campus.edu'], eq_ids['ROB-ROB-TB4'], (today - timedelta(days=8)).strftime("%Y-%m-%d"), user_ids['faculty@campus.edu'])
    )

    # 4. PRE-STAGED SCHEDULING CONFLICT SCENARIO (Directly demonstrates Section 4 AI Conflict Resolution!)
    # Both students request NVIDIA RTX 4090 Workstation (id: 1) on tomorrow at 14:00 - 16:00!
    # Maya Patel: Capstone project, deadline in 24 hours, critical priority, 0 prior bookings -> Priority Score ~89.2
    # Rahul Sharma: Mini-project, deadline in 10 days, medium priority, 2 prior bookings -> Priority Score ~47.5

    # Request A: Maya Patel (Project Request)
    execute_db(
        """
        INSERT INTO project_requests
        (user_id, equipment_id, project_title, project_description, department, project_deadline,
         preferred_date, preferred_slot, duration_hours, reason, urgency, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """,
        (
            user_ids['maya.patel@campus.edu'],
            eq_ids['GPU-CS-4090A'],
            "Autonomous Drone Visual SLAM & Real-time Obstacle Avoidance",
            "Final Year Capstone Project requiring high-throughput CUDA tensor cores to benchmark neural point-cloud SLAM against baseline datasets.",
            "Computer Science",
            day_after, # Deadline is in 48 hours!
            tomorrow,
            "14:00 - 16:00",
            2,
            "Final capstone evaluation panel demonstration scheduled in 48 hours. Urgent need for 24GB VRAM to run dense point-cloud model without CUDA out-of-memory.",
            "critical"
        )
    )

    # Request B: Rahul Sharma (Standard Booking Request for the SAME slot)
    execute_db(
        """
        INSERT INTO bookings
        (user_id, equipment_id, booking_date, time_slot, purpose, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_ids['rahul.sharma@campus.edu'],
            eq_ids['GPU-CS-4090A'],
            tomorrow,
            "14:00 - 16:00",
            "Training exploratory YOLOv8 object detector for semester robotics lab assignment (Deadline in 10 days).",
            "pending"
        )
    )

    # 5. Welcome notifications
    execute_db(
        """
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (?, 'Welcome to LabLink Platform', 'Explore campus laboratory equipment across departments, request slots, and collaborate on projects.', 'info')
        """,
        (user_ids['maya.patel@campus.edu'],)
    )
    execute_db(
        """
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (?, 'Conflict Alert: Peak Slot Contested', 'Another student requested RTX 4090 Workstation at 14:00 tomorrow. AI Conflict Resolution is actively evaluating fair priority.', 'conflict')
        """,
        (user_ids['maya.patel@campus.edu'],)
    )
    execute_db(
        """
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (?, 'Pending Request Under Review', 'Your booking request for RTX 4090 Workstation is pending faculty schedule review.', 'info')
        """,
        (user_ids['rahul.sharma@campus.edu'],)
    )

    print("Demo database successfully initialized and seeded with realistic campus laboratory data!")

if __name__ == '__main__':
    seed()
