from django.contrib import admin
from .models import KhoHang, TaiXe, DonHang, LichSuKho, DanhMucMonAn, MonAn, QuangCao, ChiTietDonHang, DanhGiaDonHang


@admin.register(KhoHang)
class KhoHangAdmin(admin.ModelAdmin):
    list_display = ('ten_kho', 'loai_hinh', 'dia_chi', 'suc_chua_toi_da', 'danh_gia', 'hotline')
    search_fields = ('ten_kho', 'dia_chi')


@admin.register(DanhMucMonAn)
class DanhMucMonAnAdmin(admin.ModelAdmin):
    list_display = ('ten_danh_muc', 'slug', 'icon', 'thu_tu')
    prepopulated_fields = {'slug': ('ten_danh_muc',)}


@admin.register(MonAn)
class MonAnAdmin(admin.ModelAdmin):
    list_display = ('ten_mon', 'danh_muc', 'kho_hang', 'gia', 'gia_khuyen_mai',
                    'so_luong_con_lai', 'da_ban', 'is_noi_bat', 'is_hoa_toc')
    list_filter = ('danh_muc', 'is_noi_bat', 'is_hoa_toc', 'is_con_mon')
    search_fields = ('ten_mon', 'mo_ta')


@admin.register(QuangCao)
class QuangCaoAdmin(admin.ModelAdmin):
    list_display = ('tieu_de', 'loai_quang_cao', 'ma_voucher', 'giam_gia_phan_tram', 'doanh_thu_ads', 'kich_hoat')
    list_filter = ('loai_quang_cao', 'kich_hoat')


class ChiTietDonHangInline(admin.TabularInline):
    model = ChiTietDonHang
    extra = 0


@admin.register(DonHang)
class DonHangAdmin(admin.ModelAdmin):
    list_display = ('ma_don', 'ten_nguoi_nhan', 'sdt_nguoi_nhan', 'loai_giao_hang',
                    'tong_tien', 'trang_thai_thanh_toan', 'trang_thai', 'ngay_tao')
    list_filter = ('trang_thai', 'loai_giao_hang', 'trang_thai_thanh_toan', 'phuong_thuc_thanh_toan')
    search_fields = ('ma_don', 'ten_nguoi_nhan', 'sdt_nguoi_nhan')
    inlines = [ChiTietDonHangInline]


@admin.register(TaiXe)
class TaiXeAdmin(admin.ModelAdmin):
    list_display = ('ten_tai_xe', 'sdt', 'bien_so', 'loai_xe', 'ca_lam_viec',
                    'dang_lam_viec', 'tong_don_thang_nay', 'doanh_thu_tich_luy')
    list_filter = ('loai_xe', 'ca_lam_viec', 'dang_lam_viec')
    search_fields = ('ten_tai_xe', 'sdt', 'bien_so')


@admin.register(LichSuKho)
class LichSuKhoAdmin(admin.ModelAdmin):
    list_display = ('don_hang', 'kho', 'trang_thai_buoc', 'thoi_gian')
    list_filter = ('trang_thai_buoc',)
    search_fields = ('don_hang__ma_don', 'ghi_chu')


@admin.register(DanhGiaDonHang)
class DanhGiaDonHangAdmin(admin.ModelAdmin):
    list_display = ('don_hang', 'ten_khach', 'so_sao', 'ngay_tao')
    list_filter = ('so_sao', 'ngay_tao')
    search_fields = ('don_hang__ma_don', 'ten_khach', 'nhan_xet')
