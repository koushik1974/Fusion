from django.conf.urls import url

from . import views

app_name = 'dep'

urlpatterns = [

    url(r'^$', views.dep_main, name='dep'),
    url(r'^facView/$', views.faculty_view, name='faculty_view'),
    url(r'^staffView/$', views.staff_view, name='staff_view'),
    url(r'^All_Students/(?P<bid>[0-9]+)/$', views.all_students,name='all_students'),
    url(r'^approved/$', views.approved, name='approved'),
    url(r'^deny/$', views.deny, name='deny'),
    url(r'^api/announcements/$', views.announcements_api, name='announcements_api'),
    url(r'^api/ann-data/(?P<branch>[A-Za-z_]+)/$', views.ann_data_api, name='ann_data_api'),
    url(r'^api/labs/$', views.labs_api, name='labs_api'),
    url(r'^api/department-resources/$', views.department_resources_api, name='department_resources_api'),
    url(r'^api/facilities/$', views.facilities_api, name='facilities_api'),
    url(r'^api/facilities/delete/$', views.facilities_delete_api, name='facilities_delete_api'),
    url(r'^api/announcements/(?P<announcement_id>[0-9]+)/$', views.delete_announcement_api, name='delete_announcement_api'),
    url(r'^api/feedback/$', views.feedback_api, name='feedback_api'),
    url(r'^api/feedback/(?P<feedback_id>[0-9]+)/resolve/$', views.resolve_feedback_api, name='resolve_feedback_api'),
    url(r'^api/timetable/$', views.timetable_api, name='timetable_api'),
    url(r'^api/timetable/(?P<timetable_id>[0-9]+)/$', views.timetable_detail_api, name='timetable_detail_api'),
    url(r'^api/stock/requests/$', views.stock_requests_api, name='stock_requests_api'),
    url(r'^api/stock/requests/(?P<stock_id>[0-9]+)/decision/$', views.stock_decision_api, name='stock_decision_api'),
    url(r'^api/stock/requests/(?P<stock_id>[0-9]+)/issue/$', views.stock_issue_api, name='stock_issue_api'),
    url(r'^api/student-profile/(?P<roll_no>[^/]+)/$', views.student_profile_api, name='student_profile_api'),
    url(r'^api/faculty-profile/(?P<username>[^/]+)/$', views.faculty_profile_api, name='faculty_profile_api'),
    url(r'^api/profile-change-requests/$', views.profile_change_requests_api, name='profile_change_requests_api'),
    url(r'^api/profile-change-requests/(?P<request_id>[0-9]+)/decision/$', views.profile_change_request_decision_api, name='profile_change_request_decision_api'),
    url(r'^api/faculty-directory/(?P<branch>[^/]+)/$', views.faculty_directory_api, name='faculty_directory_api'),
    url(r'^api/student-directory/(?P<branch>[^/]+)/$', views.student_directory_api, name='student_directory_api'),
    url(r'^api/alumni-directory/(?P<branch>[^/]+)/$', views.alumni_directory_api, name='alumni_directory_api'),
]
