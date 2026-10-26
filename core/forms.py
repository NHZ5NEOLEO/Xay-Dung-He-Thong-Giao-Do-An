from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import TaiXe, KhoHang, DonHang, LichSuKho, MonAn, DanhMucMonAn, QuangCao

# 1. Form cho Tài xế


class TaiXeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['user', 'trang_thai', 'lat_hien_tai', 'lng_hien_tai', 'doanh_thu_tich_luy', 'tong_don_thang_nay', 'loai_xe', 'ca_lam_viec', 'dang_lam_viec']:
            if field in self.fields:
                self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('trang_thai'):
            cleaned_data['trang_thai'] = 'Sẵn sàng'
        if not cleaned_data.get('loai_xe'):
            cleaned_data['loai_xe'] = 'Xe máy'
        if not cleaned_data.get('ca_lam_viec'):
            cleaned_data['ca_lam_viec'] = 'SANG'
        if cleaned_data.get('doanh_thu_tich_luy') is None:
            cleaned_data['doanh_thu_tich_luy'] = 0
        if cleaned_data.get('tong_don_thang_nay') is None:
            cleaned_data['tong_don_thang_nay'] = 0
        return cleaned_data

    class Meta:
        model = TaiXe
        fields = '__all__'
        labels = {
            'ten_tai_xe': 'Họ tên Tài xế',
            'sdt': 'Số điện thoại',
            'bien_so': 'Biển số xe',
            'loai_xe': 'Loại phương tiện',
            'trang_thai': 'Trạng thái hoạt động',
            'ca_lam_viec': 'Ca làm việc',
            'dang_lam_viec': 'Chấm công (Đang online)',
            'lat_hien_tai': 'Vĩ độ GPS hiện tại',
            'lng_hien_tai': 'Kinh độ GPS hiện tại',
            'doanh_thu_tich_luy': 'Doanh thu tích lũy',
            'tong_don_thang_nay': 'Tổng đơn tháng này',
        }
        widgets = {
            'ca_lam_viec': forms.Select(attrs={'class': 'form-control'}),
            'loai_xe': forms.Select(attrs={'class': 'form-control'}),
            'ten_tai_xe': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập họ tên...'}),
            'sdt': forms.TextInput(attrs={'class': 'form-control'}),
            'bien_so': forms.TextInput(attrs={'class': 'form-control'}),
            'trang_thai': forms.TextInput(attrs={'class': 'form-control'}),
            'lat_hien_tai': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'lng_hien_tai': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
        }


# 2. Form cho Kho Hàng / Cơ sở Bếp
class KhoHangForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['loai_hinh', 'hinh_anh', 'danh_gia', 'thoi_gian_mo_cua', 'hotline', 'suc_chua_toi_da']:
            if field in self.fields:
                self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('loai_hinh'):
            cleaned_data['loai_hinh'] = 'Quán ăn ẩm thực'
        if cleaned_data.get('danh_gia') is None:
            cleaned_data['danh_gia'] = 4.8
        if not cleaned_data.get('thoi_gian_mo_cua'):
            cleaned_data['thoi_gian_mo_cua'] = '07:00 - 22:30'
        if not cleaned_data.get('hotline'):
            cleaned_data['hotline'] = '1900 6868'
        if cleaned_data.get('suc_chua_toi_da') is None:
            cleaned_data['suc_chua_toi_da'] = 100
        return cleaned_data

    class Meta:
        model = KhoHang
        fields = '__all__'
        labels = {
            'ten_kho': 'Tên Bếp / Quán Ăn / Chi Nhánh',
            'loai_hinh': 'Loại hình cơ sở',
            'dia_chi': 'Địa chỉ',
            'lat': 'Vĩ độ (Lat)',
            'lng': 'Kinh độ (Lng)',
            'suc_chua_toi_da': 'Sức chứa tối đa (Đơn)',
            'hinh_anh': 'Link hình ảnh quán',
            'danh_gia': 'Đánh giá sao (1-5)',
            'thoi_gian_mo_cua': 'Giờ mở cửa',
            'hotline': 'Hotline liên hệ',
        }
        widgets = {
            'ten_kho': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên bếp / quán...'}),
            'loai_hinh': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Quán ẩm thực, Bếp trung tâm...'}),
            'dia_chi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Địa chỉ...'}),
            'lat': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'lng': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'suc_chua_toi_da': forms.NumberInput(attrs={'class': 'form-control'}),
            'hinh_anh': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'danh_gia': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'thoi_gian_mo_cua': forms.TextInput(attrs={'class': 'form-control'}),
            'hotline': forms.TextInput(attrs={'class': 'form-control'}),
        }


