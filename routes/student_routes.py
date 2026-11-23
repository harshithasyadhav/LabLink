from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from datetime import datetime, date
from config import STANDARD_SLOTS, DEPARTMENTS, CATEGORIES
from models import query_db, execute_db, create_notification
from services.conflict_engine import compute_priority_score

student_bp = Blueprint('student', __name__, url_prefix='/student')

def get_current_user_id():
    """Returns the current logged-in user id or default student."""
    uid = session.get('user_id')
    if not uid:
        user = query_db("SELECT id FROM users WHERE role = 'student' LIMIT 1", one=True)
        if user:
            session['user_id'] = user['id']
            session['user_role'] = 'student'
            return user['id']
    return uid

@student_bp.route('/dashboard')
def dashboard():
    """Student overview hub."""
    user_id = get_current_user_id()
    user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    
    # Active & upcoming bookings
    active_bookings = query_db(
        """
        SELECT b.*, e.name as equipment_name, e.code as equipment_code, e.location, e.department, e.category
        FROM bookings b
        JOIN equipment e ON b.equipment_id = e.id
        WHERE b.user_id = ? AND b.status IN ('pending', 'approved')
        ORDER BY b.booking_date ASC, b.time_slot ASC
        """,
        (user_id,)
    )

    # Project requests
    project_requests = query_db(
        """
        SELECT p.*, e.name as equipment_name, e.code as equipment_code
        FROM project_requests p
        JOIN equipment e ON p.equipment_id = e.id
        WHERE p.user_id = ?
        ORDER BY p.created_at DESC
        """,
        (user_id,)
    )

    # Notifications
    notifications = query_db(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (user_id,)
    )

    # Stats
    stats = {
        'total_active': len(active_bookings),
        'pending_approvals': sum(1 for b in active_bookings if b['status'] == 'pending') + sum(1 for p in project_requests if p['status'] == 'pending'),
        'approved_count': sum(1 for b in active_bookings if b['status'] == 'approved'),
        'project_count': len(project_requests)
    }

    # Featured equipment for quick discovery
    featured_equipment = query_db(
        "SELECT * FROM equipment WHERE status = 'available' ORDER BY id ASC LIMIT 4"
    )

    return render_template(
        'student_dashboard.html',
        user=user,
        active_bookings=active_bookings,
        project_requests=project_requests,
        notifications=notifications,
        stats=stats,
        featured_equipment=featured_equipment,
        departments=DEPARTMENTS,
        categories=CATEGORIES,
        standard_slots=STANDARD_SLOTS
    )

@student_bp.route('/equipment')
def equipment_catalogue():
    """Searchable & filterable equipment catalogue."""
    user_id = get_current_user_id()
    
    # Query parameters
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    department = request.args.get('department', '').strip()
    availability = request.args.get('availability', '').strip()

    sql = "SELECT * FROM equipment WHERE 1=1"
    params = []

    if search:
        sql += " AND (name LIKE ? OR specs LIKE ? OR code LIKE ? OR location LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    if category:
        sql += " AND category = ?"
        params.append(category)

    if department:
        sql += " AND department = ?"
        params.append(department)

    if availability:
        sql += " AND status = ?"
        params.append(availability)

    sql += " ORDER BY name ASC"
    equipment_list = query_db(sql, params)

    return render_template(
        'equipment_catalogue.html',
        equipment_list=equipment_list,
        categories=CATEGORIES,
        departments=DEPARTMENTS,
        selected_search=search,
        selected_category=category,
        selected_department=department,
        selected_availability=availability,
        standard_slots=STANDARD_SLOTS,
        today_date=date.today().strftime("%Y-%m-%d")
    )

@student_bp.route('/book', methods=['POST'])
def book_slot():
    """
    Submits equipment booking request.
    Validates slot availability and prevents double bookings.
    """
    user_id = get_current_user_id()
    equipment_id = request.form.get('equipment_id', type=int)
    booking_date = request.form.get('booking_date', '').strip()
    time_slot = request.form.get('time_slot', '').strip()
    purpose = request.form.get('purpose', '').strip()

    if not equipment_id or not booking_date or not time_slot or not purpose:
        flash("All fields are required to reserve laboratory equipment.", "danger")
        return redirect(url_for('student.equipment_catalogue'))

    # Verify equipment exists and is not in maintenance
    eq = query_db("SELECT * FROM equipment WHERE id = ?", (equipment_id,), one=True)
    if not eq:
        flash("Selected equipment does not exist.", "danger")
        return redirect(url_for('student.equipment_catalogue'))

    if eq['status'] == 'maintenance':
        flash(f"{eq['name']} is currently under scheduled maintenance and cannot be reserved.", "warning")
        return redirect(url_for('student.equipment_catalogue'))

    # Check for existing APPROVED booking for exact slot (strict conflict prevention)
    existing_approved = query_db(
        """
        SELECT * FROM bookings
        WHERE equipment_id = ? AND booking_date = ? AND time_slot = ? AND status = 'approved'
        """,
        (equipment_id, booking_date, time_slot),
        one=True
    )
    if existing_approved:
        flash(f"Slot '{time_slot}' on {booking_date} for {eq['name']} has already been confirmed for another student. Please select an alternative slot.", "warning")
        return redirect(url_for('student.equipment_catalogue'))

    # Check if this student already booked the same slot
    already_booked_by_user = query_db(
        """
        SELECT * FROM bookings
        WHERE user_id = ? AND equipment_id = ? AND booking_date = ? AND time_slot = ? AND status IN ('pending', 'approved')
        """,
        (user_id, equipment_id, booking_date, time_slot),
        one=True
    )
    if already_booked_by_user:
        flash("You already have an active request for this equipment at the selected time slot.", "info")
        return redirect(url_for('student.my_requests'))

    # Check if another pending booking exists at this slot (AI Conflict Resolution trigger!)
    competing_pending = query_db(
        """
        SELECT * FROM bookings
        WHERE equipment_id = ? AND booking_date = ? AND time_slot = ? AND status = 'pending'
        """,
        (equipment_id, booking_date, time_slot)
    )

    # Insert booking
    new_id = execute_db(
        """
        INSERT INTO bookings (user_id, equipment_id, booking_date, time_slot, purpose, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
        """,
        (user_id, equipment_id, booking_date, time_slot, purpose)
    )

    # Create notification
    if competing_pending:
        msg = f"Your booking for {eq['name']} on {booking_date} ({time_slot}) is queued. Notice: Multiple students requested this slot; LabLink AI Priority Scheduler will recommend fair allocation."
        create_notification(user_id, "Slot Conflict Detected", msg, "conflict")
        flash("Booking submitted! Notice: Another student has requested this slot. The AI Conflict Resolution Engine will assist faculty in fair scheduling.", "warning")
    else:
        create_notification(
            user_id,
            "Booking Request Submitted",
            f"Your booking request for {eq['name']} on {booking_date} ({time_slot}) was submitted for faculty review.",
            "info"
        )
        flash(f"Booking request for {eq['name']} successfully submitted for faculty approval!", "success")

    return redirect(url_for('student.my_requests'))

