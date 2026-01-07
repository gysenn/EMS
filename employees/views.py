from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Sum, Avg
from django.http import HttpResponse, FileResponse, HttpResponseBadRequest
from django.contrib.auth.models import User
from accounts.decorators import role_required
from .models import Employee, LeaveRequest, Attendance, SalaryComponent, Payroll
from .forms import (EmployeeForm, LeaveRequestForm, LeaveApprovalForm, 
                    AttendanceForm, SalaryComponentForm, PayrollForm)
from .utils import (export_employees_pdf, export_employees_excel, 
                    export_attendance_excel, export_leaves_excel, generate_salary_slip_pdf)
from datetime import datetime, timedelta
from calendar import monthrange
from accounts.models import UserProfile
from decimal import Decimal
from django.db.models import F, ExpressionWrapper, IntegerField
from django.db.models.functions import ExtractDay


@login_required
@role_required(['admin', 'manager'])
def employee_list(request):
    employees = Employee.objects.select_related('user').all()
    return render(request, 'employees/employee_list.html', {'employees': employees})

@login_required
def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    
    user_role = getattr(request.user.profile, 'role', 'employee') if hasattr(request.user, 'profile') else 'employee'
    if user_role == 'employee' and request.user.employee != employee:
        messages.error(request, 'You can only view your own details')
        return redirect('dashboard')
    
    return render(request, 'employees/employee_detail.html', {'employee': employee})

from django.db import IntegrityError

@login_required
@role_required(['admin'])
def employee_create(request):
    """Create a new employee along with linked User and UserProfile."""
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Extract user info
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            
            # Check if username or email already exists
            if User.objects.filter(username=username).exists():
                form.add_error('username', 'Username already exists')
            if User.objects.filter(email=email).exists():
                form.add_error('email', 'Email already exists')
            
            if form.errors:
                # Return form with errors
                return render(request, 'employees/employee_form.html', {'form': form, 'action': 'Create'})
            
            try:
                # Create User
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    password='password123'  # default password
                )
                
                # Create UserProfile
                UserProfile.objects.create(user=user, role='employee')
                
                # Create Employee
                employee = form.save(commit=False)
                employee.user = user
                employee.save()
                
                messages.success(
                    request, 
                    f'Employee {employee.employee_id} created successfully. Default password: password123'
                )
                return redirect('employees:employee_list')
            
            except IntegrityError as e:
                messages.error(request, f'Error creating employee: {str(e)}')
                form.add_error(None, 'Database error, please check the data.')
        
        else:
            messages.error(request, 'Please correct the errors below.')
    
    else:
        form = EmployeeForm()
    
    return render(request, 'employees/employee_form.html', {'form': form, 'action': 'Create'})


@login_required
@role_required(['admin'])
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            employee = form.save()
            user = employee.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.username = form.cleaned_data['username']
            user.save()
            
            messages.success(request, 'Employee updated successfully')
            return redirect('employees:employee_detail', pk=employee.pk)
    else:
        initial_data = {
            'first_name': employee.user.first_name,
            'last_name': employee.user.last_name,
            'email': employee.user.email,
            'username': employee.user.username,
        }
        form = EmployeeForm(instance=employee, initial=initial_data)
    
    return render(request, 'employees/employee_form.html', {'form': form, 'action': 'Update'})

@login_required
def employee_delete(request, pk):
    """
    Delete/deactivate employee with role-based permissions:
    - Admin: Can delete both employees and managers
    - Manager: Can only delete employees (not other managers)
    - Employee: Cannot delete anyone
    """
    employee = get_object_or_404(Employee, pk=pk)
    user_role = getattr(request.user.profile, 'role', 'employee') if hasattr(request.user, 'profile') else 'employee'
    
    # Get the target user's role
    target_role = getattr(employee.user.profile, 'role', 'employee') if hasattr(employee.user, 'profile') else 'employee'
    
    # Permission check
    if user_role == 'employee':
        messages.error(request, 'You do not have permission to delete employees')
        return redirect('dashboard')
    
    if user_role == 'manager' and target_role in ['admin', 'manager']:
        messages.error(request, 'Managers can only delete employees, not other managers or admins')
        return redirect('employees:employee_list')
    
    if user_role == 'admin' and target_role == 'admin' and employee.user == request.user:
        messages.error(request, 'You cannot delete your own admin account')
        return redirect('employees:employee_list')
    
    if request.method == 'POST':
        employee.is_active = False
        employee.save()
        
        # Also deactivate the user account
        employee.user.is_active = False
        employee.user.save()
        
        messages.success(request, f'Employee {employee.employee_id} has been deactivated successfully')
        return redirect('employees:employee_list')
    
    return render(request, 'employees/employee_confirm_delete.html', {
        'employee': employee,
        'target_role': target_role
    })

