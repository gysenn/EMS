from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile
from employees.models import Employee, LeaveRequest, Attendance
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = 'Load sample data for testing the Employee Management System'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Delete existing data before loading',
        )

    def handle(self, *args, **options):
        if options['clean']:
            self.stdout.write(self.style.WARNING('Cleaning existing data...'))
            Attendance.objects.all().delete()
            LeaveRequest.objects.all().delete()
            Employee.objects.all().delete()
            UserProfile.objects.exclude(user__is_superuser=True).delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS('✓ Data cleaned'))

        self.stdout.write(self.style.SUCCESS('Loading sample data...'))
        
        # Create admin user
        self.create_admin()
        
        # Create manager
        self.create_manager()
        
        # Create employees
        employees = self.create_employees()
        
        # Create leave requests
        self.create_leave_requests(employees)
        
        # Create attendance records
        self.create_attendance_records(employees)
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Sample data loaded successfully!'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.print_credentials()

    def create_admin(self):
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@ems.com',
                password='admin123',
                first_name='System',
                last_name='Administrator'
            )
            UserProfile.objects.create(
                user=admin, 
                role='admin',
                phone='1234567890',
                address='Admin Office, HQ Building'
            )
            self.stdout.write(self.style.SUCCESS('✓ Admin user created'))

    def create_manager(self):
        if not User.objects.filter(username='manager').exists():
            manager = User.objects.create_user(
                username='manager',
                email='manager@ems.com',
                password='manager123',
                first_name='John',
                last_name='Manager'
            )
            UserProfile.objects.create(
                user=manager,
                role='manager',
                phone='9876543210',
                address='123 Manager Street, City'
            )
            self.stdout.write(self.style.SUCCESS('✓ Manager user created'))

    def create_employees(self):
        employees_data = [
            {
                'username': 'alice.smith',
                'email': 'alice.smith@ems.com',
                'first_name': 'Alice',
                'last_name': 'Smith',
                'emp_id': 'EMP001',
                'dept': 'IT',
                'designation': 'Senior Developer',
                'salary': 75000
            },
            {
                'username': 'bob.jones',
                'email': 'bob.jones@ems.com',
                'first_name': 'Bob',
                'last_name': 'Jones',
                'emp_id': 'EMP002',
                'dept': 'HR',
                'designation': 'HR Manager',
                'salary': 65000
            },
            {
                'username': 'carol.white',
                'email': 'carol.white@ems.com',
                'first_name': 'Carol',
                'last_name': 'White',
                'emp_id': 'EMP003',
                'dept': 'FIN',
                'designation': 'Financial Analyst',
                'salary': 70000
            },
            {
                'username': 'david.brown',
                'email': 'david.brown@ems.com',
                'first_name': 'David',
                'last_name': 'Brown',
                'emp_id': 'EMP004',
                'dept': 'MKT',
                'designation': 'Marketing Manager',
                'salary': 68000
            },
            {
                'username': 'emma.davis',
                'email': 'emma.davis@ems.com',
                'first_name': 'Emma',
                'last_name': 'Davis',
                'emp_id': 'EMP005',
                'dept': 'OPS',
                'designation': 'Operations Coordinator',
                'salary': 60000
            },
        ]

        created_employees = []
        
        for data in employees_data:
            if not User.objects.filter(username=data['username']).exists():
                user = User.objects.create_user(
                    username=data['username'],
                    email=data['email'],
                    password='password123',
                    first_name=data['first_name'],
                    last_name=data['last_name']
                )
                
                UserProfile.objects.create(
                    user=user,
                    role='employee',
                    phone=f'555{random.randint(1000000, 9999999)}',
                    address=f'{random.randint(100, 999)} Employee Street, City'
                )
                
                employee = Employee.objects.create(
                    user=user,
                    employee_id=data['emp_id'],
                    department=data['dept'],
                    designation=data['designation'],
                    date_of_birth=datetime(1990, 1, 1).date() + timedelta(days=random.randint(0, 3650)),
                    date_of_joining=datetime(2020, 1, 1).date() + timedelta(days=random.randint(0, 1500)),
                    salary=data['salary'],
                    phone=f'555{random.randint(1000000, 9999999)}',
                    address=f'{random.randint(100, 999)} Main Street, City, State',
                    is_active=True
                )
                created_employees.append(employee)
                self.stdout.write(self.style.SUCCESS(f'✓ Employee created: {data["emp_id"]} - {data["first_name"]} {data["last_name"]}'))

        return created_employees if created_employees else list(Employee.objects.all())

    def create_leave_requests(self, employees):
        leave_types = ['sick', 'casual', 'annual', 'sick', 'casual']
        statuses = ['pending', 'approved', 'rejected', 'pending', 'approved']
        
        for i, emp in enumerate(employees[:5]):
            # Create 2-3 leave requests per employee
            for j in range(random.randint(2, 3)):
                start_date = datetime.now().date() + timedelta(days=random.randint(-30, 30))
                end_date = start_date + timedelta(days=random.randint(1, 5))
                
                leave = LeaveRequest.objects.create(
                    employee=emp,
                    leave_type=leave_types[i % len(leave_types)],
                    start_date=start_date,
                    end_date=end_date,
                    reason=f'Sample {leave_types[i % len(leave_types)]} leave for testing purposes',
                    status=statuses[i % len(statuses)]
                )
                
                if leave.status != 'pending':
                    try:
                        manager = User.objects.get(username='manager')
                        leave.approved_by = manager
                        leave.remarks = f'Leave request {leave.status} by manager'
                        leave.save()
                    except User.DoesNotExist:
                        pass
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created leave requests'))

    def create_attendance_records(self, employees):
        today = datetime.now().date()
        
        for emp in employees:
            # Create attendance for last 20 days
            for i in range(20):
                date = today - timedelta(days=i)
                
                # Random attendance pattern (mostly present)
                status_choices = ['present'] * 7 + ['absent'] * 1 + ['half_day'] * 1 + ['leave'] * 1
                status = random.choice(status_choices)
                
                check_in = None
                check_out = None
                
                if status == 'present':
                    check_in = datetime.strptime(f'0{random.randint(8,9)}:00', '%H:%M').time()
                    check_out = datetime.strptime(f'{random.randint(17,19)}:00', '%H:%M').time()
                elif status == 'half_day':
                    check_in = datetime.strptime(f'0{random.randint(8,9)}:00', '%H:%M').time()
                    check_out = datetime.strptime(f'{random.randint(13,14)}:00', '%H:%M').time()
                
                Attendance.objects.get_or_create(
                    employee=emp,
                    date=date,
                    defaults={
                        'status': status,
                        'check_in': check_in,
                        'check_out': check_out,
                        'remarks': f'Sample attendance record for {date}'
                    }
                )
        
        self.stdout.write(self.style.SUCCESS(f'✓ Created attendance records'))

    def print_credentials(self):
        self.stdout.write('\n' + self.style.SUCCESS('LOGIN CREDENTIALS:'))
        self.stdout.write(self.style.WARNING('─' * 60))
        self.stdout.write('  Admin:')
        self.stdout.write('    Username: admin')
        self.stdout.write('    Password: admin123')
        self.stdout.write('')
        self.stdout.write('  Manager:')
        self.stdout.write('    Username: manager')
        self.stdout.write('    Password: manager123')
        self.stdout.write('')
        self.stdout.write('  Employees:')
        self.stdout.write('    Username: alice.smith (or bob.jones, carol.white, etc.)')
        self.stdout.write('    Password: password123')
        self.stdout.write(self.style.WARNING('─' * 60))
        self.stdout.write('\n' + self.style.SUCCESS('Start the server:'))
        self.stdout.write('    python manage.py runserver')