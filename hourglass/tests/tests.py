import os
import unittest
import json
from unittest import SkipTest
from unittest.mock import patch
from django.test import TestCase as DjangoTestCase
from django.test import override_settings
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.conf.urls import url

from .. import healthcheck, __version__
from ..urls import urlpatterns
from ..decorators import staff_login_required
from ..settings_utils import (load_cups_from_vcap_services,
                              load_redis_url_from_vcap_services,
                              get_whitelisted_ips,
                              is_running_tests)


@staff_login_required
def staff_only_view(request):
    return HttpResponse('ok')

urlpatterns += [
    url(r'^staff_only_view/$', staff_only_view, name='staff_only_view'),
]


class ComplianceTests(DjangoTestCase):
    '''
    These tests ensure our site is configured with proper regulatory
    compliance and security best practices.  For more information, see:

    https://compliance-viewer.18f.gov/

    Cloud.gov's nginx proxy adds the required headers to 200 responses, but
    not to responses with error codes, so we need to add them at the app-level.
    '''

    headers = {
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block',
    }

    def assertHasHeaders(self, res):
        for header, val in self.headers.items():
            self.assertEqual(res[header], val)

    @override_settings(SECURITY_HEADERS_ON_ERROR_ONLY=False)
    def test_has_security_headers(self):
        res = self.client.get('/')
        self.assertHasHeaders(res)

    @override_settings(SECURITY_HEADERS_ON_ERROR_ONLY=False)
    def test_has_security_headers_on_404(self):
        res = self.client.get('/i-am-a-nonexistent-page')
        self.assertHasHeaders(res)

    @override_settings(SECURITY_HEADERS_ON_ERROR_ONLY=True)
    def test_no_security_headers_when_setting_enabled(self):
        res = self.client.get('/')
        for header, val in self.headers.items():
            self.assertNotIn(header, res)

    @override_settings(SECURITY_HEADERS_ON_ERROR_ONLY=True)
    def test_has_security_headers_on_404_when_setting_enabled(self):
        res = self.client.get('/i-am-a-nonexistent-page')
        self.assertHasHeaders(res)


class HealthcheckTests(DjangoTestCase):
    def test_it_works(self):
        res = self.client.get('/healthcheck/')
        self.assertEqual(res.status_code, 200)
        self.assertJSONEqual(str(res.content, encoding='utf8'), {
            'version': __version__,
            'is_database_synchronized': True,
            'rq_jobs': 0
        })

    @patch.object(healthcheck, 'is_database_synchronized')
    def test_it_returns_500_when_db_is_not_synchronized(self, mock):
        mock.return_value = False
        res = self.client.get('/healthcheck/')
        self.assertEqual(res.status_code, 500)
        self.assertJSONEqual(str(res.content, encoding='utf8'), {
            'version': __version__,
            'is_database_synchronized': False,
            'rq_jobs': 0
        })


class RobotsTests(DjangoTestCase):

    @override_settings(ENABLE_SEO_INDEXING=False)
    def test_disable_seo_indexing_works(self):
        res = self.client.get('/robots.txt')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content, b"User-agent: *\nDisallow: /")

    @override_settings(ENABLE_SEO_INDEXING=True)
    def test_enable_seo_indexing_works(self):
        res = self.client.get('/robots.txt')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content, b"User-agent: *\nDisallow:")


def make_vcap_services_env(vcap_services):
    return {
        'VCAP_SERVICES': json.dumps(vcap_services)
    }


class CupsTests(unittest.TestCase):

    def test_noop_if_vcap_services_not_in_env(self):
        env = {}
        load_cups_from_vcap_services('blah', env=env)
        self.assertEqual(env, {})

    def test_irrelevant_cups_are_ignored(self):
        env = make_vcap_services_env({
            "user-provided": [
                {
                    "label": "user-provided",
                    "name": "NOT-boop-env",
                    "syslog_drain_url": "",
                    "credentials": {
                        "boop": "jones"
                    },
                    "tags": []
                }
            ]
        })

        load_cups_from_vcap_services('boop-env', env=env)

        self.assertFalse('boop' in env)

    def test_credentials_are_loaded(self):
        env = make_vcap_services_env({
            "user-provided": [
                {
                    "label": "user-provided",
                    "name": "boop-env",
                    "syslog_drain_url": "",
                    "credentials": {
                        "boop": "jones"
                    },
                    "tags": []
                }
            ]
        })

        load_cups_from_vcap_services('boop-env', env=env)

        self.assertEqual(env['boop'], 'jones')


class RedisUrlTests(unittest.TestCase):
    def test_noop_when_vcap_not_in_env(self):
        env = {}
        load_redis_url_from_vcap_services('redis-service', env=env)
        self.assertEqual(env, {})

    def test_noop_when_name_not_in_vcap(self):
        env = make_vcap_services_env({
            'redis28': [{
                'name': 'a-different-name',
                'credentials': {
                    'hostname': 'the_host',
                    'password': 'the_password',  # nosec
                    'port': '1234'
                }
            }]
        })
        load_redis_url_from_vcap_services('boop')
        self.assertFalse('REDIS_URL' in env)

    def test_redis_url_is_loaded(self):
        env = make_vcap_services_env({
            'redis28': [{
                'name': 'redis-service',
                'credentials': {
                    'hostname': 'the_host',
                    'password': 'the_password',  # nosec
                    'port': '1234'
                }
            }]
        })

        load_redis_url_from_vcap_services('redis-service', env=env)
        self.assertTrue('REDIS_URL' in env)
        self.assertEqual(env['REDIS_URL'],
                         'redis://:the_password@the_host:1234')


