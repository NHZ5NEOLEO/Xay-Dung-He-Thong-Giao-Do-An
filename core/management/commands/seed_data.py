from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import KhoHang, TaiXe, DonHang, LichSuKho, DanhMucMonAn, MonAn, QuangCao, ChiTietDonHang
from decimal import Decimal


class Command(BaseCommand):
    help = 'Tự động tạo cơ sở dữ liệu mẫu cho Nền tảng Đặt Món và Điều Phối Giao Hàng TMĐT'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Xóa dữ liệu cũ và nạp lại toàn bộ')

    def handle(self, *args, **options):
        force = options.get('force', False)

        if force:
            self.stdout.write("Dang lam sach du lieu cu de nap moi...")
            ChiTietDonHang.objects.all().delete()
            LichSuKho.objects.all().delete()
            DonHang.objects.all().delete()
            MonAn.objects.all().delete()
            DanhMucMonAn.objects.all().delete()
            QuangCao.objects.all().delete()

        # -------------------------------------------------------------
        # 1. TẠO CÁC CƠ SỞ / QUÁN ĂN / BẾP TRUNG TÂM (KhoHang)
        # -------------------------------------------------------------
        kho_data = [
            {
                'ten_kho': 'Bếp Trung Tâm Quận 1 (Cloud Kitchen)',
                'dia_chi': '26 Phan Bội Châu, P. Bến Thành, Quận 1, TP.HCM',
                'lat': 10.7721,
                'lng': 106.6983,
                'suc_chua_toi_da': 150,
                'loai_hinh': 'Bếp trung tâm điều phối',
                'hinh_anh': 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800&auto=format&fit=crop&q=60',
                'danh_gia': 4.9,
                'thoi_gian_mo_cua': '06:00 - 23:00',
                'hotline': '1900 6868'
            },
            {
                'ten_kho': 'Quán Cơm Tấm Sài Gòn Xưa',
                'dia_chi': '128 Hai Bà Trưng, P. Đa Kao, Quận 1, TP.HCM',
                'lat': 10.7850,
                'lng': 106.6970,
                'suc_chua_toi_da': 80,
                'loai_hinh': 'Nhà hàng ẩm thực Việt',
                'hinh_anh': 'https://images.unsplash.com/photo-1544025162-d76694265947?w=800&auto=format&fit=crop&q=60',
                'danh_gia': 4.8,
                'thoi_gian_mo_cua': '06:30 - 22:00',
                'hotline': '0908 123 456'
            },
            {
                'ten_kho': 'Tiệm Trà Sữa và Đồ Uống Gong Cha Express',
                'dia_chi': '45 Lê Thánh Tôn, P. Bến Nghé, Quận 1, TP.HCM',
                'lat': 10.7780,
                'lng': 106.7025,
                'suc_chua_toi_da': 120,
                'loai_hinh': 'Thương hiệu trà sữa và Cafe',
                'hinh_anh': 'https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800&auto=format&fit=crop&q=60',
                'danh_gia': 4.9,
                'thoi_gian_mo_cua': '08:00 - 22:30',
                'hotline': '0912 345 678'
            },
            {
                'ten_kho': 'Quán Bún Bò Huế và Phở Gia Truyền',
                'dia_chi': '88 Pasteur, P. Bến Nghé, Quận 1, TP.HCM',
                'lat': 10.7745,
                'lng': 106.7005,
                'suc_chua_toi_da': 70,
                'loai_hinh': 'Quán phở bún đặc sản',
                'hinh_anh': 'https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=800&auto=format&fit=crop&q=60',
                'danh_gia': 4.7,
                'thoi_gian_mo_cua': '06:00 - 21:30',
                'hotline': '0933 888 999'
            },
            {
                'ten_kho': 'Pizza 4P\'s và Burger Fastfood',
                'dia_chi': '151 Đồng Khởi, P. Bến Nghé, Quận 1, TP.HCM',
                'lat': 10.7765,
                'lng': 106.7050,
                'suc_chua_toi_da': 100,
                'loai_hinh': 'Đồ ăn nhanh cao cấp',
                'hinh_anh': 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800&auto=format&fit=crop&q=60',
                'danh_gia': 4.9,
                'thoi_gian_mo_cua': '10:00 - 23:00',
                'hotline': '028 3822 5555'
            }
        ]

        cac_kho = []
        for k in kho_data:
            obj, _ = KhoHang.objects.update_or_create(
                ten_kho=k['ten_kho'],
                defaults=k
            )
            cac_kho.append(obj)
        self.stdout.write(f"-> Da tao {len(cac_kho)} quan an / bep trung tam.")

        # -------------------------------------------------------------
        # 2. TẠO TÀI KHOẢN VÀ SHIPPER (TaiXe)
        # -------------------------------------------------------------
        shippers_data = [
            {'user': 'shipper1', 'ten': 'Trần Văn Mạnh', 'sdt': '0901234561', 'bien': '59P1-123.45',
                'xe': 'Xe máy', 'ca': 'SANG', 'lat': 10.7750, 'lng': 106.7010, 'doanh_thu': 4500000, 'don': 95},
            {'user': 'shipper2', 'ten': 'Nguyễn Hoàng Tuấn', 'sdt': '0901234562', 'bien': '59P2-678.90',
                'xe': 'Xe máy', 'ca': 'CHIEU', 'lat': 10.7810, 'lng': 106.6960, 'doanh_thu': 5200000, 'don': 110},
            {'user': 'shipper3', 'ten': 'Lê Quang Huy', 'sdt': '0901234563', 'bien': '59P3-112.23',
                'xe': 'Xe máy', 'ca': 'DEM', 'lat': 10.7700, 'lng': 106.7030, 'doanh_thu': 3800000, 'don': 80},
            {'user': 'shipper4', 'ten': 'Phạm Minh Trí', 'sdt': '0901234564', 'bien': '59P4-445.56',
                'xe': 'Xe máy', 'ca': 'SANG', 'lat': 10.7860, 'lng': 106.6990, 'doanh_thu': 6100000, 'don': 130},
        ]

        cac_taixe = []
        for s in shippers_data:
            user_obj, created = User.objects.get_or_create(username=s['user'])
            if created or not user_obj.check_password('123'):
                user_obj.set_password('123')
                user_obj.save()

            taixe_obj, _ = TaiXe.objects.update_or_create(
                user=user_obj,
                defaults={
                    'ten_tai_xe': s['ten'],
                    'sdt': s['sdt'],
                    'bien_so': s['bien'],
                    'loai_xe': s['xe'],
                    'ca_lam_viec': s['ca'],
                    'dang_lam_viec': True,
                    'trang_thai': 'Sẵn sàng',
                    'doanh_thu_tich_luy': Decimal(s['doanh_thu']),
                    'tong_don_thang_nay': s['don'],
                    'lat_hien_tai': s['lat'],
                    'lng_hien_tai': s['lng'],
                }
            )
            cac_taixe.append(taixe_obj)
        self.stdout.write(f"-> Da tao {len(cac_taixe)} tai xe va tai khoan shipper.")

        # -------------------------------------------------------------
        # 3. TẠO DANH MỤC MÓN ĂN (DanhMucMonAn)
        # -------------------------------------------------------------
        danh_muc_data = [
            {'ten': 'Cơm và Món Mặn', 'slug': 'com-man', 'icon': 'fa-bowl-rice', 'thu_tu': 1},
            {'ten': 'Trà Sữa và Đồ Uống', 'slug': 'tra-sua-do-uong', 'icon': 'fa-mug-hot', 'thu_tu': 2},
            {'ten': 'Fast Food và Gà Rán', 'slug': 'fast-food', 'icon': 'fa-burger', 'thu_tu': 3},
            {'ten': 'Bún - Phở - Mì Nước', 'slug': 'bun-pho-mi', 'icon': 'fa-utensils', 'thu_tu': 4},
            {'ten': 'Bánh Mì và Ăn Vặt', 'slug': 'banh-mi-an-vat', 'icon': 'fa-cookie-bite', 'thu_tu': 5},
            {'ten': 'Healthy và Salad', 'slug': 'healthy-salad', 'icon': 'fa-leaf', 'thu_tu': 6},
        ]

        dm_map = {}
        for dm in danh_muc_data:
            obj, _ = DanhMucMonAn.objects.update_or_create(
                slug=dm['slug'],
                defaults={'ten_danh_muc': dm['ten'], 'icon': dm['icon'], 'thu_tu': dm['thu_tu']}
            )
            dm_map[dm['slug']] = obj
        self.stdout.write(f"-> Da tao {len(dm_map)} danh muc mon an.")

        # -------------------------------------------------------------
        # 4. TẠO THỰC ĐƠN MÓN ĂN (MonAn)
        # -------------------------------------------------------------
        mon_an_data = [
            # Cơm và Món Mặn
            {
                'ten': 'Cơm Sườn Bì Chả Đặc Biệt',
                'dm': 'com-man',
                'kho': cac_kho[1],
                'gia': Decimal(55000),
                'gia_km': Decimal(48000),
                'mo_ta': 'Sườn cốt lết nướng mật ong thơm lừng, bì giòn dai, chả trứng hấp béo ngậy kèm mỡ hành và nước mắm ớt chua ngọt chuẩn vị Sài Gòn.',
                'hinh': 'https://images.unsplash.com/photo-1544025162-d76694265947?w=800&auto=format&fit=crop&q=60',
                'noi_bat': True,
                'da_ban': 342,
                'chuan_bi': 10
            },
            {
                'ten': 'Cơm Gà Xối Mỡ Giòn Rụm',
                'dm': 'com-man',
                'kho': cac_kho[1],
                'gia': Decimal(50000),
                'gia_km': Decimal(45000),
                'mo_ta': 'Đùi gà góc tư chiên xối mỡ da giòn rụm, thịt mềm mọng nước, ăn kèm cơm chiên hoàng bào và sốt tương tỏi ớt.',
                'hinh': 'https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=800&auto=format&fit=crop&q=60',
                'noi_bat': True,
                'da_ban': 285,
                'chuan_bi': 12
            },
            {
                'ten': 'Cơm Bò Lúc Lắc Khoai Tây Chiên',
                'dm': 'com-man',
                'kho': cac_kho[0],
                'gia': Decimal(65000),
                'gia_km': Decimal(59000),
                'mo_ta': 'Bò phi lê mềm thái quân cờ xào tiêu đen thơm nức mũi, hành tây ớt chuông giòn ngọt cùng khoai tây chiên giòn.',
                'hinh': 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800&auto=format&fit=crop&q=60',
                'noi_bat': False,
                'da_ban': 160,
                'chuan_bi': 15
            },
            # Trà Sữa và Đồ Uống
            {
                'ten': 'Trà Sữa Trân Châu Hoàng Kim',
                'dm': 'tra-sua-do-uong',
                'kho': cac_kho[2],
                'gia': Decimal(38000),
                'gia_km': Decimal(32000),
                'mo_ta': 'Trà đen đậm đà hòa quyện cùng sữa tươi New Zealand thơm béo, trân châu hoàng kim dai giòn sần sật.',
                'hinh': 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=800&auto=format&fit=crop&q=60',
                'noi_bat': True,
                'da_ban': 512,
                'chuan_bi': 5
            },
            {
                'ten': 'Trà Đào Cam Sả Tươi Mát',
                'dm': 'tra-sua-do-uong',
                'kho': cac_kho[2],
                'gia': Decimal(35000),
                'gia_km': None,
                'mo_ta': 'Trà thanh dịu mát lạnh với đào giòn mọng nước, cam vàng ngọt ngào và sả tươi giải nhiệt tức thì.',
                'hinh': 'https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=800&auto=format&fit=crop&q=60',
                'noi_bat': True,
                'da_ban': 389,
                'chuan_bi': 5
            },
            {
                'ten': 'Trà Vải Hoa Hồng Thạch Ngọc Trai',
                'dm': 'tra-sua-do-uong',
                'kho': cac_kho[2],
                'gia': Decimal(42000),
                'gia_km': Decimal(36000),
                'mo_ta': 'Hương thơm hoa hồng tự nhiên thanh tao kết hợp cùng vị vải ngọt thanh và thạch củ năng ngọc trai giòn tan.',
                'hinh': 'https://images.unsplash.com/photo-1546173159-315724a31696?w=800&auto=format&fit=crop&q=60',
                'noi_bat': False,
                'da_ban': 195,
                'chuan_bi': 5
            },
            # Fast Food và Gà Rán
            {
                'ten': 'Gà Rán Giòn Sốt Cay Hàn Quốc',
                'dm': 'fast-food',
                'kho': cac_kho[4],
                'gia': Decimal(75000),
                'gia_km': Decimal(68000),
                'mo_ta': 'Gà chiên giòn chuẩn kiểu Seoul phủ đẫm sốt cay ngọt Gochujang rắc mè trắng béo bùi, ăn kèm củ cải muối chua.',
                'hinh': 'https://images.unsplash.com/photo-1562967914-608f82629710?w=800&auto=format&fit=crop&q=60',
                'noi_bat': True,
                'da_ban': 420,
                'chuan_bi': 15
            },
            {
                'ten': 'Burger Bò Phô Mai Chảy 2 Tầng',
                'dm': 'fast-food',
                'kho': cac_kho[4],
                'gia': Decimal(65000),
                'gia_km': Decimal(58000),
                'mo_ta': 'Bò Úc xay nướng than hoa thơm phức kẹp 2 lát phô mai Cheddar tan chảy, xà lách tươi và sốt BBQ đặc chế.',
                'hinh': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800&auto=format&fit=crop&q=60',
                'noi_bat': True,
                'da_ban': 310,
                'chuan_bi': 10
            },
            {
                'ten': 'Khoai Tây Chiên Lắc Phô Mai',
                'dm': 'fast-food',
                'kho': cac_kho[4],
                'gia': Decimal(30000),
                'gia_km': Decimal(25000),
                'mo_ta': 'Khoai tây cắt thẳng chiên vàng ruộm lắc đẫm bột phô mai béo mặn thơm ngậy.',
                'hinh': 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=800&auto=format&fit=crop&q=60',
                'noi_bat': False,
                'da_ban': 450,
                'chuan_bi': 8
            },
            {
                'ten': 'Pizza Hải Sản Sốt Tiêu Đen 25cm',
                'dm': 'fast-food',
                'kho': cac_kho[4],
                'gia': Decimal(129000),
                'gia_km': Decimal(109000),
                'mo_ta': 'Đế bánh nhào tay chuẩn Ý nướng củi, tôm tươi mực giòn, ớt chuông phủ đẫm phô mai Mozzarella kéo sợi.',
                'hinh': 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800&auto=format&fit=crop&q=60',
                'noi_bat': True,
                'da_ban': 230,
                'chuan_bi': 20
            },
            # Bún - Phở - Mì
            {
                'ten': 'Bún Bò Huế Sườn Bò và Chả Cua',
                'dm': 'bun-pho-mi',
                'kho': cac_kho[3],
                'gia': Decimal(55000),
                'gia_km': Decimal(49000),
                'mo_ta': 'Nước dùng hầm xương ống 12 tiếng thơm nồng hương sả và mắm ruốc, sườn bò mềm béo, chả cua Huế ngọt thanh.',
                'hinh': 'https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=800&auto=format&fit=crop&q=60',
                'noi_bat': True,
                'da_ban': 415,
                'chuan_bi': 8
            },
            {
                'ten': 'Phở Bò Tái Nạm Hà Nội Đặc Biệt',
                'dm': 'bun-pho-mi',
                'kho': cac_kho[3],
                'gia': Decimal(60000),
                'gia_km': None,
                'mo_ta': 'Bánh phở tươi mềm mướt, thịt bò tái lăn và nạm bò giòn sần sật trong nước dùng thanh trong thơm thảo quả.',
                'hinh': 'https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?w=800&auto=format&fit=crop&q=60',
                'noi_bat': True,
                'da_ban': 380,
                'chuan_bi': 8
            },
            {
                'ten': 'Hủ Tiếu Nam Vang Thập Cẩm Khô',
                'dm': 'bun-pho-mi',
                'kho': cac_kho[3],
                'gia': Decimal(52000),
                'gia_km': Decimal(46000),
                'mo_ta': 'Sợi hủ tiếu dai trộn sốt tương đen gia truyền, tôm tươi, gan heo, thịt nạc và tóp mỡ giòn rụm kèm chén súp ngọt lịm.',
                'hinh': 'https://images.unsplash.com/photo-1541832676-9b763b0239ab?w=800&auto=format&fit=crop&q=60',
                'noi_bat': False,
                'da_ban': 270,
                'chuan_bi': 10
            },
            # Bánh Mì và Ăn Vặt
            {
                'ten': 'Bánh Mì Chảo Xíu Mại Bơ Tỏi',
                'dm': 'banh-mi-an-vat',
                'kho': cac_kho[0],
                'gia': Decimal(45000),
                'gia_km': Decimal(39000),
                'mo_ta': 'Chảo gang nóng hổi gồm trứng ốp la lòng đào, xíu mại sốt cà chua đẫm thịt, pate béo ngậy kèm bánh mì giòn tan.',
                'hinh': 'https://images.unsplash.com/photo-1509722747041-616f39b57569?w=800&auto=format&fit=crop&q=60',
                'noi_bat': True,
                'da_ban': 290,
                'chuan_bi': 10
            },
            {
                'ten': 'Bánh Tráng Nướng Đà Lạt Trứng Cút',
                'dm': 'banh-mi-an-vat',
                'kho': cac_kho[0],
                'gia': Decimal(25000),
                'gia_km': None,
                'mo_ta': 'Bánh tráng nướng than hoa giòn rụm với trứng cút, tép khô, hành lá và sốt phô mai béo ngậy.',
                'hinh': 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&auto=format&fit=crop&q=60',
                'noi_bat': False,
                'da_ban': 340,
                'chuan_bi': 7
            },
            # Healthy và Salad
            {
                'ten': 'Salad Ức Gà Áp Chảo Sốt Mè Rang',
                'dm': 'healthy-salad',
                'kho': cac_kho[0],
                'gia': Decimal(55000),
                'gia_km': Decimal(49000),
                'mo_ta': 'Ức gà nướng mềm mọng nước, xà lách Romaine, cà chua bi, trứng luộc và sốt mè rang Kewpie thơm bùi thanh mát.',
                'hinh': 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&auto=format&fit=crop&q=60',
                'noi_bat': True,
                'da_ban': 180,
                'chuan_bi': 10
            }
        ]

        cac_mon = []
        for m in mon_an_data:
            obj, _ = MonAn.objects.update_or_create(
                ten_mon=m['ten'],
                defaults={
                    'danh_muc': dm_map[m['dm']],
                    'kho_hang': m['kho'],
                    'gia': m['gia'],
                    'gia_khuyen_mai': m['gia_km'],
                    'mo_ta': m['mo_ta'],
                    'hinh_anh': m['hinh'],
                    'is_noi_bat': m['noi_bat'],
                    'da_ban': m['da_ban'],
                    'thoi_gian_chuan_bi': m['chuan_bi'],
                    'so_luong_con_lai': 100,
                    'is_hoa_toc': True,
                    'is_con_mon': True,
                }
            )
            cac_mon.append(obj)
        self.stdout.write(f"-> Da tao {len(cac_mon)} mon an phong phu trong thuc don.")

        # -------------------------------------------------------------
        # 5. TẠO QUẢNG CÁO và BANNER ADS TMĐT (QuangCao)
        # -------------------------------------------------------------
        ads_data = [
            {
                'tieu_de': 'ĐẶT MÓN HỎA TỐC 15 PHÚT - NÓNG HỔI TẬN BÀN',
                'mo_ta': 'Hệ thống định vị GPS tự động điều phối Shipper gần nhất và tính lộ trình đường ngắn nhất!',
                'hinh': 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1200&auto=format&fit=crop&q=80',
                'loai': 'BANNER_CHINH',
                'voucher': 'HOATOC50',
                'giam': 50,
                'ads_revenue': Decimal(2500000),
                'thu_tu': 1
            },
            {
                'tieu_de': 'FREESHIP MỌI NẺO ĐƯỜNG - TỐI ƯU CƯỚC THEO KM',
                'mo_ta': 'Tích hợp Leaflet Maps tính khoảng cách chính xác từ quán đến bạn. Minh bạch từng mét đường!',
                'hinh': 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=1200&auto=format&fit=crop&q=80',
                'loai': 'BANNER_CHINH',
                'voucher': 'FREESHIP0D',
                'giam': 30,
                'ads_revenue': Decimal(1800000),
                'thu_tu': 2
            },
            {
                'tieu_de': 'TIỆC TRÀ SỮA ĐỒNG GIÁ 29K - TÀI TRỢ BỞI GONG CHA',
                'mo_ta': 'Ưu đãi giải nhiệt mùa hè, quét mã QR VietQR nhận ngay hoàn tiền 10% vào ví!',
                'hinh': 'https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=1200&auto=format&fit=crop&q=80',
                'loai': 'BANNER_PHU',
                'voucher': 'GONGCHA29K',
                'giam': 20,
                'ads_revenue': Decimal(1200000),
                'thu_tu': 3
            },
            {
                'tieu_de': 'FESTIVAL ẨM THỰC ĐƯỜNG PHỐ SÀI GÒN - B2B PARTNER SALE',
                'mo_ta': 'Cổng kết nối đối tác B2B Shopee/TikTok đẩy đơn tự động siêu tốc!',
                'hinh': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=1200&auto=format&fit=crop&q=80',
                'loai': 'POPUP_SALE',
                'voucher': 'B2BSALE',
                'giam': 15,
                'ads_revenue': Decimal(950000),
                'thu_tu': 4
            }
        ]

        for a in ads_data:
            QuangCao.objects.update_or_create(
                tieu_de=a['tieu_de'],
                defaults={
                    'mo_ta': a['mo_ta'],
                    'hinh_anh': a['hinh'],
                    'loai_quang_cao': a['loai'],
                    'ma_voucher': a['voucher'],
                    'giam_gia_phan_tram': a['giam'],
                    'doanh_thu_ads': a['ads_revenue'],
                    'thu_tu': a['thu_tu'],
                    'kich_hoat': True
                }
            )
        self.stdout.write(f"-> Da tao {len(ads_data)} chien dich quang cao và Banner Ads TMDT.")

        # -------------------------------------------------------------
        # 6. TẠO CÁC ĐƠN HÀNG MẪU VỚI MÓN ĂN và LỘ TRÌNH (DonHang)
        # -------------------------------------------------------------
        sample_orders = [
            {
                'ma_don': 'DH001',
                'ten': 'Nguyễn Văn Minh',
                'sdt': '0912345678',
                'email': 'minh.nguyen@gmail.com',
                'dia_chi': '12 Nguyễn Huệ, P. Bến Nghé, Quận 1, TP.HCM',
                'lat': 10.7735,
                'lng': 106.7042,
                'kho': cac_kho[0],
                'tx': cac_taixe[0],
                'loai_giao': 'HOA_TOC',
                'trang_thai': 'ĐANG VẬN CHUYỂN',
                'tt_thanh_toan': 'DA_THANH_TOAN',
                'pt_thanh_toan': 'QR_VIETQR',
                'mon_list': [(cac_mon[0], 2), (cac_mon[3], 2)],  # Cơm sườn x2, Trà sữa x2
                'km': 1.8,
                'phi_ship': 15000,
                'phu_phi': 10000,
                'giam': 10000
            },
            {
                'ma_don': 'DH002',
                'ten': 'Trần Thị Thu Hà',
                'sdt': '0987654321',
                'email': 'thuha.tran@gmail.com',
                'dia_chi': '215 Điện Biên Phủ, P. 15, Quận Bình Thạnh, TP.HCM',
                'lat': 10.7980,
                'lng': 106.7110,
                'kho': cac_kho[4],
                'tx': cac_taixe[1],
                'loai_giao': 'HOA_TOC',
                'trang_thai': 'ĐANG VẬN CHUYỂN',
                'tt_thanh_toan': 'DA_THANH_TOAN',
                'pt_thanh_toan': 'QR_VIETQR',
                'mon_list': [(cac_mon[6], 1), (cac_mon[7], 1), (cac_mon[8], 1)],  # Gà rán, Burger, Khoai tây
                'km': 3.5,
                'phi_ship': 22500,
                'phu_phi': 10000,
                'giam': 15000
            },
            {
                'ma_don': 'DH003',
                'ten': 'Lê Đức Anh',
                'sdt': '0938123456',
                'email': 'ducanh.le@gmail.com',
                'dia_chi': '45 Nam Kỳ Khởi Nghĩa, P. Bến Thành, Quận 1, TP.HCM',
                'lat': 10.7710,
                'lng': 106.6990,
                'kho': cac_kho[3],
                'tx': cac_taixe[0],
                'loai_giao': 'HOA_TOC',
                'trang_thai': 'ĐÃ GIAO THÀNH CÔNG',
                'tt_thanh_toan': 'DA_THANH_TOAN',
                'pt_thanh_toan': 'MOMO',
                'mon_list': [(cac_mon[10], 2)],  # Bún bò Huế x2
                'km': 1.2,
                'phi_ship': 15000,
                'phu_phi': 10000,
                'giam': 0
            },
            {
                'ma_don': 'DH004',
                'ten': 'Phạm Hải Yến',
                'sdt': '0977889900',
                'email': 'haiyen.pham@gmail.com',
                'dia_chi': '72 Lê Thánh Tôn, P. Bến Nghé, Quận 1, TP.HCM',
                'lat': 10.7770,
                'lng': 106.7020,
                'kho': cac_kho[2],
                'tx': None,
                'loai_giao': 'HOA_TOC',
                'trang_thai': 'CHỜ TÀI XẾ',
                'tt_thanh_toan': 'DA_THANH_TOAN',
                'pt_thanh_toan': 'QR_VIETQR',
                'mon_list': [(cac_mon[3], 3), (cac_mon[4], 2)],  # Trà sữa x3, Trà đào x2
                'km': 1.5,
                'phi_ship': 15000,
                'phu_phi': 10000,
                'giam': 20000
            },
            {
                'ma_don': 'DH005',
                'ten': 'Vũ Quốc Bảo',
                'sdt': '0909988776',
                'email': 'quocbao.vu@gmail.com',
                'dia_chi': '135 Hai Bà Trưng, P. Bến Nghé, Quận 1, TP.HCM',
                'lat': 10.7815,
                'lng': 106.6995,
                'kho': cac_kho[1],
                'tx': cac_taixe[2],
                'loai_giao': 'TIEU_CHUAN',
                'trang_thai': 'ĐANG VẬN CHUYỂN',
                'tt_thanh_toan': 'CHUA_THANH_TOAN',
                'pt_thanh_toan': 'COD',
                'mon_list': [(cac_mon[1], 2), (cac_mon[13], 1)],  # Cơm gà x2, Bánh mì chảo x1
                'km': 2.2,
                'phi_ship': 16000,
                'phu_phi': 0,
                'giam': 0
            }
        ]

        for s in sample_orders:
            tien_mon = sum(m[0].gia_hien_tai() * m[1] for m in s['mon_list'])
            tong = max(0, tien_mon + s['phi_ship'] + s['phu_phi'] - s['giam'])

            don_obj, created = DonHang.objects.update_or_create(
                ma_don=s['ma_don'],
                defaults={
                    'ten_nguoi_nhan': s['ten'],
                    'sdt_nguoi_nhan': s['sdt'],
                    'email_nguoi_nhan': s['email'],
                    'dia_chi_nguoi_nhan': s['dia_chi'],
                    'lat_khach': s['lat'],
                    'lng_khach': s['lng'],
                    'kho_xuat_phat': s['kho'],
                    'tai_xe': s['tx'],
                    'loai_giao_hang': s['loai_giao'],
                    'trang_thai': s['trang_thai'],
                    'tien_mon_an': tien_mon,
                    'phi_van_chuyen': s['phi_ship'],
                    'phu_phi_hoa_toc': s['phu_phi'],
                    'khoang_cach_km': s['km'],
                    'giam_gia': s['giam'],
                    'tong_tien': tong,
                    'phuong_thuc_thanh_toan': s['pt_thanh_toan'],
                    'trang_thai_thanh_toan': s['tt_thanh_toan'],
                    'ma_giao_dich_qr': f"VQR_{s['ma_don']}",
                    'khoi_luong': 1.5,
                }
            )

            # Xóa các chi tiết cũ nếu có và tạo mới
            don_obj.chi_tiet_mon.all().delete()
            for mon, sl in s['mon_list']:
                ChiTietDonHang.objects.create(
                    don_hang=don_obj,
                    mon_an=mon,
                    so_luong=sl,
                    don_gia=mon.gia_hien_tai(),
                    thanh_tien=mon.gia_hien_tai() * sl,
                    ghi_chu_mon='Giao nong hoi, day du dung cu an uong'
                )

            # Tạo lịch sử luân chuyển
            LichSuKho.objects.get_or_create(
                don_hang=don_obj,
                trang_thai_buoc='NHẬP KHO',
                defaults={'kho': s['kho'], 'ghi_chu': 'Bếp nhận đơn đặt hàng trực tuyến từ khách'}
            )
            if s['trang_thai'] in ['ĐANG VẬN CHUYỂN', 'ĐÃ GIAO THÀNH CÔNG']:
                LichSuKho.objects.get_or_create(
                    don_hang=don_obj,
                    trang_thai_buoc='BÀN GIAO SHIPPER',
                    defaults={'kho': s['kho'],
                              'ghi_chu': f"Bàn giao shipper {s['tx'].ten_tai_xe if s['tx'] else 'Hỏa tốc'}"}
                )
            if s['trang_thai'] == 'ĐÃ GIAO THÀNH CÔNG':
                LichSuKho.objects.get_or_create(
                    don_hang=don_obj,
                    trang_thai_buoc='XUẤT KHO',
                    defaults={'kho': s['kho'], 'ghi_chu': 'Đã giao thành công đến tay khách hàng'}
                )

        self.stdout.write(f"-> Da tao {len(sample_orders)} don hang mau voi day du mon an, lo trinh va QR thanh toan.")
        self.stdout.write(self.style.SUCCESS("=== HOAN TAT KHOI TAO DU LIEU TU DONG CHO HE THONG! ==="))