# 3. Form cho Món Ăn (Food Item)
class MonAnForm(forms.ModelForm):
    class Meta:
        model = MonAn
        fields = '__all__'
        labels = {
            'ten_mon': 'Tên Món Ăn',
            'danh_muc': 'Danh Mục Món',
            'kho_hang': 'Bếp / Quán Chế Biến',
            'gia': 'Giá Gốc (VNĐ)',
            'gia_khuyen_mai': 'Giá Khuyến Mãi (VNĐ)',
            'mo_ta': 'Mô Tả Chi Tiết',
            'hinh_anh': 'Link Ảnh Món Ăn',
            'thoi_gian_chuan_bi': 'Thời Gian Chuẩn Bị (Phút)',
            'so_luong_con_lai': 'Số Lượng Còn Lại',
            'is_noi_bat': 'Món Bán Chạy / Nổi Bật',
            'is_hoa_toc': 'Hỗ Trợ Giao Hỏa Tốc',
            'is_con_mon': 'Đang Phục Vụ',
        }
        widgets = {
            'ten_mon': forms.TextInput(attrs={'class': 'form-control'}),
            'danh_muc': forms.Select(attrs={'class': 'form-control'}),
            'kho_hang': forms.Select(attrs={'class': 'form-control'}),
            'gia': forms.NumberInput(attrs={'class': 'form-control'}),
            'gia_khuyen_mai': forms.NumberInput(attrs={'class': 'form-control'}),
            'mo_ta': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'hinh_anh': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'thoi_gian_chuan_bi': forms.NumberInput(attrs={'class': 'form-control'}),
            'so_luong_con_lai': forms.NumberInput(attrs={'class': 'form-control'}),
        }


# 4. Form cho Quảng Cáo và Ads TMĐT
class QuangCaoForm(forms.ModelForm):
    class Meta:
        model = QuangCao
        fields = '__all__'
        labels = {
            'tieu_de': 'Tiêu Đề Quảng Cáo',
            'mo_ta': 'Mô Tả / Slogan',
            'hinh_anh': 'Link Hình Ảnh',
            'loai_quang_cao': 'Loại Quảng Cáo',
            'lien_ket': 'Liên Kết Chuyển Hướng',
            'ma_voucher': 'Mã Giảm Giá Kèm Theo',
            'giam_gia_phan_tram': 'Mức Giảm (%)',
            'doanh_thu_ads': 'Doanh Thu Quảng Cáo Thu Từ Đối Tác (VNĐ)',
            'kich_hoat': 'Kích Hoạt',
            'thu_tu': 'Thứ Tự Hiển Thị',
        }
        widgets = {
            'tieu_de': forms.TextInput(attrs={'class': 'form-control'}),
            'mo_ta': forms.TextInput(attrs={'class': 'form-control'}),
            'hinh_anh': forms.TextInput(attrs={'class': 'form-control'}),
            'loai_quang_cao': forms.Select(attrs={'class': 'form-control'}),
            'lien_ket': forms.TextInput(attrs={'class': 'form-control'}),
            'ma_voucher': forms.TextInput(attrs={'class': 'form-control'}),
            'giam_gia_phan_tram': forms.NumberInput(attrs={'class': 'form-control'}),
            'doanh_thu_ads': forms.NumberInput(attrs={'class': 'form-control'}),
            'thu_tu': forms.NumberInput(attrs={'class': 'form-control'}),
        }


# 5. Form cho Danh Mục Món Ăn
class DanhMucMonAnForm(forms.ModelForm):
    class Meta:
        model = DanhMucMonAn
        fields = '__all__'
        labels = {
            'ten_danh_muc': 'Tên Danh Mục',
            'slug': 'Slug Định Danh',
            'icon': 'Icon Biểu Tượng',
            'hinh_anh': 'Link Ảnh Bìa Danh Mục',
            'thu_tu': 'Thứ Tự Hiển Thị',
        }
        widgets = {
            'ten_danh_muc': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'icon': forms.TextInput(attrs={'class': 'form-control'}),
            'hinh_anh': forms.TextInput(attrs={'class': 'form-control'}),
            'thu_tu': forms.NumberInput(attrs={'class': 'form-control'}),
        }


# 6. Form cho Đơn Hàng
class DonHangForm(forms.ModelForm):
    class Meta:
        model = DonHang
        fields = '__all__'
        exclude = ['ngay_tao', 'ma_giao_dich_qr']
        labels = {
            'ma_don': 'Mã Đơn Hàng',
            'ten_nguoi_nhan': 'Tên Khách Hàng',
            'dia_chi_nguoi_nhan': 'Địa Chỉ Giao Hàng',
            'sdt_nguoi_nhan': 'Số Điện Thoại',
            'email_nguoi_nhan': 'Email Nhận Thông Báo (Mailbox)',
            'lat_khach': 'Vĩ độ (Lat)',
            'lng_khach': 'Kinh độ (Lng)',
            'khoi_luong': 'Khối Lượng (kg)',
            'kho_xuat_phat': 'Bếp / Quán Xuất Phát',
            'tai_xe': 'Phân Công Shipper',
            'loai_giao_hang': 'Phương Thức Giao Hàng',
            'tien_mon_an': 'Tiền Món Ăn (VNĐ)',
            'phi_van_chuyen': 'Phí Vận Chuyển Theo KM (VNĐ)',
            'phu_phi_hoa_toc': 'Phụ Phí Hỏa Tốc (VNĐ)',
            'khoang_cach_km': 'Khoảng Cách (km)',
            'giam_gia': 'Giảm Giá (VNĐ)',
            'tong_tien': 'Tổng Thanh Toán (VNĐ)',
            'phuong_thuc_thanh_toan': 'Phương Thức Thanh Toán',
            'trang_thai_thanh_toan': 'Trạng Thái Thanh Toán',
            'trang_thai': 'Trạng Thái Đơn Hàng',
            'ghi_chu': 'Ghi Chú Món Ăn / Giao Hàng',
        }
        widgets = {
            'ma_don': forms.TextInput(attrs={'class': 'form-control'}),
            'ten_nguoi_nhan': forms.TextInput(attrs={'class': 'form-control'}),
            'dia_chi_nguoi_nhan': forms.TextInput(attrs={'class': 'form-control'}),
            'sdt_nguoi_nhan': forms.TextInput(attrs={'class': 'form-control'}),
            'email_nguoi_nhan': forms.EmailInput(attrs={'class': 'form-control'}),
            'lat_khach': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'lng_khach': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'khoi_luong': forms.NumberInput(attrs={'class': 'form-control'}),
            'kho_xuat_phat': forms.Select(attrs={'class': 'form-control'}),
            'tai_xe': forms.Select(attrs={'class': 'form-control'}),
            'loai_giao_hang': forms.Select(attrs={'class': 'form-control'}),
            'tien_mon_an': forms.NumberInput(attrs={'class': 'form-control'}),
            'phi_van_chuyen': forms.NumberInput(attrs={'class': 'form-control'}),
            'phu_phi_hoa_toc': forms.NumberInput(attrs={'class': 'form-control'}),
            'khoang_cach_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'giam_gia': forms.NumberInput(attrs={'class': 'form-control'}),
            'tong_tien': forms.NumberInput(attrs={'class': 'form-control'}),
            'phuong_thuc_thanh_toan': forms.Select(attrs={'class': 'form-control'}),
            'trang_thai_thanh_toan': forms.Select(attrs={'class': 'form-control'}),
            'trang_thai': forms.Select(
                attrs={'class': 'form-control'},
                choices=[
                    ('CHỜ TÀI XẾ', 'Chờ tài xế (Mới tạo)'),
                    ('ĐANG VẬN CHUYỂN', 'Đang vận chuyển hỏa tốc'),
                    ('ĐÃ GIAO THÀNH CÔNG', 'Đã giao thành công'),
                    ('ĐÃ HỦY', 'Đã hủy đơn'),
                    ('TRẢ HÀNG VỀ KHO', 'Trả hàng về quán/bếp'),
                ]
            ),
            'ghi_chu': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            last_order = DonHang.objects.all().order_by('id').last()
            if not last_order:
                next_ma_don = 'DH001'
            else:
                try:
                    last_num = int(last_order.ma_don[2:])
                    next_ma_don = f'DH{last_num + 1:03d}'
                except (ValueError, TypeError):
                    next_ma_don = 'DH001'
            self.fields['ma_don'].initial = next_ma_don

        self.fields['ma_don'].widget.attrs['readonly'] = True
        self.fields['ma_don'].widget.attrs['style'] = 'background-color: #e2e8f0; color: #64748b; cursor: not-allowed; font-weight: bold;'

    def clean(self):
        cleaned_data = super().clean()
        kho_hang = cleaned_data.get('kho_xuat_phat')
        if kho_hang:
            so_luong_hien_tai = kho_hang.so_don_dang_luu_tru()
            if self.instance.pk and self.instance.kho_xuat_phat == kho_hang:
                so_luong_hien_tai -= 1
            if so_luong_hien_tai >= kho_hang.suc_chua_toi_da:
                raise ValidationError(
                    f"⚠️ LỖI: {kho_hang.ten_kho} đã đạt giới hạn sức chứa đơn ({kho_hang.suc_chua_toi_da} đơn). "
                    f"Vui lòng điều phối sang bếp lân cận!"
                )
        return cleaned_data


# 6. Form Tài Khoản (User)
class TaiKhoanForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu mới...'}),
        required=False,
        label="Mật khẩu (Để trống nếu không muốn đổi)"
    )
    is_staff = forms.BooleanField(
        required=False,
        label="Cấp quyền Admin (Tích vào nếu là Quản lý, Bỏ tích nếu là Shipper)"
    )

    class Meta:
        model = User
        fields = ['username', 'is_staff']
        labels = {'username': 'Tên đăng nhập (Viết liền không dấu)'}
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: shipper_tuan'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


# 7. Form Lịch Sử Kho / Lộ Trình
class LichSuKhoForm(forms.ModelForm):
    trang_thai_buoc = forms.CharField(max_length=100, required=True, label='Bước luân chuyển / Tiến độ')

    class Meta:
        model = LichSuKho
        fields = ['don_hang', 'kho', 'trang_thai_buoc', 'ghi_chu']
        labels = {
            'don_hang': 'Đơn hàng',
            'kho': 'Bếp / Quán liên quan',
            'trang_thai_buoc': 'Bước luân chuyển / Tiến độ',
            'ghi_chu': 'Ghi chú chi tiết',
        }
        widgets = {
            'don_hang': forms.Select(attrs={'class': 'form-control'}),
            'kho': forms.Select(attrs={'class': 'form-control'}),
            'trang_thai_buoc': forms.Select(attrs={'class': 'form-control'}),
            'ghi_chu': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ghi chú thêm nếu có...'}),
        }
