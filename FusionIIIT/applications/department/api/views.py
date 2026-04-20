from datetime import date
import json
import logging
from typing import Optional, Dict, Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
# Create your views here.
from django.db.models import Q
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.utils.dateparse import parse_date
from applications.academic_information.models import Spi, Student
from applications.globals.models import (Designation, ExtraInfo,
                                         HoldsDesignation,Faculty, DepartmentInfo)
from applications.eis.models import (faculty_about, emp_research_projects)
from applications.office_module.models import Lab
from notifications.signals import notify

from notification.views import department_notif
from ..models import SpecialRequest, Announcements, DepartmentStock, DepartmentFeedback, DepartmentTimetable, Facility
from ..constants import DepartmentRoles, StockStatus, FeedbackStatus
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework import status


logger = logging.getLogger(__name__)

# Create your views here.


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def announcements_api(request: HttpRequest) -> Response:
    """
    Create a department announcement.
    
    HTTP Methods:
        POST: Create new announcement (requires authentication)
    
    Permissions:
        Any authenticated user with valid department profile
    
    Request Body (POST):
        - programme (str): Target programme (required)
        - batch (str): Target batch year (required)
        - department (str): Department/branch code (required)
        - message (str): Announcement content (required)
        - upload_announcement (file): Optional attachment
    
    Response (201):
        {'id': <announcement_id>, 'message': 'Announcement created successfully.'}
    
    Error Responses:
        400: Missing required fields (returns field-specific errors)
        400: User profile not found
    """
    try:
        user_info = ExtraInfo.objects.select_related('user', 'department').get(user=request.user)
    except ExtraInfo.DoesNotExist:
        return Response({'detail': 'User profile not found.'}, status=status.HTTP_400_BAD_REQUEST)

    programme = (request.data.get('programme') or '').strip()
    batch = (request.data.get('batch') or '').strip()
    department = (request.data.get('department') or '').strip()
    message = (request.data.get('message') or '').strip()
    upload_announcement = request.FILES.get('upload_announcement')

    # Validate each field individually for better error feedback
    errors = {}
    if not programme:
        errors['programme'] = 'This field is required.'
    if not batch:
        errors['batch'] = 'This field is required.'
    if not department:
        errors['department'] = 'This field is required.'
    if not message:
        errors['message'] = 'This field is required.'
    
    if errors:
        return Response({'error_code': 'VALIDATION_ERROR', 'fields': errors}, status=status.HTTP_400_BAD_REQUEST)

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
    logger.info(f'Announcement created: id={announcement.id}, dept={department}, by={request.user.username}')
    logger.info(f'Announcement created: id={announcement.id}, department={department}, by={request.user.username}')

    try:
        if department == 'ALL':
            recipients = User.objects.exclude(id=request.user.id)
        else:
            recipients = User.objects.filter(
                extrainfo__department__name__iexact=department,
            ).exclude(id=request.user.id)

        notification_message = 'New announcement posted for {}'.format(department)
        for recipient in recipients.distinct():
            notify.send(
                sender=request.user,
                recipient=recipient,
                url='dep:dep',
                module='Department',
                verb=notification_message,
                description=str(announcement.id),
            )
    except Exception:
        logger.exception(
            'Failed to dispatch department announcement notifications for announcement_id=%s',
            announcement.id,
        )

    return Response(
        {
            'id': announcement.id,
            'message': 'Announcement created successfully.',
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def ann_data_api(request, branch):
    """Return announcement list for browse view.

    - branch=ALL -> all announcements
    - branch=<DEPT> -> branch-specific + global(ALL) announcements
    """
    branch = (branch or '').strip().upper()

    announcements = Announcements.objects.select_related('maker_id__user').all().order_by('-ann_date', '-id')
    if branch != 'ALL':
        announcements = announcements.filter(Q(department=branch) | Q(department='ALL'))

    response_data = [
        {
            'id': item.id,
            'ann_date': item.ann_date,
            'message': item.message,
            'batch': item.batch,
            'programme': item.programme,
            'department': item.department,
            'maker_id': item.maker_id.user.username,
            'upload_announcement': item.upload_announcement.url if item.upload_announcement else None,
        }
        for item in announcements
    ]

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def labs_api(request):
    labs = Lab.objects.all().order_by('lab', 'day', 's_time')
    response_data = [
        {
            'id': item.id,
            'name': item.lab,
            'instructor': item.lab_instructor,
            'day': item.day,
            'start_time': item.s_time,
            'end_time': item.e_time,
        }
        for item in labs
    ]
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def department_resources_api(request):
    """Get department-specific labs and HOD details."""
    try:
        user_info = ExtraInfo.objects.select_related('user', 'department').get(user=request.user)
    except ExtraInfo.DoesNotExist:
        return Response({'detail': 'User profile not found.'}, status=status.HTTP_400_BAD_REQUEST)
    
    department = user_info.department
    if not department:
        return Response({
            'department_labs': [],
            'hod_details': None,
        }, status=status.HTTP_200_OK)
    
    # Fetch department-specific labs
    labs = Lab.objects.all().order_by('lab', 'day', 's_time')
    department_labs_data = [
        {
            'id': item.id,
            'name': item.lab,
            'instructor': item.lab_instructor,
            'day': item.day,
            'start_time': item.s_time,
            'end_time': item.e_time,
        }
        for item in labs
    ]
    
    # Fetch HOD details for the user's department
    hod_details = None
    
    # Try to find HOD designation
    hod_designation = Designation.objects.filter(
        Q(name__icontains='hod') | Q(full_name__icontains='head of department')
    ).first()
    
    if hod_designation:
        # Look for HOD holding this designation in the user's department
        hod_holders = HoldsDesignation.objects.select_related(
            'working__extrainfo__user', 'working__extrainfo__department'
        ).filter(
            designation=hod_designation,
            working__extrainfo__department=department,
        )
        
        if hod_holders.exists():
            hod_holder = hod_holders.first()
            hod_user = hod_holder.working
            try:
                hod_info = ExtraInfo.objects.select_related('user', 'department').get(user=hod_user)
                if hod_info.department and hod_info.department.id == department.id:
                    hod_details = {
                        'username': hod_info.user.username,
                        'name': '{} {}'.format(hod_info.user.first_name or '', hod_info.user.last_name or '').strip() or hod_info.user.username,
                        'email': hod_info.user.email or '',
                        'phone': str(hod_info.phone_no) if hod_info.phone_no else '',
                        'department': hod_info.department.name if hod_info.department else '',
                        'designation': hod_designation.full_name or hod_designation.name,
                    }
            except ExtraInfo.DoesNotExist:
                pass
    
    return Response({
        'department_labs': department_labs_data,
        'hod_details': hod_details,
    }, status=status.HTTP_200_OK)


def _serialize_facility(item):
    return {
        'id': item.id,
        'name': item.name,
        'branch': item.branch,
        'location': item.location,
        'lab': item.lab,
        'amount': item.amount,
        'picture': item.picture.url if item.picture else None,
        'stock_request_id': item.stock_request_id,
        'created_at': item.created_at.isoformat() if item.created_at else None,
    }


def _can_delete_department_announcement(user):
    designation_names = []

    if hasattr(user, "holds_designations"):
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__name", flat=True
            )
        )
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__full_name", flat=True
            )
        )

    normalized_names = [str(name).strip().lower() for name in designation_names if name]
    for name in normalized_names:
        if (
            "deptadmin" in name
            or "dept_admin" in name
            or name.startswith("hod")
            or "hod" in name
        ):
            return True
    return False


def _can_create_department_announcement(user):
    designation_names = []

    if hasattr(user, "holds_designations"):
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__name", flat=True
            )
        )
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__full_name", flat=True
            )
        )

    normalized_names = [str(name).strip().lower() for name in designation_names if name]
    for name in normalized_names:
        if name.startswith("hod") or "hod" in name:
            return True
    return False


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def delete_announcement_api(request, announcement_id):
    if not _can_delete_department_announcement(request.user):
        return Response(
            {"detail": "You are not allowed to delete announcements."},
            status=status.HTTP_403_FORBIDDEN,
        )

    announcement = get_object_or_404(Announcements, id=announcement_id)
    announcement.delete()
    return Response(
        {"detail": "Announcement deleted successfully."},
        status=status.HTTP_200_OK,
    )


def _can_manage_department_stock(user):
    designation_names = []

    if hasattr(user, "holds_designations"):
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__name", flat=True
            )
        )
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__full_name", flat=True
            )
        )

    normalized_names = [str(name).strip().lower() for name in designation_names if name]
    for name in normalized_names:
        if (
            "assistant professor" in name
            or "deptadmin" in name
            or "dept_admin" in name
            or name.startswith("hod")
            or "hod" in name
        ):
            return True
    return False


def _can_request_stock(user):
    """Only Assistant Professors can request stock"""
    designation_names = []

    if hasattr(user, "holds_designations"):
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__name", flat=True
            )
        )
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__full_name", flat=True
            )
        )

    normalized_names = [str(name).strip().lower() for name in designation_names if name]
    for name in normalized_names:
        if "assistant professor" in name:
            return True
    return False


def _can_approve_reject_stock(user):
    """Only HOD can approve/reject stock requests"""
    designation_names = []

    if hasattr(user, "holds_designations"):
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__name", flat=True
            )
        )
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__full_name", flat=True
            )
        )

    normalized_names = [str(name).strip().lower() for name in designation_names if name]
    for name in normalized_names:
        if name.startswith("hod") or "hod" in name:
            return True
    return False


