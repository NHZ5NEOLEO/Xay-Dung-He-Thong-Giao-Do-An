from rest_framework import serializers
from .models import DonHang, MonAn, DanhMucMonAn, KhoHang, ChiTietDonHang, TaiXe

# Serializer cơ bản giữ nguyên theo format cũ của nhóm bạn


class DonHangSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonHang
        fields = [
            'id',
            'ma_don',
            'ten_nguoi_nhan',
            'sdt_nguoi_nhan',
            'dia_chi_nguoi_nhan',
            'email_nguoi_nhan',
            'lat_khach',
            'lng_khach',
            'khoi_luong',
            'kho_xuat_phat',
            'loai_giao_hang',
            'tien_mon_an',
            'phi_van_chuyen',
            'phu_phi_hoa_toc',
            'tong_tien',
            'ghi_chu',
            'trang_thai',
            'trang_thai_thanh_toan',
            'phuong_thuc_thanh_toan',
            'ngay_tao'
        ]
        read_only_fields = ['id', 'ma_don', 'ngay_tao']


class DanhMucMonAnSerializer(serializers.ModelSerializer):
    class Meta:
        model = DanhMucMonAn
        fields = ['id', 'ten_danh_muc', 'slug', 'icon', 'thu_tu']


class KhoHangSerializer(serializers.ModelSerializer):
    class Meta:
        model = KhoHang
        fields = '__all__'


class MonAnSerializer(serializers.ModelSerializer):
    danh_muc_ten = serializers.ReadOnlyField(source='danh_muc.ten_danh_muc')
    kho_hang_ten = serializers.ReadOnlyField(source='kho_hang.ten_kho')
    gia_hien_tai = serializers.ReadOnlyField()

    class Meta:
        model = MonAn
        fields = [
            'id', 'ten_mon', 'danh_muc', 'danh_muc_ten', 'kho_hang', 'kho_hang_ten',
            'gia', 'gia_khuyen_mai', 'gia_hien_tai', 'mo_ta', 'hinh_anh',
            'danh_gia', 'da_ban', 'thoi_gian_chuan_bi', 'is_noi_bat', 'is_hoa_toc', 'is_con_mon'
        ]


class ChiTietDonHangSerializer(serializers.ModelSerializer):
    ten_mon = serializers.ReadOnlyField(source='mon_an.ten_mon')

    class Meta:
        model = ChiTietDonHang
        fields = ['id', 'mon_an', 'ten_mon', 'so_luong', 'don_gia', 'thanh_tien', 'ghi_chu_mon']


class B2BTaoDonHangSerializer(serializers.Serializer):
    """API chuẩn B2B dành cho các đối tác TMĐT (ShopeeFood, Grab, TikTok) đẩy đơn vào hệ thống"""
    ten_nguoi_nhan = serializers.CharField(max_length=100)
    sdt_nguoi_nhan = serializers.CharField(max_length=15)
    email_nguoi_nhan = serializers.EmailField(required=False, default='khachhang_test@gmail.com')
    dia_chi_nguoi_nhan = serializers.CharField(max_length=200)
    lat_khach = serializers.FloatField()
    lng_khach = serializers.FloatField()
    kho_id = serializers.IntegerField(required=False)
    loai_giao_hang = serializers.ChoiceField(choices=['HOA_TOC', 'TIEU_CHUAN'], default='HOA_TOC')
    ghi_chu = serializers.CharField(required=False, allow_blank=True, default='')
    ma_voucher = serializers.CharField(required=False, allow_blank=True, default='')
    danh_sach_mon = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text="Danh sách món: [{'mon_id': 1, 'so_luong': 2}]"
    )


class TaiXeGPSSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaiXe
        fields = ['id', 'ten_tai_xe', 'sdt', 'bien_so', 'lat_hien_tai', 'lng_hien_tai', 'cap_nhat_gps_luc']
