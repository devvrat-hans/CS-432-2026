from flask import Flask, jsonify
from flask_cors import CORS

try:
    # Works when executed from repository root as a package import.
    from assignment03.Module_B.db_management_system.api.routes import api
except ModuleNotFoundError:
    # Works when executed from assignment03/Module_B/db_management_system directly.
    from api.routes import api

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)
app.register_blueprint(api, url_prefix='/api')


@app.route('/login', methods=['POST'])
def login_alias():
    response = app.view_functions['api.login']()
    status_code = 200
    if isinstance(response, tuple):
        response, status_code = response

    data = response.get_json(silent=True) if hasattr(response, 'get_json') else {}
    if status_code != 200:
        return response, status_code

    token = data.get('token') if isinstance(data, dict) else None
    return jsonify({
        "message": "Login successful",
        "session token": token,
        "token": token,
    }), 200


@app.route('/isAuth', methods=['GET'])
def is_auth_alias():
    response = app.view_functions['api.get_me']()
    status_code = 200
    if isinstance(response, tuple):
        response, status_code = response
    if status_code != 200:
        return response, status_code

    data = response.get_json(silent=True) if hasattr(response, 'get_json') else {}
    member = data.get('member', {}) if isinstance(data, dict) else {}
    return jsonify({
        "message": "User is authenticated",
        "username": member.get('username'),
        "role": member.get('role'),
        "expiry": member.get('expires_at'),
    }), 200

@app.route('/')
def index():
    return {
        "message": "Blind Drop Module B API",
        "version": "2.0.0",
        "endpoints": {
            "POST /login": "Alias for assignment-spec login",
            "GET /isAuth": "Alias for assignment-spec session validation",
            "POST /api/auth/login": "Authenticate and create a local session",
            "POST /api/auth/logout": "Invalidate current session",
            "GET /api/auth/me": "Get currently authenticated member",
            "GET /api/members/portfolio": "View member portfolio (RBAC-aware)",
            "GET /api/audit-logs": "Admin-only audit log access",
            "GET /api/indexing/explain": "Query plan for indexed member lookup",
            "GET /api/indexing/benchmark": "Benchmark indexed member lookup",
            "GET /api/indexing/benchmark-comparison": "Compare with-index vs without-index query timings",
            "GET /api/indexing/dashboard-benchmark-comparison": "Compare dashboard summary timings with and without index hints",
            "GET /api/dashboard/summary": "Live dashboard summary counts",
            "POST /api/resilience/token-fixtures": "Create a one-time-token fixture for concurrency tests",
            "POST /api/resilience/consume-token": "Atomically consume one-time token with rollback on failure",
            "GET /api/resilience/token-status/{token_value}": "Inspect token status and download count",
            "GET /api/databases": "List all databases",
            "GET /api/databases/catalog": "List databases with table counts",
            "POST /api/databases": "Create a new database",
        }
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