def _can_allocate_issue_stock(user):
    """Only Dept Admin can allocate/issue stock"""
    designation_names = []

    if hasattr(user, "holds_designations"):
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__name", flat=True
            )
        )
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__full_name", flat=True
            )
        )

    normalized_names = [str(name).strip().lower() for name in designation_names if name]
    for name in normalized_names:
        if "deptadmin" in name or "dept_admin" in name:
            return True
    return False


def _can_manage_department_facilities(user):
    """Only Dept Admin can create or delete facilities"""
    return _can_allocate_issue_stock(user)


def _can_manage_student_profile(user):
    """Only HOD and Dept Admin can directly edit student/faculty profiles."""
    designation_names = []

    if hasattr(user, "holds_designations"):
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__name", flat=True
            )
        )
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__full_name", flat=True
            )
        )

    normalized_names = [str(name).strip().lower() for name in designation_names if name]
    for name in normalized_names:
        if "deptadmin" in name or "dept_admin" in name or name.startswith("hod") or "hod" in name:
            return True
    return False


def _stock_request_department_name(stock_request):
    if stock_request.request_receiver:
        return str(stock_request.request_receiver).strip()

    if stock_request.request_maker_id and stock_request.request_maker.department:
        return str(stock_request.request_maker.department.name or '').strip()

    return None


def _is_same_department_access(user, department_name):
    actor_department = _get_user_department_name(user)
    if not actor_department or not department_name:
        return False
    return str(actor_department).strip().upper() == str(department_name).strip().upper()


def _serialize_department_stock(item):
    return {
        'id': item.id,
        'request_maker': item.request_maker.user.username if item.request_maker_id else None,
        'request_date': item.request_date.isoformat() if item.request_date else None,
        'brief': item.brief,
        'request_details': item.request_details,
        'upload_request': item.upload_request.url if item.upload_request else None,
        'status': item.status,
        'remarks': item.remarks,
        'request_receiver': item.request_receiver,
        'lab': item.lab,
        'quantity': item.quantity,
        'stock_item_name': item.stock_item_name,
        'issued_by': item.issued_by.user.username if item.issued_by_id else None,
        'issued_quantity': item.issued_quantity,
        'issued_date': item.issued_date.isoformat() if item.issued_date else None,
    }


def _get_department_stock_queryset(user):
    queryset = DepartmentStock.objects.select_related('request_maker__user', 'issued_by__user').all()
    try:
        user_info = ExtraInfo.objects.select_related('department').get(user=user)
    except ExtraInfo.DoesNotExist:
        return queryset.none()

    if _can_manage_department_stock(user):
        user_department = user_info.department.name if user_info.department else None
        if not user_department:
            return queryset.none()
        return queryset.filter(
            Q(request_receiver__iexact=user_department)
            | Q(request_maker__department__name__iexact=user_department)
        )

    return queryset.filter(request_maker=user_info)


def _sync_facility_from_stock_request(stock_request):
    if stock_request.status not in {StockStatus.ALLOCATED, StockStatus.ISSUED}:
        return None

    branch = ''
    if stock_request.request_maker_id and stock_request.request_maker.department:
        branch = stock_request.request_maker.department.name or ''

    defaults = {
        'name': stock_request.stock_item_name,
        'branch': branch,
        'location': stock_request.lab,
        'lab': stock_request.lab,
        'amount': stock_request.issued_quantity or stock_request.quantity,
    }

    if stock_request.issued_date:
        defaults['created_at'] = stock_request.issued_date

    facility, _ = Facility.objects.update_or_create(
        stock_request_id=stock_request.id,
        defaults=defaults,
    )
    return facility


def _can_manage_department_feedback(user):
    return _can_resolve_feedback(user)


def _can_resolve_feedback(user):
    """Only Dept Admin and HOD can resolve feedback"""
    designation_names = []

    if hasattr(user, "holds_designations"):
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__name", flat=True
            )
        )
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__full_name", flat=True
            )
        )

    normalized_names = [str(name).strip().lower() for name in designation_names if name]
    for name in normalized_names:
        if (
            "deptadmin" in name
            or "dept_admin" in name
            or name.startswith("hod")
            or "hod" in name
        ):
            return True
    return False


def _normalize_branch_name(branch):
    branch_value = (branch or '').strip()
    if branch_value.upper() == 'DS':
        return 'Design'
    if branch_value.upper() == 'NS':
        return 'Natural Science'
    if branch_value.upper() == 'LA':
        return 'Liberal Arts'
    return branch_value.upper() if branch_value.upper() in {'CSE', 'ECE', 'ME', 'SM'} else branch_value


