import json
import math
import random
import string
import datetime
from decimal import Decimal
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count, Sum
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import openpyxl

# Import Models và Forms từ core
from .models import (
    KhoHang, TaiXe, DonHang, LichSuKho,
    DanhMucMonAn, MonAn, QuangCao, ChiTietDonHang, DanhGiaDonHang
)
from .forms import (
    TaiXeForm, KhoHangForm, DonHangForm, TaiKhoanForm,
    LichSuKhoForm
)
from .serializers import (
    MonAnSerializer, B2BTaoDonHangSerializer
)

# ==============================================================================
# HÀM BỔ TRỢ HỆ THỐNG: TÍNH KHOẢNG CÁCH và GỬI EMAIL MAILBOX
# ==============================================================================


def tinh_khoang_cach_haversine(lat1, lon1, lat2, lon2):
    """Tính khoảng cách đường chim bay giữa 2 tọa độ (km) theo công thức Haversine"""
    try:
        R = 6371.0
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(float(lat1))) * \
            math.cos(math.radians(float(lat2))) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)
    except Exception:
        return 2.5


def tinh_phi_ship_theo_km(khoang_cach_km, is_hoa_toc=True):
    """
    Thuật toán tính cước phí giao hàng:
    - 2km đầu: 15.000đ
    - Các km tiếp theo: 5.000đ/km
    - Phụ phí giao hỏa tốc (nếu chọn): 10.000đ
    """
    base_fee = 15000
    km = max(0.5, float(khoang_cach_km))
    if km <= 2:
        shipping_fee = base_fee
    else:
        shipping_fee = base_fee + int((km - 2) * 5000)

    # Làm tròn tới 1000đ
    shipping_fee = int(round(shipping_fee / 1000) * 1000)
    phu_phi = 10000 if is_hoa_toc else 0
    return shipping_fee, phu_phi


def ap_dung_voucher_nghiep_vu(ma_voucher, tien_mon_an, phi_ship_goc):
    """
    Quy tắc tính toán voucher chuẩn hóa đồng bộ giữa Backend và Frontend:
    - Kiểm tra điều kiện đơn tối thiểu (min_order)
    - Phân loại: FREESHIP (trợ giá vận chuyển) hoặc GIẢM GIÁ MÓN (% tiền món)
    - Áp dụng mức trần giảm tối đa (max_discount)
    - Trả về: (phi_ship_moi, giam_gia_tong, thong_bao_ket_qua)
    """
    code = (ma_voucher or '').strip().upper()
    tien_mon = Decimal(tien_mon_an)
    ship_goc = Decimal(phi_ship_goc)

    # Quy tắc cứng chuẩn TMĐT đồng bộ Frontend:
    rules = {
        'HOATOC50': {'min_order': Decimal(80000), 'percent': Decimal(50), 'max_discount': Decimal(40000), 'type': 'FOOD'},
        'FREESHIP0D': {'min_order': Decimal(100000), 'max_discount': Decimal(30000), 'type': 'FREESHIP'},
        'GONGCHA29K': {'min_order': Decimal(60000), 'percent': Decimal(20), 'max_discount': Decimal(25000), 'type': 'FOOD'},
        'B2BSALE': {'min_order': Decimal(150000), 'percent': Decimal(15), 'max_discount': Decimal(50000), 'type': 'FOOD'},
    }

    # Nếu không nhập mã:
    if not code:
        if tien_mon >= 150000:
            return Decimal(0), ship_goc, "Miễn phí vận chuyển cho đơn từ 150.000đ"
        return ship_goc, Decimal(0), ""

    rule = rules.get(code)
    if not rule:
        v_obj = QuangCao.objects.filter(ma_voucher__iexact=code, kich_hoat=True).first()
        if v_obj:
            is_ship = 'FREESHIP' in code
            rule = {
                'min_order': Decimal(100000 if is_ship else 50000),
                'percent': Decimal(v_obj.giam_gia_phan_tram),
                'max_discount': Decimal(30000),
                'type': 'FREESHIP' if is_ship else 'FOOD'
            }

    if not rule:
        phi_ship = Decimal(0) if tien_mon >= 150000 else ship_goc
        giam_gia = ship_goc if tien_mon >= 150000 else Decimal(0)
        return phi_ship, giam_gia, f"Mã voucher '{code}' không hợp lệ hoặc đã hết hạn."

    # Kiểm tra điều kiện đơn hàng tối thiểu
    if tien_mon < rule['min_order']:
        phi_ship = Decimal(0) if tien_mon >= 150000 else ship_goc
        giam_gia = ship_goc if tien_mon >= 150000 else Decimal(0)
        return phi_ship, giam_gia, f"Mã '{code}' yêu cầu đơn tối thiểu {rule['min_order']:,.0f}đ (hiện có {tien_mon:,.0f}đ)."

    if rule['type'] == 'FREESHIP':
        tro_gia = min(ship_goc, rule['max_discount'])
        phi_ship_moi = max(Decimal(0), ship_goc - tro_gia)
        return phi_ship_moi, tro_gia, f"Áp dụng thành công mã Freeship: Giảm {tro_gia:,.0f}đ phí ship."
    else:
        pct = rule.get('percent', Decimal(0))
        giam_mon = min(rule['max_discount'], Decimal(int(tien_mon * (pct / Decimal(100)))))
        phi_ship_moi = Decimal(0) if tien_mon >= 150000 else ship_goc
        giam_tong = giam_mon + (ship_goc if tien_mon >= 150000 else Decimal(0))
        return phi_ship_moi, giam_tong, f"Áp dụng thành công mã '{code}': Giảm {giam_mon:,.0f}đ."


def gui_email_mailbox(tieu_de, noi_dung, to_email=None):
    """Gửi email thông báo ngầm qua Mailtrap (Mailbox)"""
    try:
        recipient = to_email if to_email else 'khachhang_test@gmail.com'
        send_mail(
            tieu_de,
            noi_dung,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=True
        )
    except Exception as e:
        print(f"[MAILBOX ERROR] Không thể gửi email: {e}")


def tim_quan_an_gan_nhat(lat_khach, lng_khach, max_km=30.0, mon_ids=None):
    """
    Thuật toán tìm kiếm Quán ăn / Chi nhánh B2B gần khách nhất (Nearest Branch Routing):
    - Đề tài giao đồ ăn trực tuyến chỉ có bán kính giao hỏa tốc an toàn <= 30km (xe máy 20-45 phút).
    - Nếu khách chọn nhầm quán ở xa (> 30km), hệ thống tự động quét chi nhánh gần khách nhất để chuyển đơn.
    """
    try:
        ds_quan = KhoHang.objects.all()
        if mon_ids:
            quan_ids = MonAn.objects.filter(id__in=mon_ids, is_con_mon=True).values_list('kho_hang_id', flat=True)
            if quan_ids.exists():
                ds_quan = ds_quan.filter(id__in=quan_ids)

        quan_gan_nhat = None
        min_dist = float('inf')
        for q in ds_quan:
            dist = tinh_khoang_cach_haversine(q.lat, q.lng, lat_khach, lng_khach)
            if dist < min_dist:
                min_dist = dist
                quan_gan_nhat = q

        if min_dist <= max_km and quan_gan_nhat:
            return quan_gan_nhat, min_dist
        return None, min_dist
    except Exception as e:
        print(f"[NEAREST BRANCH ERROR] {e}")
        return KhoHang.objects.first(), 2.5


# ==============================================================================
# 1. HỆ THỐNG XÁC THỰC và ĐIỀU HƯỚNG PHÂN QUYỀN 4 ĐỐI TƯỢNG (AUTHENTICATION)
# ==============================================================================

def _redirect_theo_vai_tro(request, user):
    """
    Điều hướng thông minh sau đăng nhập dựa theo 4 vai trò:
    - 1. Admin / Quản trị viên (is_staff / is_superuser) -> Chuyển thẳng vào Admin Dashboard
    - 2. Tài xế Shipper (có hồ sơ TaiXe) -> Chuyển thẳng vào App Shipper
    - 3. Đối tác B2B (quản lý quán ăn/nhà hàng) -> Chuyển thẳng vào B2B Partner Dashboard
    - 4. Khách hàng đặt món -> Chuyển về Trang chủ hoặc trang trước đó (next)
    """
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url and next_url not in ['/', '/login/', '/dang-nhap/', '/logout/']:
        return redirect(next_url)

    if user.is_staff or user.is_superuser:
        return redirect('core:admin_dashboard')

    if hasattr(user, 'taixe') or TaiXe.objects.filter(user=user).exists():
        return redirect('core:app_shipper')

    if KhoHang.objects.filter(chu_so_huu=user).exists():
        return redirect('core:partner_dashboard')

    return redirect('core:home')


def dang_nhap(request):
    """Đăng nhập phân quyền thông minh: Admin -> Admin Dashboard, Shipper -> App Shipper, Khách hàng -> Trang chủ"""
    if request.user.is_authenticated:
        return _redirect_theo_vai_tro(request, request.user)

    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return _redirect_theo_vai_tro(request, user)
        else:
            messages.error(request, 'Sai tên đăng nhập hoặc mật khẩu!')

    return render(request, 'login.html')


def dang_ky(request):
    """
    Đăng ký tài khoản người dùng mới (Khách hàng đặt món hoặc Tài xế Shipper đối tác)
    """
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        sdt = request.POST.get('sdt', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        role = request.POST.get('role', 'KHACH_HANG').strip()

        if not username or not password:
            messages.error(request, 'Vui lòng điền đầy đủ tên đăng nhập và mật khẩu!')
            return render(request, 'register.html')

        if password != confirm_password:
            messages.error(request, 'Mật khẩu xác nhận không trùng khớp!')
            return render(request, 'register.html')

        if len(password) < 6:
            messages.error(request, 'Mật khẩu phải có tối thiểu 6 ký tự!')
            return render(request, 'register.html')

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f'Tên đăng nhập "{username}" đã có người sử dụng. Hãy chọn tên khác!')
            return render(request, 'register.html')

        # Tạo tài khoản User
        user = User.objects.create_user(username=username, email=email, password=password)
        if full_name:
            parts = full_name.split()
            user.last_name = parts[0] if len(parts) > 1 else ""
            user.first_name = " ".join(parts[1:]) if len(parts) > 1 else parts[0]
            user.save()

        # Nếu chọn vai trò Tài xế Shipper
        if role == 'SHIPPER':
            TaiXe.objects.create(
                user=user,
                ten_tai_xe=full_name or username,
                sdt=sdt or '0901234567',
                bien_so='59-NEW',
                loai_xe='Xe máy',
                ca_lam_viec='SANG',
                dang_lam_viec=True,
                trang_thai='Sẵn sàng',
                lat_hien_tai=10.7769,
                lng_hien_tai=106.7009
            )
        elif role == 'B2B_PARTNER':
            ten_quan = request.POST.get('ten_quan', '').strip() or f"Quán Ăn của {full_name or username}"
            dia_chi_quan = request.POST.get('dia_chi_quan', '').strip() or '123 Đường Ẩm Thực, Quận 1, TP.HCM'
            KhoHang.objects.create(
                chu_so_huu=user,
                ten_kho=ten_quan,
                dia_chi=dia_chi_quan,
                lat=10.7769,
                lng=106.7009,
                loai_hinh='Đối tác Quán ăn B2B',
                hinh_anh='https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&auto=format&fit=crop&q=60',
                danh_gia=5.0,
                thoi_gian_mo_cua='08:00 - 22:30',
                hotline=sdt or '1900 6868'
            )

        # Gửi email chào mừng qua Mailbox
        if email:
            role_desc = 'Tài xế Shipper' if role == 'SHIPPER' else ('Đối tác Quán ăn B2B' if role == 'B2B_PARTNER' else 'Khách hàng đặt món')
            gui_email_mailbox(
                f"🎉 Chào mừng {user.username} gia nhập FoodDelivery!",
                f"Xin chào {full_name or user.username},\n\nChúc mừng bạn đã tạo tài khoản thành công trên nền tảng FoodDelivery!\nTên đăng nhập: {user.username}\nVai trò: {role_desc}\n\nTrân trọng,\nĐội ngũ FoodDelivery.",
                email
            )

        # Tự động đăng nhập
        login(request, user)
        messages.success(request, f'Chào mừng {full_name or username}! Bạn đã đăng ký tài khoản thành công.')

        if role == 'SHIPPER':
            return redirect('core:app_shipper')
        elif role == 'B2B_PARTNER':
            return redirect('core:partner_dashboard')
        return redirect('core:home')

    return render(request, 'register.html')


def quen_mat_khau(request):
    """
    Khôi phục mật khẩu tài khoản qua email / Mailbox hoặc đặt mật khẩu mới trực tiếp
    """
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not identifier:
            messages.error(request, 'Vui lòng nhập tên đăng nhập hoặc email của bạn!')
            return render(request, 'forgot_password.html')

        user = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()
        if not user:
            messages.error(request, f'Không tìm thấy tài khoản nào khớp với "{identifier}"!')
            return render(request, 'forgot_password.html')

        # Người dùng nhập mật khẩu mới trực tiếp
        if new_password:
            if new_password != confirm_password:
                messages.error(request, 'Mật khẩu mới và mật khẩu xác nhận không trùng khớp!')
                return render(request, 'forgot_password.html', {'identifier': identifier})
            if len(new_password) < 6:
                messages.error(request, 'Mật khẩu mới phải có tối thiểu 6 ký tự!')
                return render(request, 'forgot_password.html', {'identifier': identifier})

            user.set_password(new_password)
            user.save()

            if user.email:
                gui_email_mailbox(
                    f"[FoodDelivery] Mật khẩu tài khoản {user.username} đã được đổi",
                    f"Xin chào {user.username},\n\nMật khẩu tài khoản của bạn trên FoodDelivery đã được đặt lại thành công.\nNếu không phải bạn thực hiện, vui lòng liên hệ ban quản trị.\n\nTrân trọng,\nĐội ngũ FoodDelivery.",
                    user.email
                )

            messages.success(request, f'Đặt lại mật khẩu thành công cho tài khoản "{user.username}"! Bạn có thể đăng nhập ngay.')
            return redirect('core:login')

        else:
            # Sinh mật khẩu tạm thời ngẫu nhiên
            temp_pass = 'Food@' + ''.join(random.choices(string.digits, k=6))
            user.set_password(temp_pass)
            user.save()

            if user.email:
                gui_email_mailbox(
                    f"[FoodDelivery] Cấp lại mật khẩu tài khoản {user.username}",
                    f"Xin chào {user.username},\n\nBạn vừa yêu cầu cấp lại mật khẩu trên hệ thống FoodDelivery.\nMật khẩu mới tạm thời của bạn là: {temp_pass}\nVui lòng đăng nhập và đổi lại mật khẩu trong trang cá nhân.\n\nTrân trọng,\nĐội ngũ FoodDelivery.",
                    user.email
                )

            messages.success(
                request,
                f'Đã cấp mật khẩu tạm thời cho tài khoản "{user.username}": {temp_pass}. '
                f'Vui lòng copy mật khẩu này để đăng nhập!'
            )
            return render(request, 'forgot_password.html', {'temp_pass': temp_pass, 'user_found': user, 'identifier': identifier})

    return render(request, 'forgot_password.html')


