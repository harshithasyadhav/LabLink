from flask import Blueprint, jsonify, request
from config import STANDARD_SLOTS
from models import query_db, execute_db
from services.conflict_engine import compute_priority_score, detect_and_analyze_conflicts

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/equipment')
def list_equipment():
    """Returns equipment list with optional search/category/dept filter."""
    category = request.args.get('category')
    dept = request.args.get('department')
    search = request.args.get('q')

    sql = "SELECT * FROM equipment WHERE 1=1"
    params = []
    if category:
        sql += " AND category = ?"
        params.append(category)
    if dept:
        sql += " AND department = ?"
        params.append(dept)
    if search:
        sql += " AND (name LIKE ? OR specs LIKE ? OR code LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    sql += " ORDER BY name ASC"
    items = query_db(sql, params)
    return jsonify({'equipment': items, 'count': len(items)})

@api_bp.route('/equipment/<int:eq_id>')
def equipment_detail(eq_id):
    """Returns single equipment details."""
    eq = query_db("SELECT * FROM equipment WHERE id = ?", (eq_id,), one=True)
    if not eq:
        return jsonify({'error': 'Equipment not found'}), 404
    return jsonify({'equipment': eq})

@api_bp.route('/equipment/<int:eq_id>/slots')
def check_slots(eq_id):
    """
    Returns the real-time availability status for each standard time slot
    on a given date.
    States: 'available', 'approved' (fully blocked), 'pending' (pending review)
    """
    target_date = request.args.get('date')
    if not target_date:
        return jsonify({'error': 'Date parameter is required (YYYY-MM-DD)'}), 400

    eq = query_db("SELECT * FROM equipment WHERE id = ?", (eq_id,), one=True)
    if not eq:
        return jsonify({'error': 'Equipment not found'}), 404

    # Fetch existing bookings for this equipment and date
    bookings = query_db(
        """
        SELECT time_slot, status, user_id FROM bookings
        WHERE equipment_id = ? AND booking_date = ? AND status IN ('approved', 'pending')
        """,
        (eq_id, target_date)
    )

    slot_status_map = {}
    for b in bookings:
        slot = b['time_slot']
        # If any booking is approved, slot is booked
        if b['status'] == 'approved':
            slot_status_map[slot] = 'approved'
        elif slot not in slot_status_map:
            slot_status_map[slot] = 'pending'

    slots = []
    for s in STANDARD_SLOTS:
        state = slot_status_map.get(s, 'available')
        slots.append({
            'slot': s,
            'status': state,
            'is_bookable': state != 'approved'
        })

    return jsonify({
        'equipment_id': eq_id,
        'equipment_name': eq['name'],
        'date': target_date,
        'equipment_status': eq['status'],
        'slots': slots
    })

@api_bp.route('/conflicts')
def get_conflicts():
    """Returns active conflict analysis."""
    conflicts = detect_and_analyze_conflicts()
    return jsonify({'conflicts': conflicts, 'count': len(conflicts)})

@api_bp.route('/preview-priority', methods=['POST'])
def preview_priority():
    """Preview priority score for student form transparency."""
    data = request.get_json() or {}
    score_data = compute_priority_score(data)
    return jsonify(score_data)

@api_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
def mark_notification_read(notif_id):
    """Marks a notification as read."""
    execute_db("UPDATE notifications SET is_read = 1 WHERE id = ?", (notif_id,))
    return jsonify({'success': True})
