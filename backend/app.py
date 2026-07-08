"""Flask application entry point."""
from flask import Flask, jsonify
from flask_cors import CORS

from blueprints.video import video_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(video_bp)


@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "service": "home-camera-monitor",
        "scenario": "居家智能摄像头监控",
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


@app.route("/api/health")
def api_health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
