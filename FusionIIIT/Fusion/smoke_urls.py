from django.conf.urls import include, url

urlpatterns = [
    url(r'^dep/', include('applications.department.api.urls')),
]
