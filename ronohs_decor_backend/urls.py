from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

def home(request):
    return HttpResponse("Ronoh's Decor Backend is running 🎉")

urlpatterns = [
    path('', home),  # 👈 Root URL
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/auth/', include('users.urls')),
]

# This tells Django to serve media files during development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
