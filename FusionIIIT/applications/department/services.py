"""Business logic and service layer for the department module.

This module centralizes business logic for department operations including
announcements, stock requests, feedback, and special requests.
"""

from datetime import datetime
from typing import Dict, Optional, Any

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from applications.globals.models import ExtraInfo
from .models import (
    Announcements,
    DepartmentFeedback,
    DepartmentStock,
    SpecialRequest,
    Facility,
    DepartmentTimetable,
)


class AnnouncementService:
    """Service for managing department announcements."""

    @staticmethod
    def create_announcement(
        user: User,
        programme: str,
        batch: str,
        department: str,
        message: str,
        upload_announcement=None,
    ) -> Announcements:
        """Create a new announcement.
        
        Args:
            user: Django user object
            programme: Program code (e.g., 'BTech', 'MTech')
            batch: Batch/year (e.g., 'Year-1')
            department: Department code (e.g., 'CSE', 'ALL')
            message: Announcement message
            upload_announcement: Optional file upload
            
        Returns:
            Created Announcements instance
            
        Raises:
            ExtraInfo.DoesNotExist: If user profile not found
        """
        user_info = ExtraInfo.objects.get(user=user)
        
        if department == 'Natural Science':
            department = 'NS'
        
        announcement = Announcements.objects.create(
            maker_id=user_info,
            programme=programme,
            batch=batch,
            department=department,
            message=message,
            upload_announcement=upload_announcement,
            ann_date=timezone.now(),
        )
        
        return announcement

    @staticmethod
    def delete_announcement(announcement_id: int, user: User) -> bool:
        """Delete an announcement (only by creator).
        
        Args:
            announcement_id: ID of announcement to delete
            user: User attempting deletion
            
        Returns:
            True if deleted, False if not authorized
        """
        try:
            announcement = Announcements.objects.get(id=announcement_id)
            user_info = ExtraInfo.objects.get(user=user)
            
            if announcement.maker_id == user_info:
                announcement.delete()
                return True
            return False
        except (Announcements.DoesNotExist, ExtraInfo.DoesNotExist):
            return False


class DepartmentStockService:
    """Service for managing department stock requests."""

    @staticmethod
    def create_stock_request(
        user: User,
        brief: str,
        request_details: str,
        stock_item_name: str,
        quantity: int,
        request_receiver: str,
        lab: str = '',
        upload_request=None,
    ) -> DepartmentStock:
        """Create a new stock request.
        
        Args:
            user: Django user object
            brief: Brief description
            request_details: Detailed description
            stock_item_name: Name of stock item
            quantity: Requested quantity
            request_receiver: Receiver designation/name
            lab: Lab name/code
            upload_request: Optional file attachment
            
        Returns:
            Created DepartmentStock instance
        """
        user_info = ExtraInfo.objects.get(user=user)
        
        stock_request = DepartmentStock.objects.create(
            request_maker=user_info,
            brief=brief,
            request_details=request_details,
            stock_item_name=stock_item_name,
            quantity=quantity,
            request_receiver=request_receiver,
            lab=lab,
            upload_request=upload_request,
            status='PENDING',
            request_date=timezone.now(),
        )
        
        return stock_request

    @staticmethod
    def issue_stock(
        stock_request_id: int,
        issued_quantity: int,
        issued_by_user: User,
        remarks: str = '',
    ) -> DepartmentStock:
        """Issue stock for a request.
        
        Args:
            stock_request_id: ID of stock request
            issued_quantity: Quantity being issued
            issued_by_user: User issuing the stock
            remarks: Optional remarks
            
        Returns:
            Updated DepartmentStock instance
        """
        stock_request = DepartmentStock.objects.get(id=stock_request_id)
        issued_by_info = ExtraInfo.objects.get(user=issued_by_user)
        
        stock_request.issued_by = issued_by_info
        stock_request.issued_quantity = issued_quantity
        stock_request.issued_date = timezone.now()
        stock_request.status = 'ISSUED'
        stock_request.remarks = remarks
        stock_request.save()
        
        return stock_request

    @staticmethod
    def reject_stock_request(
        stock_request_id: int,
        remarks: str,
    ) -> DepartmentStock:
        """Reject a stock request.
        
        Args:
            stock_request_id: ID of stock request
            remarks: Reason for rejection
            
        Returns:
            Updated DepartmentStock instance
        """
        stock_request = DepartmentStock.objects.get(id=stock_request_id)
        stock_request.status = 'REJECTED'
        stock_request.remarks = remarks
        stock_request.save()
        
        return stock_request

    @staticmethod
    def get_stock_summary() -> Dict[str, Any]:
        """Get summary statistics for stock requests.
        
        Returns:
            Dictionary with request counts by status
        """
        from django.db.models import Count, Q
        
        total = DepartmentStock.objects.count()
        pending = DepartmentStock.objects.filter(status='PENDING').count()
        issued = DepartmentStock.objects.filter(status='ISSUED').count()
        rejected = DepartmentStock.objects.filter(status='REJECTED').count()
        
        return {
            'total': total,
            'pending': pending,
            'issued': issued,
            'rejected': rejected,
        }


class FeedbackService:
    """Service for managing department feedback."""

    @staticmethod
    def create_feedback(
        user: User,
        subject: str,
        description: str,
        category: str = '',
        upload_feedback=None,
    ) -> DepartmentFeedback:
        """Create department feedback.
        
        Args:
            user: Django user object
            subject: Feedback subject
            description: Detailed description
            category: Feedback category (e.g., 'Infrastructure', 'Academic')
            upload_feedback: Optional file attachment
            
        Returns:
            Created DepartmentFeedback instance
        """
        user_info = ExtraInfo.objects.get(user=user)
        
        feedback = DepartmentFeedback.objects.create(
            submitter=user_info,
            subject=subject,
            description=description,
            category=category,
            upload_feedback=upload_feedback,
        )
        
        return feedback

    @staticmethod
    def resolve_feedback(
        feedback_id: int,
        resolved_by_user: User,
        resolution: str = '',
    ) -> DepartmentFeedback:
        """Mark feedback as resolved.
        
        Args:
            feedback_id: ID of feedback
            resolved_by_user: User resolving the feedback
            resolution: Resolution details
            
        Returns:
            Updated DepartmentFeedback instance
        """
        feedback = DepartmentFeedback.objects.get(id=feedback_id)
        resolved_by_info = ExtraInfo.objects.get(user=resolved_by_user)
        
        feedback.resolved_by = resolved_by_info
        feedback.resolved_date = timezone.now()
        feedback.resolution = resolution
        feedback.is_resolved = True
        feedback.save()
        
        return feedback


class FacilityService:
    """Service for managing department facilities."""

    @staticmethod
    def create_facility(
        name: str,
        branch: str,
        location: str = '',
        lab: str = '',
        amount: int = 1,
        picture=None,
        stock_request_id: Optional[int] = None,
    ) -> Facility:
        """Create a new facility.
        
        Args:
            name: Facility name
            branch: Branch/department
            location: Facility location
            lab: Lab designation
            amount: Quantity
            picture: Photo attachment
            stock_request_id: Link to stock request
            
        Returns:
            Created Facility instance
        """
        facility = Facility.objects.create(
            name=name,
            branch=branch,
            location=location,
            lab=lab,
            amount=amount,
            picture=picture,
            stock_request_id=stock_request_id,
        )
        return facility

    @staticmethod
    @transaction.atomic
    def bulk_delete_facilities(facility_ids: list) -> int:
        """Delete multiple facilities atomically.
        
        Args:
            facility_ids: List of facility IDs to delete
            
        Returns:
            Number of facilities deleted
        """
        deleted_count, _ = Facility.objects.filter(id__in=facility_ids).delete()
        return deleted_count


class SpecialRequestService:
    """Service for managing special requests."""

    @staticmethod
    def create_special_request(
        user: User,
        brief: str,
        request_details: str,
        request_receiver: str = '',
        upload_request=None,
    ) -> SpecialRequest:
        """Create a special request.
        
        Args:
            user: Django user object
            brief: Brief description
            request_details: Detailed description
            request_receiver: Receiver designation
            upload_request: Optional file attachment
            
        Returns:
            Created SpecialRequest instance
        """
        user_info = ExtraInfo.objects.get(user=user)
        
        special_request = SpecialRequest.objects.create(
            request_maker=user_info,
            brief=brief,
            request_details=request_details,
            request_receiver=request_receiver,
            upload_request=upload_request,
            status='Pending',
            request_date=timezone.now(),
        )
        
        return special_request

    @staticmethod
    def update_special_request_status(
        request_id: int,
        status: str,
        remarks: str = '',
    ) -> SpecialRequest:
        """Update special request status.
        
        Args:
            request_id: ID of special request
            status: New status
            remarks: Optional remarks
            
        Returns:
            Updated SpecialRequest instance
        """
        special_request = SpecialRequest.objects.get(id=request_id)
        special_request.status = status
        if remarks:
            special_request.remarks = remarks
        special_request.save()
        
        return special_request


class FacilityService:
    """Service for managing department facilities."""

    @staticmethod
    def create_facility(
        name: str,
        branch: str = '',
        location: str = '',
        lab: str = '',
        amount: int = 1,
        picture=None,
        stock_request_id: Optional[int] = None,
    ) -> Facility:
        """Create a facility record.
        
        Args:
            name: Facility name
            branch: Branch/department
            location: Location details
            lab: Lab name
            amount: Quantity
            picture: Optional facility image
            stock_request_id: Related stock request ID
            
        Returns:
            Created Facility instance
        """
        facility = Facility.objects.create(
            name=name,
            branch=branch,
            location=location,
            lab=lab,
            amount=amount,
            picture=picture,
            stock_request_id=stock_request_id,
            created_at=timezone.now(),
        )
        
        return facility

    @staticmethod
    def update_facility(
        facility_id: int,
        **kwargs,
    ) -> Facility:
        """Update facility details.
        
        Args:
            facility_id: ID of facility
            **kwargs: Fields to update
            
        Returns:
            Updated Facility instance
        """
        facility = Facility.objects.get(id=facility_id)
        
        for field, value in kwargs.items():
            if hasattr(facility, field):
                setattr(facility, field, value)
        
        facility.save()
        return facility


class DepartmentBulkOperations:
    """Service for bulk operations on department data."""

    @staticmethod
    @transaction.atomic
    def bulk_process_stock_requests(request_updates: Dict[int, Dict[str, Any]]) -> list:
        """Batch process multiple stock requests.
        
        Args:
            request_updates: Dict mapping request_id to update dict
                           (should contain 'status', 'remarks', etc.)
                           
        Returns:
            List of updated DepartmentStock instances
        """
        updated_requests = []
        
        for request_id, updates in request_updates.items():
            try:
                stock_request = DepartmentStock.objects.get(id=request_id)
                
                for field, value in updates.items():
                    if hasattr(stock_request, field):
                        setattr(stock_request, field, value)
                
                stock_request.save()
                updated_requests.append(stock_request)
            except DepartmentStock.DoesNotExist:
                continue
        
        return updated_requests
