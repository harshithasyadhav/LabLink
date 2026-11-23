import os
from flask import Flask, redirect, url_for, session, render_template
from config import SECRET_KEY
from models import init_db, query_db
from services.conflict_engine import detect_and_analyze_conflicts

def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    # Ensure database is initialized
    init_db()

    # Register blueprints
    from routes.auth_routes import auth_bp
    from routes.student_routes import student_bp
    from routes.faculty_routes import faculty_bp
    from routes.analytics_routes import analytics_bp
    from routes.api_routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_global_data():
        """Injects current user, unread notification count, and conflict count into all templates."""
        user_id = session.get('user_id')
        current_user = None
        unread_count = 0
        active_conflict_count = 0

        if user_id:
            current_user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
            notif_res = query_db(
                "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0",
                (user_id,),
                one=True
            )
            unread_count = notif_res['count'] if notif_res else 0
        else:
            # Default to first student
            current_user = query_db("SELECT * FROM users WHERE role = 'student' LIMIT 1", one=True)
            if current_user:
                session['user_id'] = current_user['id']
                session['user_role'] = current_user['role']
                session['user_name'] = current_user['name']
                session['user_dept'] = current_user['department']

        # Faculty sees conflict badge
        try:
            conflicts = detect_and_analyze_conflicts()
            active_conflict_count = len(conflicts)
        except Exception:
            active_conflict_count = 0

        demo_users = query_db("SELECT id, name, role, email, department FROM users ORDER BY role, name")

        return {
            'current_user': current_user,
            'unread_notifications_count': unread_count,
            'active_conflicts_count': active_conflict_count,
            'all_demo_users': demo_users
        }

    @app.route('/')
    def index():
        role = session.get('user_role', 'student')
        if role == 'faculty':
            return redirect(url_for('faculty.dashboard'))
        return redirect(url_for('student.dashboard'))

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    return app

# Expose top-level Flask instance named 'app' for Vercel and WSGI detection
app = create_app()
application = app

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    app.run(debug=False, host=host, port=port)
