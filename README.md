# 🍔 FoodDelivery & Express Logistics Pro
> **Nền tảng Đặt Món Trực Tuyến, Thương Mại Điện Tử & Điều Phối Giao Hàng Hỏa Tốc**  
> *Xây dựng trên nền tảng Django, Leaflet GIS, PostgreSQL / SQLite và Kiến trúc RESTful B2B API.*

---

## 📋 Giới thiệu Dự án

**FoodDelivery & Express Logistics Pro** là hệ thống toàn diện kết hợp giữa **Thương mại điện tử ẩm thực (Food Delivery)** và **Hệ thống điều phối vận tải logistics thông minh (Express Logistics Hub)**. 

Hệ thống giải quyết trọn vẹn bài toán từ khâu khách hàng duyệt thực đơn, đặt món trực tuyến, thanh toán qua mã VietQR động, gửi thông báo qua Mailbox, cho đến khâu điều phối Shipper theo thuật toán tuyến đường nhanh nhất và theo dõi lộ trình thời gian thực trên bản đồ số GIS.

---

## ✨ Các Phân Hệ & Nghiệp Vụ Chính

### 1. 🍱 Cổng Đặt Món Trực Tuyến & Giỏ Hàng TMĐT
- **Thực đơn phong phú**: Phân loại theo danh mục (Cơm, Trà sữa, Fastfood, Bún/Phở, Tráng miệng...), hỗ trợ tìm kiếm từ khóa và sắp xếp (bán chạy nhất, giá tăng/giảm).
- **Giỏ hàng trượt thông minh (Slide-Over Cart)**: Lưu trữ giỏ hàng, cập nhật số lượng tức thời, hiển thị badge số lượng realtime trên toàn bộ hệ thống.
- **Quảng cáo & Ads TMĐT**: Hệ thống banner slider, mã giảm giá voucher (`GIAM10`, `FREESHIP`), tính toán doanh thu GMV, hoa hồng sàn và doanh thu quảng cáo tài trợ.

### 2. ⚡ Giao Hàng Hỏa Tốc & Tính Cước Tự Động
- **Tính toán cước phí theo km**: Tự động tính khoảng cách thực tế từ vị trí Quán ăn / Bếp trung tâm (Cloud Kitchen) đến địa chỉ người nhận.
- **Tùy chọn vận chuyển**:
  - `⚡ Giao Hỏa Tốc (15 - 25 phút)`: Ưu tiên điều phối Shipper gần quán nhất, cộng phụ phí hỏa tốc.
  - `🛵 Giao Tiêu Chuẩn (30 - 45 phút)`: Cước phí tiết kiệm theo khoảng cách.

### 3. 💳 Thanh Toán VietQR Động & Cổng Mailbox
- **Mã VietQR chuẩn ngân hàng**: Tự động sinh link ảnh VietQR động chứa đúng số tiền, số tài khoản và cú pháp thanh toán theo mã đơn hàng.
- **Hỗ trợ đa phương thức**: VietQR, Ví điện tử MoMo, Tiền mặt khi nhận hàng (COD).
- **Hệ thống Mailbox (Mailtrap / SMTP)**:
  - Tự động gửi email xác nhận đặt hàng thành công kèm chi tiết món ăn và tổng thanh toán.
  - Tự động gửi email xác nhận thanh toán thành công.
  - Tự động gửi email thông báo khi Shipper hoàn thành chuyến giao hàng.

### 4. 🛵 Giả Lập Ứng Dụng Di Động Shipper
- Giao diện thiết kế chuẩn Mobile App cho tài xế.
- Hiển thị danh sách đơn hàng cần giao theo từng ca làm việc (Sáng, Chiều, Đêm).
- Nút **"Gửi GPS Live"**: Tự động lấy tọa độ GPS từ trình duyệt điện thoại và gửi lên máy chủ để cập nhật vị trí thời gian thực.
- Cập nhật trạng thái đơn: *Đang đi giao*, *Đã giao thành công*, *Khách hủy / Trả về quán*.

