from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from django.http import HttpResponse
from io import BytesIO

def export_employees_pdf(employees):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    title = Paragraph("Employee Report", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.3*inch))
    
    data = [['ID', 'Name', 'Department', 'Designation', 'Phone']]
    for emp in employees:
        data.append([
            emp.employee_id,
            emp.user.get_full_name(),
            emp.get_department_display(),
            emp.designation,
            emp.phone
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    return buffer

def export_employees_excel(employees):
    wb = Workbook()
    ws = wb.active
    ws.title = "Employees"
    
    headers = ['Employee ID', 'Name', 'Email', 'Department', 'Designation', 'Phone', 'Joining Date', 'Salary']
    ws.append(headers)
    
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    
    for emp in employees:
        ws.append([
            emp.employee_id,
            emp.user.get_full_name(),
            emp.user.email,
            emp.get_department_display(),
            emp.designation,
            emp.phone,
            emp.date_of_joining.strftime('%Y-%m-%d'),
            float(emp.salary)
        ])
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

def export_attendance_excel(attendance_records):
    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance"
    
    headers = ['Employee ID', 'Name', 'Date', 'Status', 'Check In', 'Check Out', 'Remarks']
    ws.append(headers)
    
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    
    for record in attendance_records:
        ws.append([
            record.employee.employee_id,
            record.employee.user.get_full_name(),
            record.date.strftime('%Y-%m-%d'),
            record.get_status_display(),
            record.check_in.strftime('%H:%M') if record.check_in else '',
            record.check_out.strftime('%H:%M') if record.check_out else '',
            record.remarks
        ])
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer