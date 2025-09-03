from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("tracker.urls")),
]

# In development, serve static files from STATICFILES_DIRS and app 'static/'
urlpatterns += staticfiles_urlpatterns()