### 5. 🗺️ Bản Đồ Số GIS & Tracking Chi Tiết
- Tích hợp thư viện bản đồ **Leaflet** và dịch vụ định tuyến **OSRM**.
- Định vị trực quan các Quán ăn / Bếp trung tâm, vị trí khách hàng và vị trí di chuyển của Shipper.
- Xem chi tiết hành trình đơn hàng, nhật ký luân chuyển (Nhập bếp -> Bàn giao Shipper -> Giao thành công).

### 6. 🌐 Cổng Đối Tác B2B RESTful API
- Xây dựng API riêng biệt cho đối tác doanh nghiệp tích hợp gửi hàng:
  - `POST /api/b2b/don-hang/tao/`: Tạo đơn vận chuyển từ hệ thống đối tác.
  - `GET /api/tinh-phi-ship/`: Tính toán trước cước phí theo khoảng cách và loại hình giao vận.
  - `GET /api/mon-an/`: Lấy danh sách thực đơn và món ăn còn phục vụ.
  - `POST /api/shipper/cap-nhat-gps/`: API tiếp nhận tọa độ GPS thời gian thực từ shipper.
- Trang giao diện **Partner Demo (`/partner-demo/`)** cho phép đối tác chọn vị trí trực quan trên bản đồ để thử nghiệm gọi API.

### 7. 🗄️ Cơ Sở Dữ Liệu PostgreSQL & Dự Phòng Tự Động
- Cấu hình kết nối **PostgreSQL (port 5432)** chuẩn Enterprise.
- **Cơ chế Fallback thông minh**: Khi máy tính chưa bật PostgreSQL, hệ thống tự động nhận diện qua socket check và kích hoạt SQLite dự phòng, đảm bảo code luôn chạy được ngay mà không báo lỗi sập ứng dụng.
- **Lệnh tạo dữ liệu tự động 100%**:
  ```bash
  python manage.py seed_data
  ```
  Tự động nạp sẵn cơ sở nhà hàng, tài xế, thực đơn món ăn, banner quảng cáo và các đơn hàng mẫu hoàn chỉnh.

---

## 🛠️ Công Nghệ Sử Dụng

| Thành Phần | Công Nghệ & Thư Viện |
|---|---|
| **Backend** | Python 3.10+, Django 6.1.2 |
| **API** | Django REST Framework (DRF) |
| **Frontend** | HTML5 Semantic, CSS3 Modern (Glassmorphism, Flexbox, Grid), JavaScript ECMAScript 6 |
| **Bản đồ & Định vị** | Leaflet JS, Leaflet Routing Machine, OpenStreetMap, OSRM Engine |
| **Thư viện UI** | FontAwesome 6, Swiper JS 11, Chart.js, Google Fonts (Be Vietnam Pro) |
| **Email Service** | Django Core Mailbox, Mailtrap SMTP Sandbox |
| **Cơ sở dữ liệu** | PostgreSQL 15+ / SQLite3 |
| **Báo cáo & Tiện ích** | Openpyxl (Xuất Excel), Pandas |

---

## 📁 Cấu Trúc Thư Mục Dự Án

