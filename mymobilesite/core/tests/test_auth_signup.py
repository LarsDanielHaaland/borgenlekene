from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase
from django.contrib.auth.models import User
from core.models import Profile
from core.registration import register_user_with_profile


class SignupTests(TestCase):
    def test_signup_creates_user_and_profile_with_display_name(self):
        resp = self.client.post('/accounts/signup/', {
            'email': 'newuser@example.com',
            'display_name': 'CoolNickname',
            'password1': 'SuperSecretPass123',
            'password2': 'SuperSecretPass123',
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.profile.display_name, 'CoolNickname')

    def test_registration_rolls_back_user_when_profile_creation_fails(self):
        def save_user():
            return User.objects.create_user(
                username='incomplete',
                email='incomplete@example.com',
                password='SuperSecretPass123',
            )

        with patch('core.registration.Profile.objects.create', side_effect=IntegrityError):
            with self.assertRaises(IntegrityError):
                register_user_with_profile(save_user, 'IncompleteProfile')

        self.assertFalse(User.objects.filter(email='incomplete@example.com').exists())

    def test_signup_rejects_duplicate_display_name_case_insensitive(self):
        user = User.objects.create_user(username='existing', email='existing@example.com', password='x')
        Profile.objects.create(user=user, display_name='CoolNickname')

        resp = self.client.post('/accounts/signup/', {
            'email': 'another@example.com',
            'display_name': 'coolnickname',
            'password1': 'SuperSecretPass123',
            'password2': 'SuperSecretPass123',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'allerede tatt')
        self.assertFalse(User.objects.filter(email='another@example.com').exists())

    def test_login_with_email(self):
        user = User.objects.create_user(username='loginuser', email='login@example.com', password='SuperSecretPass123')
        Profile.objects.create(user=user, display_name='LoginNick')

        resp = self.client.post('/accounts/login/', {
            'login': 'login@example.com',
            'password': 'SuperSecretPass123',
        })
        self.assertEqual(resp.status_code, 302)
