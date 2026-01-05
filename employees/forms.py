from django import forms
from .models import Employee, LeaveRequest, Attendance, SalaryComponent, Payroll
from django.contrib.auth.models import User

class EmployeeForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    username = forms.CharField(max_length=150)
    # Make salary component fields optional on the form; they will be auto-calculated if omitted
    basic_salary = forms.DecimalField(required=False, max_digits=10, decimal_places=2)
    hra = forms.DecimalField(required=False, max_digits=10, decimal_places=2)
    transport_allowance = forms.DecimalField(required=False, max_digits=10, decimal_places=2)
    medical_allowance = forms.DecimalField(required=False, max_digits=10, decimal_places=2)
    
    class Meta:
        model = Employee
        fields = ['employee_id', 'department', 'designation', 'date_of_birth', 
                  'date_of_joining', 'salary', 'phone', 'address', 'photo', 'is_active',
                  'basic_salary', 'hra', 'transport_allowance', 'medical_allowance']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'date_of_joining': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

class LeaveApprovalForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['status', 'remarks']
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'status', 'check_in', 'check_out', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'check_in': forms.TimeInput(attrs={'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'type': 'time'}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }

class SalaryComponentForm(forms.ModelForm):
    # Accept browser `type="month"` value (YYYY-MM) by specifying an input format
    month = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'month'}), input_formats=['%Y-%m'])

    class Meta:
        model = SalaryComponent
        fields = ['employee', 'component_type', 'name', 'amount', 'is_recurring', 'month', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class PayrollForm(forms.ModelForm):
    # Allow `type="month"` input (YYYY-MM) for month selection
    month = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'month'}), input_formats=['%Y-%m'])

    class Meta:
        model = Payroll
        fields = ['employee', 'month', 'status', 'payment_date', 'remarks']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }
    