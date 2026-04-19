"""DRF serializers for the department module.

This module provides standard serializer classes and can be imported from
applications.department.serializers.
"""

from rest_framework import serializers

from .models import (
    Announcements,
    DepartmentFeedback,
    DepartmentStock,
    DepartmentTimetable,
    Facility,
    SpecialRequest,
)


class SpecialRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialRequest
        fields = "__all__"


class AnnouncementSerializer(serializers.ModelSerializer):
    maker_username = serializers.CharField(source="maker_id.user.username", read_only=True)

    class Meta:
        model = Announcements
        fields = [
            "id",
            "maker_id",
            "maker_username",
            "ann_date",
            "message",
            "batch",
            "department",
            "programme",
            "upload_announcement",
        ]
        read_only_fields = ["id", "ann_date", "maker_username"]


class DepartmentStockSerializer(serializers.ModelSerializer):
    request_maker_username = serializers.CharField(source="request_maker.user.username", read_only=True)
    issued_by_username = serializers.CharField(source="issued_by.user.username", read_only=True)

    class Meta:
        model = DepartmentStock
        fields = [
            "id",
            "request_maker",
            "request_maker_username",
            "request_date",
            "brief",
            "request_details",
            "upload_request",
            "status",
            "remarks",
            "request_receiver",
            "lab",
            "quantity",
            "stock_item_name",
            "issued_by",
            "issued_by_username",
            "issued_quantity",
            "issued_date",
        ]


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = [
            "id",
            "name",
            "branch",
            "location",
            "lab",
            "amount",
            "picture",
            "stock_request_id",
            "created_at",
        ]


class DepartmentFeedbackSerializer(serializers.ModelSerializer):
    submitter_username = serializers.CharField(source="submitter.user.username", read_only=True)
    resolved_by_username = serializers.CharField(source="resolved_by.user.username", read_only=True)

    class Meta:
        model = DepartmentFeedback
        fields = [
            "id",
            "submitter",
            "submitter_username",
            "subject",
            "description",
            "upload_feedback",
            "category",
            "is_confidential",
            "status",
            "resolution_remarks",
            "resolved_by",
            "resolved_by_username",
            "submitted_at",
            "resolved_at",
        ]


class DepartmentTimetableSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentTimetable
        fields = [
            "id",
            "department",
            "programme",
            "batch",
            "day_of_week",
            "start_time",
            "end_time",
            "subject",
            "faculty",
            "room_no",
            "academic_year",
            "semester",
            "created_at",
            "updated_at",
        ]
