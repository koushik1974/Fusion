"""Query selectors for the department module.

These helpers centralize read-side ORM queries for department APIs.
"""

from django.db.models import Q

from applications.globals.models import ExtraInfo

from .models import Announcements, DepartmentFeedback, DepartmentStock, DepartmentTimetable


def get_department_announcements(branch):
	"""Return announcement queryset filtered by branch.

	branch=ALL returns all announcements.
	Other branch values return branch-specific plus ALL announcements.
	"""
	branch = (branch or "").strip().upper()
	queryset = Announcements.objects.select_related("maker_id__user").all().order_by("-ann_date", "-id")
	if branch and branch != "ALL":
		queryset = queryset.filter(Q(department=branch) | Q(department="ALL"))
	return queryset


def get_department_stock_for_user(user, include_all=False):
	"""Return stock requests with standard select_related joins."""
	queryset = DepartmentStock.objects.select_related("request_maker__user", "issued_by__user").all()
	if include_all:
		return queryset
	try:
		user_info = ExtraInfo.objects.get(user=user)
	except ExtraInfo.DoesNotExist:
		return queryset.none()
	return queryset.filter(request_maker=user_info)


def get_department_feedback_for_user(user, include_all=False, category=None):
	"""Return department feedback with optional category filter."""
	queryset = DepartmentFeedback.objects.select_related("submitter__user", "resolved_by__user").all()
	if include_all:
		if category:
			return queryset.filter(category__iexact=category)
		return queryset

	try:
		user_info = ExtraInfo.objects.get(user=user)
	except ExtraInfo.DoesNotExist:
		return queryset.none()

	queryset = queryset.filter(submitter=user_info)
	if category:
		queryset = queryset.filter(category__iexact=category)
	return queryset


def get_department_timetable_for_user(can_manage):
	"""Return timetable queryset; non-managers get empty queryset."""
	queryset = DepartmentTimetable.objects.all()
	return queryset if can_manage else queryset.none()