```
├── LogisticsProject/         # Thư mục cấu hình chính Django (settings, urls, wsgi, asgi)
├── core/                     # App nghiệp vụ chính
│   ├── management/commands/  # Custom command (seed_data.py tạo dữ liệu tự động)
│   ├── models.py             # Schema CSDL (KhoHang, DanhMuc, MonAn, QuangCao, TaiXe, DonHang...)
│   ├── views.py              # Xử lý Controller, Logic TMĐT, Mailbox, B2B API
│   ├── urls.py               # Định tuyến các endpoint và view
│   ├── forms.py              # Form nhập liệu
│   └── serializers.py        # Serializer cho RESTful API
├── templates/                # Giao diện HTML (Jinja/Django Template)
│   ├── base.html             # Layout gốc, thanh navbar, Slide-over Cart drawer
│   ├── home.html             # Trang chủ, Hero Banner, Thực đơn nổi bật, Biểu đồ TMĐT
│   ├── menu.html             # Trang thực đơn đầy đủ & lọc danh mục
│   ├── checkout.html         # Trang đặt hàng, tính cước theo km & chọn VietQR
│   ├── order_success.html    # Trang thông báo đặt hàng thành công & quét mã VietQR
│   ├── gis.html              # Bản đồ GIS giám sát toàn bộ đội xe & đơn hàng
│   ├── map.html              # Chi tiết lộ trình đơn hàng & dẫn đường OSRM
│   ├── shipper_dashboard.html# Giao diện App Shipper di động & Live GPS
│   ├── partner_demo.html     # Cổng gửi đơn B2B dành cho đối tác
│   ├── order_manager.html    # Bảng điều hành quản lý đơn hàng
│   └── ...
├── static/                   # Tài nguyên tĩnh (CSS, JS, ảnh)
├── manage.py                 # Django CLI Tool
└── requirements.txt          # Danh sách thư viện Python
```

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Thử

### 1. Kích hoạt môi trường ảo & cài đặt thư viện
```bash
# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### 2. Chạy Migration CSDL
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Tự động khởi tạo dữ liệu mẫu (Khuyến nghị)
Chạy lệnh sau để hệ thống tự sinh đầy đủ danh mục, quán ăn, thực đơn món, shipper và đơn hàng mẫu:
```bash
python manage.py seed_data
```

### 4. Tạo tài khoản quản trị (Admin)
```bash
python manage.py createsuperuser
```
*(Hoặc sử dụng tài khoản mẫu đã tạo sẵn: `admin` / mật khẩu `admin123`)*

### 5. Khởi chạy máy chủ
```bash
python manage.py runserver
```

---

## 📌 Danh Sách Các Đường Dẫn Quan Trọng

| Chức năng | Đường dẫn |
|---|---|
| **Trang chủ & Dashboard TMĐT** | `http://127.0.0.1:8000/` |
| **Thực đơn ẩm thực & Giỏ hàng** | `http://127.0.0.1:8000/thuc-don/` |
| **Thanh toán & Đặt hàng** | `http://127.0.0.1:8000/checkout/` |
| **Giám sát Bản đồ GIS** | `http://127.0.0.1:8000/map/` |
| **Tối ưu Tuyến đường Hỏa tốc** | `http://127.0.0.1:8000/toi-uu-lo-trinh/` |
| **Giao diện Giả lập App Shipper** | `http://127.0.0.1:8000/app-shipper/` |
| **Cổng Đối tác Gửi hàng B2B API** | `http://127.0.0.1:8000/partner-demo/` |
| **Quản lý Đơn hàng & Điều phối** | `http://127.0.0.1:8000/quan-ly-don-hang/` |
| **Trang Quản trị Django Admin** | `http://127.0.0.1:8000/admin/` |

---

## 💡 Lưu Ý Về Việc Đổi Tên Thư Mục Dự Án

* Toàn bộ mã nguồn dự án được thiết kế chuẩn mực với `BASE_DIR = Path(__file__).resolve().parent.parent`, hoàn toàn **không phụ thuộc** vào tên thư mục vật lý bên ngoài.
* **Nếu bạn muốn đổi tên thư mục gốc** (ví dụ thành `FoodDelivery-Logistics-Platform`):
  1. Đóng trình soạn thảo (VS Code / Antigravity IDE) và tắt server đang chạy.
  2. Đổi tên thư mục trong File Explorer của Windows.
  3. Mở lại thư mục vừa đổi tên trong IDE và chạy lệnh `python manage.py runserver`. Hệ thống sẽ hoạt động bình thường 100%.