@login_required
def leave_list(request):
    user_role = getattr(request.user.profile, 'role', 'employee') if hasattr(request.user, 'profile') else 'employee'
    
    if user_role in ['admin', 'manager']:
        leaves = LeaveRequest.objects.select_related('employee__user', 'approved_by').all()
    else:
        leaves = LeaveRequest.objects.filter(employee=request.user.employee)
    
    return render(request, 'employees/leave_list.html', {'leaves': leaves})

@login_required
def leave_create(request):
    if not hasattr(request.user, 'employee'):
        messages.error(request, 'You must be an employee to request leave')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = request.user.employee
            leave.save()
            messages.success(request, 'Leave request submitted successfully')
            return redirect('employees:leave_list')
    else:
        form = LeaveRequestForm()
    
    return render(request, 'employees/leave_form.html', {'form': form})

@login_required
@role_required(['admin', 'manager'])
def leave_approve(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    
    if request.method == 'POST':
        form = LeaveApprovalForm(request.POST, instance=leave)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.approved_by = request.user
            leave.save()
            messages.success(request, f'Leave request {leave.status}')
            return redirect('employees:leave_list')
    else:
        form = LeaveApprovalForm(instance=leave)
    
    return render(request, 'employees/leave_approval.html', {'form': form, 'leave': leave})

@login_required
def attendance_list(request):
    user_role = getattr(request.user.profile, 'role', 'employee') if hasattr(request.user, 'profile') else 'employee'
    
    if user_role in ['admin', 'manager']:
        attendance = Attendance.objects.select_related('employee__user').all()[:100]
    else:
        attendance = Attendance.objects.filter(employee=request.user.employee)[:30]
    
    return render(request, 'employees/attendance_list.html', {'attendance': attendance})

@login_required
@role_required(['admin', 'manager'])
def attendance_create(request):
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance recorded successfully')
            return redirect('employees:attendance_list')
    else:
        form = AttendanceForm()
    
    return render(request, 'employees/attendance_form.html', {'form': form})

@login_required
@role_required(['admin', 'manager'])
def export_employees(request, format):
    employees = Employee.objects.select_related('user').filter(is_active=True)
    
    fmt = (format or '').lower()
    if fmt == 'pdf':
        buffer = export_employees_pdf(employees)
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename='employees.pdf', content_type='application/pdf')
    elif fmt in ('excel', 'xlsx', 'xls'):
        buffer = export_employees_excel(employees)
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename='employees.xlsx', content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else:
        return HttpResponseBadRequest(f'Invalid format "{format}". Supported values: "pdf", "excel"')

@login_required
@role_required(['admin', 'manager'])
def export_attendance(request):
    attendance = Attendance.objects.select_related('employee__user').all()[:500]
    buffer = export_attendance_excel(attendance)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='attendance.xlsx', content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@login_required
@role_required(['admin', 'manager'])
def export_leaves(request):
    user_role = getattr(request.user.profile, 'role', 'employee') if hasattr(request.user, 'profile') else 'employee'
    if user_role in ['admin', 'manager']:
        leaves = LeaveRequest.objects.select_related('employee__user', 'approved_by').all()[:1000]
    else:
        leaves = LeaveRequest.objects.filter(employee=request.user.employee)

    buffer = export_leaves_excel(leaves)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='leaves.xlsx', content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
@login_required
def dashboard(request):
    """Enhanced dashboard with analytics for all users"""
    user_role = getattr(request.user.profile, 'role', 'employee') if hasattr(request.user, 'profile') else 'employee'
    today = datetime.now().date()
    current_month = today.replace(day=1)
    
    context = {
        'user_role': user_role,
        'today': today,
    }
    
    # Common statistics
    context['total_employees'] = Employee.objects.filter(is_active=True).count()
    context['pending_leaves'] = LeaveRequest.objects.filter(status='pending').count()
    
    if user_role in ['admin', 'manager']:
        # Admin/Manager Analytics
        context.update(get_admin_manager_analytics(today, current_month))
    
    if hasattr(request.user, 'employee'):
        # Employee Analytics
        context.update(get_employee_analytics(request.user.employee, today, current_month))
    
    return render(request, 'dashboard.html', context)

