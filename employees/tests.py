from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile
from .models import Employee


class EmployeeCreationTest(TestCase):
	def setUp(self):
		# create an admin user with UserProfile so role_required passes
		self.admin = User.objects.create_user(username='adminuser', password='adminpass')
		UserProfile.objects.create(user=self.admin, role='admin')

	def test_employee_create_view_creates_user_and_employee(self):
		self.client.login(username='adminuser', password='adminpass')
		url = reverse('employees:employee_create')
		data = {
			'username': 'jdoe',
			'email': 'jdoe@example.com',
			'first_name': 'John',
			'last_name': 'Doe',
			'employee_id': 'EMP001',
			'department': 'IT',
			'designation': 'Developer',
			'date_of_birth': '1990-01-01',
			'date_of_joining': '2020-01-01',
			'salary': '5000.00',
			'phone': '1234567890',
			'address': '123 Street',
			'is_active': 'on',
		}

		response = self.client.post(url, data, follow=True)

		# After successful creation the user and employee should exist
		self.assertTrue(User.objects.filter(username='jdoe').exists())
		user = User.objects.get(username='jdoe')
		self.assertTrue(Employee.objects.filter(employee_id='EMP001', user=user).exists())