@login_required(login_url='core:login')
def admin_dashboard_view(request):
    """
    Trang Bảng Điều Khiển Quản Trị Chuyên Nghiệp (Enterprise SaaS Admin Dashboard):
    - Hoạt động độc lập với giao diện người dùng hiện tại
    - Bảo vệ server-side: chỉ staff / superuser mới được truy cập
    - Thống kê thời gian thực 100% từ Django ORM, hoàn toàn không có dữ liệu giả
    - Biểu đồ xu hướng Chart.js, phân bổ trạng thái đơn, danh sách hoạt động gần đây
    """
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Bạn không có quyền truy cập khu vực quản trị hệ thống!")
        return redirect('core:home')

    # 1. TỔNG HỢP CÁC CHỈ SỐ KPI TỪ ORM THỰC TẾ
    tong_don = DonHang.objects.count()
    don_cho_tai_xe = DonHang.objects.filter(trang_thai='CHỜ TÀI XẾ').count()
    don_dang_xu_ly = DonHang.objects.filter(trang_thai__in=['ĐANG VẬN CHUYỂN', 'CHỜ TÀI XẾ', 'ĐANG PHÂN LOẠI']).count()
    don_thanh_cong = DonHang.objects.filter(trang_thai='ĐÃ GIAO THÀNH CÔNG').count()
    don_hoa_toc = DonHang.objects.filter(loai_giao_hang='HOA_TOC').count()
    don_tieu_chuan = DonHang.objects.filter(loai_giao_hang='TIEU_CHUAN').count()
    ty_le_thanh_cong = round((don_thanh_cong / tong_don * 100), 1) if tong_don > 0 else 0

    tong_gmv = DonHang.objects.aggregate(Sum('tong_tien'))['tong_tien__sum'] or Decimal(0)
    tien_mon_an_tong = DonHang.objects.aggregate(Sum('tien_mon_an'))['tien_mon_an__sum'] or Decimal(0)
    tong_phi_ship = DonHang.objects.aggregate(Sum('phi_van_chuyen'))['phi_van_chuyen__sum'] or Decimal(0)
    doanh_thu_ads_tong = QuangCao.objects.filter(kich_hoat=True).aggregate(
        Sum('doanh_thu_ads'))['doanh_thu_ads__sum'] or Decimal(0)
    hoa_hong_san = int(tien_mon_an_tong * Decimal('0.15')) + int(doanh_thu_ads_tong)

    so_tai_xe = TaiXe.objects.count()
    tai_xe_online = TaiXe.objects.filter(dang_lam_viec=True).count()
    so_quan_an = KhoHang.objects.count()
    so_mon_an = MonAn.objects.count()

    # 2. DANH SÁCH ĐƠN HÀNG MỚI NHẤT
    don_hangs_moi = DonHang.objects.select_related('kho_xuat_phat', 'tai_xe').order_by('-ngay_tao')[:10]

    # 3. ĐỘI NGŨ SHIPPER VÀ CƠ SỞ KHO
    top_tai_xe = TaiXe.objects.all().order_by('-dang_lam_viec', '-doanh_thu_tich_luy')[:5]
    active_kho_list = KhoHang.objects.annotate(
        don_chua_giao=Count('donhang', filter=~Q(donhang__trang_thai__in=['ĐÃ GIAO THÀNH CÔNG', 'HỦY', 'ĐÃ HỦY']))
    ).order_by('-don_chua_giao')[:5]

    # 4. DỮ LIỆU BIỂU ĐỒ DOANH THU & ĐƠN HÀNG 7 NGÀY GẦN NHẤT (DỮ LIỆU THỰC TỪ ORM)
    today = timezone.now().date()
    trend_labels = []
    trend_revenue = []
    trend_orders = []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        trend_labels.append(day.strftime('%d/%m'))
        dh_day_qs = DonHang.objects.filter(ngay_tao__date=day)
        cnt = dh_day_qs.count()
        rev = dh_day_qs.aggregate(Sum('tong_tien'))['tong_tien__sum'] or Decimal(0)
        trend_revenue.append(float(rev))
        trend_orders.append(cnt)

    # 5. DỮ LIỆU BIỂU ĐỒ PHÂN BỔ TRẠNG THÁI ĐƠN HÀNG (DỮ LIỆU THỰC TỪ ORM)
    thong_ke_don = DonHang.objects.values('trang_thai').annotate(total=Count('id')).order_by('-total')
    status_labels = [item['trang_thai'] for item in thong_ke_don]
    status_counts = [item['total'] for item in thong_ke_don]

    context = {
        'active_menu': 'dashboard',
        'pending_orders_count': don_cho_tai_xe,
        'stats': {
            'tong_don': tong_don,
            'don_cho_tai_xe': don_cho_tai_xe,
            'don_dang_xu_ly': don_dang_xu_ly,
            'don_thanh_cong': don_thanh_cong,
            'don_hoa_toc': don_hoa_toc,
            'don_tieu_chuan': don_tieu_chuan,
            'ty_le_thanh_cong': ty_le_thanh_cong,
            'tong_gmv': tong_gmv,
            'tong_phi_ship': tong_phi_ship,
            'hoa_hong_san': hoa_hong_san,
            'doanh_thu_ads': doanh_thu_ads_tong,
            'so_tai_xe': so_tai_xe,
            'tai_xe_online': tai_xe_online,
            'so_quan_an': so_quan_an,
            'so_mon_an': so_mon_an,
        },
        'don_hangs_moi': don_hangs_moi,
        'top_tai_xe': top_tai_xe,
        'active_kho_list': active_kho_list,
        'all_tai_xe': TaiXe.objects.all().order_by('ten_tai_xe'),
        'all_kho': KhoHang.objects.all().order_by('ten_kho'),
        'all_don_hangs_active': DonHang.objects.exclude(trang_thai__in=['ĐÃ GIAO THÀNH CÔNG', 'HỦY', 'ĐÃ HỦY']).order_by('-ngay_tao')[:40],
        'recent_lich_su': LichSuKho.objects.select_related('don_hang', 'kho').order_by('-thoi_gian')[:8],
        'trend_labels': json.dumps(trend_labels),
        'trend_revenue': json.dumps(trend_revenue),
        'trend_orders': json.dumps(trend_orders),
        'status_labels': json.dumps(status_labels),
        'status_counts': json.dumps(status_counts),
    }
    return render(request, 'admin_dashboard/dashboard.html', context)


def dashboard_view(request):
    """
    Giữ tương thích ngược cho URL /dashboard/.
    Nếu người dùng là admin/staff, chuyển tiếp sang admin_dashboard_view.
    Nếu chưa đăng nhập hoặc không phải admin, yêu cầu đăng nhập quản trị.
    """
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('core:admin_dashboard')
        messages.error(request, "Tài khoản của bạn không có quyền truy cập trang quản trị!")
        return redirect('core:home')
    return redirect('core:login')


@login_required(login_url='core:login')
def api_admin_quick_update_don_hang(request, don_id):
    """API điều phối và đổi trạng thái đơn hàng nhanh 1-Click từ Admin Dashboard (Ajax)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'success': False, 'message': 'Không có quyền quản trị!'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Chỉ chấp nhận phương thức POST'}, status=405)

    don = get_object_or_404(DonHang, id=don_id)

    trang_thai = request.POST.get('trang_thai')
    tai_xe_id = request.POST.get('tai_xe_id')
    trang_thai_thanh_toan = request.POST.get('trang_thai_thanh_toan')

    old_status = don.trang_thai
    updated_fields = []

    if trang_thai and trang_thai != don.trang_thai:
        don.trang_thai = trang_thai
        updated_fields.append(f"Trạng thái: {old_status} -> {trang_thai}")

        if trang_thai == 'ĐÃ GIAO THÀNH CÔNG' and old_status != 'ĐÃ GIAO THÀNH CÔNG' and don.tai_xe:
            don.tai_xe.doanh_thu_tich_luy += (don.phi_van_chuyen + don.phu_phi_hoa_toc)
            don.tai_xe.tong_don_thang_nay += 1
            don.tai_xe.save()
            don.trang_thai_thanh_toan = 'DA_THANH_TOAN'

    if tai_xe_id is not None:
        if tai_xe_id == '' or tai_xe_id == '0':
            don.tai_xe = None
            updated_fields.append("Hủy gán tài xế")
        else:
            try:
                tx = TaiXe.objects.get(id=int(tai_xe_id))
                don.tai_xe = tx
                updated_fields.append(f"Gán tài xế: {tx.ten_tai_xe}")
                if don.trang_thai == 'CHỜ TÀI XẾ':
                    don.trang_thai = 'ĐANG VẬN CHUYỂN'
            except (TaiXe.DoesNotExist, ValueError):
                pass

    if trang_thai_thanh_toan:
        don.trang_thai_thanh_toan = trang_thai_thanh_toan
        tt_str = "Đã thanh toán" if trang_thai_thanh_toan == 'DA_THANH_TOAN' else "Chờ thanh toán"
        updated_fields.append(f"Thanh toán: {tt_str}")

    don.save()

    ghi_chu_log = f"Cập nhật bởi {request.user.username}: " + "; ".join(updated_fields) if updated_fields else "Cập nhật nhanh"
    LichSuKho.objects.create(
        don_hang=don,
        kho=don.kho_xuat_phat,
        trang_thai_buoc=f"ADMIN CẬP NHẬT: {don.trang_thai}",
        ghi_chu=ghi_chu_log
    )

    # Admin cập nhật Mailbox (Gửi email xác nhận / cập nhật đơn cho khách hàng)
    mail_subject = f"🔔 [Admin Xác Nhận] Cập nhật đơn hàng #{don.ma_don} - {don.trang_thai}"
    mail_body = (
        f"Xin chào {don.ten_nguoi_nhan},\n\n"
        f"Ban Quản Trị FoodDelivery vừa cập nhật thông tin đơn hàng #{don.ma_don} của bạn:\n"
        f"- Trạng thái đơn: {don.trang_thai}\n"
        f"- Thanh toán: {don.get_trang_thai_thanh_toan_display()}\n"
        f"- Shipper điều phối: {don.tai_xe.ten_tai_xe if don.tai_xe else 'Đang điều phối'}\n"
        f"- Chi tiết cập nhật: {ghi_chu_log}\n\n"
        f"Theo dõi lộ trình đơn hàng tại: http://127.0.0.1:8000/chi-tiet/{don.ma_don}/\n\n"
        f"Trân trọng,\nBan Quản Trị FoodDelivery."
    )
    gui_email_mailbox(mail_subject, mail_body, don.email_nguoi_nhan)

    return JsonResponse({
        'success': True,
        'message': f'Đã cập nhật đơn #{don.ma_don} thành công!',
        'don_id': don.id,
        'ma_don': don.ma_don,
        'trang_thai': don.trang_thai,
        'tai_xe_ten': don.tai_xe.ten_tai_xe if don.tai_xe else 'Chưa phân công',
        'tai_xe_id': don.tai_xe.id if don.tai_xe else '',
        'trang_thai_thanh_toan': don.trang_thai_thanh_toan,
    })


@login_required(login_url='core:login')
def api_admin_quick_create_don_hang(request):
    """API Tạo đơn hàng hỏa tốc mới 1-Click trực tiếp tại Admin Dashboard (Ajax)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'success': False, 'message': 'Không có quyền quản trị!'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Chỉ chấp nhận phương thức POST'}, status=405)

    ten = request.POST.get('ten_nguoi_nhan', '').strip()
    sdt = request.POST.get('sdt_nguoi_nhan', '').strip()
    dia_chi = request.POST.get('dia_chi_nguoi_nhan', '').strip()
    kho_id = request.POST.get('kho_xuat_phat')

    if not ten or not sdt or not dia_chi or not kho_id:
        return JsonResponse({'success': False, 'message': 'Vui lòng điền đầy đủ Tên, SĐT, Địa chỉ và Bếp xuất phát!'}, status=400)

    try:
        kho_gui = KhoHang.objects.get(id=int(kho_id))
    except (KhoHang.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'message': 'Điểm xuất phát không tồn tại!'}, status=400)

    loai_giao_hang = request.POST.get('loai_giao_hang', 'HOA_TOC')
    tai_xe_id = request.POST.get('tai_xe_id')
    tai_xe = None
    if tai_xe_id and tai_xe_id != '' and tai_xe_id != '0':
        try:
            tai_xe = TaiXe.objects.get(id=int(tai_xe_id))
        except (TaiXe.DoesNotExist, ValueError):
            pass

    tien_mon_an = Decimal(request.POST.get('tien_mon_an') or '50000')
    phi_van_chuyen = Decimal(request.POST.get('phi_van_chuyen') or '20000')
    phu_phi_hoa_toc = Decimal(request.POST.get('phu_phi_hoa_toc') or '5000') if loai_giao_hang == 'HOA_TOC' else Decimal('0')
    phuong_thuc = request.POST.get('phuong_thuc_thanh_toan', 'TIEN_MAT_COD')
    trang_thai_tt = request.POST.get('trang_thai_thanh_toan', 'CHUA_THANH_TOAN')
    trang_thai = 'ĐANG VẬN CHUYỂN' if tai_xe else 'CHỜ TÀI XẾ'
    ghi_chu = request.POST.get('ghi_chu', '').strip()

    lat_khach = float(request.POST.get('lat_khach') or (kho_gui.lat + 0.01 if kho_gui.lat else 10.7769))
    lng_khach = float(request.POST.get('lng_khach') or (kho_gui.lng + 0.01 if kho_gui.lng else 106.7009))
    km = tinh_khoang_cach_haversine(kho_gui.lat, kho_gui.lng, lat_khach, lng_khach)

    don = DonHang.objects.create(
        ten_nguoi_nhan=ten,
        sdt_nguoi_nhan=sdt,
        dia_chi_nguoi_nhan=dia_chi,
        lat_khach=lat_khach,
        lng_khach=lng_khach,
        khoang_cach_km=km,
        kho_xuat_phat=kho_gui,
        tai_xe=tai_xe,
        loai_giao_hang=loai_giao_hang,
        tien_mon_an=tien_mon_an,
        phi_van_chuyen=phi_van_chuyen,
        phu_phi_hoa_toc=phu_phi_hoa_toc,
        phuong_thuc_thanh_toan=phuong_thuc,
        trang_thai_thanh_toan=trang_thai_tt,
        trang_thai=trang_thai,
        ghi_chu=ghi_chu,
    )

    LichSuKho.objects.create(
        don_hang=don,
        kho=kho_gui,
        trang_thai_buoc='NHẬP KHO',
        ghi_chu=f"Tạo đơn trực tiếp từ Admin Dashboard bởi {request.user.username}."
    )
    if tai_xe:
        LichSuKho.objects.create(
            don_hang=don,
            kho=kho_gui,
            trang_thai_buoc='BÀN GIAO SHIPPER',
            ghi_chu=f"Điều phối trực tiếp cho Shipper {tai_xe.ten_tai_xe} ({tai_xe.bien_so})."
        )

    return JsonResponse({
        'success': True,
        'message': f'Tạo đơn #{don.ma_don} thành công!',
        'don': {
            'id': don.id,
            'ma_don': don.ma_don,
            'ten_nguoi_nhan': don.ten_nguoi_nhan,
            'sdt_nguoi_nhan': don.sdt_nguoi_nhan,
            'kho_ten': don.kho_xuat_phat.ten_kho,
            'tai_xe_ten': don.tai_xe.ten_tai_xe if don.tai_xe else 'Chưa phân công',
            'loai_giao_hang': don.loai_giao_hang,
            'tong_tien': float(don.tong_tien),
            'trang_thai': don.trang_thai,
            'trang_thai_thanh_toan': don.trang_thai_thanh_toan,
            'ngay_tao': don.ngay_tao.strftime('%H:%M %d/%m/%Y'),
        }
    })


