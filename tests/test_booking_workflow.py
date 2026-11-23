import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from seed_data import seed
from models import query_db, execute_db

@pytest.fixture(scope="module")
def client():
    seed()
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_equipment_catalogue_discovery(client):
    """Test retrieving equipment catalogue with filters."""
    response = client.get('/student/equipment')
    assert response.status_code == 200
    assert b"NVIDIA RTX 4090" in response.data
    assert b"Bambu Lab X1-Carbon" in response.data

    # Search filter
    search_resp = client.get('/student/equipment?search=Oscilloscope')
    assert search_resp.status_code == 200
    assert b"Keysight" in search_resp.data

def test_slot_availability_api(client):
    """Test checking real-time slot availability for equipment."""
    eq = query_db("SELECT id FROM equipment WHERE code = 'OSC-ECE-1004'", one=True)
    res = client.get(f"/api/equipment/{eq['id']}/slots?date=2026-11-24")
    assert res.status_code == 200
    data = res.get_json()
    assert 'slots' in data
    assert len(data['slots']) > 0

def test_slot_booking_and_double_booking_prevention(client):
    """Test standard booking submission and strict prevention of double bookings."""
    # Authenticate as Priya
    priya = query_db("SELECT id FROM users WHERE email = 'priya.nair@campus.edu'", one=True)
    with client.session_transaction() as sess:
        sess['user_id'] = priya['id']
        sess['user_role'] = 'student'

    eq = query_db("SELECT id FROM equipment WHERE code = 'DEV-CS-RPI5'", one=True)

    # 1. Book an open slot
    book_resp = client.post('/student/book', data={
        'equipment_id': eq['id'],
        'booking_date': '2026-11-28',
        'time_slot': '09:00 - 11:00',
        'purpose': 'Embedded AI inference benchmarking'
    }, follow_redirects=True)
    assert book_resp.status_code == 200

    # Verify created
    bkg = query_db(
        "SELECT * FROM bookings WHERE equipment_id = ? AND booking_date = '2026-11-28' AND time_slot = '09:00 - 11:00'",
        (eq['id'],),
        one=True
    )
    assert bkg is not None

    # Simulate faculty approval
    execute_db("UPDATE bookings SET status = 'approved' WHERE id = ?", (bkg['id'],))

    # 2. Try to book the exact same slot by another student (David Kim)
    david = query_db("SELECT id FROM users WHERE email = 'david.kim@campus.edu'", one=True)
    with client.session_transaction() as sess:
        sess['user_id'] = david['id']
        sess['user_role'] = 'student'

    conflict_book_resp = client.post('/student/book', data={
        'equipment_id': eq['id'],
        'booking_date': '2026-11-28',
        'time_slot': '09:00 - 11:00',
        'purpose': 'Testing edge sensor'
    }, follow_redirects=True)

    # Should be rejected with double booking error warning
    assert b"already been confirmed" in conflict_book_resp.data

def test_booking_cancellation(client):
    """Test student canceling their own booking."""
    david = query_db("SELECT id FROM users WHERE email = 'david.kim@campus.edu'", one=True)
    with client.session_transaction() as sess:
        sess['user_id'] = david['id']
        sess['user_role'] = 'student'

    # Create dummy booking
    eq = query_db("SELECT id FROM equipment LIMIT 1", one=True)
    b_id = execute_db(
        "INSERT INTO bookings (user_id, equipment_id, booking_date, time_slot, purpose, status) VALUES (?, ?, '2026-12-01', '14:00 - 16:00', 'Test', 'pending')",
        (david['id'], eq['id'])
    )

    cancel_resp = client.post(f'/student/cancel-booking/{b_id}', follow_redirects=True)
    assert cancel_resp.status_code == 200

    updated = query_db("SELECT status FROM bookings WHERE id = ?", (b_id,), one=True)
    assert updated['status'] == 'cancelled'
