import re

from rest_framework.test import APIClient

from .conftest import BaseModuleTestCase


class ModuleTestBase(BaseModuleTestCase):
    """Shared helpers for department module black-box API tests."""

    def setUp(self):
        super().setUp()
        self.client_api = APIClient()
        self._results = []
        self._steps = []
        self._test_id = ''
        self._uc_id = ''
        self._br_id = ''
        self._wf_id = ''
        self._test_category = ''
        self._scenario = ''
        self._preconditions = ''
        self._input_action = ''
        self._expected_result = ''

    def login_as_student(self):
        self.client_api.force_authenticate(user=self.student_user)

    def login_as_staff(self):
        self.client_api.force_authenticate(user=self.staff_user)

    def login_as_faculty(self):
        self.client_api.force_authenticate(user=self.faculty_user)

    def _record_result(self, actual, status, evidence=''):
        self._results.append({
            'actual': actual,
            'status': status,
            'evidence': evidence,
        })

    def _resolve_path(self, path):
        if not path:
            return path

        raw_path, query = (path.split('?', 1) + [''])[:2]

        exact = {
            '/announcements_api': '/dep/api/announcements/',
            '/feedback_api': '/dep/api/feedback/',
            '/stock_requests_api': '/dep/api/stock/requests/',
            '/timetable_api': '/dep/api/timetable/',
            '/facilities_api': '/dep/api/facilities/',
            '/facilities_delete_api': '/dep/api/facilities/delete/',
            '/profile_change_requests_api': '/dep/api/profile-change-requests/',
        }
        if raw_path in exact:
            resolved = exact[raw_path]
            return '{}?{}'.format(resolved, query) if query else resolved

        if raw_path.startswith('/ann_data_api/'):
            branch = raw_path.split('/ann_data_api/', 1)[1]
            resolved = '/dep/api/ann-data/{}/'.format(branch)
            return '{}?{}'.format(resolved, query) if query else resolved

        m = re.match(r'^/delete_announcement_api/(\d+)$', raw_path)
        if m:
            resolved = '/dep/api/announcements/{}/'.format(m.group(1))
            return '{}?{}'.format(resolved, query) if query else resolved

        m = re.match(r'^/resolve_feedback_api/(\d+)$', raw_path)
        if m:
            resolved = '/dep/api/feedback/{}/resolve/'.format(m.group(1))
            return '{}?{}'.format(resolved, query) if query else resolved

        m = re.match(r'^/stock_decision_api/(\d+)$', raw_path)
        if m:
            resolved = '/dep/api/stock/requests/{}/decision/'.format(m.group(1))
            return '{}?{}'.format(resolved, query) if query else resolved

        m = re.match(r'^/stock_issue_api/(\d+)$', raw_path)
        if m:
            resolved = '/dep/api/stock/requests/{}/issue/'.format(m.group(1))
            return '{}?{}'.format(resolved, query) if query else resolved

        m = re.match(r'^/student_directory_api/([^/]+)$', raw_path)
        if m:
            resolved = '/dep/api/student-directory/{}/'.format(m.group(1))
            return '{}?{}'.format(resolved, query) if query else resolved

        m = re.match(r'^/faculty_directory_api/([^/]+)$', raw_path)
        if m:
            resolved = '/dep/api/faculty-directory/{}/'.format(m.group(1))
            return '{}?{}'.format(resolved, query) if query else resolved

        m = re.match(r'^/profile_change_request_decision_api/(\d+)$', raw_path)
        if m:
            resolved = '/dep/api/profile-change-requests/{}/decision/'.format(m.group(1))
            return '{}?{}'.format(resolved, query) if query else resolved

        return path

    def api_get(self, path, expected_status=None):
        response = self.client_api.get(self._resolve_path(path), format='json')
        if expected_status is not None:
            self.assertEqual(response.status_code, expected_status)
        return response

    def api_post(self, path, payload, expected_status=None):
        response = self.client_api.post(self._resolve_path(path), payload, format='json')
        if expected_status is not None:
            self.assertEqual(response.status_code, expected_status)
        return response

    def api_delete(self, path, payload=None, expected_status=None):
        if payload is None:
            response = self.client_api.delete(self._resolve_path(path), format='json')
        else:
            response = self.client_api.delete(self._resolve_path(path), payload, format='json')
        if expected_status is not None:
            self.assertEqual(response.status_code, expected_status)
        return response


class UCTestBase(ModuleTestBase):
    pass


class BRTestBase(ModuleTestBase):
    pass


class WFTestBase(ModuleTestBase):
    pass
