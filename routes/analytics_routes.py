from flask import Blueprint, render_template, jsonify
from services.analytics_service import get_platform_analytics

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.route('/')
def analytics_dashboard():
    """Renders comprehensive laboratory resource utilisation analytics."""
    data = get_platform_analytics()
    return render_template('analytics.html', analytics=data)

@analytics_bp.route('/api/summary')
def analytics_api():
    """JSON API endpoint for real-time dashboard data."""
    data = get_platform_analytics()
    return jsonify(data)