def _serialize_directory_row(user_info, cabin_value=''):
    full_name = '{} {}'.format(user_info.user.first_name or '', user_info.user.last_name or '').strip()
    return {
        'id': user_info.user.username,
        'name': full_name or user_info.user.username,
        'department': user_info.department.name if user_info.department else '',
        'cabin_details': 'Yes' if cabin_value else '',
        'contact': str(user_info.phone_no) if user_info.phone_no else '',
        'email': user_info.user.email or '',
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def faculty_directory_api(request: HttpRequest, branch: str) -> Response:
    """
    Retrieve paginated list of faculty members in a branch.
    
    HTTP Methods:
        GET: Retrieve faculty directory
    
    Permissions:
        Any authenticated user
    
    URL Parameters:
        branch: Department/branch code
    
    Query Parameters:
        - limit (int): Results per page (default: 50, max: 500)
        - offset (int): Result offset for pagination (default: 0)
    
    Response (200):
        {'count': <total>, 'limit': <N>, 'offset': <N>, 'results': [...]}
    """
    branch_name = _normalize_branch_name(branch)
    queryset = ExtraInfo.objects.select_related('user', 'department').filter(
        user_type='faculty',
        department__name=branch_name,
    ).order_by('user__username')

    try:
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
    except (TypeError, ValueError):
        limit, offset = 50, 0
    
    total_count = queryset.count()
    paginated_queryset = queryset[offset:offset+limit]

    rows = []
    for item in paginated_queryset:
        about_obj = faculty_about.objects.filter(user=item.user).first()
        cabin_value = getattr(about_obj, 'place_of_cabin', '') if about_obj else ''
        rows.append(_serialize_directory_row(item, cabin_value))

    return Response({'count': total_count, 'limit': limit, 'offset': offset, 'results': rows}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def student_directory_api(request: HttpRequest, branch: str) -> Response:
    """
    Retrieve paginated list of students in a branch.
    
    HTTP Methods:
        GET: Retrieve student directory
    
    Permissions:
        Any authenticated user
    
    URL Parameters:
        branch: Department/branch code
    
    Query Parameters:
        - limit (int): Results per page (default: 50, max: 500)
        - offset (int): Result offset for pagination (default: 0)
    
    Response (200):
        {'count': <total>, 'limit': <N>, 'offset': <N>, 'results': [...]}
    """
    branch_name = _normalize_branch_name(branch)
    queryset = ExtraInfo.objects.select_related('user', 'department').filter(
        user_type='student',
        department__name=branch_name,
    ).order_by('user__username')

    try:
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
    except (TypeError, ValueError):
        limit, offset = 50, 0
    
    total_count = queryset.count()
    paginated_queryset = queryset[offset:offset+limit]

    rows = [_serialize_directory_row(item) for item in paginated_queryset]
    return Response({'count': total_count, 'limit': limit, 'offset': offset, 'results': rows}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def alumni_directory_api(request: HttpRequest, branch: str) -> Response:
    """
    Retrieve paginated list of alumni in a branch.
    
    HTTP Methods:
        GET: Retrieve alumni directory
    
    Permissions:
        Any authenticated user
    
    URL Parameters:
        branch: Department/branch code
    
    Query Parameters:
        - limit (int): Results per page (default: 50, max: 500)
        - offset (int): Result offset for pagination (default: 0)
    
    Response (200):
        {'count': <total>, 'limit': <N>, 'offset': <N>, 'results': [...]}
    """
    branch_name = _normalize_branch_name(branch)
    queryset = ExtraInfo.objects.select_related('user', 'department').filter(
        user_type='student',
        user_status='ALUMNI',
        department__name=branch_name,
    ).order_by('user__username')

    try:
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
    except (TypeError, ValueError):
        limit, offset = 50, 0
    
    total_count = queryset.count()
    paginated_queryset = queryset[offset:offset+limit]

    rows = [_serialize_directory_row(item) for item in paginated_queryset]
    return Response({'count': total_count, 'limit': limit, 'offset': offset, 'results': rows}, status=status.HTTP_200_OK)


def _can_review_department_profile_changes(user):
    """Only HOD can review and approve/reject profile changes"""
    designation_names = []

    if hasattr(user, "holds_designations"):
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__name", flat=True
            )
        )
        designation_names.extend(
            user.holds_designations.select_related("designation").values_list(
                "designation__full_name", flat=True
            )
        )

    normalized_names = [str(name).strip().lower() for name in designation_names if name]
    for name in normalized_names:
        if name.startswith("hod") or "hod" in name:
            return True
    return False


def _serialize_student_profile(user_info, student_obj=None):
    return {
        'roll_no': user_info.user.username,
        'name': '{} {}'.format(user_info.user.first_name or '', user_info.user.last_name or '').strip(),
        'department': user_info.department.name if user_info.department else None,
        'about_me': user_info.about_me,
        'date_of_birth': user_info.date_of_birth.isoformat() if user_info.date_of_birth else None,
        'address': user_info.address,
        'phone_no': str(user_info.phone_no) if user_info.phone_no is not None else '',
        'programme': student_obj.programme if student_obj else None,
        'batch': student_obj.batch if student_obj else None,
    }


def _serialize_faculty_profile(user_info):
    about_obj = faculty_about.objects.filter(user=user_info.user).first()
    full_name = '{} {}'.format(user_info.user.first_name or '', user_info.user.last_name or '').strip()
    return {
        'username': user_info.user.username,
        'name': full_name or user_info.user.username,
        'department': user_info.department.name if user_info.department else None,
        'about_me': user_info.about_me,
        'date_of_birth': user_info.date_of_birth.isoformat() if user_info.date_of_birth else None,
        'address': user_info.address,
        'phone_no': str(user_info.phone_no) if user_info.phone_no is not None else '',
        'faculty_about': about_obj.about if about_obj else '',
        'education': about_obj.education if about_obj else '',
        'interest': about_obj.interest if about_obj else '',
        'contact': about_obj.contact if about_obj else '',
        'github': about_obj.github if about_obj else '',
        'linkedin': about_obj.linkedin if about_obj else '',
    }


def _apply_profile_payload(target_type, target_id, payload):
    payload = payload or {}
    target_type = (target_type or '').strip().lower()

    if target_type == 'student':
        target_user = get_object_or_404(User, username=target_id)
        target_info = get_object_or_404(ExtraInfo.objects.select_related('user', 'department'), user=target_user)

        if str(target_info.user_type).strip().lower() != 'student':
            return False, 'Target does not belong to a student.'

        update_fields = []
        if 'about_me' in payload:
            target_info.about_me = payload.get('about_me') or ''
            update_fields.append('about_me')

        if 'address' in payload:
            target_info.address = payload.get('address') or ''
            update_fields.append('address')

        if 'phone_no' in payload:
            phone_value = payload.get('phone_no')
            if phone_value in (None, ''):
                target_info.phone_no = None
            else:
                try:
                    target_info.phone_no = int(str(phone_value))
                except (TypeError, ValueError):
                    return False, 'phone_no must be numeric.'
            update_fields.append('phone_no')

        if 'date_of_birth' in payload:
            dob_value = payload.get('date_of_birth')
            if dob_value in (None, ''):
                return False, 'date_of_birth cannot be empty.'
            parsed_dob = parse_date(str(dob_value))
            if parsed_dob is None:
                return False, 'date_of_birth must be in YYYY-MM-DD format.'
            target_info.date_of_birth = parsed_dob
            update_fields.append('date_of_birth')

        if 'department' in payload:
            department_value = (payload.get('department') or '').strip()
            if not department_value:
                return False, 'department cannot be empty.'
            department_obj = DepartmentInfo.objects.filter(name=department_value).first()
            if department_obj is None:
                return False, 'Invalid department.'
            target_info.department = department_obj
            update_fields.append('department')

        if update_fields:
            target_info.save(update_fields=update_fields)

        return True, _serialize_student_profile(target_info, Student.objects.filter(id=target_info).first())

    if target_type == 'faculty':
        target_user = get_object_or_404(User, username=target_id)
        target_info = get_object_or_404(ExtraInfo.objects.select_related('user', 'department'), user=target_user)

        if str(target_info.user_type).strip().lower() != 'faculty':
            return False, 'Target does not belong to faculty.'

        update_fields = []
        if 'about_me' in payload:
            target_info.about_me = payload.get('about_me') or ''
            update_fields.append('about_me')

        if 'address' in payload:
            target_info.address = payload.get('address') or ''
            update_fields.append('address')

        if 'phone_no' in payload:
            phone_value = payload.get('phone_no')
            if phone_value in (None, ''):
                target_info.phone_no = None
            else:
                try:
                    target_info.phone_no = int(str(phone_value))
                except (TypeError, ValueError):
                    return False, 'phone_no must be numeric.'
            update_fields.append('phone_no')

        if 'date_of_birth' in payload:
            dob_value = payload.get('date_of_birth')
            if dob_value in (None, ''):
                return False, 'date_of_birth cannot be empty.'
            parsed_dob = parse_date(str(dob_value))
            if parsed_dob is None:
                return False, 'date_of_birth must be in YYYY-MM-DD format.'
            target_info.date_of_birth = parsed_dob
            update_fields.append('date_of_birth')

        if 'department' in payload:
            department_value = (payload.get('department') or '').strip()
            if not department_value:
                return False, 'department cannot be empty.'
            department_obj = DepartmentInfo.objects.filter(name=department_value).first()
            if department_obj is None:
                return False, 'Invalid department.'
            target_info.department = department_obj
            update_fields.append('department')

        if update_fields:
            target_info.save(update_fields=update_fields)

        about_obj = faculty_about.objects.filter(user=target_user).first()
        about_updates = {}
        for key in ['faculty_about', 'education', 'interest', 'contact', 'github', 'linkedin']:
            if key in payload:
                about_updates[key] = payload.get(key) or ''

        if about_updates:
            if not about_obj:
                about_obj = faculty_about(user=target_user, about='', education='', interest='')

            if 'faculty_about' in about_updates:
                about_obj.about = about_updates['faculty_about']
            if 'education' in about_updates:
                about_obj.education = about_updates['education']
            if 'interest' in about_updates:
                about_obj.interest = about_updates['interest']
            if 'contact' in about_updates:
                about_obj.contact = about_updates['contact']
            if 'github' in about_updates:
                about_obj.github = about_updates['github']
            if 'linkedin' in about_updates:
                about_obj.linkedin = about_updates['linkedin']

            about_obj.save()

        refreshed = ExtraInfo.objects.select_related('user', 'department').get(pk=target_info.pk)
        return True, _serialize_faculty_profile(refreshed)

    return False, 'Unsupported target type.'


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def student_profile_api(request, roll_no):
    if not _can_manage_student_profile(request.user):
        return Response(
            {'detail': 'You are not allowed to manage student profiles.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    target_user = get_object_or_404(User, username=roll_no)

    try:
        target_info = ExtraInfo.objects.select_related('user', 'department').get(user=target_user)
    except ExtraInfo.DoesNotExist:
        return Response({'detail': 'Student profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    if str(target_info.user_type).strip().lower() != 'student':
        return Response({'detail': 'Roll number does not belong to a student.'}, status=status.HTTP_400_BAD_REQUEST)

    target_department = target_info.department.name if target_info.department else None
    if not _is_same_department_access(request.user, target_department):
        return Response(
            {'detail': 'You can only manage profiles within your department.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    student_obj = Student.objects.filter(id=target_info).first()

    if request.method == 'GET':
        return Response(_serialize_student_profile(target_info, student_obj), status=status.HTTP_200_OK)

    payload = request.data or {}
    update_fields = []

    if 'about_me' in payload:
        target_info.about_me = payload.get('about_me') or ''
        update_fields.append('about_me')

    if 'address' in payload:
        target_info.address = payload.get('address') or ''
        update_fields.append('address')

    if 'phone_no' in payload:
        phone_value = payload.get('phone_no')
        if phone_value in (None, ''):
            target_info.phone_no = None
        else:
            try:
                target_info.phone_no = int(str(phone_value))
            except (TypeError, ValueError):
                return Response({'detail': 'phone_no must be numeric.'}, status=status.HTTP_400_BAD_REQUEST)
        update_fields.append('phone_no')

    if 'date_of_birth' in payload:
        dob_value = payload.get('date_of_birth')
        if dob_value in (None, ''):
            return Response({'detail': 'date_of_birth cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)
        parsed_dob = parse_date(str(dob_value))
        if parsed_dob is None:
            return Response({'detail': 'date_of_birth must be in YYYY-MM-DD format.'}, status=status.HTTP_400_BAD_REQUEST)
        target_info.date_of_birth = parsed_dob
        update_fields.append('date_of_birth')

    if 'department' in payload:
        department_value = (payload.get('department') or '').strip()
        if not department_value:
            return Response({'detail': 'department cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)
        department_obj = DepartmentInfo.objects.filter(name=department_value).first()
        if department_obj is None:
            return Response({'detail': 'Invalid department.'}, status=status.HTTP_400_BAD_REQUEST)
        target_info.department = department_obj
        update_fields.append('department')

    if update_fields:
        target_info.save(update_fields=update_fields)

    refreshed = ExtraInfo.objects.select_related('user', 'department').get(pk=target_info.pk)
    return Response(_serialize_student_profile(refreshed, student_obj), status=status.HTTP_200_OK)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def faculty_profile_api(request, username):
    if not _can_manage_student_profile(request.user):
        return Response(
            {'detail': 'You are not allowed to manage faculty profiles.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    target_user = get_object_or_404(User, username=username)

    try:
        target_info = ExtraInfo.objects.select_related('user', 'department').get(user=target_user)
    except ExtraInfo.DoesNotExist:
        return Response({'detail': 'Faculty profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    if str(target_info.user_type).strip().lower() != 'faculty':
        return Response({'detail': 'Username does not belong to faculty.'}, status=status.HTTP_400_BAD_REQUEST)

    target_department = target_info.department.name if target_info.department else None
    if not _is_same_department_access(request.user, target_department):
        return Response(
            {'detail': 'You can only manage profiles within your department.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == 'GET':
        return Response(_serialize_faculty_profile(target_info), status=status.HTTP_200_OK)

    success, result = _apply_profile_payload('faculty', username, request.data or {})
    if not success:
        return Response({'detail': result}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result, status=status.HTTP_200_OK)


def _load_profile_change_payload(special_request):
    if not special_request.upload_request:
        return {}
    try:
        special_request.upload_request.open('r')
        raw_data = special_request.upload_request.read()
        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode('utf-8')
        return json.loads(raw_data or '{}')
    except Exception:
        logger.exception(
            'Failed to load profile change payload for special_request_id=%s',
            special_request.id,
        )
        return {}
    finally:
        try:
            special_request.upload_request.close()
        except Exception:
            logger.exception(
                'Failed to close profile change payload file for special_request_id=%s',
                special_request.id,
            )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def profile_change_requests_api(request: HttpRequest) -> Response:
    """
    Submit and review profile change requests.
    
    HTTP Methods:
        GET: View profile change requests (role-filtered)
        POST: Submit profile change request
    
    Permissions:
        GET: HOD/DeptAdmin see department requests; others see own requests
        POST: Any authenticated user
    
    Request Body (POST):
        - target_type (str): 'student' or 'faculty' (required)
        - target_id (int): User ID to modify (required, must exist)
        - changes (dict): Field changes as key-value pairs (required)
    
    Response (200/201):
        GET: Array of profile change request objects
        POST: Created profile change request object
    
    Error Responses:
        400: Missing required fields or invalid format
        404: Target user not found (data integrity check)
        403: Insufficient permissions
    """
    try:
        user_info = ExtraInfo.objects.select_related('user', 'department').get(user=request.user)
    except ExtraInfo.DoesNotExist:
        return Response({'detail': 'User profile not found.'}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'GET':
        queryset = SpecialRequest.objects.select_related('request_maker__user', 'request_maker__department').filter(
            brief='PROFILE_CHANGE'
        ).order_by('-request_date', '-id')

        if _can_review_department_profile_changes(request.user):
            department_name = user_info.department.name if user_info.department else None
            if department_name:
                queryset = queryset.filter(request_receiver=department_name)
        else:
            queryset = queryset.filter(request_maker=user_info)

        response_rows = []
        for item in queryset:
            payload = _load_profile_change_payload(item)
            response_rows.append({
                'id': item.id,
                'status': item.status,
                'remarks': item.remarks,
                'request_date': item.request_date.isoformat() if item.request_date else None,
                'request_receiver': item.request_receiver,
                'request_maker': item.request_maker.user.username if item.request_maker_id else None,
                'target_type': payload.get('target_type') or None,
                'target_id': payload.get('target_id') or None,
                'changes': payload.get('changes') or {},
                'requested_by_name': payload.get('requested_by_name') or '',
            })

        return Response(response_rows, status=status.HTTP_200_OK)

    target_type = (request.data.get('target_type') or '').strip().lower()
    target_id = str(request.data.get('target_id') or '').strip()
    changes = request.data.get('changes') or {}

    if target_type not in {'student', 'faculty'}:
        return Response({'detail': 'target_type must be student or faculty.'}, status=status.HTTP_400_BAD_REQUEST)

    if not target_id:
        return Response({'detail': 'target_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        target_user_id = int(target_id)
    except (TypeError, ValueError):
        return Response({'detail': 'target_id must be a valid user ID.'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not User.objects.filter(id=target_user_id).exists():
        return Response({'detail': 'Target user not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not isinstance(changes, dict) or not changes:
        return Response({'detail': 'changes payload is required.'}, status=status.HTTP_400_BAD_REQUEST)

    receiver = user_info.department.name if user_info.department else '--'
    profile_change_request = SpecialRequest.objects.create(
        request_maker=user_info,
        request_date=timezone.now(),
        brief='PROFILE_CHANGE',
        request_details='PROFILE_CHANGE:{}:{}'.format(target_type.upper(), target_id),
        status='Pending',
        remarks='--',
        request_receiver=receiver,
    )

    payload = {
        'target_type': target_type,
        'target_id': target_id,
        'changes': changes,
        'requested_by_name': '{} {}'.format(request.user.first_name or '', request.user.last_name or '').strip() or request.user.username,
    }
    json_bytes = json.dumps(payload, ensure_ascii=True).encode('utf-8')
    profile_change_request.upload_request.save(
        'profile_change_request_{}.json'.format(profile_change_request.id),
        ContentFile(json_bytes),
        save=True,
    )

    return Response(
        {
            'id': profile_change_request.id,
            'detail': 'Profile change request submitted for review.',
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@transaction.atomic
def profile_change_request_decision_api(request, request_id):
    if not _can_review_department_profile_changes(request.user):
        return Response(
            {'detail': 'You are not allowed to review profile change requests.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        reviewer_info = ExtraInfo.objects.select_related('department').get(user=request.user)
    except ExtraInfo.DoesNotExist:
        return Response({'detail': 'User profile not found.'}, status=status.HTTP_400_BAD_REQUEST)

    profile_change_request = get_object_or_404(
        SpecialRequest.objects.select_related('request_maker__user', 'request_maker__department'),
        id=request_id,
        brief='PROFILE_CHANGE',
    )

    reviewer_department = reviewer_info.department.name if reviewer_info.department else None
    if reviewer_department and profile_change_request.request_receiver != reviewer_department:
        return Response({'detail': 'This request belongs to a different department.'}, status=status.HTTP_403_FORBIDDEN)

    decision = (request.data.get('decision') or '').strip().upper()
    remarks = (request.data.get('remarks') or '').strip()

    if decision not in {'APPROVED', 'REJECTED'}:
        return Response({'detail': 'decision must be APPROVED or REJECTED.'}, status=status.HTTP_400_BAD_REQUEST)

    if decision == 'REJECTED':
        profile_change_request.status = 'Denied'
        profile_change_request.remarks = remarks or '--'
        profile_change_request.save(update_fields=['status', 'remarks'])

        try:
            notify.send(
                sender=request.user,
                recipient=profile_change_request.request_maker.user,
                url='dep:dep',
                module='Department',
                verb='Your profile change request #{} was rejected.'.format(profile_change_request.id),
                description=str(profile_change_request.id),
            )
        except Exception:
            logger.exception(
                'Failed to dispatch profile-change rejection notification for request_id=%s',
                profile_change_request.id,
            )

        return Response({'detail': 'Profile change request rejected.'}, status=status.HTTP_200_OK)

    payload = _load_profile_change_payload(profile_change_request)
    success, result = _apply_profile_payload(
        payload.get('target_type'),
        payload.get('target_id'),
        payload.get('changes') or {},
    )
    if not success:
        return Response({'detail': result}, status=status.HTTP_400_BAD_REQUEST)

    profile_change_request.status = 'Approved'
    profile_change_request.remarks = remarks or '--'
    profile_change_request.save(update_fields=['status', 'remarks'])

    try:
        notify.send(
            sender=request.user,
            recipient=profile_change_request.request_maker.user,
            url='dep:dep',
            module='Department',
            verb='Your profile change request #{} was approved.'.format(profile_change_request.id),
            description=str(profile_change_request.id),
        )
    except Exception:
        logger.exception(
            'Failed to dispatch profile-change approval notification for request_id=%s',
            profile_change_request.id,
        )

    return Response(
        {
            'detail': 'Profile change request approved and applied.',
            'updated_profile': result,
        },
        status=status.HTTP_200_OK,
    )


def _serialize_department_feedback(item):
    return {
        'id': item.id,
        'submitter': item.submitter.user.username if item.submitter_id else None,
        'submitter_id': item.submitter_id,
        'subject': item.subject,
        'description': item.description,
        'upload_feedback': item.upload_feedback.url if item.upload_feedback else None,
        'category': item.category,
        'is_confidential': item.is_confidential,
        'status': item.status,
        'resolution_remarks': item.resolution_remarks,
        'resolved_by': item.resolved_by.user.username if item.resolved_by_id else None,
        'resolved_by_id': item.resolved_by_id,
        'submitted_at': item.submitted_at.isoformat() if item.submitted_at else None,
        'resolved_at': item.resolved_at.isoformat() if item.resolved_at else None,
    }


def _get_department_feedback_queryset(user, category=None):
    queryset = DepartmentFeedback.objects.select_related('submitter__user', 'resolved_by__user').all()
    if _can_manage_department_feedback(user):
        manager_department = _get_user_department_name(user)
        if not manager_department:
            return queryset.none()
        queryset = queryset.filter(category__iexact=manager_department)
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


def _coerce_boolean(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _can_manage_department_timetable(user):
    """Only Dept Admin can manage timetable"""
    designation_names = []

    if hasattr(user, 'holds_designations'):
        designation_names.extend(
            user.holds_designations.select_related('designation').values_list(
                'designation__name', flat=True
            )
        )
        designation_names.extend(
            user.holds_designations.select_related('designation').values_list(
                'designation__full_name', flat=True
            )
        )

    normalized_names = [str(name).strip().lower() for name in designation_names if name]
    for name in normalized_names:
        if "deptadmin" in name or "dept_admin" in name:
            return True
    return False


def _serialize_department_timetable(item):
    def _safe_string(value):
        if value is None:
            return None
        return value.isoformat() if hasattr(value, 'isoformat') else str(value)

    return {
        'id': item.id,
        'department': item.department,
        'programme': item.programme,
        'batch': item.batch,
        'day_of_week': item.day_of_week,
        'start_time': _safe_string(item.start_time),
        'end_time': _safe_string(item.end_time),
        'subject': item.subject,
        'faculty': item.faculty,
        'room_no': item.room_no,
        'academic_year': item.academic_year,
        'semester': item.semester,
        'created_at': _safe_string(item.created_at),
        'updated_at': _safe_string(item.updated_at),
    }


def _get_department_timetable_queryset(user):
    queryset = DepartmentTimetable.objects.all()
    if _can_manage_department_timetable(user):
        manager_department = _get_user_department_name(user)
        if not manager_department:
            return queryset.none()
        return queryset.filter(department__iexact=manager_department)
    return queryset.none()


def _get_user_department_name(user):
    try:
        user_info = ExtraInfo.objects.select_related('department').get(user=user)
    except ExtraInfo.DoesNotExist:
        return None
    return user_info.department.name if user_info.department else None


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def timetable_api(request: HttpRequest) -> Response:
    """
    Manage department timetable entries.
    
    HTTP Methods:
        GET: Retrieve all timetable entries
        POST: Create new timetable entry (DeptAdmin only)
    
    Permissions:
        GET: Any authenticated user
        POST: Department Admin only
    
    Request Body (POST):
        - programme, batch, day_of_week, start_time, end_time, subject, faculty, room_no, academic_year, semester (all required)
    
    Response (200/201):
        GET: Array of timetable entries
        POST: Created timetable entry
    
    Error Responses:
        400: Missing required fields
        403: Insufficient permissions for POST
    """
    if not _can_manage_department_timetable(request.user):
        return Response(
            {'detail': 'You are not allowed to manage the department timetable.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == 'GET':
        timetable_items = _get_department_timetable_queryset(request.user)
        return Response([
            _serialize_department_timetable(item)
            for item in timetable_items
        ], status=status.HTTP_200_OK)

    department_name = _get_user_department_name(request.user)
    if not department_name:
        return Response({'detail': 'User department not found.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_info = ExtraInfo.objects.get(user=request.user)
    except ExtraInfo.DoesNotExist:
        return Response({'detail': 'User profile not found.'}, status=status.HTTP_400_BAD_REQUEST)

    department = str(department_name).strip().upper()
    programme = (request.data.get('programme') or '').strip()
    batch = (request.data.get('batch') or '').strip()
    day_of_week = (request.data.get('day_of_week') or '').strip()
    start_time = (request.data.get('start_time') or '').strip()
    end_time = (request.data.get('end_time') or '').strip()
    subject = (request.data.get('subject') or '').strip()
    faculty = (request.data.get('faculty') or '').strip()
    room_no = (request.data.get('room_no') or '').strip()
    academic_year = (request.data.get('academic_year') or '').strip()
    semester = (request.data.get('semester') or '').strip()

    # Validate each field individually for better error feedback
    errors = {}
    if not programme:
        errors['programme'] = 'This field is required.'
    if not batch:
        errors['batch'] = 'This field is required.'
    if not day_of_week:
        errors['day_of_week'] = 'This field is required.'
    if not start_time:
        errors['start_time'] = 'This field is required.'
    if not end_time:
        errors['end_time'] = 'This field is required.'
    if not subject:
        errors['subject'] = 'This field is required.'
    if not faculty:
        errors['faculty'] = 'This field is required.'
    if not room_no:
        errors['room_no'] = 'This field is required.'
    if not academic_year:
        errors['academic_year'] = 'This field is required.'
    if not semester:
        errors['semester'] = 'This field is required.'
    
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        timetable_item = DepartmentTimetable.objects.create(
            department=department,
            programme=programme,
            batch=batch,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            subject=subject,
            faculty=faculty,
            room_no=room_no,
            academic_year=academic_year,
            semester=semester,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
    except Exception:
        logger.exception(
            'Unable to create timetable entry for user=%s department=%s',
            request.user.username,
            department,
        )
        return Response(
            {'detail': 'Unable to create timetable entry. Please try again later.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(_serialize_department_timetable(timetable_item), status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def timetable_detail_api(request, timetable_id):
    if not _can_manage_department_timetable(request.user):
        return Response(
            {'detail': 'You are not allowed to manage the department timetable.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    department_name = _get_user_department_name(request.user)
    if not department_name:
        return Response({'detail': 'User department not found.'}, status=status.HTTP_400_BAD_REQUEST)

    timetable_item = get_object_or_404(DepartmentTimetable, id=timetable_id)
    if not _is_same_department_access(request.user, timetable_item.department):
        return Response(
            {'detail': 'You can only manage timetable entries for your own department.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == 'GET':
        return Response(_serialize_department_timetable(timetable_item), status=status.HTTP_200_OK)

    if request.method == 'DELETE':
        timetable_item.delete()
        return Response({'detail': 'Timetable entry deleted successfully.'}, status=status.HTTP_200_OK)

    fields_to_update = []
    update_map = {
        'department': 'department',
        'programme': 'programme',
        'batch': 'batch',
        'day_of_week': 'day_of_week',
        'start_time': 'start_time',
        'end_time': 'end_time',
        'subject': 'subject',
        'faculty': 'faculty',
        'room_no': 'room_no',
        'academic_year': 'academic_year',
        'semester': 'semester',
    }

    for key, attr in update_map.items():
        value = request.data.get(key)
        if value is not None and str(value).strip() != '':
            if key == 'department':
                if str(value).strip().upper() != department_name.upper():
                    return Response(
                        {'detail': 'You can only manage timetable entries for your own department.'},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                value = str(value).strip().upper()
            else:
                value = str(value).strip()
            setattr(timetable_item, attr, value)
            fields_to_update.append(attr)

    if fields_to_update:
        timetable_item.updated_at = timezone.now()
        fields_to_update.append('updated_at')
        timetable_item.save(update_fields=fields_to_update)

    return Response(_serialize_department_timetable(timetable_item), status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def feedback_api(request: HttpRequest) -> Response:
    """
    Manage department feedback submissions and reviews.
    
    HTTP Methods:
        GET: Retrieve feedback (filtered by role)
        POST: Submit new feedback (students only)
    
    Permissions:
        GET: HOD/DeptAdmin see department feedback; Students see their own
        POST: Students only
    
    Request Body (POST):
        - subject (str): Feedback title (required)
        - description (str): Feedback content (required)
        - category (str): Feedback category (optional if user has department)
        - is_confidential (bool): Mark as confidential (default: false)
        - upload_feedback (file): Optional attachment
    
    Response (200/201):
        GET: Array of feedback items
        POST: Created feedback object
    
    Error Responses:
        400: Missing required fields
        403: Only students can submit feedback
    """
    if request.method == 'GET':
        category = (request.query_params.get('category') or '').strip()
        feedback_items = _get_department_feedback_queryset(request.user, category or None)
        
        # Add pagination support
        try:
            limit = int(request.query_params.get('limit', 50))
            offset = int(request.query_params.get('offset', 0))
            limit = max(1, min(limit, 500))
            offset = max(0, offset)
        except (TypeError, ValueError):
            limit, offset = 50, 0
        
        total_count = feedback_items.count()
        paginated_items = feedback_items[offset:offset+limit]
        
        return Response({
            'count': total_count,
            'limit': limit,
            'offset': offset,
            'results': [_serialize_department_feedback(item) for item in paginated_items]
        }, status=status.HTTP_200_OK)

    try:
        user_info = ExtraInfo.objects.select_related('user', 'department').get(user=request.user)
    except ExtraInfo.DoesNotExist:
        return Response({'detail': 'User profile not found.'}, status=status.HTTP_400_BAD_REQUEST)

    if user_info.user_type != 'student':
        return Response(
            {'detail': 'Only students can submit feedback.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    subject = (request.data.get('subject') or '').strip()
    description = (request.data.get('description') or '').strip()
    category = (request.data.get('category') or '').strip()
    is_confidential = _coerce_boolean(request.data.get('is_confidential', False))
    upload_feedback = request.FILES.get('upload_feedback')

    # Validate each field individually for better error feedback
    errors = {}
    if not subject:
        errors['subject'] = 'This field is required.'
    if not description:
        errors['description'] = 'This field is required.'
    
    if errors:
        return Response({'error_code': 'VALIDATION_ERROR', 'fields': errors}, status=status.HTTP_400_BAD_REQUEST)

    if not category and getattr(user_info, 'department', None):
        category = user_info.department.name

    if not category:
        return Response(
            {'category': 'This field is required when the user has no department.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    feedback_item = DepartmentFeedback.objects.create(
        submitter=user_info,
        subject=subject,
        description=description,
        upload_feedback=upload_feedback,
        category=category,
        is_confidential=is_confidential,
        status=FeedbackStatus.NEW,
        submitted_at=timezone.now(),
    )
    logger.info(f'Feedback submitted: id={feedback_item.id}, category={category}, by={request.user.username}')
    logger.info(f'Feedback submitted: id={feedback_item.id}, category={category}, by={request.user.username}')

    return Response(_serialize_department_feedback(feedback_item), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@transaction.atomic
def resolve_feedback_api(request, feedback_id):
    if not _can_manage_department_feedback(request.user):
        return Response(
            {'detail': 'You are not allowed to resolve feedback.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        user_info = ExtraInfo.objects.get(user=request.user)
    except ExtraInfo.DoesNotExist:
        return Response({'detail': 'User profile not found.'}, status=status.HTTP_400_BAD_REQUEST)

    feedback_item = get_object_or_404(
        DepartmentFeedback.objects.select_related('submitter__user', 'resolved_by__user'),
        id=feedback_id,
    )

    if not _is_same_department_access(request.user, feedback_item.category):
        return Response(
            {'detail': 'You can only resolve feedback from your own department.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    status_value = (request.data.get('status') or FeedbackStatus.RESOLVED).strip().upper()
    remarks = (request.data.get('resolution_remarks') or '').strip()

    if status_value != FeedbackStatus.RESOLVED:
        return Response(
            {'detail': 'Only RESOLVED status can be set from this endpoint.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    feedback_item.status = FeedbackStatus.RESOLVED
    feedback_item.resolution_remarks = remarks
    feedback_item.resolved_by = user_info
    feedback_item.resolved_at = timezone.now()
    feedback_item.save(update_fields=['status', 'resolution_remarks', 'resolved_by', 'resolved_at'])

    try:
        notify.send(
            sender=request.user,
            recipient=feedback_item.submitter.user,
            url='dep:dep',
            module='Department',
            verb='Your feedback "{}" has been resolved.'.format(feedback_item.subject),
            description=str(feedback_item.id),
        )
    except Exception:
        logger.exception(
            'Failed to dispatch feedback resolution notification for feedback_id=%s',
            feedback_item.id,
        )

    return Response(_serialize_department_feedback(feedback_item), status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def facilities_api(request: HttpRequest) -> Response:
    """
    Manage department facilities (equipment, resources).
    
    HTTP Methods:
        GET: Retrieve facilities (filtered by branch)
        POST: Create new facility (DeptAdmin only)
    
    Permissions:
        GET: Any authenticated user
        POST: Department Admin only
    
    Query Parameters (GET):
        - branch (str): Filter by branch code (optional)
    
    Request Body (POST):
        - name (str): Facility name (required)
        - location (str): Location (optional)
        - lab (str): Lab name (optional)
        - amount (int): Quantity (default: 1)
        - stock_request_id (str): Link to stock request (optional)
        - picture (file): Facility photo (optional)
    
    Response (200/201):
        GET: Array of facility objects
        POST: Created facility object
    
    Error Responses:
        400: Missing required fields or invalid amount
        403: Only DeptAdmin can create facilities
    """
    if request.method == 'GET':
        facilities = Facility.objects.all()
        branch = (request.query_params.get('branch') or '').strip()
        if branch:
            facilities = facilities.filter(Q(branch__iexact=branch) | Q(branch=''))
        return Response([
            _serialize_facility(item)
            for item in facilities
        ], status=status.HTTP_200_OK)

    if not _can_manage_department_facilities(request.user):
        return Response(
            {'detail': 'Only Department Admin can create facilities.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    name = (request.data.get('name') or '').strip()
    manager_department = _get_user_department_name(request.user)
    if not manager_department:
        return Response({'detail': 'User department not found.'}, status=status.HTTP_400_BAD_REQUEST)

    branch = manager_department
    location = (request.data.get('location') or '').strip()
    lab = (request.data.get('lab') or '').strip()
    amount = request.data.get('amount') or 1
    stock_request_id = request.data.get('stock_request_id')
    picture = request.FILES.get('picture')

    # Validate each field individually for better error feedback
    errors = {}
    if not name:
        errors['name'] = 'This field is required.'

    try:
        amount = int(amount)
    except (TypeError, ValueError):
        errors['amount'] = 'This field must be a number.'

    if not errors and amount < 1:
        errors['amount'] = 'Amount must be greater than zero.'
    
    if errors:
        return Response({'error_code': 'VALIDATION_ERROR', 'fields': errors}, status=status.HTTP_400_BAD_REQUEST)

    facility = Facility.objects.create(
        name=name,
        branch=branch,
        location=location,
        lab=lab,
        amount=amount,
        picture=picture,
        stock_request_id=stock_request_id,
    )

    return Response(_serialize_facility(facility), status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@transaction.atomic
def facilities_delete_api(request):
    if not _can_manage_department_facilities(request.user):
        return Response(
            {'detail': 'Only Department Admin can delete facilities.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    facility_ids = request.data.get('facility_ids') or []
    if not isinstance(facility_ids, list):
        return Response({'detail': 'facility_ids must be a list.'}, status=status.HTTP_400_BAD_REQUEST)

    manager_department = _get_user_department_name(request.user)
    if not manager_department:
        return Response({'detail': 'User department not found.'}, status=status.HTTP_400_BAD_REQUEST)

    facilities = Facility.objects.filter(id__in=facility_ids)
    if facilities.count() != len(facility_ids):
        return Response({'detail': 'One or more facilities were not found.'}, status=status.HTTP_404_NOT_FOUND)

    for facility in facilities:
        if not _is_same_department_access(request.user, facility.branch):
            return Response(
                {'detail': 'You can only delete facilities from your own department.'},
                status=status.HTTP_403_FORBIDDEN,
            )

    Facility.objects.filter(id__in=facility_ids).delete()
    return Response({'detail': 'Facilities deleted successfully.'}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def stock_requests_api(request: HttpRequest) -> Response:
    """
    Manage department stock requests.
    
    HTTP Methods:
        GET: Retrieve stock requests (filtered by user role)
        POST: Create new stock request (Assistant Professors only)
    
    Permissions:
        GET: All authenticated users (filtered by role)
        POST: Assistant Professors only
    
    Request Body (POST):
        - brief (str): Brief summary (required)
        - request_details (str): Detailed description (required)
        - stock_item_name (str): Item name (required)
        - quantity (int): Quantity needed (required, >= 1)
        - lab (str): Lab name (required)
        - request_receiver (str): Receiving department (optional)
        - remarks (str): Additional remarks (optional)
        - upload_request (file): Supporting document (optional)
    
    Response (200/201):
        GET: Array of stock request objects
        POST: Created stock request object
    
    Error Responses:
        400: Missing required fields or invalid quantity
        403: Only Assistant Professors can create requests
    """
    if request.method == 'GET':
        stock_requests = _get_department_stock_queryset(request.user)
        
        # Add pagination support
        try:
            limit = int(request.query_params.get('limit', 50))
            offset = int(request.query_params.get('offset', 0))
            limit = max(1, min(limit, 500))
            offset = max(0, offset)
        except (TypeError, ValueError):
            limit, offset = 50, 0
        
        total_count = stock_requests.count()
        paginated_requests = stock_requests[offset:offset+limit]
        
        return Response({
            'count': total_count,
            'limit': limit,
            'offset': offset,
            'results': [_serialize_department_stock(item) for item in paginated_requests]
        }, status=status.HTTP_200_OK)

    # POST: Only Assistant Professors can create stock requests
    if not _can_request_stock(request.user):
        return Response(
            {'detail': 'Only Assistant Professors can request stock.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        user_info = ExtraInfo.objects.select_related('user', 'department').get(user=request.user)
    except ExtraInfo.DoesNotExist:
        return Response({'detail': 'User profile not found.'}, status=status.HTTP_400_BAD_REQUEST)

    brief = (request.data.get('brief') or '').strip()
    request_details = (request.data.get('request_details') or '').strip()
    request_receiver = (request.data.get('request_receiver') or '').strip()
    lab = (request.data.get('lab') or '').strip()
    quantity = request.data.get('quantity') or 1
    stock_item_name = (request.data.get('stock_item_name') or '').strip()
    remarks = (request.data.get('remarks') or '').strip()
    upload_request = request.FILES.get('upload_request')

    if getattr(user_info, 'department', None):
        request_receiver = user_info.department.name

    # Validate each field individually for better error feedback
    errors = {}
    if not brief:
        errors['brief'] = 'This field is required.'
    if not request_details:
        errors['request_details'] = 'This field is required.'
    if not request_receiver:
        errors['request_receiver'] = 'This field is required.'
    if not stock_item_name:
        errors['stock_item_name'] = 'This field is required.'
    if not lab:
        errors['lab'] = 'This field is required.'
    
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        errors['quantity'] = 'This field must be a number.'

    if not errors and quantity < 1:
        errors['quantity'] = 'Quantity must be greater than zero.'
    
    if errors:
        return Response({'error_code': 'VALIDATION_ERROR', 'fields': errors}, status=status.HTTP_400_BAD_REQUEST)

    stock_request = DepartmentStock.objects.create(
        request_maker=user_info,
        request_date=timezone.now(),
        brief=brief,
        request_details=request_details,
        upload_request=upload_request,
        status=StockStatus.PENDING,
        remarks=remarks,
        request_receiver=request_receiver,
        lab=lab,
        quantity=quantity,
        stock_item_name=stock_item_name,
    )
    logger.info(f'Stock request created: id={stock_request.id}, item={stock_item_name}, qty={quantity}')
    logger.info(f'Stock request created: id={stock_request.id}, item={stock_item_name}, qty={quantity}, by={request.user.username}')

    return Response(_serialize_department_stock(stock_request), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@transaction.atomic
def stock_decision_api(request: HttpRequest, stock_id: int) -> Response:
    """
    Approve or reject stock requests.
    
    HTTP Methods:
        POST: Approve or reject a pending stock request (HOD only)
    
    Permissions:
        HOD only
    
    URL Parameters:
        stock_id: ID of the stock request to review
    
    Request Body:
        - decision (str): 'APPROVED' or 'REJECTED' (required)
        - remarks (str): Decision remarks/feedback (optional)
    
    Response (200):
        {'id': <stock_id>, 'status': 'APPROVED' or 'REJECTED', 'message': '...'}
    
    Error Responses:
        404: Stock request not found
        403: Only HOD can make decisions
        400: Invalid decision value or not in PENDING status
    """
    if not _can_approve_reject_stock(request.user):
        logger.warning(f'Unauthorized stock approval attempt by user_id={request.user.id}')
        return Response(
            {'detail': 'Only HOD can approve or reject stock requests.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    stock_request = get_object_or_404(
        DepartmentStock.objects.select_related('request_maker__user', 'issued_by__user'),
        id=stock_id,
    )

    request_department = _stock_request_department_name(stock_request)
    if not _is_same_department_access(request.user, request_department):
        return Response(
            {'detail': 'You can only review stock requests from your own department.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    decision = (request.data.get('decision') or '').strip().upper()
    remarks = (request.data.get('remarks') or '').strip()

    if decision not in {StockStatus.APPROVED, StockStatus.REJECTED}:
        return Response(
            {'detail': f'decision must be {StockStatus.APPROVED} or {StockStatus.REJECTED}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    stock_request.status = decision
    if remarks:
        stock_request.remarks = remarks
    stock_request.save(update_fields=['status', 'remarks'])

    try:
        notify.send(
            sender=request.user,
            recipient=stock_request.request_maker.user,
            url='dep:dep',
            module='Department',
            verb='Your stock request #{} was {}.'.format(stock_request.id, stock_request.status),
            description=str(stock_request.id),
        )
    except Exception:
        logger.exception(
            'Failed to dispatch stock decision notification for stock_id=%s',
            stock_request.id,
        )

    if stock_request.status in {StockStatus.ALLOCATED, StockStatus.ISSUED}:
        _sync_facility_from_stock_request(stock_request)

    return Response(_serialize_department_stock(stock_request), status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
@transaction.atomic
def stock_issue_api(request: HttpRequest, stock_id: int) -> Response:
    """
    Allocate or issue approved stock requests.
    
    HTTP Methods:
        POST: Allocate stock (PENDING->ALLOCATED) or issue it (ALLOCATED->ISSUED)
    
    Permissions:
        Department Admin only
    
    URL Parameters:
        stock_id: ID of the approved stock request
    
    Request Body:
        - action (str): 'ALLOCATE' or 'ISSUE' (required)
        - allocated_qty (int): Quantity to allocate (required for ALLOCATE)
        - issued_qty (int): Quantity to issue (required for ISSUE)
        - remarks (str): Action remarks (optional)
    
    Response (200):
        {'id': <stock_id>, 'status': 'ALLOCATED' or 'ISSUED', 'message': '...'}
    
    Error Responses:
        404: Stock request not found
        403: Only DeptAdmin can allocate/issue
        400: Invalid action value or wrong status
    """
    if not _can_allocate_issue_stock(request.user):
        logger.warning(f'Unauthorized stock allocation attempt by user_id={request.user.id}')
        return Response(
            {'detail': 'Only Department Admin can allocate or issue stock.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        user_info = ExtraInfo.objects.get(user=request.user)
    except ExtraInfo.DoesNotExist:
        return Response({'detail': 'User profile not found.'}, status=status.HTTP_400_BAD_REQUEST)

    stock_request = get_object_or_404(
        DepartmentStock.objects.select_related('request_maker__user', 'issued_by__user'),
        id=stock_id,
    )

    request_department = _stock_request_department_name(stock_request)
    if not _is_same_department_access(request.user, request_department):
        return Response(
            {'detail': 'You can only issue stock requests from your own department.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    action = (request.data.get('action') or 'ISSUE').strip().upper()
    issued_quantity = request.data.get('issued_quantity') or stock_request.quantity
    remarks = (request.data.get('remarks') or '').strip()

    if stock_request.status not in {StockStatus.APPROVED, StockStatus.ALLOCATED}:
        return Response(
            {'detail': 'Only approved or allocated requests can be issued.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        issued_quantity = int(issued_quantity)
    except (TypeError, ValueError):
        return Response({'detail': 'issued_quantity must be a number.'}, status=status.HTTP_400_BAD_REQUEST)

    if issued_quantity < 1:
        return Response({'detail': 'issued_quantity must be greater than zero.'}, status=status.HTTP_400_BAD_REQUEST)

    if issued_quantity > stock_request.quantity:
        return Response(
            {'detail': 'issued_quantity cannot exceed requested quantity.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if action not in {'ALLOCATE', 'ISSUE'}:
        return Response(
            {'detail': 'action must be ALLOCATE or ISSUE.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    stock_request.issued_by = user_info
    stock_request.issued_quantity = issued_quantity
    stock_request.issued_date = timezone.now()
    stock_request.status = StockStatus.ALLOCATED if action == 'ALLOCATE' else StockStatus.ISSUED
    if remarks:
        stock_request.remarks = remarks
    stock_request.save(update_fields=['issued_by', 'issued_quantity', 'issued_date', 'status', 'remarks'])
    logger.info(f'Stock {action.lower()}: id={stock_id}, qty={issued_quantity}, by={request.user.username}')

    _sync_facility_from_stock_request(stock_request)

    try:
        notify.send(
            sender=request.user,
            recipient=stock_request.request_maker.user,
            url='dep:dep',
            module='Department',
            verb='Your stock request #{} was {}.'.format(stock_request.id, stock_request.status),
            description=str(stock_request.id),
        )
    except Exception:
        logger.exception(
            'Failed to dispatch stock issue notification for stock_id=%s',
            stock_request.id,
        )

    return Response(_serialize_department_stock(stock_request), status=status.HTTP_200_OK)


def browse_announcements():
    """
    This function is used to browse Announcements Department-Wise
    made by different faculties and admin.

    @variables:
        cse_ann - Stores CSE Department Announcements
        ece_ann - Stores ECE Department Announcements
        me_ann - Stores ME Department Announcements
        sm_ann - Stores SM Department Announcements
        all_ann - Stores Announcements intended for all Departments
        context - Dictionary for storing all above data

    """
    cse_ann = Announcements.objects.filter(department="CSE")
    ece_ann = Announcements.objects.filter(department="ECE")
    me_ann = Announcements.objects.filter(department="ME")
    sm_ann = Announcements.objects.filter(department="SM")
    all_ann = Announcements.objects.filter(department="ALL")

    context = {
        "cse" : cse_ann,
        "ece" : ece_ann,
        "me" : me_ann,
        "sm" : sm_ann,
        "all" : all_ann
    }

    return context

def get_make_request(user_id):
    """
    This function is used to get requests for maker

    @variables:
        req - Contains request queryset

    """
    req = SpecialRequest.objects.filter(request_maker=user_id)
    return req

def get_to_request(username):
    """
    This function is used to get requests for the receiver

    @variables:
        req - Contains request queryset

    """
    req = SpecialRequest.objects.filter(request_receiver=username)
    return req

@login_required(login_url='/accounts/login')
def dep_main(request):
    """
    This function is used to differentiate between Different users
    and redirect them to different urls.

    @param:
        request - contains metadata about the requested page

    @variables:
        fac_view - Check if user is Faculty
        student - Check if user is student
        context - Stores data returned by browse_announcement()
        context_f - Stores data returned by faculty()

    """
    user = request.user
    usrnm = get_object_or_404(User, username=request.user.username)
    user_info = ExtraInfo.objects.all().select_related('user','department').filter(user=usrnm).first()
    ann_maker_id = user_info.id
    user_info = ExtraInfo.objects.all().select_related('user','department').get(id=ann_maker_id)

    requests_made = get_make_request(user_info)
    
    fac_view = request.user.holds_designations.filter(designation__name='faculty').exists()
    student = request.user.holds_designations.filter(designation__name='student').exists()
    staff = request.user.holds_designations.filter(designation__name='staff').exists()
    
    context = browse_announcements()
    context_f = faculty()
    user_designation = ""
    
    if fac_view:
        user_designation = "faculty"
    elif student:
        user_designation = "student"
    else:
        user_designation = "staff"

    if request.method == 'POST':
        request_type = request.POST.get('request_type', '')
        request_to = request.POST.get('request_to', '')
        request_details = request.POST.get('request_details', '')
        request_date = date.today()

        obj_sprequest, created_object = SpecialRequest.objects.get_or_create(request_maker=user_info,
                                                    request_date=request_date,
                                                    brief=request_type,
                                                    request_details=request_details,
                                                    status="Pending",
                                                    remarks="--",
                                                    request_receiver=request_to
                                                    )
    
    if user_designation == "student":
        return render(request,"department/index.html", {"announcements":context,
                                                        "fac_list" : context_f,
                                                        "requests_made" : requests_made
                                                    })
    # elif(str(user.extrainfo.user_type)=="faculty"):
    elif user_designation=="faculty":
        return HttpResponseRedirect("facView")
    elif user_designation=="staff":
        return HttpResponseRedirect("staffView")

def faculty_view(request):
    """
    This function is contains data for Requests and Announcement Related methods.
    Data is added to Announcement Table using this function.

    @param:
        request - contains metadata about the requested page

    @variables:
        usrnm, user_info, ann_maker_id - Stores data needed for maker
        batch, programme, message, upload_announcement,
        department, ann_date, user_info - Gets and store data from FORM used for Announcements.

    """
    usrnm = get_object_or_404(User, username=request.user.username)
    user_info = ExtraInfo.objects.all().select_related('user','department').filter(user=usrnm).first()
    num = 1
    ann_maker_id = user_info.id
    requests_received = get_to_request(usrnm)
    if request.method == 'POST':
        batch = request.POST.get('batch', '')
        programme = request.POST.get('programme', '')
        message = request.POST.get('announcement', '')
        upload_announcement = request.FILES.get('upload_announcement')
        department = request.POST.get('department')
        ann_date = date.today()
        user_info = ExtraInfo.objects.all().select_related('user','department').get(id=ann_maker_id)
        getstudents = ExtraInfo.objects.select_related('user')
        recipients = User.objects.filter(extrainfo__in=getstudents)

        obj1, created = Announcements.objects.get_or_create(maker_id=user_info,
                                    batch=batch,
                                    programme=programme,
                                    message=message,
                                    upload_announcement=upload_announcement,
                                    department = department,
                                    ann_date=ann_date)
        # department_notif(usrnm, recipients , message)
        
    context = browse_announcements()
    return render(request, 'department/dep_request.html', {"user_designation":user_info.user_type,
                                                            "announcements":context,
                                                            "request_to":requests_received
                                                        })

def staff_view(request):
    """
    This function is contains data for Requests and Announcement Related methods.
    Data is added to Announcement Table using this function.

    @param:
        request - contains metadata about the requested page

    @variables:
        usrnm, user_info, ann_maker_id - Stores data needed for maker
        batch, programme, message, upload_announcement,
        department, ann_date, user_info - Gets and store data from FORM used for Announcements for Students.

    """
    usrnm = get_object_or_404(User, username=request.user.username)
    user_info = ExtraInfo.objects.all().select_related('user','department').filter(user=usrnm).first()
    num = 1
    ann_maker_id = user_info.id
    requests_received = get_to_request(usrnm)
    if request.method == 'POST':
        batch = request.POST.get('batch', '')
        programme = request.POST.get('programme', '')
        message = request.POST.get('announcement', '')
        upload_announcement = request.FILES.get('upload_announcement')
        department = request.POST.get('department')
        ann_date = date.today()
        user_info = ExtraInfo.objects.all().select_related('user','department').get(id=ann_maker_id)
        getstudents = ExtraInfo.objects.select_related('user')
        recipients = User.objects.filter(extrainfo__in=getstudents)

        obj1, created = Announcements.objects.get_or_create(maker_id=user_info,
                                    batch=batch,
                                    programme=programme,
                                    message=message,
                                    upload_announcement=upload_announcement,
                                    department = department,
                                    ann_date=ann_date)
        # department_notif(usrnm, recipients , message)
        
    context = browse_announcements()
    return render(request, 'department/dep_request.html', {"user_designation":user_info.user_type,
                                                            "announcements":context,
                                                            "request_to":requests_received
                                                        })

@login_required(login_url='/accounts/login')
def all_students(request,bid):
    """
    This function is used to Return data of Faculties Department-Wise.

    @param:
        request - contains metadata about the requested page
        bid - stores key for different batches

    @variables:
        student_list1 - Stores student data department, batch and programme-wise
        student_list - Stores data pagewise

    """
    if int(bid)==1:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2021,
                                                            id__user_type='student',
                                                            id__department__name='CSE').select_related('id') 
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==11:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2020,
                                                            id__user_type='student',
                                                            id__department__name='CSE').select_related('id') 
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==111:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2019,
                                                            id__user_type='student',
                                                            id__department__name='CSE').select_related('id') 
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==1111:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2018,
                                                            id__user_type='student',
                                                            id__department__name='CSE').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==11111:
        student_list1=Student.objects.order_by('id').filter(programme='M.Tech',
                                                            batch=2021,
                                                            id__user_type='student',
                                                            id__department__name='CSE').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==111111:
        student_list1=Student.objects.order_by('id').filter(programme='M.Tech',
                                                            batch=2020,
                                                            id__user_type='student',
                                                            id__department__name='CSE').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==1111111:
        student_list1=Student.objects.order_by('id').filter(programme='PhD',
                                                            id__user_type='student',
                                                            id__department__name='CSE').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==2:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2021,
                                                            id__user_type='student',
                                                            id__department__name='ECE').select_related('id') 
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==21:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2020,
                                                            id__user_type='student',
                                                            id__department__name='ECE').select_related('id') 
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==211:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2019,
                                                            id__user_type='student',
                                                            id__department__name='ECE').select_related('id') 
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==2111:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2018,
                                                            id__user_type='student',
                                                            id__department__name='ECE').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==21111:
        student_list1=Student.objects.order_by('id').filter(programme='M.Tech',
                                                            batch=2021,
                                                            id__user_type='student',
                                                            id__department__name='ECE').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==211111:
        student_list1=Student.objects.order_by('id').filter(programme='M.Tech',
                                                            batch=2020,
                                                            id__user_type='student',
                                                            id__department__name='ECE').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==2111111:
        student_list1=Student.objects.order_by('id').filter(programme='PhD',
                                                            id__user_type='student',
                                                            id__department__name='ECE').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==3:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2021,
                                                            id__user_type='student',
                                                            id__department__name='ME').select_related('id') 
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==31:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2020,
                                                            id__user_type='student',
                                                            id__department__name='ME').select_related('id') 
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==311:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2019,
                                                            id__user_type='student',
                                                            id__department__name='ME').select_related('id') 
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==3111:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2018,
                                                            id__user_type='student',
                                                            id__department__name='ME').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==31111:
        student_list1=Student.objects.order_by('id').filter(programme='M.Tech',
                                                            batch=2021,
                                                            id__user_type='student',
                                                            id__department__name='ME').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==311111:
        student_list1=Student.objects.order_by('id').filter(programme='M.Tech',
                                                            batch=2020,
                                                            id__user_type='student',
                                                            id__department__name='ME').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==3111111:
        student_list1=Student.objects.order_by('id').filter(programme='PhD',
                                                            id__user_type='student',
                                                            id__department__name='ME').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==4:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2021,
                                                            id__user_type='student',
                                                            id__department__name='SM').select_related('id') 
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==41:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2020,
                                                            id__user_type='student',
                                                            id__department__name='SM').select_related('id') 
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==411:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2019,
                                                            id__user_type='student',
                                                            id__department__name='SM').select_related('id') 
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==4111:
        student_list1=Student.objects.order_by('id').filter(programme='B.Tech',
                                                            batch=2018,
                                                            id__user_type='student',
                                                            id__department__name='SM').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==41111:
        student_list1=Student.objects.order_by('id').filter(programme='M.Tech',
                                                            batch=2021,
                                                            id__user_type='student',
                                                            id__department__name='SM').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==411111:
        student_list1=Student.objects.order_by('id').filter(programme='M.Tech',
                                                            batch=2020,
                                                            id__user_type='student',
                                                            id__department__name='SM').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)
    elif int(bid)==4111111:
        student_list1=Student.objects.order_by('id').filter(programme='PhD',
                                                            id__user_type='student',
                                                            id__department__name='SM').select_related('id')
        paginator=Paginator(student_list1,25,orphans=5)
        page_number=request.GET.get('page')
        student_list=paginator.get_page(page_number)
        id_dict={'student_list':student_list,}
        return render(request, 'department/AllStudents.html',context=id_dict)

    

def faculty():
    """
    This function is used to Return data of Faculties Department-Wise.

    @variables:
        cse_f - Stores data of faculties from CSE Department
        ece_f - Stores data of faculties from ECE Department
        me_f - Stores data of faculties from ME Department
        sm_f - Stores data of faculties from ME Department
        context_f - Stores all above variables in Dictionary

    """
    cse_f=ExtraInfo.objects.filter(department__name='CSE',user_type='faculty')
    ece_f=ExtraInfo.objects.filter(department__name='ECE',user_type='faculty')
    me_f=ExtraInfo.objects.filter(department__name='ME',user_type='faculty')
    sm_f=ExtraInfo.objects.filter(department__name='SM',user_type='faculty')
    staff=ExtraInfo.objects.filter(user_type='staff')

    context_f = {
        "cse_f" : cse_f,
        "ece_f" : ece_f,
        "me_f" : me_f,
        "sm_f" : sm_f,
        "staffNcse" : list(staff)+list(cse_f),
        "staffNece" : list(staff)+list(ece_f),
        "staffNme" : list(staff)+list(me_f),
        "staffNsm" : list(staff)+list(sm_f)


    }
    return context_f

def approved(request):
    """
    This function is used to approve requests.

    @variables:
        request_id - Contains ID of the request to be updated
        remark - Contains Remarks added by the user while Approving the status

    """
    if request.method == 'POST':
        request_id = request.POST.get('id')
        remark = request.POST.get('remark')
        SpecialRequest.objects.filter(id=request_id).update(status="Approved", remarks=remark)
    request.method = ''
    return redirect('/dep/facView/')

def deny(request):
    """
    This function is used to deny requests.

    @variables:
        request_id - Contains ID of the request to be updated
        remark - Contains Remarks added by the user while Denying the status

    """
    if request.method == 'POST':
        request_id = request.POST.get('id')
        remark = request.POST.get('remark')
        SpecialRequest.objects.filter(id=request_id).update(status="Denied", remarks=remark)
    request.method = ''
    return redirect('/dep/facView/')