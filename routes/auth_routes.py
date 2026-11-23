from flask import Blueprint, session, redirect, url_for, request, jsonify, flash
from models import query_db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/switch-role/<role>')
def switch_role(role):
    """
    Convenient 1-click role switcher for seamless evaluation and testing.
    Selects sample user based on role or specific user id.
    """
    if role == 'faculty':
        user = query_db("SELECT * FROM users WHERE role = 'faculty' LIMIT 1", one=True)
    elif role == 'student_maya':
        user = query_db("SELECT * FROM users WHERE email = 'maya.patel@campus.edu'", one=True)
    elif role == 'student_rahul':
        user = query_db("SELECT * FROM users WHERE email = 'rahul.sharma@campus.edu'", one=True)
    elif role == 'student':
        user = query_db("SELECT * FROM users WHERE role = 'student' LIMIT 1", one=True)
    else:
        user = query_db("SELECT * FROM users WHERE id = ?", (role,), one=True)

    if user:
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['user_role'] = user['role']
        session['user_dept'] = user['department']

        if user['role'] == 'faculty':
            return redirect(url_for('faculty.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))

    return redirect(url_for('student.dashboard'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Demo login form."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']
            session['user_dept'] = user['department']
            if user['role'] == 'faculty':
                return redirect(url_for('faculty.dashboard'))
            return redirect(url_for('student.dashboard'))
        else:
            flash("Invalid email. Please choose from demo accounts.", "danger")

    demo_users = query_db("SELECT * FROM users ORDER BY role, name")
    return jsonify({'demo_users': demo_users})
