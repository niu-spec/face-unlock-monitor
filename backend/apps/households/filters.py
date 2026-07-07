"""HouseholdFilterBackend — 自动按 active_household_id 过滤"""
from rest_framework import filters


class HouseholdFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.active_household_id:
            return queryset.filter(household_id=request.active_household_id)
        # 无活跃家庭 → 返回空
        return queryset.none()
