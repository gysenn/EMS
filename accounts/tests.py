from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import UserProfile


class ProfileUpdateTest(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='user1', password='pass1')
		UserProfile.objects.create(user=self.user, role='employee')

	def test_profile_update(self):
		self.client.login(username='user1', password='pass1')
		url = reverse('accounts:profile')
		data = {
			'phone': '5551112222',
			'address': 'New Address'
		}
		response = self.client.post(url, data, follow=True)
		profile = UserProfile.objects.get(user=self.user)
		self.assertEqual(profile.phone, '5551112222')
		self.assertEqual(profile.address, 'New Address')
