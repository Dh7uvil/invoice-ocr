"""
URL configuration for OCR app.
"""

from django.urls import path
from . import views

app_name = 'ocr_app'

urlpatterns = [
    # Job management
    path('jobs/', views.InvoiceProcessingJobListView.as_view(), name='job-list'),
    path('jobs/<int:pk>/', views.InvoiceProcessingJobDetailView.as_view(), name='job-detail'),
    path('jobs/<int:job_id>/status/', views.job_status, name='job-status'),
    path('jobs/<int:job_id>/delete/', views.delete_job, name='delete-job'),
    
    # Invoice processing
    path('invoices/upload/', views.upload_invoice, name='upload-invoice'),
    path('invoices/export/csv/', views.export_csv, name='export-csv'),
    path('invoices/export/line-items.csv', views.export_line_items_csv, name='export-line-items-csv'),
    # Admin helper
    path('parties/<int:invoice_data_id>/', views.get_parties_by_invoice, name='get-parties-by-invoice'),
]
