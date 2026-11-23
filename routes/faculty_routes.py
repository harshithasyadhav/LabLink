from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from datetime import datetime, date
from config import STANDARD_SLOTS, DEPARTMENTS, CATEGORIES
from models import query_db, execute_db, create_notification
from services.conflict_engine import detect_and_analyze_conflicts, resolve_conflict_recommendation
from services.analytics_service import get_platform_analytics

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')

@faculty_bp.before_request
def require_faculty_access():
    """Enforces Role-Based Access Control: restricts faculty endpoints to faculty role."""
    role = session.get('user_role')
    if role != 'faculty':
        flash("Faculty authorization required to access administrative portals. Please switch role in top navigation.", "warning")
        return redirect(url_for('student.dashboard'))

def get_current_faculty_id():
    """Returns logged-in faculty user ID."""
    uid = session.get('user_id')
    if uid:
        return uid
    fac = query_db("SELECT id FROM users WHERE role = 'faculty' LIMIT 1", one=True)
    return fac['id'] if fac else 1

@faculty_bp.route('/dashboard')
def dashboard():
    """Faculty overview hub with analytics, pending actions, and conflict alerts."""
    faculty_id = get_current_faculty_id()
    analytics = get_platform_analytics()

    # Detect conflicts
    conflicts = detect_and_analyze_conflicts()

    # Pending bookings
    pending_bookings = query_db(
        """
        SELECT b.*, u.name as user_name, u.email as user_email, u.department as user_dept,
               e.name as equipment_name, e.code as equipment_code, e.location
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN equipment e ON b.equipment_id = e.id
        WHERE b.status = 'pending'
        ORDER BY b.created_at ASC
        LIMIT 8
        """
    )

    # Pending project requests
    pending_projects = query_db(
        """
        SELECT p.*, u.name as user_name, u.email as user_email, u.department as user_dept,
               e.name as equipment_name, e.code as equipment_code
        FROM project_requests p
        JOIN users u ON p.user_id = u.id
        JOIN equipment e ON p.equipment_id = e.id
        WHERE p.status = 'pending'
        ORDER BY p.created_at ASC
        LIMIT 8
        """
    )

    # Overbooked or contested equipment list
    contested_equipment_ids = {c['equipment_id'] for c in conflicts}
    contested_equipment = []
    if contested_equipment_ids:
        placeholders = ','.join('?' for _ in contested_equipment_ids)
        contested_equipment = query_db(
            f"SELECT * FROM equipment WHERE id IN ({placeholders})",
            list(contested_equipment_ids)
        )

    return render_template(
        'faculty_dashboard.html',
        analytics=analytics,
        conflicts=conflicts,
        pending_bookings=pending_bookings,
        pending_projects=pending_projects,
        contested_equipment=contested_equipment
    )

@faculty_bp.route('/requests')
def all_requests():
    """Review all incoming booking & project access requests with filtering."""
    status_filter = request.args.get('status', 'all')
    type_filter = request.args.get('type', 'all')

    # Bookings
    b_sql = """
        SELECT b.*, u.name as user_name, u.email as user_email, u.department as user_dept,
               e.name as equipment_name, e.code as equipment_code
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN equipment e ON b.equipment_id = e.id
    """
    b_params = []
    if status_filter != 'all':
        b_sql += " WHERE b.status = ?"
        b_params.append(status_filter)
    b_sql += " ORDER BY b.created_at DESC"
    bookings = query_db(b_sql, b_params)

    # Projects
    p_sql = """
        SELECT p.*, u.name as user_name, u.email as user_email, u.department as user_dept,
               e.name as equipment_name, e.code as equipment_code
        FROM project_requests p
        JOIN users u ON p.user_id = u.id
        JOIN equipment e ON p.equipment_id = e.id
    """
    p_params = []
    if status_filter != 'all':
        p_sql += " WHERE p.status = ?"
        p_params.append(status_filter)
    p_sql += " ORDER BY p.created_at DESC"
    projects = query_db(p_sql, p_params)

    return render_template(
        'faculty_requests.html',
        bookings=bookings,
        projects=projects,
        status_filter=status_filter,
        type_filter=type_filter
    )