class GetWhitelistedIPsTest(unittest.TestCase):

    def test_returns_none_when_not_in_env(self):
        env = {}
        self.assertIsNone(get_whitelisted_ips(env))

    def test_returns_whitelisted_ips_list(self):
        env = {
            'WHITELISTED_IPS': '1.2.3.4,1.2.3.8, 1.2.3.16'
        }
        ips = get_whitelisted_ips(env)
        self.assertListEqual(ips, ['1.2.3.4', '1.2.3.8', '1.2.3.16'])


@override_settings(
    # This will make tests run faster.
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    # Ignore our custom auth backend so we can log the user in via
    # Django 1.8's login helpers.
    AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend'],
)
class AdminLoginTest(DjangoTestCase):
    def test_non_logged_in_user_is_redirected_to_login(self):
        res = self.client.get('/admin/')
        self.assertEqual(res.status_code, 302)
        self.assertTrue(
            res['Location'].startswith('http://testserver/admin/login'))

    def test_is_staff_user_can_view(self):
        user = User.objects.create_user(  # nosec
            username='nonstaff',
            password='foo',
        )
        user.is_staff = True
        user.save()
        logged_in = self.client.login(  # nosec
            username=user.username, password='foo')
        self.assertTrue(logged_in)
        res = self.client.get('/admin/')
        self.assertEqual(res.status_code, 200)

    def test_non_is_staff_user_is_not_permitted(self):
        user = User.objects.create_user(  # nosec
            username='nonstaff',
            password='foo',
        )
        user.is_staff = False
        user.save()
        logged_in = self.client.login(  # nosec
            username=user.username, password='foo')
        self.assertTrue(logged_in)
        res = self.client.get('/admin/', follow=True)
        self.assertEqual(res.status_code, 403)


class IsRunningTestsTests(unittest.TestCase):
    def test_returns_true_when_running_tests(self):
        self.assertTrue(is_running_tests(), True)

    def test_returns_false_when_running_gunicorn(self):
        self.assertFalse(is_running_tests(['gunicorn']))

    def test_returns_false_when_running_manage_runserver(self):
        self.assertFalse(is_running_tests(['manage.py', 'runserver']))

    def test_returns_true_when_running_manage_test(self):
        self.assertTrue(is_running_tests(['manage.py', 'test']))

    def test_returns_true_when_running_py_test(self):
        self.assertTrue(is_running_tests(['/usr/local/bin/py.test']))


@override_settings(
    ROOT_URLCONF=__name__,
    # This will make tests run faster.
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    # Ignore our custom auth backend so we can log the user in via
    # Django 1.8's login helpers.
    AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend']
)
class StaffLoginRequiredTests(DjangoTestCase):

    def login(self, is_staff=False):
        user = User.objects.create_user(username='foo',  # nosec
                                        password='bar')
        if is_staff:
            user.is_staff = True
            user.save()
        assert self.client.login(username='foo', password='bar')  # nosec
        return user

    def test_redirects_to_login(self):
        res = self.client.get('/staff_only_view/')
        self.assertEqual(302, res.status_code)
        self.assertTrue(
            res['Location'].startswith('http://testserver/auth/login'))

    def test_staff_user_is_permitted(self):
        self.login(is_staff=True)
        res = self.client.get('/staff_only_view/')
        self.assertEqual(200, res.status_code)
        self.assertEqual(b'ok', res.content)

    def test_non_staff_user_is_denied(self):
        self.login(is_staff=False)
        res = self.client.get('/staff_only_view/')
        self.assertEqual(403, res.status_code)


class CachingTests(DjangoTestCase):
    def test_max_age_defaults_to_zero(self):
        res = self.client.get('/')
        self.assertEqual(res['Cache-Control'], 'max-age=0')


class ContextProcessorTests(DjangoTestCase):
    @override_settings(GA_TRACKING_ID='boop')
    def test_ga_tracking_id_is_included(self):
        res = self.client.get('/')
        self.assertIn('GA_TRACKING_ID', res.context)
        self.assertEqual(res.context['GA_TRACKING_ID'], 'boop')

    def test_ga_tracking_id_defaults_to_empty_string(self):
        if 'GA_TRACKING_ID' in os.environ:
            # Oof, GA_TRACKING_ID is defined in our outside environment,
            # so we can't actually test this.
            raise SkipTest()
        res = self.client.get('/')
        self.assertIn('GA_TRACKING_ID', res.context)
        self.assertEqual(res.context['GA_TRACKING_ID'], '')

    @override_settings(ETHNIO_SCREENER_ID='hoopla')
    def test_ethnio_screener_id_is_included(self):
        res = self.client.get('/')
        self.assertIn('ETHNIO_SCREENER_ID', res.context)
        self.assertEquals(res.context['ETHNIO_SCREENER_ID'], 'hoopla')

    @override_settings(HELP_EMAIL='help@calc.com')
    def test_help_email_is_included(self):
        res = self.client.get('/')
        self.assertIn('HELP_EMAIL', res.context)
        self.assertEquals(res.context['HELP_EMAIL'], 'help@calc.com')

    @override_settings(NON_PROD_INSTANCE_NAME='Staging')
    def test_non_prod_instance_name_is_included(self):
        res = self.client.get('/')
        self.assertIn('NON_PROD_INSTANCE_NAME', res.context)
        self.assertEquals(res.context['NON_PROD_INSTANCE_NAME'], 'Staging')
