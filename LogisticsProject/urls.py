from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 1. Đường dẫn vào trang quản trị (Admin)
    path('admin/', admin.site.urls),

    # 2. Đường dẫn vào App chính (core)
    # Nó sẽ nối với file core/urls.py
    path('', include('core.urls')),
]

# 3. Cấu hình load file tĩnh (CSS/JS/Ảnh) khi chạy thử (DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