@faculty_bp.route('/request/<req_type>/<int:req_id>/<action>', methods=['POST'])
def review_request(req_type, req_id, action):
    """
    Approve or reject a standard booking or project-based request.
    Collects faculty review comments.
    """
    faculty_id = get_current_faculty_id()
    comments = request.form.get('comments', '').strip()

    if action not in ['approve', 'reject', 'complete']:
        flash("Invalid action.", "danger")
        return redirect(url_for('faculty.all_requests'))

    target_status = 'approved' if action == 'approve' else ('rejected' if action == 'reject' else 'completed')
    if not comments:
        comments = f"Marked as {target_status} by Faculty Laboratory Supervisor."

    if req_type == 'booking':
        b = query_db("SELECT * FROM bookings WHERE id = ?", (req_id,), one=True)
        if not b:
            flash("Booking record not found.", "danger")
            return redirect(url_for('faculty.all_requests'))

        execute_db(
            "UPDATE bookings SET status = ?, reviewed_by = ?, review_comments = ? WHERE id = ?",
            (target_status, faculty_id, comments, req_id)
        )

        create_notification(
            b['user_id'],
            f"Booking {target_status.capitalize()}",
            f"Your booking on {b['booking_date']} ({b['time_slot']}) was {target_status}. Notes: {comments}",
            'success' if target_status == 'approved' else 'warning'
        )

    elif req_type == 'project':
        p = query_db("SELECT * FROM project_requests WHERE id = ?", (req_id,), one=True)
        if not p:
            flash("Project request not found.", "danger")
            return redirect(url_for('faculty.all_requests'))

        execute_db(
            "UPDATE project_requests SET status = ?, faculty_comments = ? WHERE id = ?",
            (target_status, comments, req_id)
        )

        create_notification(
            p['user_id'],
            f"Project Access Request {target_status.capitalize()}",
            f"Your project request for '{p['project_title']}' was {target_status}. Notes: {comments}",
            'success' if target_status == 'approved' else 'warning'
        )

    flash(f"Request marked as {target_status} successfully.", "success")
    return redirect(request.referrer or url_for('faculty.all_requests'))

@faculty_bp.route('/conflicts')
def conflict_center():
    """
    Dedicated AI Conflict Resolution & Fairness Optimization Center.
    Presents overlapping requests, transparent priority score breakdown,
    alternative allocations, and 1-click resolution.
    """
    conflicts = detect_and_analyze_conflicts()
    return render_template(
        'faculty_conflicts.html',
        conflicts=conflicts
    )

@faculty_bp.route('/conflicts/resolve', methods=['POST'])
def resolve_conflict_action():
    """Applies the recommended AI allocation for a detected conflict."""
    faculty_id = get_current_faculty_id()
    conflict_key = request.form.get('conflict_key')

    result = resolve_conflict_recommendation(conflict_key, 'approve_recommendation', faculty_id)
    if result.get('success'):
        flash(result['message'], "success")
    else:
        flash(result.get('message', 'Unable to resolve conflict.'), "danger")

    return redirect(url_for('faculty.conflict_center'))

@faculty_bp.route('/equipment', methods=['GET', 'POST'])
def manage_equipment():
    """Faculty equipment inventory management (Add, Edit, Maintenance toggle)."""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            name = request.form.get('name', '').strip()
            code = request.form.get('code', '').strip()
            category = request.form.get('category', '').strip()
            department = request.form.get('department', '').strip()
            location = request.form.get('location', '').strip()
            specs = request.form.get('specs', '').strip()
            instructions = request.form.get('instructions', '').strip()
            image_icon = request.form.get('image_icon', 'chip').strip()

            if not all([name, code, category, department, location]):
                flash("Please fill in all mandatory equipment details.", "danger")
            else:
                try:
                    execute_db(
                        """
                        INSERT INTO equipment (name, code, category, department, location, specs, instructions, image_icon, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'available')
                        """,
                        (name, code, category, department, location, specs, instructions, image_icon)
                    )
                    flash(f"Equipment '{name}' ({code}) added to laboratory inventory.", "success")
                except Exception as e:
                    flash(f"Error adding equipment: {str(e)}", "danger")

        elif action == 'toggle_status':
            eq_id = request.form.get('equipment_id', type=int)
            new_status = request.form.get('new_status', 'available')
            execute_db("UPDATE equipment SET status = ? WHERE id = ?", (new_status, eq_id))
            flash(f"Equipment status updated to '{new_status}'.", "info")

        return redirect(url_for('faculty.manage_equipment'))

    equipment_list = query_db("SELECT * FROM equipment ORDER BY department, name")
    return render_template(
        'faculty_equipment.html',
        equipment_list=equipment_list,
        categories=CATEGORIES,
        departments=DEPARTMENTS
    )

@faculty_bp.route('/schedule')
def equipment_schedule():
    """Calendar/timeline view of equipment reservations."""
    selected_date = request.args.get('date', date.today().strftime("%Y-%m-%d"))
    
    # Bookings for date
    bookings = query_db(
        """
        SELECT b.*, u.name as user_name, e.name as equipment_name, e.code as equipment_code, e.location
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN equipment e ON b.equipment_id = e.id
        WHERE b.booking_date = ? AND b.status IN ('approved', 'pending')
        ORDER BY b.time_slot ASC
        """,
        (selected_date,)
    )

    equipment_list = query_db("SELECT id, name, code, department FROM equipment ORDER BY department, name")

    # Map bookings by (equipment_id, time_slot)
    schedule_matrix = {}
    for b in bookings:
        schedule_matrix[(b['equipment_id'], b['time_slot'])] = b

    return render_template(
        'faculty_schedule.html',
        selected_date=selected_date,
        equipment_list=equipment_list,
        standard_slots=STANDARD_SLOTS,
        schedule_matrix=schedule_matrix
    )
