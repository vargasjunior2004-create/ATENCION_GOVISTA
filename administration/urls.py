"""HTTP namespace for Administración del Sistema.

The domain models remain in ``core`` for backwards compatibility.  This
module gives the administration UI an independent API boundary while the
authorization and serializers stay centralized in the existing backend.
"""

from django.urls import path

from core import views


urlpatterns = [
    path('usuarios', views.UserListView.as_view()),
    path('usuarios/<int:pk>', views.UserDetailView.as_view()),
    path('usuarios/<int:user_id>/roles', views.UserRoleListView.as_view()),
    path('usuarios/roles/<int:pk>', views.UserRoleDetailView.as_view()),
    path('roles', views.RoleListView.as_view()),
    path('roles/<int:pk>', views.RoleDetailView.as_view()),
    path('permisos', views.PermissionListView.as_view()),
    path('auditoria', views.AuditLogListView.as_view()),
    path('respaldos', views.BackupListView.as_view()),
    path('respaldos/<int:pk>', views.BackupDeleteView.as_view()),
]
