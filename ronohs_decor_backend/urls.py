from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def healthcheck(request):
    return JsonResponse({
        "status": "ok",
        "message": "Ronoh's Decor Backend is running 🎉",
        "environment": settings.DEBUG and "development" or "production"
    })

urlpatterns = [
    path('', healthcheck),  # 👈 Root healthcheck endpoint
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/auth/', include('users.urls')),
]

# This tells Django to serve media files during development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
