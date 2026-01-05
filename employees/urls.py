from django.urls import path
from . import views

app_name = 'employees'

urlpatterns = [
    # Employee URLs
    path('', views.employee_list, name='employee_list'),
    path('<int:pk>/', views.employee_detail, name='employee_detail'),
    path('create/', views.employee_create, name='employee_create'),
    path('<int:pk>/update/', views.employee_update, name='employee_update'),
    path('<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    
    # Leave URLs
    path('leaves/', views.leave_list, name='leave_list'),
    path('leaves/create/', views.leave_create, name='leave_create'),
    path('leaves/<int:pk>/approve/', views.leave_approve, name='leave_approve'),
    
    # Attendance URLs
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/create/', views.attendance_create, name='attendance_create'),
    
    # Export URLs
    path('export/<str:format>/', views.export_employees, name='export_employees'),
    path('export/attendance/', views.export_attendance, name='export_attendance'),
    
    # Payroll URLs (NEW)
    path('payroll/', views.payroll_list, name='payroll_list'),
    path('payroll/generate/', views.payroll_generate, name='payroll_generate'),
    path('payroll/<int:pk>/', views.payroll_detail, name='payroll_detail'),
    path('payroll/<int:pk>/download/', views.download_salary_slip, name='download_salary_slip'),
    path('my-payrolls/', views.my_payrolls, name='my_payrolls'),
    
    # Salary Component URLs (NEW)
    path('salary-components/', views.salary_component_list, name='salary_component_list'),
    path('salary-components/create/', views.salary_component_create, name='salary_component_create'),
]