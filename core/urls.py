from django.urls import path
from . import views
from . import report_views

urlpatterns = [
    path('health', views.HealthView.as_view()),
    path('auth/login', views.LoginView.as_view()),
    path('auth/me', views.MeView.as_view()),

    path('plans', views.PlanListView.as_view()),
    path('plans/active', views.ActivePlansView.as_view()),
    path('plans/<int:pk>', views.PlanDetailView.as_view()),

    path('sales', views.SaleListView.as_view()),
    path('sales/<int:pk>', views.SaleDetailView.as_view()),
    path('dashboard/stats', views.DashboardStatsView.as_view()),

    path('users', views.UserListView.as_view()),
    path('users/<int:pk>', views.UserDetailView.as_view()),

    path('customers', views.CustomerListView.as_view()),

    path('cash-count', views.CashCountView.as_view()),
    path('arqueo', views.CashCountView.as_view()),
    path('cash-count/outflows', views.OutflowCreateView.as_view()),
    path('cash-count/outflows/<int:pk>', views.OutflowDetailView.as_view()),

    path('reports/pdf', report_views.SalesPdfView.as_view()),
    path('reports/xlsx', report_views.SalesXlsxView.as_view()),
    path('reports/png', report_views.SalesPngView.as_view()),
    path('reports/pdf-link', report_views.SalesPdfLinkView.as_view()),
    path('reports/xlsx-link', report_views.SalesXlsxLinkView.as_view()),
    path('reports/pdf-public', report_views.SalesPdfPublicView.as_view()),
    path('reports/pdf-public/', report_views.SalesPdfPublicView.as_view()),
    path('reports/xlsx-public', report_views.SalesXlsxPublicView.as_view()),
    path('reports/xlsx-public/', report_views.SalesXlsxPublicView.as_view()),
    path('reports/cash-public', report_views.CashPdfPublicView.as_view()),
    path('reports/cash-public/', report_views.CashPdfPublicView.as_view()),
    path('cash-count/pdf', report_views.CashPdfView.as_view()),
    path('cash-count/pdf-link', report_views.CashPdfLinkView.as_view()),

    path('backups', views.BackupListView.as_view()),
    path('backups/<int:pk>/download', views.BackupDownloadView.as_view()),
    path('backups/<int:pk>', views.BackupDeleteView.as_view()),
]
