from django.apps import AppConfig
import sys


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Hệ Thống Đặt Món và Logistics'

    def ready(self):
        # Tự động nạp dữ liệu mẫu nếu bảng món ăn chưa có dữ liệu
        # Chỉ chạy khi chạy lệnh runserver
        if 'runserver' in sys.argv:
            try:
                from .models import MonAn
                from django.core.management import call_command
                if MonAn.objects.count() == 0:
                    print("[AUTO-SEED] Co so du lieu chua co mon an. Tu dong khoi tao du lieu mau...")
                    call_command('seed_data')
            except Exception:
                pass
