"""告警数据模型。

记录检测模块产生的各类告警事件：
  - ZONE_INTRUSION: 危险区域闯入
  - FLOOD: 积水
  - FIRE: 着火
  - FALL: 摔倒
"""

import enum
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class AlertType(str, enum.Enum):
    """告警类型枚举。"""

    FACE_UNKNOWN = "FACE_UNKNOWN"       # 陌生人（人脸模块负责）
    ZONE_INTRUSION = "ZONE_INTRUSION"   # 危险区域闯入
    FLOOD = "FLOOD"                     # 积水
    FIRE = "FIRE"                       # 着火
    FALL = "FALL"                       # 摔倒


class AlertStatus(str, enum.Enum):
    """告警处置状态枚举。"""

    PENDING = "pending"         # 待处理
    CONFIRMED = "confirmed"     # 已确认
    RESOLVED = "resolved"       # 已解决
    DISMISSED = "dismissed"     # 已忽略


class Alert(db.Model):
    """告警记录表。

    Attributes:
        id: 主键自增 ID。
        alert_type: 告警类型。
        stream_id: 关联的摄像头流 ID。
        message: 告警描述信息。
        status: 处置状态。
        snapshot_path: 告警截图路径（可选）。
        detected_at: 检测到异常的时间。
        created_at: 记录创建时间。
        updated_at: 记录更新时间。
    """

    __tablename__ = "alert"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alert_type = db.Column(
        db.String(32), nullable=False, comment="告警类型"
    )
    stream_id = db.Column(db.String(16), nullable=False, comment="摄像头流ID")
    message = db.Column(db.String(256), nullable=False, comment="告警描述")
    status = db.Column(
        db.String(16),
        default=AlertStatus.PENDING.value,
        comment="处置状态",
    )
    snapshot_path = db.Column(db.String(256), comment="告警截图路径")
    detected_at = db.Column(
        db.DateTime, server_default=db.func.now(), comment="检测时间"
    )
    created_at = db.Column(
        db.DateTime, server_default=db.func.now(), comment="创建时间"
    )
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        comment="更新时间",
    )

    def to_dict(self) -> dict:
        """将模型实例序列化为字典。"""
        return {
            "id": self.id,
            "alert_type": self.alert_type,
            "stream_id": self.stream_id,
            "message": self.message,
            "status": self.status,
            "snapshot_path": self.snapshot_path,
            "detected_at": (
                self.detected_at.isoformat() if self.detected_at else None
            ),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }