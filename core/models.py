from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

# ==============================================================================
# 1. BẢNG CƠ SỞ / NHÀ HÀNG / KHO HÀNG (RESTAURANT và LOGISTICS HUB)
# ==============================================================================


class KhoHang(models.Model):
    chu_so_huu = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='cac_quan_an', verbose_name="Chủ quán / Đối tác B2B")
    ten_kho = models.CharField(max_length=100, verbose_name="Tên Quán Ăn / Nhà Hàng / Chi Nhánh")
    dia_chi = models.CharField(max_length=200, verbose_name="Địa chỉ")
    lat = models.FloatField(help_text="Vĩ độ (Latitude)")
    lng = models.FloatField(help_text="Kinh độ (Longitude)")
    suc_chua_toi_da = models.IntegerField(default=100, verbose_name="Công suất phục vụ tối đa (Đơn/ngày)")
    loai_hinh = models.CharField(max_length=50, default='Quán ăn ẩm thực', verbose_name="Loại hình cơ sở")
    hinh_anh = models.CharField(max_length=500, blank=True, null=True, default='', verbose_name="Ảnh đại diện quán/bếp")
    danh_gia = models.FloatField(default=4.8, verbose_name="Điểm đánh giá sao")
    thoi_gian_mo_cua = models.CharField(max_length=100, default='07:00 - 22:30', verbose_name="Giờ mở cửa")
    hotline = models.CharField(max_length=20, default='1900 6868', verbose_name="Hotline liên hệ")

    class Meta:
        verbose_name = "Quán ăn / Nhà hàng đối tác B2B"
        verbose_name_plural = "Danh sách Quán ăn / Nhà hàng B2B"

    def __str__(self):
        return self.ten_kho

    def so_don_dang_luu_tru(self):
        """Hàm đếm số đơn hàng đang được chế biến / chờ giao của quán"""
        return self.donhang_set.exclude(trang_thai__in=['ĐÃ GIAO THÀNH CÔNG', 'HỦY', 'ĐÃ HỦY']).count()


# ==============================================================================
# 2. DANH MỤC MÓN ĂN và THỰC ĐƠN (FOOD CATEGORIES)
# ==============================================================================
class DanhMucMonAn(models.Model):
    ten_danh_muc = models.CharField(max_length=100, verbose_name="Tên danh mục")
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    icon = models.CharField(max_length=50, default='fa-bowl-rice', verbose_name="FontAwesome Icon")
    hinh_anh = models.CharField(max_length=500, blank=True, null=True, verbose_name="Ảnh danh mục")
    thu_tu = models.IntegerField(default=0, verbose_name="Thứ tự hiển thị")

    class Meta:
        verbose_name = "Danh mục món ăn"
        verbose_name_plural = "Danh mục món ăn"
        ordering = ['thu_tu', 'id']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.ten_danh_muc)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.ten_danh_muc


# ==============================================================================
# 3. BẢNG MÓN ĂN / THỰC ĐƠN TRỰC TUYẾN (FOOD MENU ITEMS)
# ==============================================================================
class MonAn(models.Model):
    danh_muc = models.ForeignKey(DanhMucMonAn, on_delete=models.CASCADE,
                                 related_name='mon_ans', verbose_name="Danh mục")
    kho_hang = models.ForeignKey(KhoHang, on_delete=models.CASCADE, related_name='thuc_don',
                                 null=True, blank=True, verbose_name="Quán / Bếp chế biến")
    ten_mon = models.CharField(max_length=150, verbose_name="Tên món ăn")
    mo_ta = models.TextField(blank=True, default='', verbose_name="Mô tả món ăn")
    gia = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Giá bán gốc (VNĐ)")
    gia_khuyen_mai = models.DecimalField(max_digits=12, decimal_places=0, null=True,
                                         blank=True, verbose_name="Giá khuyến mãi (VNĐ)")
    hinh_anh = models.CharField(max_length=500, verbose_name="Link ảnh món ăn")
    so_luong_con_lai = models.IntegerField(default=99, verbose_name="Số lượng còn lại")
    da_ban = models.IntegerField(default=0, verbose_name="Số lượng đã bán")
    danh_gia = models.FloatField(default=4.9, verbose_name="Điểm đánh giá")
    thoi_gian_chuan_bi = models.IntegerField(default=15, verbose_name="Thời gian chuẩn bị (Phút)")
    is_noi_bat = models.BooleanField(default=False, verbose_name="Món Best Seller / Nổi bật")
    is_hoa_toc = models.BooleanField(default=True, verbose_name="Hỗ trợ giao hỏa tốc")
    is_con_mon = models.BooleanField(default=True, verbose_name="Đang phục vụ")

    class Meta:
        verbose_name = "Món ăn"
        verbose_name_plural = "Thực đơn món ăn"
        ordering = ['-is_noi_bat', '-da_ban', 'id']

    def __str__(self):
        return f"{self.ten_mon} - {self.gia:,.0f}đ"

    def gia_hien_tai(self):
        """Lấy giá bán thực tế (nếu có khuyến mãi thì ưu tiên)"""
        return self.gia_khuyen_mai if self.gia_khuyen_mai and self.gia_khuyen_mai > 0 else self.gia

    def phan_tram_giam_gia(self):
        if self.gia_khuyen_mai and self.gia_khuyen_mai < self.gia:
            return int(((self.gia - self.gia_khuyen_mai) / self.gia) * 100)
        return 0


# ==============================================================================
# 4. BẢNG QUẢNG CÁO và ADS TMĐT (ADS và REVENUE ENGINE)
# ==============================================================================
class QuangCao(models.Model):
    LOAI_ADS_CHOICES = [
        ('BANNER_CHINH', 'Banner chính slider (Hero Banner)'),
        ('BANNER_PHU', 'Banner khuyến mãi phụ'),
        ('POPUP_SALE', 'Popup Flash Sale khuyến mãi'),
        ('ADS_SPONSOR', 'Tài trợ đối tác B2B (Doanh thu Ads)'),
    ]

    tieu_de = models.CharField(max_length=200, verbose_name="Tiêu đề quảng cáo")
    mo_ta = models.CharField(max_length=300, blank=True, verbose_name="Mô tả / Slogan")
    hinh_anh = models.CharField(max_length=500, verbose_name="Link hình ảnh quảng cáo")
    loai_quang_cao = models.CharField(max_length=50, choices=LOAI_ADS_CHOICES,
                                      default='BANNER_CHINH', verbose_name="Loại quảng cáo")
    lien_ket = models.CharField(max_length=200, default='#', verbose_name="Liên kết chuyển hướng")
    ma_voucher = models.CharField(max_length=50, blank=True, default='', verbose_name="Mã giảm giá kèm theo")
    giam_gia_phan_tram = models.IntegerField(default=0, verbose_name="Giảm giá %")
    doanh_thu_ads = models.DecimalField(max_digits=12, decimal_places=0, default=500000,
                                        verbose_name="Doanh thu quảng cáo thu từ đối tác (VNĐ)")
    kich_hoat = models.BooleanField(default=True, verbose_name="Kích hoạt hiển thị")
    thu_tu = models.IntegerField(default=0, verbose_name="Thứ tự hiển thị")

    class Meta:
        verbose_name = "Quảng cáo và Banner"
        verbose_name_plural = "Quảng cáo và Ads TMĐT"
        ordering = ['thu_tu', 'id']

    def __str__(self):
        return f"[{self.get_loai_quang_cao_display()}] {self.tieu_de}"


# ==============================================================================
# 5. BẢNG TÀI XẾ / SHIPPER (CÓ GPS VỊ TRÍ THỰC TẾ)
# ==============================================================================
class TaiXe(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True,
                                blank=True, verbose_name="Tài khoản đăng nhập")
    ten_tai_xe = models.CharField(max_length=100, verbose_name="Họ tên tài xế")
    sdt = models.CharField(max_length=15, verbose_name="Số điện thoại")
    bien_so = models.CharField(max_length=20, verbose_name="Biển số xe")

    loai_xe = models.CharField(max_length=50, choices=[
        ('Xe máy', 'Xe máy'),
        ('Xe tải', 'Xe tải'),
        ('Xe bán tải', 'Xe bán tải')
    ], default='Xe máy', verbose_name="Loại phương tiện")

    trang_thai = models.CharField(max_length=20, default='Sẵn sàng', verbose_name="Trạng thái hoạt động")

    CA_LAM_CHOICES = [
        ('SANG', 'Ca Sáng (6h - 14h)'),
        ('CHIEU', 'Ca Chiều (14h - 22h)'),
        ('TOI', 'Ca Tối (14h - 22h)'),
        ('DEM', 'Ca Đêm (22h - 6h)'),
    ]
    ca_lam_viec = models.CharField(max_length=10, choices=CA_LAM_CHOICES, default='SANG', verbose_name="Ca làm việc")
    dang_lam_viec = models.BooleanField(default=False, verbose_name="Đang Online (Chấm công)")

    tong_don_thang_nay = models.IntegerField(default=0, verbose_name="KPI Số đơn/Tháng")
    doanh_thu_tich_luy = models.DecimalField(max_digits=15, decimal_places=0,
                                             default=0, verbose_name="Doanh thu tích lũy")

    # 👇 TỌA ĐỘ GPS THỰC TẾ CỦA SHIPPER ĐỂ HIỂN THỊ TRÊN LEAFLET MAP 👇
    lat_hien_tai = models.FloatField(default=10.7769, verbose_name="Vĩ độ GPS hiện tại")
    lng_hien_tai = models.FloatField(default=106.7009, verbose_name="Kinh độ GPS hiện tại")
    cap_nhat_gps_luc = models.DateTimeField(auto_now=True, verbose_name="Thời điểm cập nhật GPS")

    def __str__(self):
        return f"{self.ten_tai_xe} ({self.loai_xe}) - {self.get_ca_lam_viec_display()}"


# ==============================================================================
# 6. BẢNG ĐƠN HÀNG (HỖ TRỢ ĐẶT MÓN, GIAO HỎA TỐC, TMĐT và THANH TOÁN QR)
# ==============================================================================
class DonHang(models.Model):
    khach_hang = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='don_hang_cua_khach', verbose_name="Tài khoản khách đặt")
    ma_don = models.CharField(max_length=20, unique=True, blank=True, verbose_name="Mã đơn hàng")
    ten_nguoi_nhan = models.CharField(max_length=100, verbose_name="Tên người nhận")
    dia_chi_nguoi_nhan = models.CharField(max_length=200, verbose_name="Địa chỉ giao hàng")
    sdt_nguoi_nhan = models.CharField(max_length=15, verbose_name="Số điện thoại")
    email_nguoi_nhan = models.CharField(max_length=100, blank=True,
                                        default='khachhang_test@gmail.com', verbose_name="Email nhận thông báo Mailbox")

    # Tọa độ khách hàng
    lat_khach = models.FloatField(verbose_name="Vĩ độ khách")
    lng_khach = models.FloatField(verbose_name="Kinh độ khách")
    khoi_luong = models.FloatField(default=1.0, help_text="Đơn vị: kg", verbose_name="Khối lượng (kg)")

    # Liên kết với Quán/Kho và Tài xế
    kho_xuat_phat = models.ForeignKey(KhoHang, on_delete=models.CASCADE, verbose_name="Bếp / Quán xuất phát")
    tai_xe = models.ForeignKey(TaiXe, on_delete=models.SET_NULL, null=True,
                               blank=True, verbose_name="Shipper điều phối")

    # Nghiệp vụ trạng thái giữ nguyên theo hệ thống cũ
    trang_thai = models.CharField(max_length=50, default='CHỜ TÀI XẾ', verbose_name="Trạng thái đơn hàng")
    ngay_tao = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạo đơn")
    ghi_chu = models.TextField(blank=True, default='', verbose_name="Ghi chú món ăn / Lưu ý giao hàng")

    # NGHIỆP VỤ GIAO HÀNG HỎA TỐC (LẤY TỪ THUẬT TOÁN ĐƯỜNG ĐI NHANH NHẤT)
    LOAI_GIAO_CHOICES = [
        ('HOA_TOC', '⚡ Giao Hỏa Tốc (15-25 phút - Ưu tiên tuyến đường nhanh nhất)'),
        ('TIEU_CHUAN', '🛵 Giao Tiêu Chuẩn (30-45 phút)'),
    ]
    loai_giao_hang = models.CharField(max_length=30, choices=LOAI_GIAO_CHOICES,
                                      default='HOA_TOC', verbose_name="Phương thức vận chuyển")

    # NGHIỆP VỤ TMĐT và TÍNH TIỀN THEO TỔNG ĐƯỜNG ĐI
    tien_mon_an = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Tiền món ăn (VNĐ)")
    phi_van_chuyen = models.DecimalField(max_digits=12, decimal_places=0, default=15000,
                                         verbose_name="Cước phí vận chuyển tính theo km (VNĐ)")
    phu_phi_hoa_toc = models.DecimalField(max_digits=12, decimal_places=0,
                                          default=0, verbose_name="Phụ phí hỏa tốc (VNĐ)")
    khoang_cach_km = models.FloatField(default=2.5, verbose_name="Khoảng cách tính phí (km)")
    giam_gia = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Giảm giá voucher (VNĐ)")
    tong_tien = models.DecimalField(max_digits=12, decimal_places=0, default=0,
                                    verbose_name="Tổng tiền thanh toán (VNĐ)")

    # NGHIỆP VỤ THANH TOÁN QR và PHƯƠNG THỨC TMĐT
    PT_THANH_TOAN_CHOICES = [
        ('QR_VIETQR', 'Mã QR Ngân Hàng (VietQR)'),
        ('MOMO', 'Ví điện tử MoMo'),
        ('COD', 'Tiền mặt khi nhận hàng (COD)'),
    ]
    phuong_thuc_thanh_toan = models.CharField(
        max_length=30, choices=PT_THANH_TOAN_CHOICES, default='QR_VIETQR', verbose_name="Phương thức thanh toán")

    TT_THANH_TOAN_CHOICES = [
        ('CHUA_THANH_TOAN', 'Chờ thanh toán'),
        ('DA_THANH_TOAN', 'Đã thanh toán thành công'),
    ]
    trang_thai_thanh_toan = models.CharField(
        max_length=30, choices=TT_THANH_TOAN_CHOICES, default='CHUA_THANH_TOAN', verbose_name="Trạng thái thanh toán")
    ma_giao_dich_qr = models.CharField(max_length=50, blank=True, default='',
                                       verbose_name="Mã giao dịch / Mã QR thanh toán")

    # NGHIỆP VỤ THU NHẬP SHIPPER VÀ THUẾ NỀN TẢNG
    thue_phi_san = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name="Thuế TNCN và Phí sàn khấu trừ (VNĐ)"
    )
    tien_shipper_thuc_nhan = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        verbose_name="Tiền Shipper thực nhận sau thuế (VNĐ)"
    )
    TT_THANH_TOAN_SHIPPER_CHOICES = [
        ('CHO_NHAN_TIEN', 'Chờ nhận tiền hàng (Đã trừ thuế)'),
        ('DA_NHAN_TIEN', 'Đã quyết toán vào ví'),
    ]
    trang_thai_thanh_toan_shipper = models.CharField(
        max_length=30, choices=TT_THANH_TOAN_SHIPPER_CHOICES,
        default='CHO_NHAN_TIEN', verbose_name="Trạng thái nhận tiền của Shipper"
    )

    def save(self, *args, **kwargs):
        # TỰ ĐỘNG TẠO MÃ ĐƠN HÀNG (VD: DH001, DH002...)
        if not self.ma_don:
            last_order = DonHang.objects.all().order_by('id').last()
            if not last_order:
                self.ma_don = 'DH001'
            else:
                try:
                    last_num = int(last_order.ma_don[2:])
                    self.ma_don = f'DH{last_num + 1:03d}'
                except (ValueError, TypeError):
                    self.ma_don = f'DH{DonHang.objects.count() + 1:03d}'

        # TỰ ĐỘNG TÍNH TỔNG TIỀN NẾU CHƯA CÓ
        if not self.tong_tien or self.tong_tien == 0:
            self.tong_tien = max(0, self.tien_mon_an + self.phi_van_chuyen + self.phu_phi_hoa_toc - self.giam_gia)

        # TỰ ĐỘNG TÍNH THUẾ VÀ TIỀN THỰC NHẬN CỦA SHIPPER (10% THUẾ/PHÍ NỀN TẢNG)
        tong_cuoc_ship = (self.phi_van_chuyen or 0) + (self.phu_phi_hoa_toc or 0)
        if not self.thue_phi_san or self.thue_phi_san == 0:
            self.thue_phi_san = round(Decimal(tong_cuoc_ship) * Decimal('0.10'))
        if not self.tien_shipper_thuc_nhan or self.tien_shipper_thuc_nhan == 0:
            self.tien_shipper_thuc_nhan = max(Decimal(0), Decimal(tong_cuoc_ship) - self.thue_phi_san)

        super(DonHang, self).save(*args, **kwargs)

    def __str__(self):
        return f"Đơn {self.ma_don} - {self.ten_nguoi_nhan} ({self.trang_thai})"

    def link_qr_vietqr(self):
        """Tạo link mã QR VietQR động thanh toán trực tiếp qua ngân hàng"""
        # Format VietQR: https://img.vietqr.io/image/<BANK_ID>-<ACCOUNT_NO>-<TEMPLATE>.png?amount=<AMOUNT>&addInfo=<INFO>
        bank_id = "MB"
        account_no = "0345678999"
        template = "compact2"
        amount = int(self.tong_tien) if self.tong_tien else 50000
        info = f"THANH TOAN DON {self.ma_don}"
        return f"https://img.vietqr.io/image/{bank_id}-{account_no}-{template}.png?amount={amount}&addInfo={info}&accountName=FOODDELIVERY"


# ==============================================================================
# 7. CHI TIẾT CÁC MÓN TRONG ĐƠN HÀNG (ORDER ITEMS)
# ==============================================================================
class ChiTietDonHang(models.Model):
    don_hang = models.ForeignKey(DonHang, on_delete=models.CASCADE,
                                 related_name='chi_tiet_mon', verbose_name="Đơn hàng")
    mon_an = models.ForeignKey(MonAn, on_delete=models.CASCADE, verbose_name="Món ăn")
    so_luong = models.IntegerField(default=1, verbose_name="Số lượng")
    don_gia = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Đơn giá (VNĐ)")
    thanh_tien = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Thành tiền (VNĐ)")
    ghi_chu_mon = models.CharField(max_length=200, blank=True, default='', verbose_name="Yêu cầu cụ thể")

    def save(self, *args, **kwargs):
        self.thanh_tien = self.so_luong * self.don_gia
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.mon_an.ten_mon} x {self.so_luong}"


# ==============================================================================
# 8. BẢNG LỊCH SỬ LUÂN CHUYỂN / NHẬT KÝ ĐƠN HÀNG (TRACKING LOG)
# ==============================================================================
class LichSuKho(models.Model):
    TRANG_THAI_CHOICES = [
        ('BẾP TIẾP NHẬN', 'Bếp tiếp nhận đơn đặt món'),
        ('BẾP ĐANG NẤU', 'Bếp đang chế biến món ăn'),
        ('CHẾ BIẾN HOÀN TẤT', 'Bếp hoàn tất & Đóng gói món'),
        ('BÀN GIAO SHIPPER', 'Bàn giao Shipper lấy món'),
        ('ĐANG GIAO HỎA TỐC', 'Shipper đang giao hàng hỏa tốc'),
        ('GIAO THÀNH CÔNG', 'Giao hàng thành công'),
        ('GIAO THẤT BẠI', 'Giao hàng thất bại / Hủy'),
        ('ADMIN CẬP NHẬT', 'Admin điều phối hệ thống'),
        # Tương thích bản ghi cũ
        ('NHẬP KHO', 'Bếp tiếp nhận (Cũ)'),
        ('XUẤT KHO', 'Bếp hoàn tất (Cũ)'),
        ('ĐANG PHÂN LOẠI', 'Đang đóng gói (Cũ)'),
        ('ĐANG LUÂN CHUYỂN', 'Đang vận chuyển (Cũ)'),
    ]
    don_hang = models.ForeignKey(DonHang, on_delete=models.CASCADE, related_name='lich_su_kho')
    kho = models.ForeignKey(KhoHang, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Quán ăn / Bếp chế biến")
    trang_thai_buoc = models.CharField(
        max_length=100,
        choices=TRANG_THAI_CHOICES,
        default='BẾP TIẾP NHẬN'
    )
    thoi_gian = models.DateTimeField(auto_now_add=True)
    ghi_chu = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Nhật ký chế biến & Vận chuyển món"
        verbose_name_plural = "Nhật ký chế biến & Vận chuyển món"
        ordering = ['-thoi_gian']

    def __str__(self):
        return f"{self.don_hang.ma_don} - {self.trang_thai_buoc}"


# ==============================================================================
# 9. ĐÁNH GIÁ & PHẢN HỒI ĐƠN HÀNG (CUSTOMER REVIEWS & RATINGS)
# ==============================================================================
class DanhGiaDonHang(models.Model):
    don_hang = models.ForeignKey(DonHang, on_delete=models.CASCADE, related_name='danh_gia_list', verbose_name="Đơn hàng")
    ten_khach = models.CharField(max_length=100, blank=True, default='', verbose_name="Họ tên người đánh giá")
    so_sao = models.IntegerField(default=5, verbose_name="Số sao chung (1-5)")
    nhan_xet = models.TextField(blank=True, default='', verbose_name="Nội dung đánh giá chung")
    
    # ĐÁNH GIÁ KÉP: SHIPPER VÀ MÓN ĂN
    so_sao_shipper = models.IntegerField(default=5, verbose_name="Số sao Shipper (1-5)")
    nhan_xet_shipper = models.TextField(blank=True, default='', verbose_name="Nhận xét Shipper")
    so_sao_mon = models.IntegerField(default=5, verbose_name="Số sao Món ăn (1-5)")
    nhan_xet_mon = models.TextField(blank=True, default='', verbose_name="Nhận xét Món ăn")

    mon_an = models.ForeignKey(MonAn, on_delete=models.SET_NULL, null=True, blank=True, related_name='danh_gia_mon', verbose_name="Món ăn đánh giá")
    ngay_tao = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian đánh giá")

    class Meta:
        ordering = ['-ngay_tao']
        verbose_name = "Đánh giá đơn hàng"
        verbose_name_plural = "Đánh giá đơn hàng"

    def __str__(self):
        return f"Đánh giá Đơn {self.don_hang.ma_don} - Shipper: {self.so_sao_shipper}★, Món: {self.so_sao_mon}★"

