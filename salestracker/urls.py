from django.contrib import admin
from django.urls import path, include, re_path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
]

# Servir el build del frontend en producción (SPA: todo lo no-API -> index.html)
try:
    from django.conf import settings
    from django.shortcuts import render
    from pathlib import Path

    def index_view(request):
        """index.html sin caché para que el navegador siempre tome el bundle nuevo."""
        response = render(request, 'index.html')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response

    build_dir = Path(settings.FRONTEND_BUILD_DIR)
    if build_dir.exists():
        urlpatterns += [
            path('', index_view),
            re_path(r'^(?!api/|static/|admin/).*', index_view),
        ]
except Exception:
    pass