@login_required(login_url='core:login')
def admin_quan_ly_mon_an(request):
    """Trang Quản lý Thực đơn Món Ăn chuẩn Enterprise SaaS trong Admin Dashboard"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Bạn không có quyền truy cập trang quản trị món ăn!")
        return redirect('core:home')

    q = request.GET.get('q', '').strip()
    danh_muc_id = request.GET.get('danh_muc', '').strip()
    status_filter = request.GET.get('status', '').strip()

    mon_qs = MonAn.objects.select_related('danh_muc', 'kho_hang').all()

    if q:
        mon_qs = mon_qs.filter(Q(ten_mon__icontains=q) | Q(mo_ta__icontains=q))
    if danh_muc_id:
        mon_qs = mon_qs.filter(danh_muc_id=danh_muc_id)
    if status_filter == 'con_mon':
        mon_qs = mon_qs.filter(is_con_mon=True)
    elif status_filter == 'het_mon':
        mon_qs = mon_qs.filter(is_con_mon=False)
    elif status_filter == 'noi_bat':
        mon_qs = mon_qs.filter(is_noi_bat=True)

    mon_qs = mon_qs.order_by('-is_noi_bat', '-da_ban', 'id')

    paginator = Paginator(mon_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    tong_mon = MonAn.objects.count()
    mon_con = MonAn.objects.filter(is_con_mon=True).count()
    mon_het = MonAn.objects.filter(is_con_mon=False).count()
    mon_noi_bat = MonAn.objects.filter(is_noi_bat=True).count()

    danh_mucs = DanhMucMonAn.objects.all()
    kho_hangs = KhoHang.objects.all()
    don_cho_tai_xe = DonHang.objects.filter(trang_thai='CHỜ TÀI XẾ').count()

    return render(request, 'admin_dashboard/quan_ly_mon_an.html', {
        'active_menu': 'mon_an',
        'pending_orders_count': don_cho_tai_xe,
        'page_obj': page_obj,
        'danh_mucs': danh_mucs,
        'kho_hangs': kho_hangs,
        'q': q,
        'selected_danh_muc': danh_muc_id,
        'selected_status': status_filter,
        'stats': {
            'tong_mon': tong_mon,
            'mon_con': mon_con,
            'mon_het': mon_het,
            'mon_noi_bat': mon_noi_bat,
        }
    })


@login_required(login_url='core:login')
@require_POST
def api_admin_toggle_mon_an(request, mon_id):
    """Bật / Tắt trạng thái Còn món vs Hết món tức thì bằng Ajax"""
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'success': False, 'message': 'Không có quyền quản trị!'}, status=403)

    mon = get_object_or_404(MonAn, id=mon_id)
    mon.is_con_mon = not mon.is_con_mon
    mon.save()

    return JsonResponse({
        'success': True,
        'is_con_mon': mon.is_con_mon,
        'status_text': 'Đang phục vụ' if mon.is_con_mon else 'Tạm hết món',
        'message': f'Đã chuyển "{mon.ten_mon}" sang: {"Đang phục vụ" if mon.is_con_mon else "Tạm hết món"}'
    })


@login_required(login_url='core:login')
@require_POST
def admin_them_mon_an(request):
    """Thêm món ăn mới từ Admin Dashboard"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Không có quyền quản trị!")
        return redirect('core:home')

    ten_mon = request.POST.get('ten_mon', '').strip()
    danh_muc_id = request.POST.get('danh_muc_id')
    kho_hang_id = request.POST.get('kho_hang_id')
    gia = request.POST.get('gia', 0)
    gia_km = request.POST.get('gia_khuyen_mai') or None
    hinh_anh = request.POST.get('hinh_anh', '').strip()
    mo_ta = request.POST.get('mo_ta', '').strip()
    is_noi_bat = bool(request.POST.get('is_noi_bat'))
    is_hoa_toc = bool(request.POST.get('is_hoa_toc'))
    is_con_mon = bool(request.POST.get('is_con_mon', True))

    if not ten_mon or not danh_muc_id or not gia:
        messages.error(request, "Vui lòng điền đầy đủ Tên món, Danh mục và Giá bán!")
        return redirect('core:admin_quan_ly_mon_an')

    if not hinh_anh:
        hinh_anh = 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&auto=format&fit=crop&q=60'

    mon = MonAn.objects.create(
        ten_mon=ten_mon,
        danh_muc_id=danh_muc_id,
        kho_hang_id=kho_hang_id if kho_hang_id else None,
        gia=Decimal(gia),
        gia_khuyen_mai=Decimal(gia_km) if gia_km else None,
        hinh_anh=hinh_anh,
        mo_ta=mo_ta,
        is_noi_bat=is_noi_bat,
        is_hoa_toc=is_hoa_toc,
        is_con_mon=is_con_mon
    )
    messages.success(request, f'🎉 Đã thêm thành công món ăn mới: "{mon.ten_mon}"!')
    return redirect('core:admin_quan_ly_mon_an')


