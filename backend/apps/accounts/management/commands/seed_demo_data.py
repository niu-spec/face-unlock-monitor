"""填充演示用示例数据"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User, FamilyMember
from apps.households.models import Household, HouseholdMembership, JoinApplication, Camera
from apps.zones.models import Zone
from apps.alerts.models import Alert
from apps.events.models import Event


class Command(BaseCommand):
    help = "填充演示示例数据（家庭、成员、区域、告警、事件）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--phone",
            default="13800138000",
            help="作为家庭管理员的用户手机号",
        )

    def handle(self, *args, **options):
        phone = options["phone"]
        user, _ = User.objects.get_or_create(phone=phone, defaults={"is_active": True})
        if not user.has_usable_password():
            user.set_password("123456")
            user.save()

        household, created = Household.objects.get_or_create(
            name="张三家",
            created_by=user,
            defaults={},
        )
        if created:
            self.stdout.write(f"创建家庭: {household.name}")
        HouseholdMembership.objects.get_or_create(
            household=household,
            user=user,
            defaults={"role": "admin"},
        )

        members_data = [
            ("张三", "爸爸", "adult"),
            ("李四", "妈妈", "adult"),
            ("小明", "儿子", "child"),
        ]
        for name, identity, role in members_data:
            FamilyMember.objects.get_or_create(
                household=household,
                name=name,
                defaults={"identity": identity, "role": role, "is_active": True},
            )

        kitchen_zone_points = [[100, 100], [400, 100], [400, 350], [100, 350]]
        Zone.objects.get_or_create(
            household=household,
            name="厨房禁区",
            stream_id="kitchen",
            defaults={
                "points_json": kitchen_zone_points,
                "forbidden_roles": ["child"],
                "safe_distance": 50,
                "dwell_time": 5,
            },
        )

        Camera.objects.get_or_create(
            household=household,
            stream_id="living_room",
            defaults={"name": "客厅摄像头", "rtsp_url": "rtsp://demo/living_room"},
        )
        Camera.objects.get_or_create(
            household=household,
            stream_id="kitchen",
            defaults={"name": "厨房摄像头", "rtsp_url": "rtsp://demo/kitchen"},
        )

        now = timezone.now()
        alerts_data = [
            ("FACE_UNKNOWN", "HIGH", "living_room", "客厅检测到陌生人", "pending"),
            ("INTRUSION", "HIGH", "kitchen", "小孩进入厨房禁区", "pending"),
            ("FIRE", "MEDIUM", "kitchen", "厨房检测到火情", "handled"),
            ("FALL", "HIGH", "living_room", "客厅检测到人员摔倒", "pending"),
        ]
        for alert_type, level, stream_id, desc, status in alerts_data:
            Alert.objects.get_or_create(
                household=household,
                type=alert_type,
                description=desc,
                defaults={
                    "level": level,
                    "stream_id": stream_id,
                    "status": status,
                    "handled_at": now if status == "handled" else None,
                },
            )

        events_data = [
            ("FACE_MATCHED", "living_room", "识别到家人：爸爸"),
            ("FACE_MATCHED", "living_room", "识别到家人：妈妈"),
            ("FACE_UNKNOWN", "living_room", "检测到陌生人出现"),
            ("INTRUSION", "kitchen", "小孩闯入厨房禁区"),
            ("SYSTEM", "living_room", "系统启动，监控正常运行"),
        ]
        for event_type, stream_id, desc in events_data:
            Event.objects.get_or_create(
                household=household,
                event_type=event_type,
                description=desc,
                defaults={"stream_id": stream_id, "metadata": {}},
            )

        applicant, _ = User.objects.get_or_create(
            phone="13800000001",
            defaults={"is_active": True},
        )
        if not applicant.has_usable_password():
            applicant.set_password("123456")
            applicant.save()

        JoinApplication.objects.get_or_create(
            household=household,
            applicant=applicant,
            defaults={
                "status": "pending",
                "message": "我是张家的亲戚，想加入家庭",
            },
        )

        self.stdout.write(self.style.SUCCESS(
            f"\n示例数据已就绪（管理员: {phone}）\n"
            f"  家庭: {household.name} (ID={household.id})\n"
            f"  成员: 爸爸、妈妈、小孩\n"
            f"  区域: 厨房禁区\n"
            f"  告警: {Alert.objects.filter(household=household).count()} 条\n"
            f"  事件: {Event.objects.filter(household=household).count()} 条\n"
            f"  待审核申请: 1 条 (13800000001)\n"
        ))
