"""ActiveHouseholdMiddleware — 读取 X-Active-Household-Id 请求头"""
from .models import HouseholdMembership


class ActiveHouseholdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        household_id = request.headers.get("X-Active-Household-Id")
        request.active_household_id = None
        if household_id:
            try:
                hid = int(household_id)
                if request.user.is_authenticated and HouseholdMembership.objects.filter(
                    household_id=hid, user=request.user
                ).exists():
                    request.active_household_id = hid
            except (ValueError, TypeError):
                pass
        return self.get_response(request)
