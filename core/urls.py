from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # 1. Trang chủ (Hero Carousel, Thực đơn nổi bật, TMĐT Doanh thu, Dashboard)
    path('', views.home, name='home'),

    # 2. Nghiệp vụ Thực đơn, Đặt món trực tuyến và Giỏ hàng
    path('thuc-don/', views.thuc_don, name='thuc_don'),
    path('menu/', views.thuc_don, name='menu_alias'),
    path('dat-mon/checkout/', views.checkout_view, name='checkout'),
    path('checkout/', views.checkout_view, name='checkout_alias'),
    path('dat-mon/xac-nhan/', views.tao_don_hang_mon_an, name='tao_don_hang_mon_an'),
    path('don-hang/xac-nhan-thanh-toan/<str:ma_don>/', views.xac_nhan_thanh_toan_don, name='xac_nhan_thanh_toan'),
    path('don-hang-cua-toi/', views.lich_su_don_hang, name='lich_su_don_hang'),
    path('my-orders/', views.lich_su_don_hang, name='my_orders_alias'),

    # 3. Bản đồ GIS và Chi tiết lộ trình đơn hàng & Đánh giá
    path('map/', views.ban_do_chung, name='ban_do_chung'),
    path('gis/', views.ban_do_chung, name='gis_alias'),
    path('ban-do/', views.ban_do_chung, name='ban_do_alias'),
    path('chi-tiet/<str:ma_don>/', views.chi_tiet, name='chi_tiet'),
    path('chi-tiet/<str:ma_don>/danh-gia/', views.gui_danh_gia, name='gui_danh_gia'),
    path('danh-gia/<str:ma_don>/', views.gui_danh_gia, name='gui_danh_gia_alias'),
    path('toi-uu-lo-trinh/', views.toi_uu_lo_trinh, name='toi_uu'),

    # 4. Quản lý Tài xế
    path('quan-ly-tai-xe/', views.quan_ly_tai_xe, name='quan_ly_tai_xe'),
    path('them-tai-xe/', views.them_tai_xe, name='them_tai_xe'),
    path('sua-tai-xe/<int:id>/', views.sua_tai_xe, name='sua_tai_xe'),
    path('xoa-tai-xe/<int:id>/', views.xoa_tai_xe, name='xoa_tai_xe'),

    # 5. Quản lý Cơ sở / Bếp / Kho
    path('quan-ly-kho/', views.quan_ly_kho, name='quan_ly_kho'),
    path('them-kho/', views.them_kho, name='them_kho'),
    path('sua-kho/<int:id>/', views.sua_kho, name='sua_kho'),
    path('xoa-kho/<int:id>/', views.xoa_kho, name='xoa_kho'),

    # 6. Quản lý Đơn hàng
    path('quan-ly-don-hang/', views.quan_ly_don_hang, name='quan_ly_don_hang'),
    path('them-don-hang/', views.them_don_hang, name='them_don_hang'),
    path('sua-don-hang/<int:id>/', views.sua_don_hang, name='sua_don_hang'),
    path('xoa-don-hang/<int:id>/', views.xoa_don_hang, name='xoa_don_hang'),

    # 7. Dashboard Báo Cáo Thống Kê Chuyên Sâu & Admin Portal
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('api/admin/don-hang/<int:don_id>/quick-update/', views.api_admin_quick_update_don_hang, name='api_admin_quick_update_don_hang'),
    path('api/admin/don-hang/<int:don_id>/dieu-phoi-shipper/', views.api_admin_dieu_phoi_shipper, name='api_admin_dieu_phoi_shipper'),
    path('api/admin/dieu-phoi-tat-ca/', views.api_admin_dieu_phoi_tat_ca, name='api_admin_dieu_phoi_tat_ca'),
    path('api/admin/don-hang/quick-create/', views.api_admin_quick_create_don_hang, name='api_admin_quick_create_don_hang'),
    path('admin-dashboard/mon-an/', views.admin_quan_ly_mon_an, name='admin_quan_ly_mon_an'),
    path('api/admin/mon-an/<int:mon_id>/toggle-status/', views.api_admin_toggle_mon_an, name='api_admin_toggle_mon_an'),
    path('admin-dashboard/mon-an/them/', views.admin_them_mon_an, name='admin_them_mon_an'),
    path('admin-dashboard/mon-an/sua/<int:id>/', views.admin_sua_mon_an, name='admin_sua_mon_an'),
    path('admin-dashboard/mon-an/xoa/<int:id>/', views.admin_xoa_mon_an, name='admin_xoa_mon_an'),

    # 8. Đăng nhập / Đăng xuất / Đăng ký / Quên mật khẩu
    path('login/', views.dang_nhap, name='login'),
    path('logout/', views.dang_xuat, name='logout'),
    path('dang-ky/', views.dang_ky, name='dang_ky'),
    path('register/', views.dang_ky, name='register_alias'),
    path('quen-mat-khau/', views.quen_mat_khau, name='quen_mat_khau'),
    path('forgot-password/', views.quen_mat_khau, name='forgot_password_alias'),

    # 8. App Shipper di động
    path('app-shipper/', views.app_shipper, name='app_shipper'),
    path('shipper/', views.app_shipper, name='shipper_alias'),
    path('shipper-cap-nhat/<int:don_id>/', views.shipper_cap_nhat, name='shipper_cap_nhat'),
    path('shipper/don-hang/<int:don_id>/cap-nhat/', views.shipper_cap_nhat, name='shipper_cap_nhat_alias'),

    # 9. Quản lý Tài khoản và Phân quyền
    path('quan-ly-tai-khoan/', views.quan_ly_tai_khoan, name='quan_ly_tai_khoan'),
    path('them-tai-khoan/', views.them_tai_khoan, name='them_tai_khoan'),
    path('sua-tai-khoan/<int:id>/', views.sua_tai_khoan, name='sua_tai_khoan'),
    path('xoa-tai-khoan/<int:id>/', views.xoa_tai_khoan, name='xoa_tai_khoan'),

    # 10. Quản lý Lịch sử luân chuyển và Xuất Excel
    path('quan-ly-lich-su/', views.quan_ly_lich_su, name='quan_ly_lich_su'),
    path('quan-ly-lich-su/them/', views.them_lich_su, name='them_lich_su'),
    path('quan-ly-lich-su/xoa/<int:id>/', views.xoa_lich_su, name='xoa_lich_su'),
    path('export-excel/', views.export_excel, name='export_excel'),

    # 11. Cổng đối tác B2B (Quán Ăn / Nhà Hàng) và Webhook
    path('partner-dashboard/', views.partner_dashboard, name='partner_dashboard'),
    path('b2b-dashboard/', views.partner_dashboard, name='b2b_dashboard_alias'),
    path('partner-demo/', views.partner_demo_tao_don, name='partner_demo'),

    # 12. CÁC API RESTFUL (KHÁCH ĐẶT MÓN + B2B MENU SYNC + SHIPPER GPS + REALTIME)
    path('api/tao-don-hang/', views.api_tao_don_hang, name='api_tao_don_hang'),
    path('api/don-hang/tao/', views.api_tao_don_hang, name='api_don_hang_tao'),
    path('api/b2b/don-hang/tao/', views.api_tao_don_hang, name='api_b2b_don_hang_tao'),
    path('api/b2b/tao-don/', views.api_tao_don_hang, name='api_b2b_tao_don'),
    path('api/b2b/thuc-don/', views.api_b2b_thuc_don, name='api_b2b_thuc_don'),
    path('api/b2b/thuc-don/cap-nhat/', views.api_b2b_cap_nhat_mon, name='api_b2b_cap_nhat_mon'),
    path('api/b2b/don-hang/<int:don_id>/cap-nhat-bep/', views.api_b2b_bep_cap_nhat_don, name='api_b2b_bep_cap_nhat_don'),
    path('api/mon-an/', views.api_danh_sach_mon, name='api_danh_sach_mon'),
    path('api/shipper/cap-nhat-gps/', views.api_cap_nhat_gps_shipper, name='api_cap_nhat_gps_shipper'),
    path('api/tinh-phi-ship/', views.api_tinh_phi_van_chuyen, name='api_tinh_phi_van_chuyen'),
    path('api/tinh-phi-van-chuyen/', views.api_tinh_phi_van_chuyen, name='api_tinh_phi_van_chuyen_alias'),
    path('api/check-new-orders/', views.check_new_orders, name='check_new_orders'),
    path('api/don-hang/<str:ma_don>/items/', views.api_don_hang_items, name='api_don_hang_items'),
    path('api/vouchers/', views.api_danh_sach_voucher, name='api_danh_sach_voucher'),
]
