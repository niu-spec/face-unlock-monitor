"""Flask application entry point."""
from flask import Flask, jsonify
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# ---------------------------------------------------------------------------
# 注册蓝图
# ---------------------------------------------------------------------------

# D-李东礼：危险区域与异常检测
from blueprints.detection import detection_bp
app.register_blueprint(detection_bp)


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