def get_admin_manager_analytics(today, current_month):
    """Get analytics for admin and manager roles"""
    analytics = {}
    
    # Department-wise employee count
    analytics['department_stats'] = Employee.objects.filter(
        is_active=True
    ).values('department').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Monthly attendance summary
    analytics['monthly_attendance'] = Attendance.objects.filter(
        date__gte=current_month,
        date__lte=today
    ).values('status').annotate(
        count=Count('id')
    )
    
    # Leave statistics
    analytics['leave_stats'] = LeaveRequest.objects.filter(
        created_at__month=today.month,
        created_at__year=today.year
    ).values('status').annotate(count=Count('id'))
    
    # Recent leaves
    analytics['recent_leaves'] = LeaveRequest.objects.select_related(
        'employee__user'
    ).order_by('-created_at')[:5]
    
    # Payroll statistics
    analytics['total_payroll'] = Payroll.objects.filter(
        month=current_month,
        status__in=['processed', 'paid']
    ).aggregate(
        total=Sum('net_salary'),
        count=Count('id')
    )
    
    # Pending payroll processing
    analytics['pending_payroll'] = Employee.objects.filter(
        is_active=True
    ).exclude(
        payrolls__month=current_month
    ).count()
    
    # Top earners
    analytics['top_earners'] = Employee.objects.filter(
        is_active=True
    ).order_by('-salary')[:5]
    
    # Attendance rate this month
    total_working_days = today.day
    total_possible_attendance = Employee.objects.filter(is_active=True).count() * total_working_days
    present_count = Attendance.objects.filter(
        date__gte=current_month,
        date__lte=today,
        status='present'
    ).count()
    
    analytics['attendance_rate'] = (present_count / total_possible_attendance * 100) if total_possible_attendance > 0 else 0
    
    return analytics

def get_employee_analytics(employee, today, current_month):
    """Get analytics for employee role"""
    analytics = {}
    
    # Monthly attendance stats
    analytics['my_attendance'] = Attendance.objects.filter(
        employee=employee,
        date__gte=current_month,
        date__lte=today
    ).values('status').annotate(count=Count('id'))
    
    # Leave balance calculation
    total_annual_leaves = 20  # Can be made configurable
  

    used_leaves = LeaveRequest.objects.filter(
        employee=employee,
        status='approved',
        start_date__year=today.year
        ).annotate(
        days=ExpressionWrapper(
        F('end_date') - F('start_date'),
        output_field=IntegerField()
        )
        ).aggregate(total=Sum('days'))['total'] or 0

    analytics['leave_balance'] = total_annual_leaves - used_leaves
    analytics['used_leaves'] = used_leaves

    
    analytics['leave_balance'] = total_annual_leaves - used_leaves
    analytics['used_leaves'] = used_leaves
    
    # My recent leaves
    analytics['my_leaves'] = LeaveRequest.objects.filter(
        employee=employee
    ).order_by('-created_at')[:5]
    
    # Current month salary info
    try:
        analytics['current_payroll'] = Payroll.objects.get(
            employee=employee,
            month=current_month
        )
    except Payroll.DoesNotExist:
        analytics['current_payroll'] = None
    
    # Salary components
    analytics['salary_components'] = SalaryComponent.objects.filter(
        employee=employee,
        is_recurring=True
    )
    
    # Attendance count this month
    analytics['my_attendance_count'] = Attendance.objects.filter(
        employee=employee,
        date__gte=current_month,
        status='present'
    ).count()
    
    # Working days this month
    analytics['working_days'] = today.day
    
    # Attendance percentage
    if analytics['working_days'] > 0:
        analytics['attendance_percentage'] = (
            analytics['my_attendance_count'] / analytics['working_days'] * 100
        )
    else:
        analytics['attendance_percentage'] = 0
    
    return analytics

# Payroll Management Views

@login_required
@role_required(['admin'])
def payroll_list(request):
    """List all payrolls"""
    month_filter = request.GET.get('month')
    status_filter = request.GET.get('status')
    
    payrolls = Payroll.objects.select_related('employee__user').all()
    
    if month_filter:
        try:
            filter_date = datetime.strptime(month_filter, '%Y-%m').date()
            payrolls = payrolls.filter(month=filter_date)
        except ValueError:
            pass
    
    if status_filter:
        payrolls = payrolls.filter(status=status_filter)
    
    # Get unique months for filter dropdown
    months = Payroll.objects.dates('month', 'month', order='DESC')
    
    context = {
        'payrolls': payrolls[:100],
        'months': months,
        'selected_month': month_filter,
        'selected_status': status_filter,
    }
    
    return render(request, 'employees/payroll_list.html', context)

