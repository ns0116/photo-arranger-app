import logging

from flask import Blueprint, jsonify

from services.db_service import get_report_stats

report_bp = Blueprint("report", __name__)


@report_bp.route("/api/report", methods=["GET"])
def report():
    """Returns aggregated arrange activity statistics sourced from history.

    Read-only endpoint (no CSRF token required, consistent with the other
    GET route in this app, `/`). Aggregation is entirely derived from the
    existing sessions/file_history tables; no new tables are created.
    """
    try:
        stats = get_report_stats()
        return jsonify(stats)
    except Exception as e:
        logging.error(f"Error generating report stats: {e}")
        return jsonify({"error": str(e)}), 500
