from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from applications.globals.models import ExtraInfo, DepartmentInfo, Designation, HoldsDesignation
from applications.academic_information.models import Student

# your models
from applications.department.models import (
    Announcements,
    DepartmentFeedback,
    DepartmentStock,
    DepartmentTimetable,
    SpecialRequest
)


class BaseModuleTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):

        # ---------------- USERS ----------------
        cls.student_user = User.objects.create_user(
            username='student1',
            password='test123'
        )

        cls.staff_user = User.objects.create_user(
            username='staff1',
            password='test123'
        )

        cls.faculty_user = User.objects.create_user(
            username='faculty1',
            password='test123'
        )

        # ---------------- DEPARTMENT ----------------
        cls.department = DepartmentInfo.objects.create(
            name='CSE'
        )

        # ---------------- EXTRAINFO ----------------
        cls.student_extra = ExtraInfo.objects.create(
            user=cls.student_user,
            id='STU001',
            user_type='student',
            department=cls.department
        )

        cls.staff_extra = ExtraInfo.objects.create(
            user=cls.staff_user,
            id='STAFF001',
            user_type='staff',
            department=cls.department
        )

        cls.faculty_extra = ExtraInfo.objects.create(
            user=cls.faculty_user,
            id='FAC001',
            user_type='faculty',
            department=cls.department
        )

        # ---------------- DESIGNATIONS / ROLES ----------------
        cls.designation_student, _ = Designation.objects.get_or_create(
            name='student',
            defaults={'full_name': 'Student', 'type': 'academic'}
        )
        cls.designation_asst_prof, _ = Designation.objects.get_or_create(
            name='Assistant Professor',
            defaults={'full_name': 'Assistant Professor', 'type': 'academic'}
        )
        cls.designation_hod, _ = Designation.objects.get_or_create(
            name='HOD',
            defaults={'full_name': 'Head of Department', 'type': 'administrative'}
        )
        cls.designation_dept_admin, _ = Designation.objects.get_or_create(
            name='dept_admin',
            defaults={'full_name': 'Department Admin', 'type': 'administrative'}
        )

        HoldsDesignation.objects.get_or_create(
            user=cls.student_user,
            working=cls.student_user,
            designation=cls.designation_student,
        )
        # Give staff all department-management roles for positive-path tests.
        HoldsDesignation.objects.get_or_create(
            user=cls.staff_user,
            working=cls.staff_user,
            designation=cls.designation_asst_prof,
        )
        HoldsDesignation.objects.get_or_create(
            user=cls.staff_user,
            working=cls.staff_user,
            designation=cls.designation_hod,
        )
        HoldsDesignation.objects.get_or_create(
            user=cls.staff_user,
            working=cls.staff_user,
            designation=cls.designation_dept_admin,
        )

        # ---------------- STUDENT MODEL ----------------
        cls.student = Student.objects.create(
            id=cls.student_extra,
            programme='B.Tech',
            batch=2021
        )

        # ---------------- SAMPLE DATA (IMPORTANT FOR GET APIs) ----------------

        # Announcement
        cls.announcement = Announcements.objects.create(
            maker_id=cls.faculty_extra,
            message="Test announcement",
            batch="2021",
            programme="B.Tech",
            department="CSE",
            ann_date=timezone.now(),
        )

        # Feedback
        cls.feedback = DepartmentFeedback.objects.create(
            submitter=cls.student_extra,
            subject="Test Feedback",
            description="Test Description",
            category="CSE"
        )

        # Stock Request
        cls.stock = DepartmentStock.objects.create(
            request_maker=cls.student_extra,
            brief="Need item",
            request_details="Details",
            request_receiver="CSE",
            quantity=1,
            stock_item_name="Marker"
        )

        # Timetable
        cls.timetable = DepartmentTimetable.objects.create(
            department="CSE",
            programme="B.Tech",
            batch="2021",
            day_of_week="Monday",
            start_time="09:00",
            end_time="10:00",
            subject="Math",
            faculty="Prof X",
            room_no="101",
            academic_year="2025-26",
            semester="1"
        )

        # Special Request
        cls.special_request = SpecialRequest.objects.create(
            request_maker=cls.student_extra,
            request_details="Test request"
        )   