@login_required(login_url='core:login')
@require_POST
def admin_sua_mon_an(request, id):
    """Chỉnh sửa thông tin món ăn từ Admin Dashboard"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Không có quyền quản trị!")
        return redirect('core:home')

    mon = get_object_or_404(MonAn, id=id)

    mon.ten_mon = request.POST.get('ten_mon', mon.ten_mon).strip()
    danh_muc_id = request.POST.get('danh_muc_id')
    if danh_muc_id:
        mon.danh_muc_id = danh_muc_id
    kho_hang_id = request.POST.get('kho_hang_id')
    mon.kho_hang_id = kho_hang_id if kho_hang_id else None

    gia = request.POST.get('gia')
    if gia:
        mon.gia = Decimal(gia)
    gia_km = request.POST.get('gia_khuyen_mai')
    mon.gia_khuyen_mai = Decimal(gia_km) if gia_km else None

    hinh_anh = request.POST.get('hinh_anh')
    if hinh_anh:
        mon.hinh_anh = hinh_anh.strip()

    mon.mo_ta = request.POST.get('mo_ta', '').strip()
    mon.is_noi_bat = bool(request.POST.get('is_noi_bat'))
    mon.is_hoa_toc = bool(request.POST.get('is_hoa_toc'))
    mon.is_con_mon = bool(request.POST.get('is_con_mon'))

    mon.save()
    messages.success(request, f'✅ Đã lưu cập nhật món: "{mon.ten_mon}"!')
    return redirect('core:admin_quan_ly_mon_an')


@login_required(login_url='core:login')
def admin_xoa_mon_an(request, id):
    """Xóa món ăn khỏi thực đơn"""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Không có quyền quản trị!")
        return redirect('core:home')

    mon = get_object_or_404(MonAn, id=id)
    ten = mon.ten_mon
    mon.delete()
    messages.success(request, f'🗑️ Đã xóa món ăn "{ten}" khỏi thực đơn!')
    return redirect('core:admin_quan_ly_mon_an')


def dang_xuat(request):
    logout(request)
    return redirect('core:home')


# ==============================================================================
# 2. TRANG CHỦ, HERO CAROUSEL CHUYỂN ĐỘNG và DOANH THU TMĐT
# ==============================================================================

def home(request):
    """
    Trang chủ:
    - Hero Swiper Carousel giới thiệu nền tảng đặt món và giao hàng hỏa tốc
    - Danh mục món ăn và thực đơn nổi bật
    - Dashboard TMĐT với doanh thu GMV, hoa hồng sàn, doanh thu Ads và lương shipper
    - Tra cứu vận đơn cho khách hàng
    """
    q = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'ALL')

    # Danh sách đơn hàng cho tra cứu hoặc quản lý
    ds_don = DonHang.objects.all().order_by('-id')
    if status_filter and status_filter != 'ALL':
        ds_don = ds_don.filter(trang_thai=status_filter)
    if q:
        ds_don = ds_don.filter(Q(ma_don__icontains=q) | Q(sdt_nguoi_nhan__icontains=q) | Q(ten_nguoi_nhan__icontains=q))

    paginator = Paginator(ds_don, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Dữ liệu cho trang chủ TMĐT
    danh_muc_list = DanhMucMonAn.objects.all()
    mon_an_noi_bat = MonAn.objects.filter(is_con_mon=True, is_noi_bat=True)[:8]
    ads_banners = QuangCao.objects.filter(kich_hoat=True, loai_quang_cao__in=['BANNER_CHINH', 'BANNER_PHU'])

    # THỐNG KÊ DOANH THU TMĐT ĐẦY ĐỦ
    tong_gmv = DonHang.objects.aggregate(Sum('tong_tien'))['tong_tien__sum'] or Decimal(0)
    tien_mon_an_tong = DonHang.objects.aggregate(Sum('tien_mon_an'))['tien_mon_an__sum'] or Decimal(0)
    doanh_thu_ads_tong = QuangCao.objects.filter(kich_hoat=True).aggregate(
        Sum('doanh_thu_ads'))['doanh_thu_ads__sum'] or Decimal(0)
    doanh_thu_shipper_tong = TaiXe.objects.aggregate(Sum('doanh_thu_tich_luy'))['doanh_thu_tich_luy__sum'] or Decimal(0)
    # Hoa hồng sàn TMĐT (15% từ doanh thu món ăn của nhà hàng + doanh thu ads)
    hoa_hong_san = int(tien_mon_an_tong * Decimal(0.15)) + int(doanh_thu_ads_tong)

    top_tai_xe = TaiXe.objects.order_by('-doanh_thu_tich_luy')[:5]
    thong_ke_don = DonHang.objects.values('trang_thai').annotate(so_luong=Count('id'))

    context = {
        'don_hangs': page_obj if (request.user.is_authenticated or q) else [],
        'page_obj': page_obj,
        'current_status': status_filter,
        'q': q,
        'danh_muc_list': danh_muc_list,
        'mon_an_noi_bat': mon_an_noi_bat,
        'ads_banners': ads_banners,
        'stats': {
            'tong_don': DonHang.objects.count(),
            'don_dang_giao': DonHang.objects.filter(trang_thai__in=['ĐANG VẬN CHUYỂN', 'CHỜ TÀI XẾ']).count(),
            'tong_gmv': tong_gmv,
            'hoa_hong_san': hoa_hong_san,
            'doanh_thu_ads': doanh_thu_ads_tong,
            'tong_doanh_thu_shipper': doanh_thu_shipper_tong,
            'so_tai_xe': TaiXe.objects.count(),
            'so_mon_an': MonAn.objects.count(),
        },
        'labels_tai_xe': json.dumps([tx.ten_tai_xe for tx in top_tai_xe]),
        'data_doanh_thu': json.dumps([float(tx.doanh_thu_tich_luy or 0) for tx in top_tai_xe]),
        'labels_trang_thai': json.dumps([item['trang_thai'] for item in thong_ke_don]),
        'data_trang_thai': json.dumps([item['so_luong'] for item in thong_ke_don]),
    }
    return render(request, 'home.html', context)


# ==============================================================================
# 3. THỰC ĐƠN, GIỎ HÀNG, CHECKOUT và THANH TOÁN QR VIETQR
# ==============================================================================

def thuc_don(request):
    """Trang thực đơn món ăn trực tuyến: lọc đa tiêu chí, tìm kiếm thông minh, sắp xếp"""
    slug_dm = request.GET.get('danh_muc', '')
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '')
    muc_gia = request.GET.get('muc_gia', '')
    dac_diem = request.GET.get('dac_diem', '')

    ds_mon = MonAn.objects.filter(is_con_mon=True)
    danh_muc_dang_chon = None

    if slug_dm:
        danh_muc_dang_chon = get_object_or_404(DanhMucMonAn, slug=slug_dm)
        ds_mon = ds_mon.filter(danh_muc=danh_muc_dang_chon)

    if q:
        ds_mon = ds_mon.filter(Q(ten_mon__icontains=q) | Q(mo_ta__icontains=q) | Q(danh_muc__ten_danh_muc__icontains=q))

    # Lọc theo mức giá
    if muc_gia == 'duoi_50k':
        ds_mon = ds_mon.filter(gia__lt=50000)
    elif muc_gia == '50k_100k':
        ds_mon = ds_mon.filter(gia__gte=50000, gia__lte=100000)
    elif muc_gia == 'tren_100k':
        ds_mon = ds_mon.filter(gia__gt=100000)

    # Lọc theo đặc điểm nổi bật
    if dac_diem == 'hoa_toc':
        ds_mon = ds_mon.filter(is_hoa_toc=True)
    elif dac_diem == 'best_seller':
        ds_mon = ds_mon.filter(is_noi_bat=True)
    elif dac_diem == 'khuyen_mai':
        ds_mon = ds_mon.filter(gia_khuyen_mai__gt=0)

    # Sắp xếp
    if sort == 'gia_tang':
        ds_mon = ds_mon.order_by('gia')
    elif sort == 'gia_giam':
        ds_mon = ds_mon.order_by('-gia')
    elif sort == 'ban_chay':
        ds_mon = ds_mon.order_by('-da_ban')
    elif sort == 'danh_gia':
        ds_mon = ds_mon.order_by('-danh_gia')
    elif sort == 'chuan_bi':
        ds_mon = ds_mon.order_by('thoi_gian_chuan_bi')

    danh_mucs = DanhMucMonAn.objects.all()
    ads_phu = QuangCao.objects.filter(kich_hoat=True, loai_quang_cao='BANNER_PHU').first()

    return render(request, 'menu.html', {
        'ds_mon': ds_mon,
        'danh_mucs': danh_mucs,
        'danh_muc_dang_chon': danh_muc_dang_chon,
        'q': q,
        'sort': sort,
        'muc_gia': muc_gia,
        'dac_diem': dac_diem,
        'tong_mon': ds_mon.count(),
        'ads_phu': ads_phu,
    })



def checkout_view(request):
    """
    Trang Checkout Đặt Món và Tính Tiền Tổng Tuyến Đường:
    - Nhập thông tin người nhận, địa chỉ
    - Bản đồ Leaflet với GPS hiện tại của khách
    - Tính khoảng cách từ Quán/Bếp đến Khách -> tính phí ship theo KM
    - Chọn giao hỏa tốc hoặc giao tiêu chuẩn
    - Tạo mã QR VietQR thanh toán
    """
    ds_kho = KhoHang.objects.all()
    kho_mac_dinh = ds_kho.first()

    # Dữ liệu truyền sang để vẽ bản đồ
    kho_json = json.dumps([{
        'id': k.id,
        'ten': k.ten_kho,
        'lat': k.lat,
        'lng': k.lng,
        'dia_chi': k.dia_chi,
        'hotline': k.hotline
    } for k in ds_kho])

    # Lấy các mã voucher hợp lệ
    vouchers = QuangCao.objects.filter(kich_hoat=True).exclude(
        ma_voucher='').values('ma_voucher', 'giam_gia_phan_tram', 'tieu_de')

    return render(request, 'checkout.html', {
        'ds_kho': ds_kho,
        'kho_mac_dinh': kho_mac_dinh,
        'kho_json': kho_json,
        'vouchers_json': json.dumps(list(vouchers)),
    })


def tao_don_hang_mon_an(request):
    """
    Xử lý gửi form Checkout:
    - Tạo đơn hàng vào CSDL
    - Tự động lưu các món ăn trong giỏ vào ChiTietDonHang
    - Tính toán phụ phí hỏa tốc và phí vận chuyển
    - Tự động điều phối Shipper gần nhất (nếu chọn hỏa tốc)
    - Gửi email thông báo đơn hàng và thanh toán QR qua Mailbox
    """
    if request.method != 'POST':
        return redirect('core:thuc_don')

    ten_nguoi_nhan = request.POST.get('ten_nguoi_nhan')
    sdt_nguoi_nhan = request.POST.get('sdt_nguoi_nhan')
    email_nguoi_nhan = request.POST.get('email_nguoi_nhan', 'khachhang_test@gmail.com')
    dia_chi_nguoi_nhan = request.POST.get('dia_chi_nguoi_nhan')
    lat_khach = float(request.POST.get('lat_khach', 10.7769))
    lng_khach = float(request.POST.get('lng_khach', 106.7009))
    kho_id = request.POST.get('kho_xuat_phat')
    loai_giao_hang = request.POST.get('loai_giao_hang', 'HOA_TOC')
    phuong_thuc_thanh_toan = request.POST.get('phuong_thuc_thanh_toan', 'QR_VIETQR')
    ghi_chu = request.POST.get('ghi_chu', '')
    ma_voucher = request.POST.get('ma_voucher', '')

    kho_xuat_phat = None
    if kho_id:
        kho_xuat_phat = KhoHang.objects.filter(id=kho_id).first()
    if not kho_xuat_phat:
        kho_xuat_phat = KhoHang.objects.first()
    if not kho_xuat_phat:
        messages.error(request, "Hệ thống chưa thiết lập cơ sở / nhà hàng xuất phát.")
        return redirect('core:thuc_don')

    # Phân tích danh sách món ăn từ giỏ hàng (JSON)
    cart_json_str = request.POST.get('cart_data', '[]')
    try:
        cart_items = json.loads(cart_json_str)
    except Exception:
        cart_items = []

    # Tính khoảng cách thực tế
    km = tinh_khoang_cach_haversine(kho_xuat_phat.lat, kho_xuat_phat.lng, lat_khach, lng_khach)

    # ⛔ KIỂM TRA BÁN KÍNH GIAO ĐỒ ĂN HỎA TỐC (GIỚI HẠN TỐI ĐA 30KM)
    # Nếu vượt quá 30km: Quét tìm chi nhánh/quán ăn B2B gần khách nhất (Nearest Branch Routing)
    if km > 30.0:
        mon_ids = [int(item.get('id')) for item in cart_items if item.get('id')]
        quan_gan, dist_moi = tim_quan_an_gan_nhat(lat_khach, lng_khach, max_km=30.0, mon_ids=mon_ids)
        if quan_gan:
            messages.info(
                request,
                f"💡 Quán xuất phát ban đầu ({kho_xuat_phat.ten_kho}) cách bạn {km:.1f}km (quá xa để giao hỏa tốc). "
                f"Hệ thống đã tự động chuyển đơn sang chi nhánh gần nhất: {quan_gan.ten_kho} (cách bạn {dist_moi:.1f}km) "
                f"để đảm bảo món ăn nóng hổi trong 20 phút và tối ưu cước phí ship!"
            )
            kho_xuat_phat = quan_gan
            km = dist_moi
        else:
            messages.error(
                request,
                f"⛔ Không thể giao hàng! Khoảng cách ({km:.1f} km) vượt quá bán kính tối đa cho phép giao hỏa tốc (30 km). "
                f"Theo logic đồ ăn trực tuyến, không thể giao đồ ăn quá xa bằng xe máy vì món ăn sẽ bị nguội hỏng và cước ship phi thực tế!"
            )
            return redirect('core:checkout')

    is_hoa_toc = (loai_giao_hang == 'HOA_TOC')
    phi_ship, phu_phi_hoa_toc = tinh_phi_ship_theo_km(km, is_hoa_toc)

    # Tính tiền món ăn
    tien_mon_an = Decimal(0)
    mon_obj_list = []
    for item in cart_items:
        mon_id = item.get('id')
        qty = int(item.get('quantity', 1))
        mon = MonAn.objects.filter(id=mon_id).first()
        if mon:
            gia_ban = mon.gia_hien_tai()
            tien_mon_an += (gia_ban * qty)
            mon_obj_list.append({'mon': mon, 'qty': qty, 'gia': gia_ban})

    # Nếu giỏ hàng trống (test đặt nhanh), lấy mặc định 1 món
    if not mon_obj_list:
        mon_mac_dinh = MonAn.objects.first()
        if mon_mac_dinh:
            mon_obj_list.append({'mon': mon_mac_dinh, 'qty': 1, 'gia': mon_mac_dinh.gia_hien_tai()})
            tien_mon_an += mon_mac_dinh.gia_hien_tai()

    # Áp dụng chính sách Freeship và voucher nghiệp vụ chuẩn TMĐT
    phi_ship_sau_giam, giam_gia, thong_bao_voucher = ap_dung_voucher_nghiep_vu(ma_voucher, tien_mon_an, phi_ship)
    if thong_bao_voucher:
        if 'yêu cầu' in thong_bao_voucher or 'không hợp lệ' in thong_bao_voucher:
            messages.warning(request, f"⚠️ {thong_bao_voucher}")
        else:
            messages.success(request, f"🎉 {thong_bao_voucher}")

    tong_tien = max(Decimal(0), tien_mon_an + Decimal(phi_ship) + Decimal(phu_phi_hoa_toc) - giam_gia)

    # ĐIỀU PHỐI SHIPPER TỰ ĐỘNG CHO ĐƠN HỎA TỐC
    # Tìm tài xế đang online gần quán xuất phát nhất (thuật toán đường đi nhanh nhất)
    tai_xe_phu_trach = None
    if is_hoa_toc:
        ds_tx_online = TaiXe.objects.filter(dang_lam_viec=True)
        min_dist = float('inf')
        for tx in ds_tx_online:
            dist = tinh_khoang_cach_haversine(kho_xuat_phat.lat, kho_xuat_phat.lng, tx.lat_hien_tai, tx.lng_hien_tai)
            if dist < min_dist:
                min_dist = dist
                tai_xe_phu_trach = tx

    # Lưu đơn hàng (gắn liên kết với tài khoản khách hàng nếu đã đăng nhập)
    don = DonHang.objects.create(
        khach_hang=request.user if request.user.is_authenticated else None,
        ten_nguoi_nhan=ten_nguoi_nhan,
        sdt_nguoi_nhan=sdt_nguoi_nhan,
        email_nguoi_nhan=email_nguoi_nhan,
        dia_chi_nguoi_nhan=dia_chi_nguoi_nhan,
        lat_khach=lat_khach,
        lng_khach=lng_khach,
        kho_xuat_phat=kho_xuat_phat,
        tai_xe=tai_xe_phu_trach,
        loai_giao_hang=loai_giao_hang,
        trang_thai='ĐANG VẬN CHUYỂN' if tai_xe_phu_trach else 'CHỜ TÀI XẾ',
        tien_mon_an=tien_mon_an,
        phi_van_chuyen=Decimal(phi_ship),
        phu_phi_hoa_toc=Decimal(phu_phi_hoa_toc),
        khoang_cach_km=km,
        giam_gia=giam_gia,
        tong_tien=tong_tien,
        phuong_thuc_thanh_toan=phuong_thuc_thanh_toan,
        trang_thai_thanh_toan='DA_THANH_TOAN' if phuong_thuc_thanh_toan == 'QR_VIETQR' else 'CHUA_THANH_TOAN',
        ghi_chu=ghi_chu,
    )

    # Lưu chi tiết món
    for item in mon_obj_list:
        ChiTietDonHang.objects.create(
            don_hang=don,
            mon_an=item['mon'],
            so_luong=item['qty'],
            don_gia=item['gia'],
            thanh_tien=item['gia'] * item['qty'],
            ghi_chu_mon=ghi_chu
        )
        # Tăng số lượng đã bán
        item['mon'].da_ban += item['qty']
        item['mon'].save()

    # Ghi nhật ký tiến trình chế biến & giao món
    LichSuKho.objects.create(
        don_hang=don,
        kho=kho_xuat_phat,
        trang_thai_buoc='BẾP TIẾP NHẬN',
        ghi_chu=f"Bếp {kho_xuat_phat.ten_kho} đã tiếp nhận đơn đặt món #{don.ma_don} qua cổng trực tuyến."
    )
    if tai_xe_phu_trach:
        LichSuKho.objects.create(
            don_hang=don,
            kho=kho_xuat_phat,
            trang_thai_buoc='BÀN GIAO SHIPPER',
            ghi_chu=f"Điều phối Hỏa Tốc cho Shipper: {tai_xe_phu_trach.ten_tai_xe} ({tai_xe_phu_trach.bien_so})."
        )

    # GỬI EMAIL THÔNG BÁO TỰ ĐỘNG QUA MAILBOX (MAILTRAP)
    email_subject = f"🎉 [FoodDelivery] Xác nhận đơn hàng #{don.ma_don} - {loai_giao_hang}"
    fmt_tien_mon = f"{tien_mon_an:,.0f}".replace(",", ".")
    fmt_phi_ship = f"{phi_ship:,.0f}".replace(",", ".")
    fmt_phu_phi = f"{phu_phi_hoa_toc:,.0f}".replace(",", ".")
    fmt_giam = f"{giam_gia:,.0f}".replace(",", ".")
    fmt_tong = f"{tong_tien:,.0f}".replace(",", ".")

    email_body = (
        f"Xin chào {don.ten_nguoi_nhan},\n\n"
        f"Cảm ơn bạn đã đặt món trên nền tảng FoodDelivery và Logistics!\n"
        f"Thông tin đơn hàng #{don.ma_don}:\n"
        f"- Cửa hàng chế biến: {kho_xuat_phat.ten_kho}\n"
        f"- Địa chỉ giao: {don.dia_chi_nguoi_nhan}\n"
        f"- Hình thức giao: {'⚡ HỎA TỐC (15-25 phút)' if is_hoa_toc else '🛵 Tiêu chuẩn'}\n"
        f"- Khoảng cách: {km} km\n"
        f"- Tiền món ăn: {fmt_tien_mon}đ\n"
        f"- Phí vận chuyển: {fmt_phi_ship}đ\n"
        f"- Phụ phí hỏa tốc: {fmt_phu_phi}đ\n"
        f"- Giảm giá: {fmt_giam}đ\n"
        f"- TỔNG THANH TOÁN: {fmt_tong}đ\n"
        f"- Phương thức thanh toán: {don.get_phuong_thuc_thanh_toan_display()}\n"
        f"- Trạng thái thanh toán: {don.get_trang_thai_thanh_toan_display()}\n\n"
        f"Tài xế giao hàng: {tai_xe_phu_trach.ten_tai_xe if tai_xe_phu_trach else 'Đang điều phối'}\n"
        f"Bạn có thể theo dõi hành trình đơn hàng tại: http://127.0.0.1:8000/chi-tiet/{don.ma_don}/\n\n"
        f"Trân trọng,\nĐội ngũ FoodDelivery."
    )
    gui_email_mailbox(email_subject, email_body, don.email_nguoi_nhan)

    return render(request, 'order_success.html', {
        'don': don,
        'chi_tiet': don.chi_tiet_mon.all(),
        'qr_url': don.link_qr_vietqr(),
    })


# ==============================================================================
# 4. BẢN ĐỒ GIS, CHI TIẾT ĐƠN HÀNG và TỐI ƯU LỘ TRÌNH HỎA TỐC (CORE GIS)
# ==============================================================================

def chi_tiet(request, ma_don):
    """Chi tiết lộ trình đơn hàng: Leaflet Map + GPS Shipper thực tế + Tiến độ + Đánh giá"""
    don_hang = get_object_or_404(DonHang, ma_don=ma_don)
    lich_su = don_hang.lich_su_kho.all().order_by('-thoi_gian')
    chi_tiet_mon = don_hang.chi_tiet_mon.all()
    danh_gia_list = don_hang.danh_gia_list.all()

    # Xác định bước tiến độ trong 5 bước
    # Bước 1: Đã đặt hàng -> Bước 2: Quán nhận đơn -> Bước 3: Đang chế biến -> Bước 4: Shipper đang giao -> Bước 5: Giao thành công
    status_str = don_hang.trang_thai.upper()
    current_step = 1
    if 'THÀNH CÔNG' in status_str or 'ĐÃ GIAO' in status_str:
        current_step = 5
    elif 'ĐANG VẬN CHUYỂN' in status_str or 'GIAO' in status_str or don_hang.tai_xe:
        current_step = 4
    elif lich_su.filter(trang_thai_buoc__in=['ĐANG PHÂN LOẠI', 'XUẤT KHO']).exists():
        current_step = 3
    elif 'CHỜ TÀI XẾ' in status_str or lich_su.filter(trang_thai_buoc='NHẬP KHO').exists():
        current_step = 2

    return render(request, 'map.html', {
        'dh': don_hang,
        'lich_su': lich_su,
        'chi_tiet_mon': chi_tiet_mon,
        'qr_url': don_hang.link_qr_vietqr(),
        'danh_gia_list': danh_gia_list,
        'current_step': current_step,
        'da_danh_gia': danh_gia_list.exists(),
    })


@require_POST
def gui_danh_gia(request, ma_don):
    """API gửi đánh giá & phản hồi chất lượng đơn hàng (sao + nhận xét)"""
    don_hang = get_object_or_404(DonHang, ma_don=ma_don)
    try:
        so_sao = int(request.POST.get('so_sao', 5))
        so_sao = max(1, min(5, so_sao))
    except (ValueError, TypeError):
        so_sao = 5

    ten_khach = request.POST.get('ten_khach', '').strip() or don_hang.ten_nguoi_nhan
    nhan_xet = request.POST.get('nhan_xet', '').strip()

    danh_gia = DanhGiaDonHang.objects.create(
        don_hang=don_hang,
        ten_khach=ten_khach,
        so_sao=so_sao,
        nhan_xet=nhan_xet
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == '1':
        return JsonResponse({
            'status': 'success',
            'message': 'Đánh giá của bạn đã được ghi nhận thành công!',
            'so_sao': danh_gia.so_sao,
            'ten_khach': danh_gia.ten_khach,
            'nhan_xet': danh_gia.nhan_xet,
            'ngay_tao': danh_gia.ngay_tao.strftime('%d/%m/%Y %H:%M')
        })

    messages.success(request, 'Cảm ơn bạn đã đánh giá đơn hàng!')
    return redirect('core:chi_tiet', ma_don=don_hang.ma_don)


@login_required(login_url='core:login')
def ban_do_chung(request):
    """
    Bản đồ giám sát và điều phối GIS phân quyền nghiêm ngặt theo 4 đối tượng:
    1. Admin (Quản trị viên): Thấy TOÀN BỘ CSDL database (tất cả quán, tất cả đơn hàng, tất cả tài xế online).
    2. Đối tác B2B (Quán ăn/Nhà hàng): CHỈ THẤY quán của mình, các đơn hàng thuộc quán mình, và shipper phụ trách đơn của quán mình.
    3. Shipper (Tài xế giao hàng): CHỈ THẤY các đơn hàng được giao cho chính mình, điểm lấy món của quán và vị trí GPS của mình.
    4. Khách hàng: CHỈ THẤY đơn hàng của chính mình (quán đặt và shipper giao đơn đó), tuyệt đối không thấy đơn của người khác.
    """
    user = request.user

    if user.is_staff or user.is_superuser:
        user_role = 'ADMIN'
        role_badge = 'Admin Quản Trị Hệ Thống'
        role_description = 'Toàn quyền CSDL: Xem tất cả quán ăn, toàn bộ đơn hàng và toàn bộ đội ngũ Shipper.'
        ds_don = DonHang.objects.all().order_by('-id')[:100]
        ds_kho = KhoHang.objects.all()
        ds_tai_xe = TaiXe.objects.filter(dang_lam_viec=True)

    elif hasattr(user, 'taixe') or TaiXe.objects.filter(user=user).exists():
        user_role = 'SHIPPER'
        tai_xe = user.taixe if hasattr(user, 'taixe') else TaiXe.objects.filter(user=user).first()
        role_badge = f'Tài Xế Shipper: {tai_xe.ten_tai_xe}'
        role_description = 'Chỉ hiển thị các đơn hàng được phân công cho bạn và lộ trình nhận món.'
        ds_don = DonHang.objects.filter(tai_xe=tai_xe).order_by('-id')
        ds_kho = KhoHang.objects.filter(id__in=ds_don.values_list('kho_xuat_phat_id', flat=True))
        ds_tai_xe = TaiXe.objects.filter(id=tai_xe.id)

    elif KhoHang.objects.filter(chu_so_huu=user).exists():
        user_role = 'B2B_PARTNER'
        my_shops = KhoHang.objects.filter(chu_so_huu=user)
        shop_names = ", ".join([s.ten_kho for s in my_shops])
        role_badge = f'Đối Tác B2B: {shop_names}'
        role_description = 'Bảo mật CSDL: Bạn chỉ có quyền xem đơn hàng và lộ trình giao của quán bạn.'
        ds_don = DonHang.objects.filter(kho_xuat_phat__in=my_shops).order_by('-id')
        ds_kho = my_shops
        ds_tai_xe = TaiXe.objects.filter(donhang__in=ds_don, dang_lam_viec=True).distinct()

    else:
        # Khách hàng thông thường
        user_role = 'KHACH_HANG'
        role_badge = f'Khách Hàng: {user.username}'
        role_description = 'Hiển thị các đơn hàng đang giao của bạn và vị trí shipper giao đồ ăn.'
        ds_don = DonHang.objects.filter(
            Q(khach_hang=user) | 
            Q(email_nguoi_nhan__iexact=user.email) | 
            Q(ten_nguoi_nhan__icontains=user.username)
        ).order_by('-id')
        ds_kho = KhoHang.objects.filter(id__in=ds_don.values_list('kho_xuat_phat_id', flat=True))
        ds_tai_xe = TaiXe.objects.filter(donhang__in=ds_don, dang_lam_viec=True).distinct()

    return render(request, 'gis.html', {
        'ds_don': ds_don,
        'ds_kho': ds_kho,
        'ds_tai_xe': ds_tai_xe,
        'user_role': user_role,
        'role_badge': role_badge,
        'role_description': role_description,
    })


@login_required(login_url='core:login')
def toi_uu_lo_trinh(request):
    """Thuật toán tối ưu hóa lộ trình giao hàng đường phố nhanh nhất (TSP)"""
    ds_tai_xe = TaiXe.objects.all()
    tai_xe_id = request.GET.get('tai_xe_id')

    if hasattr(request.user, 'taixe'):
        tx_dang_chon = request.user.taixe
    else:
        tx_dang_chon = TaiXe.objects.filter(id=tai_xe_id).first() if tai_xe_id else None

    ds_don = []
    don_hang_json = '[]'

    if tx_dang_chon:
        ds_don = DonHang.objects.filter(tai_xe=tx_dang_chon, trang_thai__in=['ĐANG VẬN CHUYỂN', 'CHỜ TÀI XẾ'])
        don_data = []
        for d in ds_don:
            don_data.append({
                'ma_don': d.ma_don,
                'ten': d.ten_nguoi_nhan,
                'dia_chi': d.dia_chi_nguoi_nhan,
                'lat': float(d.lat_khach),
                'lng': float(d.lng_khach),
                'loai_giao': d.loai_giao_hang,
                'tong_tien': float(d.tong_tien or 0)
            })
        don_hang_json = json.dumps(don_data)

    return render(request, 'optimize.html', {
        'ds_tai_xe': ds_tai_xe,
        'tx_dang_chon': tx_dang_chon,
        'ds_don': ds_don,
        'don_hang_json': don_hang_json,
    })


# ==============================================================================
# 5. GIAO DIỆN APP SHIPPER (TÍCH HỢP GPS và GIAO HÀNG HỎA TỐC)
# ==============================================================================

@login_required(login_url='core:login')
def app_shipper(request):
    """App dành cho Shipper với danh sách đơn giao thức ăn, nút GPS và định vị"""
    if hasattr(request.user, 'taixe'):
        tai_xe = request.user.taixe
    elif request.user.is_staff:
        tai_xe = TaiXe.objects.first()
    else:
        tai_xe = None

    if not tai_xe:
        messages.warning(request, "Tài khoản của bạn chưa được liên kết với hồ sơ Tài xế.")
        return redirect('core:home')

    don_hangs = DonHang.objects.filter(tai_xe=tai_xe).order_by('-id')

    return render(request, 'shipper_dashboard.html', {
        'tai_xe': tai_xe,
        'don_hangs': don_hangs
    })


@login_required(login_url='core:login')
def shipper_cap_nhat(request, don_id):
    """Shipper cập nhật trạng thái đơn (chờ nhận, đang giao, đã giao) + Tích lũy doanh thu + Cập nhật Mailbox"""
    if request.method == 'POST':
        don = get_object_or_404(DonHang, id=don_id)
        if hasattr(request.user, 'taixe') and don.tai_xe != request.user.taixe:
            return redirect('core:app_shipper')

        trang_thai_moi = request.POST.get('trang_thai')
        don.trang_thai = trang_thai_moi
        don.save()

        tai_xe_ten = request.user.taixe.ten_tai_xe if hasattr(request.user, 'taixe') else "Shipper"

        # Ghi nhật ký tiến trình vận chuyển
        LichSuKho.objects.create(
            don_hang=don,
            kho=don.kho_xuat_phat,
            trang_thai_buoc=f"SHIPPER CẬP NHẬT: {trang_thai_moi}",
            ghi_chu=f"Cập nhật bởi tài xế: {tai_xe_ten}"
        )

        fmt_tong_don = f"{don.tong_tien:,.0f}".replace(",", ".")

        # Nếu giao thành công -> Cộng doanh thu tích lũy cho tài xế và gửi mail
        if trang_thai_moi == 'ĐÃ GIAO THÀNH CÔNG':
            if hasattr(request.user, 'taixe'):
                tai_xe = request.user.taixe
                tai_xe.doanh_thu_tich_luy += (don.phi_van_chuyen + don.phu_phi_hoa_toc)
                tai_xe.tong_don_thang_nay += 1
                tai_xe.save()

            don.trang_thai_thanh_toan = 'DA_THANH_TOAN'
            don.save()

            # Gửi mail thông báo giao thành công qua Mailbox
            subject = f"🎉 Giao hàng thành công - Đơn hàng #{don.ma_don}"
            body = (
                f"Chào {don.ten_nguoi_nhan},\n\n"
                f"Đơn hàng #{don.ma_don} đã được Shipper {tai_xe_ten} giao thành công đến bạn tại địa chỉ:\n"
                f"{don.dia_chi_nguoi_nhan}.\n\n"
                f"Tổng tiền thanh toán: {fmt_tong_don}đ ({don.get_phuong_thuc_thanh_toan_display()}).\n"
                f"Chúc bạn thưởng thức bữa ăn ngon miệng!\n\n"
                f"Đội ngũ FoodDelivery."
            )
            gui_email_mailbox(subject, body, don.email_nguoi_nhan)
        else:
            # Gửi mail thông báo tiến độ hành trình qua Mailbox
            subject = f"🛵 [Shipper Cập Nhật] Đơn #{don.ma_don}: {trang_thai_moi}"
            body = (
                f"Chào {don.ten_nguoi_nhan},\n\n"
                f"Tài xế Shipper {tai_xe_ten} vừa cập nhật trạng thái đơn hàng #{don.ma_don}:\n"
                f"👉 TRẠNG THÁI HIỆN TẠI: {trang_thai_moi}\n"
                f"Quán chế biến: {don.kho_xuat_phat.ten_kho}\n\n"
                f"Theo dõi vị trí Shipper trên bản đồ tại: http://127.0.0.1:8000/chi-tiet/{don.ma_don}/\n\n"
                f"Trân trọng,\nĐội ngũ FoodDelivery."
            )
            gui_email_mailbox(subject, body, don.email_nguoi_nhan)

    return redirect('core:app_shipper')


# ==============================================================================
# 6. CỔNG API RESTFUL CHO KHÁCH HÀNG & ĐỐI TÁC B2B (MENU & ĐẶT MÓN & LIVE GPS)
# ==============================================================================

@api_view(['POST'])
def api_tao_don_hang(request):
    """
    Cổng API nhận đơn hàng trực tuyến (Khách hàng & B2B):
    - Đóng vai trò API truyền dữ liệu đơn hàng mỗi khi đặt
    - Tự động kiểm tra khoảng cách: nếu > 30km sẽ quét tìm chi nhánh gần nhất
    - Nếu không có chi nhánh hợp lệ trong 30km: Từ chối đơn và trả mã lỗi rõ ràng
    """
    serializer = B2BTaoDonHangSerializer(data=request.data)

    if serializer.is_valid():
        data = serializer.validated_data

        # Chọn quán xuất phát
        kho_id = data.get('kho_id')
        if kho_id:
            kho = KhoHang.objects.filter(id=kho_id).first()
        else:
            kho = KhoHang.objects.first()

        if not kho:
            return Response({"status": "error", "message": "Hệ thống chưa thiết lập Quán ăn / Nhà hàng xuất phát"}, status=status.HTTP_400_BAD_REQUEST)

        # Tính khoảng cách
        km = tinh_khoang_cach_haversine(kho.lat, kho.lng, data['lat_khach'], data['lng_khach'])

        # ⛔ KIỂM TRA BÁN KÍNH GIAO ĐỒ ĂN HỎA TỐC (TỐI ĐA 30KM)
        if km > 30.0:
            mon_ids = [int(m.get('mon_id')) for m in data.get('danh_sach_mon', []) if m.get('mon_id')]
            quan_gan, dist_moi = tim_quan_an_gan_nhat(data['lat_khach'], data['lng_khach'], max_km=30.0, mon_ids=mon_ids)
            if quan_gan:
                kho = quan_gan
                km = dist_moi
            else:
                return Response({
                    "status": "error",
                    "code": "DISTANCE_EXCEEDED",
                    "message": f"Khoảng cách giao hàng ({km:.1f} km) vượt quá bán kính tối đa cho phép giao hỏa tốc (30 km). Tiêu chuẩn đồ ăn không thể vận chuyển xe máy đường dài vì thức ăn sẽ bị nguội hỏng và cước ship phi thực tế!"
                }, status=status.HTTP_400_BAD_REQUEST)

        is_hoa_toc = (data.get('loai_giao_hang') == 'HOA_TOC')
        phi_ship, phu_phi = tinh_phi_ship_theo_km(km, is_hoa_toc)

        # Tạo đơn hàng
        don = DonHang.objects.create(
            khach_hang=request.user if request.user.is_authenticated else None,
            ten_nguoi_nhan=data['ten_nguoi_nhan'],
            sdt_nguoi_nhan=data['sdt_nguoi_nhan'],
            email_nguoi_nhan=data.get('email_nguoi_nhan', 'b2b_khach@gmail.com'),
            dia_chi_nguoi_nhan=data['dia_chi_nguoi_nhan'],
            lat_khach=data['lat_khach'],
            lng_khach=data['lng_khach'],
            kho_xuat_phat=kho,
            loai_giao_hang=data.get('loai_giao_hang', 'HOA_TOC'),
            phi_van_chuyen=Decimal(phi_ship),
            phu_phi_hoa_toc=Decimal(phu_phi),
            khoang_cach_km=km,
            ghi_chu=data.get('ghi_chu', 'Đơn hàng từ cổng API trực tuyến'),
            trang_thai='CHỜ TÀI XẾ'
        )

        # Gắn danh sách món nếu có
        danh_sach_mon = data.get('danh_sach_mon', [])
        tien_mon = Decimal(0)
        for m_item in danh_sach_mon:
            m_id = m_item.get('mon_id')
            m_qty = int(m_item.get('so_luong', 1))
            m_obj = MonAn.objects.filter(id=m_id).first()
            if m_obj:
                thanh_tien = m_obj.gia_hien_tai() * m_qty
                tien_mon += thanh_tien
                ChiTietDonHang.objects.create(
                    don_hang=don,
                    mon_an=m_obj,
                    so_luong=m_qty,
                    don_gia=m_obj.gia_hien_tai(),
                    thanh_tien=thanh_tien
                )

        # Áp dụng chính sách Freeship và voucher nghiệp vụ chuẩn TMĐT
        ma_voucher = data.get('ma_voucher', '')
        phi_ship_sau_giam, giam_gia_tong, thong_bao_voucher = ap_dung_voucher_nghiep_vu(ma_voucher, tien_mon, phi_ship)

        don.tien_mon_an = tien_mon
        don.giam_gia = giam_gia_tong
        don.tong_tien = max(Decimal(0), tien_mon + Decimal(phi_ship) + Decimal(phu_phi) - giam_gia_tong)
        don.save()

        # Tạo lịch sử tiếp nhận
        LichSuKho.objects.create(
            don_hang=don,
            kho=kho,
            trang_thai_buoc='BẾP TIẾP NHẬN',
            ghi_chu=f"Đơn hàng #{don.ma_don} được tiếp nhận tự động từ Cổng API Đặt Món."
        )

        # Gửi email thông báo Mailbox
        gui_email_mailbox(
            f"🔔 [API Đặt Món] Tiếp nhận đơn hàng #{don.ma_don}",
            f"Hệ thống vừa nhận đơn từ API.\nKhách: {don.ten_nguoi_nhan}\nĐịa chỉ: {don.dia_chi_nguoi_nhan}\nQuán chế biến: {kho.ten_kho}\nKhoảng cách: {km}km\nTổng tiền: {don.tong_tien:,.0f} đ",
            don.email_nguoi_nhan
        )

        return Response({
            "status": "success",
            "message": "Đã tiếp nhận đơn hàng thành công!",
            "ma_don": don.ma_don,
            "quan_xuat_phat": kho.ten_kho,
            "khoang_cach_km": km,
            "tong_tien": float(don.tong_tien),
            "qr_url": don.link_qr_vietqr(),
            "tracking_url": f"/chi-tiet/{don.ma_don}/"
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def api_cap_nhat_gps_shipper(request):
    """API cho phép thiết bị Shipper gửi tọa độ GPS hiện tại lên máy chủ theo thời gian thực"""
    lat = request.data.get('lat')
    lng = request.data.get('lng')
    shipper_id = request.data.get('shipper_id') or request.data.get('tai_xe_id')

    if not lat or not lng:
        return Response({"error": "Thiếu tọa độ lat, lng"}, status=status.HTTP_400_BAD_REQUEST)

    tx = None
    if shipper_id:
        tx = TaiXe.objects.filter(id=shipper_id).first()
    elif request.user.is_authenticated and hasattr(request.user, 'taixe'):
        tx = request.user.taixe

    if not tx:
        return Response({"error": "Không xác định được tài xế"}, status=status.HTTP_404_NOT_FOUND)

    tx.lat_hien_tai = float(lat)
    tx.lng_hien_tai = float(lng)
    tx.save()

    return Response({
        "status": "success",
        "message": f"Đã cập nhật vị trí GPS cho tài xế {tx.ten_tai_xe}",
        "lat": tx.lat_hien_tai,
        "lng": tx.lng_hien_tai
    })


@api_view(['GET'])
def api_danh_sach_mon(request):
    """API lấy danh sách thực đơn món ăn cho ứng dụng di động hoặc đối tác"""
    mon_ans = MonAn.objects.filter(is_con_mon=True)
    serializer = MonAnSerializer(mon_ans, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def api_tinh_phi_van_chuyen(request):
    """API tính cước phí và khoảng cách giữa 2 tọa độ kèm kiểm tra bán kính tối đa 30km"""
    kho_id = request.GET.get('kho_id')
    if kho_id:
        kho = KhoHang.objects.filter(id=kho_id).first()
        if kho and kho.lat and kho.lng:
            lat1 = float(kho.lat)
            lng1 = float(kho.lng)
        else:
            lat1 = float(request.GET.get('lat1', 10.7721))
            lng1 = float(request.GET.get('lng1', 106.6983))
    else:
        lat1 = float(request.GET.get('lat1', 10.7721))
        lng1 = float(request.GET.get('lng1', 106.6983))

    lat2 = float(request.GET.get('lat_khach') or request.GET.get('lat2') or 10.7769)
    lng2 = float(request.GET.get('lng_khach') or request.GET.get('lng2') or 106.7009)
    is_hoa_toc = request.GET.get('hoa_toc', 'true').lower() in ('true', '1') or request.GET.get('loai_giao_hang') == 'HOA_TOC'

    km = tinh_khoang_cach_haversine(lat1, lng1, lat2, lng2)
    phi_ship, phu_phi = tinh_phi_ship_theo_km(km, is_hoa_toc)

    co_the_giao = (km <= 30.0)
    thong_bao = "Khoảng cách hợp lệ cho dịch vụ giao đồ ăn hỏa tốc."
    quan_de_xuat = None

    if not co_the_giao:
        thong_bao = f"Khoảng cách {km}km vượt quá giới hạn giao đồ ăn hỏa tốc (tối đa 30km). Không thể giao xe máy đường dài vì thức ăn sẽ bị nguội hỏng và cước ship phi thực tế!"
        quan_gan, dist_gan = tim_quan_an_gan_nhat(lat2, lng2, max_km=30.0)
        if quan_gan:
            ship_gan, phu_phi_gan = tinh_phi_ship_theo_km(dist_gan, is_hoa_toc)
            quan_de_xuat = {
                'id': quan_gan.id,
                'ten': quan_gan.ten_kho,
                'dia_chi': quan_gan.dia_chi,
                'lat': quan_gan.lat,
                'lng': quan_gan.lng,
                'khoang_cach_km': dist_gan,
                'phi_van_chuyen': ship_gan + phu_phi_gan
            }

    return Response({
        'khoang_cach_km': km,
        'phi_van_chuyen': phi_ship,
        'phu_phi_hoa_toc': phu_phi,
        'tong_phi_giao_hang': phi_ship + phu_phi,
        'co_the_giao': co_the_giao,
        'max_km_cho_phep': 30.0,
        'thong_bao': thong_bao,
        'quan_de_xuat_gan_nhat': quan_de_xuat
    })


# ==============================================================================
# PHÂN HỆ ĐỐI TÁC B2B (QUÁN ĂN / NHÀ HÀNG): API MENU VÀ DASHBOARD BẢO MẬT
# ==============================================================================

@api_view(['GET'])
def api_b2b_thuc_don(request):
    """
    API đối tác B2B truyền dữ liệu thực đơn bán hàng:
    - Trả về danh sách món ăn của quán mình
    """
    shop_id = request.GET.get('shop_id')
    if shop_id:
        mon_qs = MonAn.objects.filter(kho_hang_id=shop_id)
    elif request.user.is_authenticated and KhoHang.objects.filter(chu_so_huu=request.user).exists():
        mon_qs = MonAn.objects.filter(kho_hang__chu_so_huu=request.user)
    else:
        mon_qs = MonAn.objects.all()

    serializer = MonAnSerializer(mon_qs, many=True)
    return Response({
        "status": "success",
        "total": mon_qs.count(),
        "menu": serializer.data
    })


@api_view(['POST'])
def api_b2b_cap_nhat_mon(request):
    """
    API đối tác B2B truyền dữ liệu thực đơn bán hàng (Thêm món mới / Cập nhật giá món ăn)
    """
    mon_id = request.data.get('mon_id')
    ten_mon = request.data.get('ten_mon')
    gia = request.data.get('gia')
    danh_muc_id = request.data.get('danh_muc_id')
    kho_hang_id = request.data.get('kho_hang_id')
    is_con_mon = request.data.get('is_con_mon', True)
    hinh_anh = request.data.get('hinh_anh', 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800')

    if not ten_mon or not gia:
        return Response({"status": "error", "message": "Vui lòng nhập tên món và giá bán!"}, status=status.HTTP_400_BAD_REQUEST)

    if mon_id:
        mon = MonAn.objects.filter(id=mon_id).first()
        if not mon:
            return Response({"status": "error", "message": "Không tìm thấy món ăn!"}, status=status.HTTP_404_NOT_FOUND)
        mon.ten_mon = ten_mon
        mon.gia = Decimal(gia)
        if danh_muc_id:
            mon.danh_muc_id = danh_muc_id
        if kho_hang_id:
            mon.kho_hang_id = kho_hang_id
        mon.is_con_mon = bool(is_con_mon)
        if hinh_anh:
            mon.hinh_anh = hinh_anh
        mon.save()
        action = "cập nhật"
    else:
        dm = DanhMucMonAn.objects.filter(id=danh_muc_id).first() or DanhMucMonAn.objects.first()
        if kho_hang_id:
            kho = KhoHang.objects.filter(id=kho_hang_id).first()
        elif request.user.is_authenticated and KhoHang.objects.filter(chu_so_huu=request.user).exists():
            kho = KhoHang.objects.filter(chu_so_huu=request.user).first()
        else:
            kho = KhoHang.objects.first()

        mon = MonAn.objects.create(
            ten_mon=ten_mon,
            gia=Decimal(gia),
            danh_muc=dm,
            kho_hang=kho,
            is_con_mon=bool(is_con_mon),
            hinh_anh=hinh_anh
        )
        action = "thêm mới"

    return Response({
        "status": "success",
        "message": f"Đối tác B2B đã {action} món ăn '{mon.ten_mon}' vào thực đơn bán hàng thành công!",
        "mon": MonAnSerializer(mon).data
    }, status=status.HTTP_201_CREATED if not mon_id else status.HTTP_200_OK)


@login_required(login_url='core:login')
def partner_dashboard(request):
    """
    Cổng Quản Trị Dành Riêng Cho Đối Tác B2B (Quán Ăn / Nhà Hàng):
    - Đảm bảo tính bảo mật CSDL: B2B chỉ có thể thấy toàn bộ đơn shop của mình và thực đơn của quán mình!
    - Cập nhật tiến độ nấu món tại Bếp (Bếp nhận đơn -> Đang nấu -> Xong bàn giao Shipper)
    - Đồng bộ và quản lý thực đơn bán hàng
    """
    if request.user.is_staff or request.user.is_superuser:
        my_shops = KhoHang.objects.all()
    else:
        my_shops = KhoHang.objects.filter(chu_so_huu=request.user)

    if not my_shops.exists():
        messages.warning(request, "Tài khoản của bạn chưa được liên kết với Quán Ăn / Nhà Hàng B2B nào. Vui lòng liên hệ Admin để tạo liên kết!")
        return redirect('core:home')

    shop_id = request.GET.get('shop_id')
    current_shop = my_shops.filter(id=shop_id).first() if shop_id else my_shops.first()

    # BẢO MẬT: CHỈ LẤY ĐƠN HÀNG THUỘC SHOP CỦA MÌNH!
    ds_don = DonHang.objects.filter(kho_xuat_phat=current_shop).order_by('-ngay_tao')
    ds_mon = MonAn.objects.filter(kho_hang=current_shop).order_by('-id')

    tong_don = ds_don.count()
    don_cho_bep = ds_don.filter(trang_thai='CHỜ TÀI XẾ').count()
    don_dang_giao = ds_don.filter(trang_thai='ĐANG VẬN CHUYỂN').count()
    don_hoan_thanh = ds_don.filter(trang_thai='ĐÃ GIAO THÀNH CÔNG').count()
    doanh_thu_mon = ds_don.filter(trang_thai='ĐÃ GIAO THÀNH CÔNG').aggregate(Sum('tien_mon_an'))['tien_mon_an__sum'] or Decimal(0)

    return render(request, 'partner_dashboard.html', {
        'my_shops': my_shops,
        'current_shop': current_shop,
        'ds_don': ds_don[:25],
        'ds_mon': ds_mon,
        'danh_mucs': DanhMucMonAn.objects.all(),
        'stats': {
            'tong_don': tong_don,
            'don_cho_bep': don_cho_bep,
            'don_dang_giao': don_dang_giao,
            'don_hoan_thanh': don_hoan_thanh,
            'doanh_thu_mon': doanh_thu_mon,
        }
    })


@login_required(login_url='core:login')
@require_POST
def api_b2b_bep_cap_nhat_don(request, don_id):
    """Đối tác B2B cập nhật tiến độ chế biến món tại bếp và đồng thời kích hoạt Mailbox"""
    don = get_object_or_404(DonHang, id=don_id)

    # Kiểm tra quyền sở hữu
    if not (request.user.is_staff or (don.kho_xuat_phat and don.kho_xuat_phat.chu_so_huu == request.user)):
        return JsonResponse({'success': False, 'message': 'Bạn không có quyền quản lý đơn của quán này!'}, status=403)

    hanh_dong = request.POST.get('hanh_dong', 'BẾP ĐANG NẤU')
    ghi_chu = request.POST.get('ghi_chu', '') or f"Quán {don.kho_xuat_phat.ten_kho} đã cập nhật tiến độ."

    LichSuKho.objects.create(
        don_hang=don,
        kho=don.kho_xuat_phat,
        trang_thai_buoc=hanh_dong,
        ghi_chu=ghi_chu
    )

    # Gửi email Mailbox thông báo tiến trình cho khách hàng
    mail_subject = f"🍲 [Quán Cập Nhật] Đơn #{don.ma_don}: {hanh_dong}"
    mail_body = (
        f"Xin chào {don.ten_nguoi_nhan},\n\n"
        f"Quán '{don.kho_xuat_phat.ten_kho}' vừa cập nhật tiến độ món ăn đơn hàng #{don.ma_don}:\n"
        f"👉 TIẾN TRÌNH: {hanh_dong}\n"
        f"Ghi chú bếp: {ghi_chu}\n\n"
        f"Theo dõi đơn hàng tại: http://127.0.0.1:8000/chi-tiet/{don.ma_don}/\n\n"
        f"Trân trọng,\nĐội ngũ FoodDelivery."
    )
    gui_email_mailbox(mail_subject, mail_body, don.email_nguoi_nhan)

    return JsonResponse({
        'success': True,
        'message': f'Đã cập nhật tiến độ món sang: {hanh_dong}!',
        'trang_thai_buoc': hanh_dong
    })


def check_new_orders(request):
    """Hàm mắt thần kiểm tra đơn hàng mới để rung chuông thông báo trên Header"""
    moi = DonHang.objects.filter(trang_thai='CHỜ TÀI XẾ').order_by('-id')
    data = {
        'count': moi.count(),
        'orders': [
            {'ma_don': d.ma_don, 'khach': d.ten_nguoi_nhan, 'ngay': d.ngay_tao.strftime('%H:%M')}
            for d in moi[:5]
        ]
    }
    return JsonResponse(data)


# ==============================================================================
# 7. QUẢN LÝ DÀNH CHO ADMIN (CRUD TÀI XẾ, KHO, MÓN ĂN, QUẢNG CÁO, ĐƠN HÀNG)
# ==============================================================================

@login_required(login_url='core:login')
def quan_ly_tai_xe(request):
    if not request.user.is_staff:
        return redirect('core:home')
    ds = TaiXe.objects.all().order_by('-id')
    q = request.GET.get('q', '').strip()
    if q:
        ds = ds.filter(Q(ten_tai_xe__icontains=q) | Q(sdt__icontains=q) | Q(bien_so__icontains=q))
    sort = request.GET.get('sort')
    if sort == 'ten_az':
        ds = ds.order_by('ten_tai_xe')
    elif sort == 'luong_cao':
        ds = ds.order_by('-doanh_thu_tich_luy')

    tong_so_tx = TaiXe.objects.count()
    dang_online = TaiXe.objects.filter(dang_lam_viec=True).count()
    ca_sang = TaiXe.objects.filter(ca_lam_viec='SANG').count()
    ca_toi = TaiXe.objects.filter(ca_lam_viec__in=['TOI', 'CHIEU', 'DEM']).count()
    tong_doanh_thu = TaiXe.objects.aggregate(Sum('doanh_thu_tich_luy'))['doanh_thu_tich_luy__sum'] or 0

    stats = {
        'tong_so_tx': tong_so_tx,
        'dang_online': dang_online,
        'ca_sang': ca_sang,
        'ca_toi': ca_toi,
        'tong_doanh_thu': tong_doanh_thu,
    }

    return render(request, 'admin_dashboard/quan_ly_tai_xe.html', {
        'ds_tai_xe': ds,
        'stats': stats,
        'q': q,
        'sort': sort,
        'active_menu': 'tai_xe',
    })


@login_required(login_url='core:login')
def them_tai_xe(request):
    if not request.user.is_staff:
        return redirect('core:home')
    if request.method == 'POST':
        form = TaiXeForm(request.POST)
        if form.is_valid():
            tx = form.save()
            messages.success(request, f"Đã thêm tài xế {tx.ten_tai_xe} ({tx.bien_so}) thành công!")
            return redirect('core:quan_ly_tai_xe')
        else:
            messages.error(request, "Dữ liệu tài xế không hợp lệ. Vui lòng kiểm tra lại!")
            return redirect('core:quan_ly_tai_xe')
    form = TaiXeForm()
    return render(request, 'form_taixe.html', {'form': form, 'title': 'Thêm Tài Xế Mới'})


@login_required(login_url='core:login')
def sua_tai_xe(request, id):
    if not request.user.is_staff:
        return redirect('core:home')
    taixe = get_object_or_404(TaiXe, id=id)
    if request.method == 'POST':
        form = TaiXeForm(request.POST, instance=taixe)
        if form.is_valid():
            form.save()
            messages.success(request, f"Đã cập nhật hồ sơ tài xế {taixe.ten_tai_xe} thành công!")
            return redirect('core:quan_ly_tai_xe')
        else:
            messages.error(request, "Thông tin cập nhật tài xế không hợp lệ. Vui lòng kiểm tra lại!")
            return redirect('core:quan_ly_tai_xe')
    form = TaiXeForm(instance=taixe)
    return render(request, 'form_taixe.html', {'form': form, 'title': f'Sửa Tài Xế: {taixe.ten_tai_xe}'})


@login_required(login_url='core:login')
def xoa_tai_xe(request, id):
    if not request.user.is_staff:
        return redirect('core:home')
    taixe = get_object_or_404(TaiXe, id=id)
    ten = taixe.ten_tai_xe
    taixe.delete()
    messages.success(request, f"Đã xóa tài xế {ten} khỏi hệ thống!")
    return redirect('core:quan_ly_tai_xe')


@login_required(login_url='core:login')
def quan_ly_kho(request):
    if not request.user.is_staff:
        return redirect('core:home')
    ds_kho = KhoHang.objects.all().order_by('id')
    q = request.GET.get('q', '').strip()
    if q:
        ds_kho = ds_kho.filter(Q(ten_kho__icontains=q) | Q(dia_chi__icontains=q))

    # Tính toán tải đơn hàng cho từng cơ sở kho
    for kho in ds_kho:
        kho.don_chua_giao = kho.donhang_set.exclude(trang_thai__in=['ĐÃ GIAO THÀNH CÔNG', 'ĐÃ HỦY']).count()
        if kho.suc_chua_toi_da and kho.suc_chua_toi_da > 0:
            kho.ty_le_tai = min(round((kho.don_chua_giao / kho.suc_chua_toi_da) * 100), 100)
        else:
            kho.ty_le_tai = 0

    tong_kho = KhoHang.objects.count()
    tong_don_dang_xu_ly = DonHang.objects.exclude(trang_thai__in=['ĐÃ GIAO THÀNH CÔNG', 'ĐÃ HỦY']).count()
    tong_suc_chua = KhoHang.objects.aggregate(Sum('suc_chua_toi_da'))['suc_chua_toi_da__sum'] or 0
    ty_le_tai = round((tong_don_dang_xu_ly / tong_suc_chua * 100), 1) if tong_suc_chua > 0 else 0

    stats = {
        'tong_kho': tong_kho,
        'tong_don_dang_xu_ly': tong_don_dang_xu_ly,
        'tong_suc_chua': tong_suc_chua,
        'ty_le_tai': ty_le_tai,
    }

    return render(request, 'admin_dashboard/quan_ly_kho.html', {
        'ds_kho': ds_kho,
        'stats': stats,
        'q': q,
        'active_menu': 'kho_hang',
    })


@login_required(login_url='core:login')
def them_kho(request):
    if not request.user.is_staff:
        return redirect('core:home')
    if request.method == 'POST':
        form = KhoHangForm(request.POST)
        if form.is_valid():
            kho = form.save()
            messages.success(request, f"Đã thêm cơ sở '{kho.ten_kho}' thành công!")
            return redirect('core:quan_ly_kho')
        else:
            messages.error(request, "Thông tin cơ sở không hợp lệ. Vui lòng kiểm tra lại!")
            return redirect('core:quan_ly_kho')
    form = KhoHangForm()
    return render(request, 'form_general.html', {'form': form, 'title': 'Thêm Bếp / Quán Mới', 'back_url': 'core:quan_ly_kho'})


@login_required(login_url='core:login')
def sua_kho(request, id):
    if not request.user.is_staff:
        return redirect('core:home')
    kho = get_object_or_404(KhoHang, id=id)
    if request.method == 'POST':
        form = KhoHangForm(request.POST, instance=kho)
        if form.is_valid():
            kho = form.save()
            messages.success(request, f"Đã cập nhật cơ sở '{kho.ten_kho}' thành công!")
            return redirect('core:quan_ly_kho')
        else:
            messages.error(request, "Dữ liệu cập nhật cơ sở không hợp lệ!")
            return redirect('core:quan_ly_kho')
    form = KhoHangForm(instance=kho)
    return render(request, 'form_general.html', {'form': form, 'title': f'Sửa Bếp/Quán: {kho.ten_kho}', 'back_url': 'core:quan_ly_kho'})


@login_required(login_url='core:login')
def xoa_kho(request, id):
    if not request.user.is_staff:
        return redirect('core:home')
    kho = get_object_or_404(KhoHang, id=id)
    ten = kho.ten_kho
    kho.delete()
    messages.success(request, f"Đã xóa cơ sở '{ten}' thành công!")
    return redirect('core:quan_ly_kho')


@login_required(login_url='core:login')
def quan_ly_don_hang(request):
    if not request.user.is_staff:
        return redirect('core:home')
    ds = DonHang.objects.all().select_related('kho_xuat_phat', 'tai_xe').order_by('-ngay_tao')
    q = request.GET.get('q', '').strip()
    if q:
        ds = ds.filter(Q(ma_don__icontains=q) | Q(ten_nguoi_nhan__icontains=q) | Q(sdt_nguoi_nhan__icontains=q))

    selected_trang_thai = request.GET.get('trang_thai', '').strip()
    if selected_trang_thai:
        ds = ds.filter(trang_thai=selected_trang_thai)

    selected_loai_giao = request.GET.get('loai_giao', '').strip()
    if selected_loai_giao:
        ds = ds.filter(loai_giao_hang=selected_loai_giao)

    selected_thanh_toan = request.GET.get('thanh_toan', '').strip()
    if selected_thanh_toan:
        ds = ds.filter(trang_thai_thanh_toan=selected_thanh_toan)

    sort = request.GET.get('sort')
    if sort == 'trang_thai':
        ds = ds.order_by('trang_thai')
    elif sort == 'hoa_toc':
        ds = ds.filter(loai_giao_hang='HOA_TOC')

    tong_don = DonHang.objects.count()
    don_dang_xu_ly = DonHang.objects.filter(trang_thai__in=['CHỜ TÀI XẾ', 'ĐANG VẬN CHUYỂN', 'ĐANG CHUẨN BỊ']).count()
    don_cho_tai_xe = DonHang.objects.filter(trang_thai='CHỜ TÀI XẾ').count()
    don_hoa_toc = DonHang.objects.filter(loai_giao_hang='HOA_TOC').count()
    don_thanh_cong = DonHang.objects.filter(trang_thai='ĐÃ GIAO THÀNH CÔNG').count()
    ty_le_thanh_cong = round((don_thanh_cong / tong_don * 100), 1) if tong_don > 0 else 0

    stats = {
        'tong_don': tong_don,
        'don_dang_xu_ly': don_dang_xu_ly,
        'don_cho_tai_xe': don_cho_tai_xe,
        'don_hoa_toc': don_hoa_toc,
        'don_thanh_cong': don_thanh_cong,
        'ty_le_thanh_cong': ty_le_thanh_cong,
    }

    all_kho = KhoHang.objects.all().order_by('ten_kho')
    all_tai_xe = TaiXe.objects.filter(dang_lam_viec=True).order_by('ten_tai_xe')

    return render(request, 'admin_dashboard/quan_ly_don_hang.html', {
        'ds_don': ds,
        'stats': stats,
        'q': q,
        'selected_trang_thai': selected_trang_thai,
        'selected_loai_giao': selected_loai_giao,
        'selected_thanh_toan': selected_thanh_toan,
        'all_kho': all_kho,
        'all_tai_xe': all_tai_xe,
        'active_menu': 'don_hang',
    })


@login_required(login_url='core:login')
def them_don_hang(request):
    if not request.user.is_staff:
        return redirect('core:home')
    form = DonHangForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        don = form.save()
        messages.success(request, f"Đã tạo mới đơn hàng #{don.ma_don} thành công!")
        gui_email_mailbox(
            f"📦 ĐƠN HÀNG MỚI #{don.ma_don}",
            f"Admin vừa tạo đơn mới.\nKhách: {don.ten_nguoi_nhan}\nĐịa chỉ: {don.dia_chi_nguoi_nhan}",
            settings.DEFAULT_FROM_EMAIL
        )
        return redirect('core:quan_ly_don_hang')

    return render(request, 'form_general.html', {
        'form': form,
        'title': 'Tạo Đơn Hàng Mới',
        'back_url': 'core:quan_ly_don_hang'
    })


@login_required(login_url='core:login')
def sua_don_hang(request, id):
    if not request.user.is_staff:
        return redirect('core:home')
    don = get_object_or_404(DonHang, id=id)
    form = DonHangForm(request.POST or None, instance=don)
    if form.is_valid():
        form.save()
        messages.success(request, f"Đã cập nhật đơn hàng #{don.ma_don} thành công!")
        return redirect('core:quan_ly_don_hang')
    return render(request, 'form_general.html', {'form': form, 'title': f'Cập nhật Đơn: {don.ma_don}', 'back_url': 'core:quan_ly_don_hang'})


@login_required(login_url='core:login')
def xoa_don_hang(request, id):
    if not request.user.is_staff:
        return redirect('core:home')
    don = get_object_or_404(DonHang, id=id)
    ma_don = don.ma_don
    don.delete()
    messages.success(request, f"Đã xóa vĩnh viễn đơn hàng #{ma_don}!")
    return redirect('core:quan_ly_don_hang')


@login_required(login_url='core:login')
def xac_nhan_thanh_toan_don(request, ma_don):
    """Admin hoặc thu ngân xác nhận đã nhận thanh toán QR/Chuyển khoản"""
    don = get_object_or_404(DonHang, ma_don=ma_don)
    don.trang_thai_thanh_toan = 'DA_THANH_TOAN'
    don.save()

    gui_email_mailbox(
        f"💰 Xác nhận thanh toán thành công đơn #{don.ma_don}",
        f"Hệ thống đã xác nhận thanh toán thành công số tiền {don.tong_tien:,.0f} đ cho đơn hàng #{don.ma_don}.\nCảm ơn bạn!",
        don.email_nguoi_nhan
    )
    messages.success(request, f"Đã xác nhận thanh toán thành công cho đơn #{don.ma_don}!")
    return redirect('core:chi_tiet', ma_don=ma_don)


@login_required(login_url='core:login')
def quan_ly_tai_khoan(request):
    if not request.user.is_staff:
        return redirect('core:home')
    ds_tk = User.objects.all().order_by('-id')
    q = request.GET.get('q', '').strip()
    if q:
        ds_tk = ds_tk.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))

    tong_user = User.objects.count()
    admin_count = User.objects.filter(is_staff=True).count()
    shipper_count = User.objects.filter(taixe__isnull=False).count()
    customer_count = User.objects.filter(is_staff=False, taixe__isnull=True).count()

    stats = {
        'tong_user': tong_user,
        'admin_count': admin_count,
        'shipper_count': shipper_count,
        'customer_count': customer_count,
    }

    return render(request, 'admin_dashboard/quan_ly_tai_khoan.html', {
        'ds_tai_khoan': ds_tk,
        'stats': stats,
        'q': q,
        'active_menu': 'tai_khoan',
    })


@login_required(login_url='core:login')
def them_tai_khoan(request):
    if not request.user.is_staff:
        return redirect('core:home')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        is_staff = request.POST.get('is_staff') in ['on', 'true', '1', True]

        if not username or not password:
            messages.error(request, "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")
            return redirect('core:quan_ly_tai_khoan')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Tên đăng nhập '{username}' đã tồn tại!")
            return redirect('core:quan_ly_tai_khoan')

        User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff
        )
        role_label = "Quản Trị Viên (Staff)" if is_staff else "Khách Hàng/Shipper"
        messages.success(request, f"Đã tạo tài khoản '{username}' ({role_label}) thành công!")
        return redirect('core:quan_ly_tai_khoan')

    form = TaiKhoanForm(request.POST or None)
    return render(request, 'form_taikhoan.html', {'form': form, 'title': 'Tạo Tài Khoản Mới', 'back_url': 'core:quan_ly_tai_khoan'})


@login_required(login_url='core:login')
def sua_tai_khoan(request, id):
    if not request.user.is_staff:
        return redirect('core:home')
    tk = get_object_or_404(User, id=id)
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '').strip()
        is_staff = request.POST.get('is_staff') in ['on', 'true', '1', True]
        is_active = request.POST.get('is_active') in ['on', 'true', '1', True]

        tk.email = email
        tk.first_name = first_name
        tk.last_name = last_name
        tk.is_staff = is_staff
        tk.is_active = is_active
        if password:
            tk.set_password(password)
        tk.save()
        messages.success(request, f"Đã cập nhật tài khoản '{tk.username}' thành công!")
        return redirect('core:quan_ly_tai_khoan')

    form = TaiKhoanForm(request.POST or None, instance=tk)
    return render(request, 'form_taikhoan.html', {'form': form, 'title': f'Sửa Tài Khoản: {tk.username}', 'back_url': 'core:quan_ly_tai_khoan'})


@login_required(login_url='core:login')
def xoa_tai_khoan(request, id):
    if not request.user.is_staff:
        return redirect('core:home')
    tk = get_object_or_404(User, id=id)
    if tk.id == request.user.id:
        messages.error(request, "Không thể xóa chính tài khoản bạn đang đăng nhập!")
    else:
        uname = tk.username
        tk.delete()
        messages.success(request, f"Đã xóa tài khoản '{uname}' thành công!")
    return redirect('core:quan_ly_tai_khoan')


def export_excel(request):
    """Xuất danh sách đơn hàng ra file Excel"""
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="Danh_sach_don_hang_FoodDelivery.xlsx"'

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Đơn Hàng"

    columns = ['Mã Đơn', 'Khách Hàng', 'SĐT', 'Địa Chỉ', 'Loại Giao', 'Tổng Tiền (VNĐ)', 'Thanh Toán', 'Trạng Thái']
    ws.append(columns)

    queryset = DonHang.objects.all().order_by('-id')
    for dh in queryset:
        ws.append([
            dh.ma_don,
            dh.ten_nguoi_nhan,
            dh.sdt_nguoi_nhan,
            dh.dia_chi_nguoi_nhan,
            dh.get_loai_giao_hang_display(),
            float(dh.tong_tien or 0),
            dh.get_trang_thai_thanh_toan_display(),
            dh.trang_thai
        ])

    wb.save(response)
    return response


@login_required(login_url='core:login')
def cap_nhat_kho(request, don_id):
    if request.method == 'POST':
        don = get_object_or_404(DonHang, id=don_id)
        kho_id = request.POST.get('kho_id')
        hanh_dong = request.POST.get('hanh_dong')
        kho = get_object_or_404(KhoHang, id=kho_id)

        LichSuKho.objects.create(
            don_hang=don,
            kho=kho,
            trang_thai_buoc=hanh_dong,
            ghi_chu=f"Đơn hàng {hanh_dong.lower()} tại {kho.ten_kho}"
        )
        don.trang_thai = f"ĐÃ {hanh_dong} - {kho.ten_kho}"
        don.save()

    return redirect('core:quan_ly_don_hang')


@login_required(login_url='core:login')
def quan_ly_lich_su(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Bạn không có quyền truy cập trang quản trị!")
        return redirect('core:home')

    ds = LichSuKho.objects.select_related('don_hang', 'kho').all().order_by('-thoi_gian')
    q = request.GET.get('q', '').strip()
    kho_id = request.GET.get('kho', '').strip()
    action = request.GET.get('action', '').strip()

    if q:
        ds = ds.filter(
            Q(don_hang__ma_don__icontains=q) | 
            Q(trang_thai_buoc__icontains=q) | 
            Q(ghi_chu__icontains=q) |
            Q(kho__ten_kho__icontains=q) |
            Q(don_hang__ten_nguoi_nhan__icontains=q)
        )
    if kho_id:
        ds = ds.filter(kho_id=kho_id)
    if action:
        ds = ds.filter(trang_thai_buoc__icontains=action)

    today = timezone.now().date()
    tong_lich_su = LichSuKho.objects.count()
    today_lich_su = LichSuKho.objects.filter(thoi_gian__date=today).count()
    tong_kho = KhoHang.objects.count()
    don_dang_giao = DonHang.objects.filter(trang_thai='ĐANG VẬN CHUYỂN').count()

    danh_sach_don = DonHang.objects.all().order_by('-ngay_tao')[:50]
    danh_sach_kho = KhoHang.objects.all().order_by('ten_kho')

    context = {
        'active_menu': 'lich_su',
        'title': 'Nhật Ký Luân Chuyển Kho',
        'ds_lich_su': ds,
        'q': q,
        'selected_kho': kho_id,
        'selected_action': action,
        'danh_sach_don': danh_sach_don,
        'danh_sach_kho': danh_sach_kho,
        'stats': {
            'tong_lich_su': tong_lich_su,
            'today_lich_su': today_lich_su,
            'tong_kho': tong_kho,
            'don_dang_giao': don_dang_giao,
        }
    }
    return render(request, 'admin_dashboard/quan_ly_lich_su.html', context)


@login_required(login_url='core:login')
def them_lich_su(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Bạn không có quyền quản trị!")
        return redirect('core:home')

    if request.method == 'POST':
        form = LichSuKhoForm(request.POST)
        if form.is_valid():
            log = form.save()
            action_map = {
                'BÀN GIAO SHIPPER': 'ĐANG VẬN CHUYỂN',
                'ĐANG LUÂN CHUYỂN': 'ĐANG VẬN CHUYỂN',
                'GIAO THÀNH CÔNG': 'ĐÃ GIAO THÀNH CÔNG',
            }
            if log.trang_thai_buoc in action_map and log.don_hang:
                log.don_hang.trang_thai = action_map[log.trang_thai_buoc]
                log.don_hang.save()

            messages.success(request, f"Đã ghi nhận nhật ký mới cho đơn #{log.don_hang.ma_don}!")

            is_ajax = (
                request.headers.get('x-requested-with') == 'XMLHttpRequest' or 
                request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' or 
                request.POST.get('ajax') == '1'
            )
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': f"Đã ghi nhật ký cho đơn #{log.don_hang.ma_don}!",
                    'ma_don': log.don_hang.ma_don,
                    'action': log.trang_thai_buoc,
                })

            redirect_to = request.POST.get('next') or 'core:quan_ly_lich_su'
            return redirect(redirect_to)
        else:
            messages.error(request, "Dữ liệu nhập vào chưa hợp lệ, vui lòng kiểm tra lại!")

    return redirect('core:quan_ly_lich_su')


@login_required(login_url='core:login')
def xoa_lich_su(request, id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Bạn không có quyền quản trị!")
        return redirect('core:home')

    log = get_object_or_404(LichSuKho, id=id)
    ma_don = log.don_hang.ma_don
    log.delete()
    messages.success(request, f"Đã xóa dòng nhật ký của đơn #{ma_don} thành công!")

    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or 
        request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' or 
        request.GET.get('ajax') == '1'
    )
    if is_ajax:
        return JsonResponse({'success': True, 'message': 'Đã xóa nhật ký thành công!'})

    return redirect('core:quan_ly_lich_su')


def partner_demo_tao_don(request):
    """Cổng đối tác B2B (ShopeeFood, TikTok Shop) giả lập đẩy đơn tự động vào hệ thống"""
    ds_kho = KhoHang.objects.all()
    ds_mon = MonAn.objects.filter(is_con_mon=True)

    if request.method == 'POST':
        ten = request.POST.get('ten_nguoi_nhan')
        sdt = request.POST.get('sdt_nguoi_nhan')
        dia_chi = request.POST.get('dia_chi_nguoi_nhan')
        lat = float(request.POST.get('lat_khach', 10.7769))
        lng = float(request.POST.get('lng_khach', 106.7009))
        kho_id = request.POST.get('kho_xuat_phat')
        khoi_luong = float(request.POST.get('khoi_luong', 1.0))
        loai_giao_hang = request.POST.get('loai_giao_hang', 'HOA_TOC')

        kho_gui = get_object_or_404(KhoHang, id=kho_id)
        km = tinh_khoang_cach_haversine(kho_gui.lat, kho_gui.lng, lat, lng)
        is_hoa_toc = (loai_giao_hang == 'HOA_TOC')
        phi_ship, phu_phi = tinh_phi_ship_theo_km(km, is_hoa_toc)

        don = DonHang.objects.create(
            ten_nguoi_nhan=ten,
            sdt_nguoi_nhan=sdt,
            dia_chi_nguoi_nhan=dia_chi,
            lat_khach=lat,
            lng_khach=lng,
            khoi_luong=khoi_luong,
            kho_xuat_phat=kho_gui,
            loai_giao_hang=loai_giao_hang,
            phi_van_chuyen=Decimal(phi_ship),
            phu_phi_hoa_toc=Decimal(phu_phi),
            khoang_cach_km=km,
            tong_tien=Decimal(phi_ship + phu_phi + 50000),
            tien_mon_an=Decimal(50000),
            trang_thai='CHỜ TÀI XẾ'
        )

        LichSuKho.objects.create(
            don_hang=don,
            kho=kho_gui,
            trang_thai_buoc='NHẬP KHO',
            ghi_chu=f"Đơn hàng #{don.ma_don} được khởi tạo từ Cổng kết nối Đối tác B2B (Demo)."
        )

        return render(request, 'partner_success.html', {'don': don})

    return render(request, 'partner_demo.html', {'ds_kho': ds_kho, 'ds_mon': ds_mon})


# ==============================================================================
# 13. TÍNH NĂNG KHÁCH HÀNG: LỊCH SỬ ĐƠN HÀNG, ĐẶT LẠI MÓN VÀ KHO VOUCHER
# ==============================================================================

@login_required(login_url='core:login')
def lich_su_don_hang(request):
    """
    Trang Lịch sử đơn hàng của tôi & Đặt lại đơn hàng (My Orders & Re-order):
    - Bắt buộc đăng nhập để bảo mật thông tin đơn hàng cá nhân
    - Khách hàng chỉ xem được danh sách đơn hàng của chính tài khoản mình
    - Tra cứu theo SĐT, mã đơn hàng hoặc trạng thái đơn
    - 1-Click Re-order nạp lại giỏ hàng và mở checkout
    - Modal hóa đơn điện tử E-Invoice
    """
    user = request.user
    sdt = request.GET.get('sdt', '').strip()
    ma_don = request.GET.get('ma_don', '').strip()
    trang_thai = request.GET.get('trang_thai', '').strip()

    if user.is_staff or user.is_superuser:
        qs = DonHang.objects.all().order_by('-ngay_tao')
    else:
        qs = DonHang.objects.filter(
            Q(khach_hang=user) | 
            Q(email_nguoi_nhan__iexact=user.email) | 
            Q(ten_nguoi_nhan__icontains=user.username)
        ).order_by('-ngay_tao')

    if sdt:
        qs = qs.filter(sdt_nguoi_nhan__icontains=sdt)
    if ma_don:
        qs = qs.filter(ma_don__icontains=ma_don)

    if trang_thai:
        qs = qs.filter(trang_thai__icontains=trang_thai)

    paginator = Paginator(qs, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    tong_don = qs.count()
    tong_chi_tieu = qs.aggregate(tong=Sum('tong_tien'))['tong'] or 0

    return render(request, 'my_orders.html', {
        'orders': page_obj,
        'sdt': sdt,
        'ma_don': ma_don,
        'trang_thai': trang_thai,
        'tong_don': tong_don,
        'tong_chi_tieu': tong_chi_tieu,
    })


def api_don_hang_items(request, ma_don):
    """API lấy danh sách các món trong đơn hàng để phục vụ 1-Click Đặt Lại Món (Re-order)"""
    don = get_object_or_404(DonHang, ma_don=ma_don)
    items = []
    for ct in don.chi_tiet_mon.all():
        mon = ct.mon_an
        items.append({
            'id': mon.id,
            'name': mon.ten_mon,
            'price': float(ct.don_gia),
            'quantity': ct.so_luong,
            'img': mon.hinh_anh,
            'kho_id': mon.kho_hang.id if mon.kho_hang else 1,
            'kho_name': mon.kho_hang.ten_kho if mon.kho_hang else 'Bếp trung tâm'
        })
    return JsonResponse({
        'status': 'success',
        'ma_don': don.ma_don,
        'items': items,
        'count': len(items)
    })


def api_danh_sach_voucher(request):
    """API lấy danh sách các mã giảm giá và voucher khả dụng từ Kho Voucher với đầy đủ điều kiện nghiệp vụ"""
    vouchers = QuangCao.objects.filter(kich_hoat=True).exclude(ma_voucher='').order_by('-giam_gia_phan_tram')
    data = []
    for v in vouchers:
        loai_voucher = 'PHAN_TRAM'
        if 'FREESHIP' in v.ma_voucher.upper():
            loai_voucher = 'FREESHIP'
        elif v.giam_gia_phan_tram == 0:
            loai_voucher = 'TIEN_MAT'

        # Quy tắc nghiệp vụ chi tiết cho từng mã
        if v.ma_voucher == 'HOATOC50':
            min_order = 80000
            max_discount = 40000
            tag_type = 'HỎA TỐC'
            dieu_kien_text = 'Đơn từ 80.000đ • Tối đa 40.000đ'
            hsd_text = 'HSD: 31/10/2026 (Còn 8 ngày)'
            progress_pct = 78
        elif v.ma_voucher == 'FREESHIP0D':
            min_order = 100000
            max_discount = 30000
            tag_type = 'FREESHIP'
            dieu_kien_text = 'Đơn từ 100.000đ • Trợ giá ship 30.000đ'
            hsd_text = 'HSD: 31/10/2026 (Còn 8 ngày)'
            progress_pct = 85
        elif v.ma_voucher == 'GONGCHA29K':
            min_order = 60000
            max_discount = 25000
            tag_type = 'QUÁN TÀI TRỢ'
            dieu_kien_text = 'Đơn từ 60.000đ • Tối đa 25.000đ'
            hsd_text = 'HSD: 05/11/2026 (Còn 13 ngày)'
            progress_pct = 52
        elif v.ma_voucher == 'B2BSALE':
            min_order = 150000
            max_discount = 50000
            tag_type = 'ĐỐI TÁC B2B'
            dieu_kien_text = 'Đơn từ 150.000đ • Tối đa 50.000đ'
            hsd_text = 'HSD: 15/11/2026 (Còn 23 ngày)'
            progress_pct = 40
        else:
            min_order = 50000
            max_discount = 30000
            tag_type = 'GIẢM GIÁ'
            dieu_kien_text = f'Đơn từ {min_order:,.0f}đ • Tối đa {max_discount:,.0f}đ'
            hsd_text = 'HSD: 31/10/2026'
            progress_pct = 60

        data.append({
            'id': v.id,
            'ma_voucher': v.ma_voucher,
            'giam_gia_phan_tram': v.giam_gia_phan_tram,
            'loai_voucher': loai_voucher,
            'tag_type': tag_type,
            'tieu_de': v.tieu_de,
            'mo_ta': v.mo_ta or f"Giảm ngay {v.giam_gia_phan_tram}% cho đơn hàng",
            'dieu_kien': dieu_kien_text,
            'min_order': min_order,
            'max_discount': max_discount,
            'hsd': hsd_text,
            'da_dung_phan_tram': progress_pct,
        })
    return JsonResponse({
        'status': 'success',
        'vouchers': data
    })
