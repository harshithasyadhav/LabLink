import pytest
import os
import sys

# Ensure project path is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.conflict_engine import (
    calculate_deadline_score,
    calculate_criticality_score,
    calculate_duration_score,
    calculate_fairness_score,
    compute_priority_score,
    find_alternative_allocation,
    detect_and_analyze_conflicts,
    resolve_conflict_recommendation
)
from seed_data import seed
from models import query_db, execute_db

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Reset and seed fresh database before test module run."""
    seed()

def test_deadline_scoring_imminent_vs_future():
    """Test that closer project deadlines receive significantly higher scores."""
    # Target date = 2026-11-25
    target_date = "2026-11-25"
    
    # Imminent deadline (next day: 2026-11-26)
    score_imminent = calculate_deadline_score("2026-11-26", target_date)
    # Distant deadline (2 weeks: 2026-12-09)
    score_distant = calculate_deadline_score("2026-12-09", target_date)

    assert score_imminent >= 90.0, f"Expected imminent deadline score >= 90, got {score_imminent}"
    assert score_distant <= 50.0, f"Expected distant deadline score <= 50, got {score_distant}"
    assert score_imminent > score_distant

def test_criticality_scoring():
    """Test that critical projects receive highest urgency weight."""
    score_critical = calculate_criticality_score("critical", is_project=True)
    score_high = calculate_criticality_score("high", is_project=True)
    score_med = calculate_criticality_score("medium", is_project=True)
    score_low = calculate_criticality_score("low", is_project=True)

    assert score_critical == 100.0
    assert score_high == 75.0
    assert score_med == 50.0
    assert score_low == 25.0
    assert score_critical > score_high > score_med > score_low

def test_duration_scoring():
    """Test that shorter, efficient bookings score higher to avoid resource hoarding."""
    score_2h = calculate_duration_score(2)
    score_4h = calculate_duration_score(4)
    score_6h = calculate_duration_score(6)

    assert score_2h == 100.0
    assert score_2h > score_4h > score_6h

def test_fairness_equity_boost():
    """Test that students with fewer recent bookings receive a fairness equity boost."""
    maya = query_db("SELECT id FROM users WHERE email = 'maya.patel@campus.edu'", one=True)
    rahul = query_db("SELECT id FROM users WHERE email = 'rahul.sharma@campus.edu'", one=True)

    # Maya has 0 prior bookings in past 14 days
    maya_fairness = calculate_fairness_score(maya['id'])
    # Rahul has 2 prior bookings seeded in past 14 days
    rahul_fairness = calculate_fairness_score(rahul['id'])

    assert maya_fairness == 100.0, f"Expected 100 fairness for first-time user, got {maya_fairness}"
    assert rahul_fairness <= 60.0, f"Expected <= 60 fairness for frequent user, got {rahul_fairness}"
    assert maya_fairness > rahul_fairness

def test_conflict_detection_and_alternative():
    """Test detection of pre-staged conflict between Maya and Rahul on RTX 4090."""
    conflicts = detect_and_analyze_conflicts()
    assert len(conflicts) >= 1, "Expected at least 1 conflict detected from seed data"

    c = conflicts[0]
    assert c['winner']['user_name'] == "Maya Patel"
    assert c['competitor']['user_name'] == "Rahul Sharma"
    assert c['winner']['scores']['composite'] > c['competitor']['scores']['composite']
    assert c['alternative'] is not None
    assert 'summary' in c['alternative']
    assert c['explanation'] is not None

def test_one_click_conflict_resolution():
    """Test executing 1-click conflict resolution."""
    conflicts = detect_and_analyze_conflicts()
    assert len(conflicts) >= 1
    conflict_key = conflicts[0]['conflict_key']

    res = resolve_conflict_recommendation(conflict_key, 'approve_recommendation', faculty_id=1)
    assert res['success'] is True

    # After resolution, conflict should be resolved
    remaining = detect_and_analyze_conflicts()
    assert len(remaining) == 0, "All conflicts should be cleared after resolution"
