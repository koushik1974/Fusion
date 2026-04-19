from datetime import date

from django.db import models
from django.utils import timezone

# Create your models here.
from applications.globals.models import ExtraInfo
  
class SpecialRequest(models.Model):
    request_maker = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE)
    request_date = models.DateTimeField(default=date.today)
    brief = models.CharField(max_length=20, default='--')
    request_details = models.CharField(max_length=200)
    upload_request = models.FileField(blank=True)
    status = models.CharField(max_length=50,default='Pending')
    remarks = models.CharField(max_length=300, default="--")
    request_receiver = models.CharField(max_length=30, default="--")

    def __str__(self):
        return str(self.request_maker.user.username)


class Announcements(models.Model):
    maker_id = models.ForeignKey(ExtraInfo, on_delete=models.CASCADE)
    ann_date = models.DateTimeField(default="04-04-2021")
    message = models.CharField(max_length=200)
    batch = models.CharField(max_length=40,default="Year-1")
    department = models.CharField(max_length=40,default="ALL")
    programme = models.CharField(max_length=10)
    upload_announcement = models.FileField(upload_to='department/upload_announcement', null=True, default=" ")
    def __str__(self):
        return str(self.maker_id.user.username)


class DepartmentStock(models.Model):
    request_maker = models.ForeignKey(
        ExtraInfo,
        on_delete=models.CASCADE,
        db_column='request_maker_id',
        related_name='department_stock_requests',
    )
    request_date = models.DateTimeField(default=timezone.now)
    brief = models.CharField(max_length=50)
    request_details = models.CharField(max_length=300)
    upload_request = models.FileField(blank=True, null=True, upload_to='department/upload_request')
    status = models.CharField(max_length=20, default='PENDING')
    remarks = models.CharField(max_length=300, default='')
    request_receiver = models.CharField(max_length=50)
    lab = models.CharField(max_length=100, default='')
    quantity = models.IntegerField(default=1)
    stock_item_name = models.CharField(max_length=100)
    issued_by = models.ForeignKey(
        ExtraInfo,
        on_delete=models.SET_NULL,
        db_column='issued_by_id',
        related_name='department_stock_issued',
        null=True,
        blank=True,
    )
    issued_quantity = models.IntegerField(null=True, blank=True)
    issued_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'department_stock'
        managed = False
        ordering = ['-request_date', '-id']

    def __str__(self):
        return '{} - {}'.format(self.stock_item_name, self.request_maker.user.username)


class Facility(models.Model):
    name = models.CharField(max_length=100)
    branch = models.CharField(max_length=40, blank=True, default='')
    location = models.CharField(max_length=100, blank=True, default='')
    lab = models.CharField(max_length=100, blank=True, default='')
    amount = models.IntegerField(default=1)
    picture = models.ImageField(upload_to='department/facilities', null=True, blank=True)
    stock_request_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'department_facility'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.name


class DepartmentFeedback(models.Model):
    submitter = models.ForeignKey(
        ExtraInfo,
        on_delete=models.CASCADE,
        db_column='submitter_id',
        related_name='department_feedback_submitted',
    )
    subject = models.CharField(max_length=200)
    description = models.TextField()
    upload_feedback = models.FileField(blank=True, null=True, upload_to='department/upload_feedback')
    category = models.CharField(max_length=100, null=True, blank=True)
    is_confidential = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default='NEW')
    resolution_remarks = models.TextField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        ExtraInfo,
        on_delete=models.SET_NULL,
        db_column='resolved_by_id',
        related_name='department_feedback_resolved',
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'department_feedback'
        managed = False
        ordering = ['-submitted_at', '-id']

    def __str__(self):
        return '{} - {}'.format(self.subject, self.submitter.user.username)


class DepartmentTimetable(models.Model):
    department = models.CharField(max_length=10)
    programme = models.CharField(max_length=10)
    batch = models.CharField(max_length=40)
    day_of_week = models.CharField(max_length=10)
    start_time = models.TimeField()
    end_time = models.TimeField()
    subject = models.CharField(max_length=100)
    faculty = models.CharField(max_length=100)
    room_no = models.CharField(max_length=20)
    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=10)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'department_timetable'
        managed = False
        ordering = ['department', 'programme', 'batch', 'day_of_week', 'start_time', 'room_no']

    def __str__(self):
        return '{} - {} - {}'.format(self.department, self.day_of_week, self.subject)
