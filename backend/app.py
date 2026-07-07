"""Flask application entry point."""
from flask import Flask, jsonify
from flask_restx import Api
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# ---------------------------------------------------------------------------
# 注册蓝图
# ---------------------------------------------------------------------------

# D-李东礼：危险区域与异常检测
from blueprints.detection import detection_bp
app.register_blueprint(detection_bp)

# C-王梓铭：人脸识别、家庭成员注册与人员统计
from blueprints.face import face_ns
from blueprints.home import home_ns

api = Api(
    app,
    version="1.0",
    title="Home Camera Monitor API",
    description="居家智能摄像头监控系统接口",
    doc="/api/docs",
)
api.add_namespace(face_ns, path="/api/face")
api.add_namespace(home_ns, path="/api/home")


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
