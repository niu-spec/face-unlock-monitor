"""危险区域数据模型。

用于存储前端配置的禁区多边形（如厨房等），
包含禁止进入的角色类型（如 child）。
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Zone(db.Model):
    """危险区域配置表。

    Attributes:
        id: 主键自增 ID。
        name: 区域名称，如「厨房」。
        stream_id: 关联的摄像头流 ID。
        points_json: 多边形顶点坐标，JSON 字符串格式。
        forbidden_roles: 禁止进入的角色，逗号分隔，如 "child"。
        enabled: 是否启用此区域检测。
        created_at: 创建时间。
    """

    __tablename__ = "zone"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), nullable=False, comment="区域名称")
    stream_id = db.Column(db.String(16), nullable=False, comment="摄像头流ID")
    points_json = db.Column(db.Text, nullable=False, comment="多边形顶点坐标JSON")
    forbidden_roles = db.Column(
        db.String(64), default="child", comment="禁止进入的角色，逗号分隔"
    )
    enabled = db.Column(db.Boolean, default=True, comment="是否启用")
    created_at = db.Column(
        db.DateTime, server_default=db.func.now(), comment="创建时间"
    )

    def to_dict(self) -> dict:
        """将模型实例序列化为字典。"""
        import json

        return {
            "id": self.id,
            "name": self.name,
            "stream_id": self.stream_id,
            "points_json": self.points_json,
            "points": json.loads(self.points_json) if self.points_json else [],
            "forbidden_roles": (
                self.forbidden_roles.split(",") if self.forbidden_roles else []
            ),
            "enabled": self.enabled,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }