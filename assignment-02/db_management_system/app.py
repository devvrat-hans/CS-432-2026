from flask import Flask
from api.routes import api
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}}, supports_credentials=True)
app.register_blueprint(api, url_prefix='/api')

@app.route('/')
def index():
    return {
        "message": "Blind Drop Module B API",
        "version": "2.0.0",
        "endpoints": {
            "POST /api/auth/login": "Authenticate and create a local session",
            "POST /api/auth/logout": "Invalidate current session",
            "GET /api/auth/me": "Get currently authenticated member",
            "GET /api/members/portfolio": "View member portfolio (RBAC-aware)",
            "GET /api/audit-logs": "Admin-only audit log access",
            "GET /api/indexing/explain": "Query plan for indexed member lookup",
            "GET /api/indexing/benchmark": "Benchmark indexed member lookup",
            "GET /api/indexing/benchmark-comparison": "Compare with-index vs without-index query timings",
            "GET /api/dashboard/summary": "Live dashboard summary counts",
            "GET /api/databases": "List all databases",
            "GET /api/databases/catalog": "List databases with table counts",
            "POST /api/databases": "Create a new database",
        }
    }

if __name__ == '__main__':
    app.run(debug=True, port=8080)
