import json
from datetime import datetime, timedelta
from config import STANDARD_SLOTS, GEMINI_API_KEY
from models import query_db, execute_db, create_notification

def parse_date(date_str):
    """Safely parse YYYY-MM-DD date."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return datetime.now().date()

def calculate_deadline_score(deadline_str, target_date_str):
    """
    Computes deadline score (0 - 100).
    Closer deadline relative to target date yields higher score.
    """
    if not deadline_str:
        return 30.0  # Base score for general non-project bookings
    
    deadline = parse_date(deadline_str)
    target_date = parse_date(target_date_str)
    delta_days = (deadline - target_date).days

    if delta_days <= 0:
        return 100.0  # Overdue or due on booking day
    elif delta_days == 1:
        return 95.0   # Due next day (< 24-48h)
    elif delta_days <= 3:
        return 85.0   # Imminent (< 72h)
    elif delta_days <= 7:
        return 65.0   # Within 1 week
    elif delta_days <= 14:
        return 45.0   # Within 2 weeks
    elif delta_days <= 30:
        return 30.0   # Within 1 month
    else:
        return max(15.0, 30.0 - (delta_days - 30) * 0.5)

def calculate_criticality_score(urgency, is_project=True):
    """Computes requirement necessity score (0 - 100)."""
    mapping = {
        'critical': 100.0,
        'high': 75.0,
        'medium': 50.0,
        'low': 25.0
    }
    urgency_clean = (urgency or 'medium').lower()
    base = mapping.get(urgency_clean, 50.0)
    if not is_project:
        # Non-project ad-hoc bookings have slight lower criticality weight
        base = max(20.0, base * 0.8)
    return base

def calculate_duration_score(duration_hours):
    """
    Computes duration efficiency score (0 - 100).
    Shorter, targeted bookings are preferred to avoid slot hoarding.
    """
    try:
        hours = float(duration_hours or 2.0)
    except (ValueError, TypeError):
        hours = 2.0

    if hours <= 2.0:
        return 100.0
    elif hours <= 4.0:
        return 75.0
    elif hours <= 6.0:
        return 50.0
    else:
        return max(20.0, 100.0 - (hours - 2.0) * 15.0)

def calculate_fairness_score(user_id):
    """
    Computes fairness equity score (0 - 100).
    Students with fewer bookings in the past 14 days receive an equity boost
    to prevent repeat monopolization.
    """
    # Count approved bookings in last 14 days
    res = query_db(
        """
        SELECT COUNT(*) as count FROM bookings
        WHERE user_id = ? AND status IN ('approved', 'completed')
        AND created_at >= datetime('now', '-14 days')
        """,
        (user_id,),
        one=True
    )
    prior_count = res['count'] if res else 0

    if prior_count == 0:
        return 100.0  # Max equity boost for unserved students
    elif prior_count == 1:
        return 80.0
    elif prior_count == 2:
        return 60.0
    elif prior_count == 3:
        return 40.0
    else:
        return max(15.0, 60.0 - (prior_count - 2) * 15.0)

def compute_priority_score(request_dict):
    """
    Calculates multi-factor priority score with breakdown:
    Composite = 35% Deadline + 25% Criticality + 15% Duration + 25% Fairness
    """
    user_id = request_dict.get('user_id')
    deadline = request_dict.get('project_deadline') or request_dict.get('deadline')
    target_date = request_dict.get('booking_date') or request_dict.get('preferred_date')
    urgency = request_dict.get('urgency') or 'medium'
    duration = request_dict.get('duration_hours') or 2
    is_project = bool(request_dict.get('project_title'))

    s_deadline = calculate_deadline_score(deadline, target_date)
    s_criticality = calculate_criticality_score(urgency, is_project)
    s_duration = calculate_duration_score(duration)
    s_fairness = calculate_fairness_score(user_id)

    composite = (
        0.35 * s_deadline +
        0.25 * s_criticality +
        0.15 * s_duration +
        0.25 * s_fairness
    )
    composite = round(composite, 1)

    return {
        'composite': composite,
        'breakdown': {
            'deadline_score': round(s_deadline, 1),
            'criticality_score': round(s_criticality, 1),
            'duration_score': round(s_duration, 1),
            'fairness_score': round(s_fairness, 1)
        }
    }

def find_alternative_allocation(equipment_id, conflict_date, conflict_slot, exclude_user_id=None):
    """
    Finds alternative feasible allocations for the competing student:
    1. Same equipment at an alternative time slot on the same date
    2. Same equipment on the next academic day
    3. Alternative compatible equipment in same category/department at requested slot
    """
    eq = query_db("SELECT * FROM equipment WHERE id = ?", (equipment_id,), one=True)
    if not eq:
        return None

    # Option A: Check other slots on same date for same equipment
    occupied_slots = query_db(
        """
        SELECT time_slot FROM bookings
        WHERE equipment_id = ? AND booking_date = ? AND status IN ('approved', 'pending')
        """,
        (equipment_id, conflict_date)
    )
    taken = {row['time_slot'] for row in occupied_slots}

    for slot in STANDARD_SLOTS:
        if slot != conflict_slot and slot not in taken:
            return {
                'type': 'same_equipment_different_slot',
                'equipment_id': eq['id'],
                'equipment_name': eq['name'],
                'equipment_code': eq['code'],
                'date': conflict_date,
                'slot': slot,
                'summary': f"Reserve {eq['name']} on {conflict_date} during {slot} (Same Day Alternative)"
            }

    # Option B: Check alternative compatible equipment in same category or department
    alternatives = query_db(
        """
        SELECT * FROM equipment
        WHERE id != ? AND (category = ? OR department = ?) AND status = 'available'
        ORDER BY CASE WHEN category = ? THEN 0 ELSE 1 END
        """,
        (equipment_id, eq['category'], eq['department'], eq['category'])
    )

    for alt_eq in alternatives:
        alt_occupied = query_db(
            """
            SELECT id FROM bookings
            WHERE equipment_id = ? AND booking_date = ? AND time_slot = ? AND status IN ('approved', 'pending')
            """,
            (alt_eq['id'], conflict_date, conflict_slot),
            one=True
        )
        if not alt_occupied:
            return {
                'type': 'alternative_equipment_same_slot',
                'equipment_id': alt_eq['id'],
                'equipment_name': alt_eq['name'],
                'equipment_code': alt_eq['code'],
                'date': conflict_date,
                'slot': conflict_slot,
                'summary': f"Allocate equivalent resource '{alt_eq['name']}' ({alt_eq['department']}) at {conflict_slot} on {conflict_date}"
            }

    # Option C: Next day slot on same equipment
    try:
        curr_dt = parse_date(conflict_date)
        next_day = (curr_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        return {
            'type': 'next_day_slot',
            'equipment_id': eq['id'],
            'equipment_name': eq['name'],
            'equipment_code': eq['code'],
            'date': next_day,
            'slot': conflict_slot,
            'summary': f"Priority rollover to next day ({next_day}) at {conflict_slot} on {eq['name']}"
        }
    except Exception:
        return {
            'type': 'manual_faculty_coordination',
            'summary': "Lab Coordinator intervention recommended for custom slot scheduling."
        }

def generate_ai_explanation(winner_data, competitor_data, alt_rec):
    """
    Generates transparent, natural-language explanation of why the allocation
    was recommended, highlighting deadline, fairness, and the alternative provided.
    If GEMINI_API_KEY is available, enriches with GenAI; otherwise uses
    deterministic local intelligent reasoning breakdown.
    """
    w_name = winner_data['user_name']
    w_proj = winner_data.get('project_title', 'Scheduled Research Task')
    w_score = winner_data['scores']['composite']
    w_bd = winner_data['scores']['breakdown']
    w_deadline = winner_data.get('project_deadline', 'Immediate')
    
    c_name = competitor_data['user_name']
    c_proj = competitor_data.get('project_title', 'Academic Laboratory Task')
    c_score = competitor_data['scores']['composite']
    c_bd = competitor_data['scores']['breakdown']
    c_deadline = competitor_data.get('project_deadline', 'Flexible')

    local_text = (
        f"LabLink AI Scheduling Engine evaluated both competing requests using multi-factor fairness optimization. "
        f"{w_name} ({w_proj}) achieved a priority score of {w_score}/100 compared to {c_name} ({c_proj}) at {c_score}/100.\n\n"
        f"Key Deciding Factors:\n"
        f"1. Project Deadline: {w_name}'s deadline is {w_deadline} (Score: {w_bd['deadline_score']}/100), "
        f"prioritizing imminent completion compared to {c_name}'s deadline ({c_deadline}, Score: {c_bd['deadline_score']}/100).\n"
        f"2. Fairness & Historical Equity: {w_name} received an equity score of {w_bd['fairness_score']}/100, "
        f"guaranteeing fair lab distribution.\n"
        f"3. Win-Win Resource Provisioning: {alt_rec['summary']}. Both students continue without progress blockage."
    )

    mode = "Local Intelligent Recommendation Engine (Deterministic & Transparent)"

    # Optional Gemini GenAI enhancement if API key is present
    if GEMINI_API_KEY:
        try:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            prompt = (
                f"You are the LabLink Academic AI Lab Coordinator. Explain this lab equipment scheduling conflict resolution:\n"
                f"Winner: {w_name}, Project: '{w_proj}', Deadline: {w_deadline}, Score: {w_score} (Breakdown: {w_bd}).\n"
                f"Competing: {c_name}, Project: '{c_proj}', Deadline: {c_deadline}, Score: {c_score} (Breakdown: {c_bd}).\n"
                f"Recommended Alternative for {c_name}: {alt_rec['summary']}.\n"
                f"Write a professional, concise, encouraging 2-paragraph decision summary for faculty and students."
            )
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=4
            )
            if resp.status_code == 200:
                data = resp.json()
                gen_text = data['candidates'][0]['content']['parts'][0]['text']
                return {
                    'text': gen_text.strip(),
                    'mode': 'GenAI Enhanced (Gemini 1.5 Flash)',
                    'structured_breakdown': local_text
                }
        except Exception:
            pass  # Fallback to deterministic local engine seamlessly

    return {
        'text': local_text,
        'mode': mode,
        'structured_breakdown': local_text
    }

def detect_and_analyze_conflicts():
    """
    Scans pending bookings and project requests across the database to detect
    any slot collisions on the same equipment.
    Computes priority scores, alternative allocations, and recommendations.
    """
    # Fetch all pending requests grouped by equipment, date, slot
    # Check regular bookings
    bookings = query_db(
        """
        SELECT b.id, b.user_id, b.equipment_id, b.booking_date, b.time_slot, b.purpose, b.status,
               u.name as user_name, u.email as user_email, u.department as user_dept,
               e.name as equipment_name, e.code as equipment_code, e.department as eq_dept, e.category as eq_cat,
               'booking' as req_type, '' as project_title, '' as project_deadline, 'medium' as urgency, 2 as duration_hours
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN equipment e ON b.equipment_id = e.id
        WHERE b.status = 'pending'
        """
    )

    # Check project requests
    projects = query_db(
        """
        SELECT p.id, p.user_id, p.equipment_id, p.preferred_date as booking_date, p.preferred_slot as time_slot,
               p.reason as purpose, p.status, u.name as user_name, u.email as user_email, u.department as user_dept,
               e.name as equipment_name, e.code as equipment_code, e.department as eq_dept, e.category as eq_cat,
               'project' as req_type, p.project_title, p.project_deadline, p.urgency, p.duration_hours
        FROM project_requests p
        JOIN users u ON p.user_id = u.id
        JOIN equipment e ON p.equipment_id = e.id
        WHERE p.status = 'pending'
        """
    )

    all_pending = bookings + projects

    # Group by (equipment_id, booking_date, time_slot)
    grouped = {}
    for req in all_pending:
        key = f"{req['equipment_id']}_{req['booking_date']}_{req['time_slot']}"
        grouped.setdefault(key, []).append(req)

    conflicts = []

    for key, items in grouped.items():
        if len(items) >= 2:
            # We have a scheduling conflict!
            # Score each competing request
            scored_items = []
            for item in items:
                score_info = compute_priority_score(item)
                item_copy = dict(item)
                item_copy['scores'] = score_info
                scored_items.append(item_copy)

            # Sort descending by composite priority score
            scored_items.sort(key=lambda x: x['scores']['composite'], reverse=True)

            winner = scored_items[0]
            competitors = scored_items[1:]

            eq_id = winner['equipment_id']
            conf_date = winner['booking_date']
            conf_slot = winner['time_slot']

            for competitor in competitors:
                alt_rec = find_alternative_allocation(eq_id, conf_date, conf_slot, exclude_user_id=competitor['user_id'])
                explanation = generate_ai_explanation(winner, competitor, alt_rec)

                conflict_obj = {
                    'conflict_key': f"{key}_{winner['id']}_{competitor['id']}",
                    'equipment_id': eq_id,
                    'equipment_name': winner['equipment_name'],
                    'equipment_code': winner['equipment_code'],
                    'department': winner['eq_dept'],
                    'date': conf_date,
                    'slot': conf_slot,
                    'winner': winner,
                    'competitor': competitor,
                    'alternative': alt_rec,
                    'explanation': explanation,
                    'raw_key': key
                }
                conflicts.append(conflict_obj)

    return conflicts

def resolve_conflict_recommendation(conflict_key, resolution_action='approve_recommendation', faculty_id=None):
    """
    Executes the conflict resolution:
    - 'approve_recommendation': Approves winner for primary slot, reschedules/approves
      competitor for recommended alternative, sends notifications.
    """
    conflicts = detect_and_analyze_conflicts()
    target_conflict = next((c for c in conflicts if c['conflict_key'] == conflict_key), None)

    if not target_conflict:
        return {'success': False, 'message': 'Conflict record not found or already resolved.'}

    # Ensure valid faculty_id for foreign key constraints
    fac = None
    if faculty_id:
        fac = query_db("SELECT id FROM users WHERE id = ?", (faculty_id,), one=True)
    if not fac:
        fac = query_db("SELECT id FROM users WHERE role = 'faculty' LIMIT 1", one=True)
    actual_faculty_id = fac['id'] if fac else None

    winner = target_conflict['winner']
    competitor = target_conflict['competitor']
    alt = target_conflict['alternative']

    # 1. Approve winner
    if winner['req_type'] == 'booking':
        execute_db(
            "UPDATE bookings SET status = 'approved', reviewed_by = ?, review_comments = ? WHERE id = ?",
            (actual_faculty_id, f"Approved via AI Conflict Resolution (Priority Score: {winner['scores']['composite']})", winner['id'])
        )
    else:
        execute_db(
            "UPDATE project_requests SET status = 'approved', faculty_comments = ? WHERE id = ?",
            (f"Approved via AI Conflict Resolution (Priority Score: {winner['scores']['composite']})", winner['id'])
        )

    create_notification(
        winner['user_id'],
        "Booking Confirmed via AI Priority Scheduling",
        f"Your request for {winner['equipment_name']} on {winner['booking_date']} ({winner['time_slot']}) was APPROVED with priority score {winner['scores']['composite']}.",
        "success"
    )

    # 2. Reschedule or offer alternative for competitor
    alt_summary = alt.get('summary', 'Alternative slot proposed')
    if alt.get('type') in ['same_equipment_different_slot', 'alternative_equipment_same_slot', 'next_day_slot']:
        alt_eq_id = alt.get('equipment_id', competitor['equipment_id'])
        alt_date = alt.get('date', competitor['booking_date'])
        alt_slot = alt.get('slot', competitor['time_slot'])

        if competitor['req_type'] == 'booking':
            execute_db(
                """
                UPDATE bookings SET equipment_id = ?, booking_date = ?, time_slot = ?, status = 'approved',
                reviewed_by = ?, review_comments = ? WHERE id = ?
                """,
                (alt_eq_id, alt_date, alt_slot, actual_faculty_id, f"Fairness Reallocation: {alt_summary}", competitor['id'])
            )
        else:
            execute_db(
                """
                UPDATE project_requests SET equipment_id = ?, preferred_date = ?, preferred_slot = ?, status = 'resolved',
                faculty_comments = ? WHERE id = ?
                """,
                (alt_eq_id, alt_date, alt_slot, f"Fairness Reallocation: {alt_summary}", competitor['id'])
            )

        create_notification(
            competitor['user_id'],
            "Fair Equipment Reallocation Arranged",
            f"Your request for {competitor['equipment_name']} was fairly reallocated to avoid project delay: {alt_summary}.",
            "info"
        )
    else:
        # Standard rejection with alternative guidance
        if competitor['req_type'] == 'booking':
            execute_db(
                "UPDATE bookings SET status = 'rejected', reviewed_by = ?, review_comments = ? WHERE id = ?",
                (actual_faculty_id, f"Slot contested. Reallocation guidance: {alt_summary}", competitor['id'])
            )
        else:
            execute_db(
                "UPDATE project_requests SET status = 'rejected', faculty_comments = ? WHERE id = ?",
                (f"Slot contested. Reallocation guidance: {alt_summary}", competitor['id'])
            )

        create_notification(
            competitor['user_id'],
            "Slot Contested - Alternative Proposed",
            f"Due to imminent project submission priority, please rebook using alternative: {alt_summary}.",
            "warning"
        )

    # Record resolution history in conflict_resolutions table
    execute_db(
        """
        INSERT INTO conflict_resolutions
        (conflict_key, equipment_id, conflict_date, time_slot, winning_id, winning_user_name,
         competing_id, competing_user_name, scores_json, reasoning, alternative_recommendation, status, resolved_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', ?)
        """,
        (
            conflict_key,
            target_conflict['equipment_id'],
            target_conflict['date'],
            target_conflict['slot'],
            winner['id'],
            winner['user_name'],
            competitor['id'],
            competitor['user_name'],
            json.dumps({'winner_score': winner['scores'], 'competitor_score': competitor['scores']}),
            target_conflict['explanation']['text'],
            alt_summary,
            actual_faculty_id
        )
    )

    return {
        'success': True,
        'message': f"Conflict resolved successfully! {winner['user_name']} awarded primary slot, and {competitor['user_name']} allocated alternative ({alt_summary})."
    }