@login_required
@role_required(['admin'])
def payroll_generate(request):
    """Generate payroll for a specific month"""
    if request.method == 'POST':
        month_str = request.POST.get('month')
        try:
            month_date = datetime.strptime(month_str, '%Y-%m').date().replace(day=1)
        except ValueError:
            messages.error(request, 'Invalid month format')
            return redirect('employees:payroll_list')
        
        # Get all active employees
        employees = Employee.objects.filter(is_active=True)
        generated_count = 0
        
        for emp in employees:
            # Check if payroll already exists
            if Payroll.objects.filter(employee=emp, month=month_date).exists():
                continue
            
            # Calculate attendance
            _, last_day = monthrange(month_date.year, month_date.month)
            month_end = month_date.replace(day=last_day)
            
            attendance_stats = Attendance.objects.filter(
                employee=emp,
                date__gte=month_date,
                date__lte=month_end
            ).values('status').annotate(count=Count('id'))
            
            present_days = 0
            absent_days = 0
            leave_days = 0
            
            for stat in attendance_stats:
                if stat['status'] == 'present':
                    present_days = stat['count']
                elif stat['status'] == 'absent':
                    absent_days = stat['count']
                elif stat['status'] == 'leave':
                    leave_days = stat['count']
            
            # Get additional components
            allowances = SalaryComponent.objects.filter(
                employee=emp,
                component_type='allowance',
                is_recurring=True
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            bonuses = SalaryComponent.objects.filter(
                employee=emp,
                component_type='bonus',
                month=month_date
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            deductions = SalaryComponent.objects.filter(
                employee=emp,
                component_type='deduction',
                is_recurring=True
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate tax (simple 10% on gross)
            gross_before_tax = (
                emp.basic_salary + emp.hra + 
                emp.transport_allowance + emp.medical_allowance + 
                Decimal(str(allowances)) + Decimal(str(bonuses))
            )
            tax = gross_before_tax * Decimal('0.10')
            
            # Create payroll
            payroll = Payroll.objects.create(
                employee=emp,
                month=month_date,
                basic_salary=emp.basic_salary,
                hra=emp.hra,
                transport_allowance=emp.transport_allowance,
                medical_allowance=emp.medical_allowance,
                other_allowances=allowances,
                bonus=bonuses,
                tax=tax,
                provident_fund=emp.basic_salary * Decimal('0.12'),  # 12% PF
                insurance=Decimal('500'),  # Fixed insurance
                other_deductions=deductions,
                working_days=last_day,
                present_days=present_days,
                absent_days=absent_days,
                leave_days=leave_days,
                gross_salary=0,  # Will be calculated
                total_deductions=0,  # Will be calculated
                net_salary=0,  # Will be calculated
                status='processed',
                created_by=request.user
            )
            
            payroll.calculate_salary()
            generated_count += 1
        
        messages.success(request, f'Successfully generated {generated_count} payroll(s) for {month_date.strftime("%B %Y")}')
        return redirect('employees:payroll_list')
    
    return render(request, 'employees/payroll_generate.html')

@login_required
def payroll_detail(request, pk):
    """View payroll detail"""
    payroll = get_object_or_404(Payroll, pk=pk)
    user_role = getattr(request.user.profile, 'role', 'employee')
    
    # Employee can only view their own payroll
    if user_role == 'employee' and payroll.employee.user != request.user:
        messages.error(request, 'You can only view your own payroll')
        return redirect('dashboard')
    
    return render(request, 'employees/payroll_detail.html', {'payroll': payroll})

@login_required
def download_salary_slip(request, pk):
    """Download salary slip as PDF"""
    payroll = get_object_or_404(Payroll, pk=pk)
    user_role = getattr(request.user.profile, 'role', 'employee')
    
    # Employee can only download their own slip
    if user_role == 'employee' and payroll.employee.user != request.user:
        messages.error(request, 'You can only download your own salary slip')
        return redirect('dashboard')
    
    buffer = generate_salary_slip_pdf(payroll)
    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f'salary_slip_{payroll.employee.employee_id}_{payroll.month.strftime("%B_%Y")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@login_required
def my_payrolls(request):
    """Employee view their own payrolls"""
    if not hasattr(request.user, 'employee'):
        messages.error(request, 'Employee profile not found')
        return redirect('dashboard')
    
    payrolls = Payroll.objects.filter(
        employee=request.user.employee
    ).order_by('-month')
    
    return render(request, 'employees/my_payrolls.html', {'payrolls': payrolls})

@login_required
@role_required(['admin'])
def salary_component_list(request):
    """List all salary components"""
    components = SalaryComponent.objects.select_related('employee__user').all()[:100]
    return render(request, 'employees/salary_component_list.html', {'components': components})

@login_required
@role_required(['admin'])
def salary_component_create(request):
    """Create new salary component"""
    if request.method == 'POST':
        form = SalaryComponentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salary component created successfully')
            return redirect('employees:salary_component_list')
    else:
        form = SalaryComponentForm()
    
    return render(request, 'employees/salary_component_form.html', {'form': form, 'action': 'Create'})