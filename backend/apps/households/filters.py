"""HouseholdFilterBackend — 自动按 X-Active-Household-Id 过滤"""
from rest_framework import filters

from .models import HouseholdMembership


def resolve_active_household_id(request):
    """JWT 在 DRF 层认证，需在 filter 阶段（认证之后）解析活跃家庭。"""
    cached = getattr(request, "active_household_id", None)
    if cached:
        return cached

    household_id = request.headers.get("X-Active-Household-Id")
    if not household_id or not getattr(request.user, "is_authenticated", False):
        return None

    try:
        hid = int(household_id)
    except (ValueError, TypeError):
        return None

    if not HouseholdMembership.objects.filter(household_id=hid, user=request.user).exists():
        return None

    request.active_household_id = hid
    return hid


class HouseholdFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        hid = resolve_active_household_id(request)
        if hid:
            return queryset.filter(household_id=hid)
        return queryset.none()
