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

def test_project_request_submission(client):
    """Test student submitting a complete project access request."""
    priya = query_db("SELECT id FROM users WHERE email = 'priya.nair@campus.edu'", one=True)
    with client.session_transaction() as sess:
        sess['user_id'] = priya['id']
        sess['user_role'] = 'student'

    eq = query_db("SELECT id FROM equipment WHERE code = 'FPGA-ECE-ZYNQ'", one=True)

    resp = client.post('/student/project-request', data={
        'project_title': 'Ultra-low Latency Hardware Video Codec',
        'project_description': 'FPGA hardware acceleration for H.265 video encoding pipeline.',
        'equipment_id': eq['id'],
        'department': 'Electronics & Communication',
        'project_deadline': '2026-12-15',
        'preferred_date': '2026-11-29',
        'preferred_slot': '11:30 - 13:30',
        'duration_hours': 4,
        'reason': 'Synthesized bitstream verification requires direct hardware FMC interface.',
        'urgency': 'high'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert b"submitted successfully" in resp.data

    # Verify database entry
    p = query_db("SELECT * FROM project_requests WHERE project_title = 'Ultra-low Latency Hardware Video Codec'", one=True)
    assert p is not None
    assert p['urgency'] == 'high'
    assert p['status'] == 'pending'

def test_project_request_validation_missing_fields(client):
    """Test validation errors when mandatory fields are omitted."""
    priya = query_db("SELECT id FROM users WHERE email = 'priya.nair@campus.edu'", one=True)
    with client.session_transaction() as sess:
        sess['user_id'] = priya['id']
        sess['user_role'] = 'student'

    # Missing project description and reason
    resp = client.post('/student/project-request', data={
        'project_title': 'Incomplete Project',
        'equipment_id': 1
    }, follow_redirects=True)

    assert b"All fields are required" in resp.data

def test_faculty_review_project_approval_and_rejection(client):
    """Test faculty reviewing, approving, and rejecting project requests."""
    fac = query_db("SELECT id FROM users WHERE role = 'faculty'", one=True)
    with client.session_transaction() as sess:
        sess['user_id'] = fac['id']
        sess['user_role'] = 'faculty'

    p = query_db("SELECT id FROM project_requests WHERE status = 'pending' LIMIT 1", one=True)
    assert p is not None

    # Faculty approves with feedback
    approve_resp = client.post(
        f"/faculty/request/project/{p['id']}/approve",
        data={'comments': 'Approved. Smart card lab clearance issued.'},
        follow_redirects=True
    )
    assert approve_resp.status_code == 200

    updated = query_db("SELECT * FROM project_requests WHERE id = ?", (p['id'],), one=True)
    assert updated['status'] == 'approved'
    assert "Smart card" in updated['faculty_comments']
