from django.contrib import admin

# Register your models here.
from .models import(Announcements, SpecialRequest, DepartmentStock, DepartmentFeedback, DepartmentTimetable)

admin.site.register(Announcements)
admin.site.register(SpecialRequest)
admin.site.register(DepartmentStock)
admin.site.register(DepartmentFeedback)
admin.site.register(DepartmentTimetable)