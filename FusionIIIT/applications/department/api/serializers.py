"""API-specific serializers for the department module.

This module provides request/response serializers for department API endpoints,
complementing the main serializers in the department module.
"""

from rest_framework import serializers
from django.contrib.auth.models import User

from applications.globals.models import ExtraInfo
from ..models import (
    Announcements,
    DepartmentFeedback,
    DepartmentStock,
    DepartmentTimetable,
    Facility,
    SpecialRequest,
)


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for user details."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id']


class ExtraInfoDetailSerializer(serializers.ModelSerializer):
    """Serializer for ExtraInfo (user profile) details."""
    
    user = UserDetailSerializer(read_only=True)
    
    class Meta:
        model = ExtraInfo
        fields = ['id', 'user', 'department', 'phd_status']
        read_only_fields = ['id', 'user']


class AnnouncementCreateSerializer(serializers.Serializer):
    """Serializer for creating announcements."""
    
    programme = serializers.CharField(max_length=10, required=True)
    batch = serializers.CharField(max_length=40, required=True)
    department = serializers.CharField(max_length=40, required=True)
    message = serializers.CharField(max_length=200, required=True)
    upload_announcement = serializers.FileField(required=False, allow_null=True)
    
    def validate_programme(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Programme cannot be empty.")
        return value.strip()
    
    def validate_batch(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Batch cannot be empty.")
        return value.strip()
    
    def validate_department(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Department cannot be empty.")
        return value.strip()
    
    def validate_message(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty.")
        return value.strip()


class AnnouncementResponseSerializer(serializers.ModelSerializer):
    """Serializer for announcement responses."""
    
    maker_username = serializers.CharField(source='maker_id.user.username', read_only=True)
    upload_announcement_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcements
        fields = [
            'id',
            'maker_id',
            'maker_username',
            'ann_date',
            'message',
            'batch',
            'department',
            'programme',
            'upload_announcement_url',
        ]
        read_only_fields = ['id', 'ann_date', 'maker_username']
    
    def get_upload_announcement_url(self, obj):
        if obj.upload_announcement:
            return obj.upload_announcement.url
        return None


class StockRequestCreateSerializer(serializers.Serializer):
    """Serializer for creating stock requests."""
    
    brief = serializers.CharField(max_length=50, required=True)
    request_details = serializers.CharField(max_length=300, required=True)
    stock_item_name = serializers.CharField(max_length=100, required=True)
    quantity = serializers.IntegerField(min_value=1, required=True)
    request_receiver = serializers.CharField(max_length=50, required=True)
    lab = serializers.CharField(max_length=100, required=False, allow_blank=True)
    upload_request = serializers.FileField(required=False, allow_null=True)
    
    def validate_brief(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Brief cannot be empty.")
        return value.strip()
    
    def validate_request_details(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Request details cannot be empty.")
        return value.strip()


class StockRequestResponseSerializer(serializers.ModelSerializer):
    """Serializer for stock request responses."""
    
    request_maker_username = serializers.CharField(
        source='request_maker.user.username',
        read_only=True,
    )
    issued_by_username = serializers.CharField(
        source='issued_by.user.username',
        read_only=True,
        allow_null=True,
    )
    upload_request_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DepartmentStock
        fields = [
            'id',
            'request_maker',
            'request_maker_username',
            'request_date',
            'brief',
            'request_details',
            'stock_item_name',
            'quantity',
            'request_receiver',
            'lab',
            'status',
            'remarks',
            'issued_by',
            'issued_by_username',
            'issued_quantity',
            'issued_date',
            'upload_request_url',
        ]
        read_only_fields = [
            'id',
            'request_date',
            'status',
            'remarks',
            'issued_by',
            'issued_quantity',
            'issued_date',
        ]
    
    def get_upload_request_url(self, obj):
        if obj.upload_request:
            return obj.upload_request.url
        return None


class StockRequestUpdateSerializer(serializers.Serializer):
    """Serializer for updating stock request status."""
    
    status = serializers.CharField(max_length=20, required=True)
    remarks = serializers.CharField(max_length=300, required=False, allow_blank=True)
    issued_quantity = serializers.IntegerField(min_value=1, required=False)
    
    def validate_status(self, value):
        valid_statuses = ['PENDING', 'ISSUED', 'REJECTED', 'CANCELLED']
        if value.upper() not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        return value.upper()


class FeedbackCreateSerializer(serializers.Serializer):
    """Serializer for creating feedback."""
    
    subject = serializers.CharField(max_length=200, required=True)
    description = serializers.CharField(required=True)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    upload_feedback = serializers.FileField(required=False, allow_null=True)
    
    def validate_subject(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Subject cannot be empty.")
        return value.strip()
    
    def validate_description(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Description cannot be empty.")
        return value.strip()


class FeedbackResponseSerializer(serializers.ModelSerializer):
    """Serializer for feedback responses."""
    
    submitter_username = serializers.CharField(
        source='submitter.user.username',
        read_only=True,
    )
    resolved_by_username = serializers.CharField(
        source='resolved_by.user.username',
        read_only=True,
        allow_null=True,
    )
    upload_feedback_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DepartmentFeedback
        fields = [
            'id',
            'submitter',
            'submitter_username',
            'subject',
            'description',
            'category',
            'is_resolved',
            'resolved_by',
            'resolved_by_username',
            'resolved_date',
            'resolution',
            'upload_feedback_url',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'is_resolved',
            'resolved_by',
            'resolved_date',
            'resolution',
            'created_at',
        ]
    
    def get_upload_feedback_url(self, obj):
        if obj.upload_feedback:
            return obj.upload_feedback.url
        return None


class SpecialRequestCreateSerializer(serializers.Serializer):
    """Serializer for creating special requests."""
    
    brief = serializers.CharField(max_length=20, required=True)
    request_details = serializers.CharField(max_length=200, required=True)
    request_receiver = serializers.CharField(max_length=30, required=False, allow_blank=True)
    upload_request = serializers.FileField(required=False, allow_null=True)
    
    def validate_brief(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Brief cannot be empty.")
        return value.strip()


class SpecialRequestResponseSerializer(serializers.ModelSerializer):
    """Serializer for special request responses."""
    
    request_maker_username = serializers.CharField(
        source='request_maker.user.username',
        read_only=True,
    )
    upload_request_url = serializers.SerializerMethodField()
    
    class Meta:
        model = SpecialRequest
        fields = [
            'id',
            'request_maker',
            'request_maker_username',
            'request_date',
            'brief',
            'request_details',
            'status',
            'remarks',
            'request_receiver',
            'upload_request_url',
        ]
        read_only_fields = ['id', 'request_date', 'status', 'remarks']
    
    def get_upload_request_url(self, obj):
        if obj.upload_request:
            return obj.upload_request.url
        return None


class FacilityCreateSerializer(serializers.Serializer):
    """Serializer for creating facilities."""
    
    name = serializers.CharField(max_length=100, required=True)
    branch = serializers.CharField(max_length=40, required=False, allow_blank=True)
    location = serializers.CharField(max_length=100, required=False, allow_blank=True)
    lab = serializers.CharField(max_length=100, required=False, allow_blank=True)
    amount = serializers.IntegerField(min_value=1, required=False, default=1)
    picture = serializers.ImageField(required=False, allow_null=True)
    stock_request_id = serializers.IntegerField(required=False, allow_null=True)


class FacilityResponseSerializer(serializers.ModelSerializer):
    """Serializer for facility responses."""
    
    picture_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Facility
        fields = [
            'id',
            'name',
            'branch',
            'location',
            'lab',
            'amount',
            'picture_url',
            'stock_request_id',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_picture_url(self, obj):
        if obj.picture:
            return obj.picture.url
        return None


class DepartmentStockSummarySerializer(serializers.Serializer):
    """Serializer for department stock summary."""
    
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    issued = serializers.IntegerField()
    rejected = serializers.IntegerField()
