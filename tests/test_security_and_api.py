import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from seed_data import seed
from models import query_db

@pytest.fixture(scope="module")
def client():
    seed()
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_sql_injection_resistance(client):
    """Test searching with malicious SQL injection payload does not compromise database."""
    malicious_payload = "' OR 1=1; DROP TABLE users; --"
    resp = client.get(f'/student/equipment?search={malicious_payload}')
    assert resp.status_code == 200

    # Verify tables and users are intact
    users = query_db("SELECT COUNT(*) as count FROM users", one=True)
    assert users['count'] > 0

def test_analytics_api(client):
    """Test analytics summary endpoint returns comprehensive metrics."""
    resp = client.get('/analytics/api/summary')
    assert resp.status_code == 200
    data = resp.get_json()

    assert 'total_equipment' in data
    assert 'available_equipment' in data
    assert 'utilization_rate' in data
    assert 'dept_usage' in data
    assert data['total_equipment'] >= 10

def test_role_switch_endpoints(client):
    """Test 1-click role switcher transitions session correctly."""
    # Switch to faculty
    resp = client.get('/switch-role/faculty', follow_redirects=False)
    assert resp.status_code == 302
    assert '/faculty/dashboard' in resp.headers['Location']

    # Switch to Maya
    resp2 = client.get('/switch-role/student_maya', follow_redirects=False)
    assert resp2.status_code == 302
    assert '/student/dashboard' in resp2.headers['Location']

def test_unauthorized_student_access_to_faculty_routes(client):
    """Test that student session cannot access faculty administration endpoints (RBAC)."""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['user_role'] = 'student'

    # Student attempts to access faculty dashboard directly
    resp = client.get('/faculty/dashboard', follow_redirects=False)
    assert resp.status_code == 302
    assert '/student/dashboard' in resp.headers['Location']

    # Follow redirect and verify security flash warning
    resp_followed = client.get('/faculty/dashboard', follow_redirects=True)
    assert resp_followed.status_code == 200
    assert b"Faculty authorization required" in resp_followed.data
