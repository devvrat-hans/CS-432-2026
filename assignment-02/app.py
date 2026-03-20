from flask import Flask
from flask_cors import CORS

from routes.auth_routes import auth_bp
from routes.member_routes import member_bp
from routes.user_routes import user_bp
from routes.benchmark_routes import benchmark_bp
from routes.crud_routes import (
    device_bp, session_bp, file_bp, token_bp,
    download_bp, ratelimit_bp, integrity_bp,
    sysadmin_bp, error_bp, audit_bp, policy_bp,
)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}},
     supports_credentials=True)

# Auth (no prefix — spec defines /login /isAuth /)
app.register_blueprint(auth_bp)

# All project APIs under /api
for bp in [
    member_bp, user_bp, device_bp, session_bp, file_bp,
    token_bp, download_bp, ratelimit_bp, integrity_bp,
    sysadmin_bp, error_bp, audit_bp, policy_bp, benchmark_bp,
]:
    app.register_blueprint(bp, url_prefix="/api")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
