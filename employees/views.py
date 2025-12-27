from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.contrib.auth.models import User
from accounts.decorators import role_required
from .models import Employee, LeaveRequest, Attendance
from .forms import EmployeeForm, LeaveRequestForm, LeaveApprovalForm, AttendanceForm
from .utils import export_employees_pdf, export_employees_excel, export_attendance_excel
from datetime import datetime, timedelta
from accounts.models import UserProfile

@login_required
def dashboard(request):
    user_role = getattr(request.user.profile, 'role', 'employee') if hasattr(request.user, 'profile') else 'employee'
    
    context = {
        'total_employees': Employee.objects.filter(is_active=True).count(),
        'pending_leaves': LeaveRequest.objects.filter(status='pending').count(),
        'recent_leaves': LeaveRequest.objects.select_related('employee__user').order_by('-created_at')[:5],
        'user_role': user_role,
    }
    
    if hasattr(request.user, 'employee'):
        emp = request.user.employee
        context['my_leaves'] = LeaveRequest.objects.filter(employee=emp).order_by('-created_at')[:5]
        
        today = datetime.now().date()
        month_start = today.replace(day=1)
        context['my_attendance_count'] = Attendance.objects.filter(
            employee=emp,
            date__gte=month_start,
            status='present'
        ).count()
    
    return render(request, 'dashboard.html', context)

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

@login_required
@role_required(['admin'])
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                password='password123'
            )
            
            UserProfile.objects.create(user=user, role='employee')
            
            employee = form.save(commit=False)
            employee.user = user
            employee.save()
            
            messages.success(request, f'Employee {employee.employee_id} created successfully. Default password: password123')
            return redirect('employees:employee_list')
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
    
    if format == 'pdf':
        buffer = export_employees_pdf(employees)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="employees.pdf"'
    elif format == 'excel':
        buffer = export_employees_excel(employees)
        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="employees.xlsx"'
    else:
        return HttpResponse('Invalid format', status=400)
    
    return response

@login_required
@role_required(['admin', 'manager'])
def export_attendance(request):
    attendance = Attendance.objects.select_related('employee__user').all()[:500]
    buffer = export_attendance_excel(attendance)
    response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="attendance.xlsx"'
    return response