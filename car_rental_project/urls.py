from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
import users
from django.conf import settings
from django.conf.urls.static import static

app_name = "car_rental"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('car_rental.urls')),
    path('', include('users.urls', namespace='users')),
    path('__debug__/', include('debug_toolbar.urls')),
    ]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

