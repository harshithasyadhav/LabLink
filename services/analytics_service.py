from models import query_db

def get_platform_analytics():
    """
    Computes real-time resource utilization analytics, department statistics,
    and equipment frequency metrics for the dashboard.
    """
    # Total equipment
    total_eq_res = query_db("SELECT COUNT(*) as count FROM equipment", one=True)
    total_equipment = total_eq_res['count'] if total_eq_res else 0

    # Available equipment
    avail_eq_res = query_db("SELECT COUNT(*) as count FROM equipment WHERE status = 'available'", one=True)
    available_equipment = avail_eq_res['count'] if avail_eq_res else 0

    # Maintenance / reserved
    maint_eq_res = query_db("SELECT COUNT(*) as count FROM equipment WHERE status IN ('maintenance', 'reserved')", one=True)
    maintenance_equipment = maint_eq_res['count'] if maint_eq_res else 0

    # Pending requests (bookings + project requests)
    pending_bookings = query_db("SELECT COUNT(*) as count FROM bookings WHERE status = 'pending'", one=True)
    pending_projects = query_db("SELECT COUNT(*) as count FROM project_requests WHERE status = 'pending'", one=True)
    pending_requests = (pending_bookings['count'] if pending_bookings else 0) + (pending_projects['count'] if pending_projects else 0)

    # Approved bookings
    approved_bookings_res = query_db("SELECT COUNT(*) as count FROM bookings WHERE status = 'approved'", one=True)
    approved_projects_res = query_db("SELECT COUNT(*) as count FROM project_requests WHERE status IN ('approved', 'resolved')", one=True)
    approved_bookings = (approved_bookings_res['count'] if approved_bookings_res else 0) + (approved_projects_res['count'] if approved_projects_res else 0)

    # Completed bookings
    completed_bookings_res = query_db("SELECT COUNT(*) as count FROM bookings WHERE status = 'completed'", one=True)
    completed_bookings = completed_bookings_res['count'] if completed_bookings_res else 0

    # Equipment currently in active booked state (distinct equipment with approved/active bookings today/upcoming)
    active_booked_res = query_db(
        """
        SELECT COUNT(DISTINCT equipment_id) as count FROM bookings
        WHERE status = 'approved'
        """,
        one=True
    )
    currently_booked_equipment = active_booked_res['count'] if active_booked_res else 0

    # Overall utilization rate (%)
    if total_equipment > 0:
        utilization_rate = round((currently_booked_equipment / total_equipment) * 100, 1)
    else:
        utilization_rate = 0.0

    # Department-wise equipment usage count
    dept_usage = query_db(
        """
        SELECT e.department, COUNT(b.id) as booking_count, COUNT(DISTINCT e.id) as equipment_count
        FROM equipment e
        LEFT JOIN bookings b ON e.id = b.equipment_id AND b.status IN ('approved', 'completed')
        GROUP BY e.department
        ORDER BY booking_count DESC
        """
    )

    # Most frequently requested resources
    top_resources = query_db(
        """
        SELECT e.id, e.name, e.code, e.department, e.category, COUNT(b.id) as request_count
        FROM equipment e
        LEFT JOIN bookings b ON e.id = b.equipment_id
        GROUP BY e.id
        ORDER BY request_count DESC
        LIMIT 6
        """
    )

    # Category distribution
    cat_distribution = query_db(
        """
        SELECT category, COUNT(*) as count
        FROM equipment
        GROUP BY category
        ORDER BY count DESC
        """
    )

    # Slot popularity
    slot_popularity = query_db(
        """
        SELECT time_slot, COUNT(*) as count
        FROM bookings
        GROUP BY time_slot
        ORDER BY count DESC
        """
    )

    return {
        'total_equipment': total_equipment,
        'available_equipment': available_equipment,
        'maintenance_equipment': maintenance_equipment,
        'currently_booked_equipment': currently_booked_equipment,
        'pending_requests': pending_requests,
        'approved_bookings': approved_bookings,
        'completed_bookings': completed_bookings,
        'utilization_rate': utilization_rate,
        'dept_usage': dept_usage,
        'top_resources': top_resources,
        'cat_distribution': cat_distribution,
        'slot_popularity': slot_popularity
    }
