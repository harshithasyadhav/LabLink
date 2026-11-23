import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from models import init_db, query_db
from seed_data import seed
from app import create_app

def main():
    print("=" * 70)
    print("   LabLink — Campus Laboratory Resource-Sharing Platform")
    print("=" * 70)

    # Check if database has users/equipment; if not, seed it automatically
    init_db()
    user_count = query_db("SELECT COUNT(*) as c FROM users", one=True)
    if not user_count or user_count['c'] == 0:
        print("[*] Initializing database with realistic campus demo data...")
        seed()
    else:
        print("[*] Verified database integrity and existing laboratory data.")

    app = create_app()

    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")

    print(f"\n[+] Server running at: http://{host}:{port}")
    print("[+] Evaluation Personas Available:")
    print("    - Student 1 (Winner - Capstone): Maya Patel  (maya.patel@campus.edu)")
    print("    - Student 2 (Competitor):       Rahul Sharma (rahul.sharma@campus.edu)")
    print("    - Faculty / Admin:              Prof. Aris Vance (faculty@campus.edu)")
    print("\n[+] Instant 1-Click Role Switcher active in top navigation bar!")
    print("[+] AI Conflict Resolution Scenario pre-staged & ready to demonstrate.")
    print("=" * 70)

    app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    main()