@student_bp.route('/project-request', methods=['GET', 'POST'])
def project_request():
    """Project-based access request submission and guidance."""
    user_id = get_current_user_id()
    
    if request.method == 'POST':
        project_title = request.form.get('project_title', '').strip()
        project_description = request.form.get('project_description', '').strip()
        equipment_id = request.form.get('equipment_id', type=int)
        department = request.form.get('department', '').strip()
        project_deadline = request.form.get('project_deadline', '').strip()
        preferred_date = request.form.get('preferred_date', '').strip()
        preferred_slot = request.form.get('preferred_slot', '').strip()
        duration_hours = request.form.get('duration_hours', 2, type=int)
        reason = request.form.get('reason', '').strip()
        urgency = request.form.get('urgency', 'medium').strip()

        # Validation
        if not all([project_title, project_description, equipment_id, department, project_deadline, preferred_date, preferred_slot, reason]):
            flash("All fields are required to submit a project-based access request.", "danger")
            return redirect(url_for('student.project_request'))

        # Check equipment
        eq = query_db("SELECT * FROM equipment WHERE id = ?", (equipment_id,), one=True)
        if not eq:
            flash("Selected equipment does not exist.", "danger")
            return redirect(url_for('student.project_request'))

        # Save request
        new_id = execute_db(
            """
            INSERT INTO project_requests
            (user_id, equipment_id, project_title, project_description, department,
             project_deadline, preferred_date, preferred_slot, duration_hours, reason, urgency, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (user_id, equipment_id, project_title, project_description, department,
             project_deadline, preferred_date, preferred_slot, duration_hours, reason, urgency)
        )

        create_notification(
            user_id,
            "Project Request Submitted",
            f"Project access request for '{project_title}' ({eq['name']}) submitted. Faculty review pending.",
            "info"
        )

        flash(f"Project-based access request for '{project_title}' submitted successfully!", "success")
        return redirect(url_for('student.my_requests'))

    # GET: Form
    equipment_list = query_db("SELECT * FROM equipment WHERE status != 'maintenance' ORDER BY name ASC")
    today_date = date.today().strftime("%Y-%m-%d")

    return render_template(
        'project_request.html',
        equipment_list=equipment_list,
        departments=DEPARTMENTS,
        standard_slots=STANDARD_SLOTS,
        today_date=today_date
    )

@student_bp.route('/my-requests')
def my_requests():
    """Track student's booking requests and project access requests."""
    user_id = get_current_user_id()
    user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)

    bookings = query_db(
        """
        SELECT b.*, e.name as equipment_name, e.code as equipment_code, e.location, e.department, e.category
        FROM bookings b
        JOIN equipment e ON b.equipment_id = e.id
        WHERE b.user_id = ?
        ORDER BY b.created_at DESC
        """,
        (user_id,)
    )

    projects = query_db(
        """
        SELECT p.*, e.name as equipment_name, e.code as equipment_code, e.location
        FROM project_requests p
        JOIN equipment e ON p.equipment_id = e.id
        WHERE p.user_id = ?
        ORDER BY p.created_at DESC
        """,
        (user_id,)
    )

    notifications = query_db(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )

    return render_template(
        'my_requests.html',
        user=user,
        bookings=bookings,
        projects=projects,
        notifications=notifications
    )

@student_bp.route('/cancel-booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    """Allows student to cancel pending or approved booking."""
    user_id = get_current_user_id()
    b = query_db("SELECT * FROM bookings WHERE id = ? AND user_id = ?", (booking_id, user_id), one=True)
    if not b:
        flash("Booking not found or permission denied.", "danger")
        return redirect(url_for('student.my_requests'))

    execute_db("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
    flash("Booking cancelled successfully.", "info")
    return redirect(url_for('student.my_requests'))
