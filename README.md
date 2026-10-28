# DMCL Refrigerator (REF) Daily Price Scraper

Hệ thống tự động hóa quét giá và danh mục Tủ lạnh (REF) trên Siêu thị Điện Máy Chợ Lớn (`dienmaycholon.com/tu-lanh`) và đồng bộ trực tiếp lên Google Spreadsheet Master:

- **Google Spreadsheet Master:** [DMCL_REF_Price_Tracking_Master](https://docs.google.com/spreadsheets/d/1r0oqzTog9jwFhIDl717CUQTsYfAcET_phuDbGyP5tJs/edit)
- **Tần suất chạy:** 07:00 AM (giờ Việt Nam) hàng ngày qua GitHub Actions.
- **Chi phí vận hành:** 0 VNĐ vĩnh viễn (Serverless).

---

## 1. Cấu Trúc Dự Án

```
dmcl_price_tracker/
├── .github/
│   └── workflows/
│       └── daily_scrape.yml      # Kịch bản GitHub Actions tự động 07:00 AM
├── scrape_and_export_gsheets.py  # Python Scraper & Google Sheets API Sync
├── requirements.txt              # Thư viện phụ thuộc (requests)
├── .gitignore                    # Bỏ qua file rác và token
└── README.md                     # Hướng dẫn chi tiết
```

---

## 2. Hướng Dẫn Đẩy Lên GitHub & Kích Hoạt

### Bước 1: Khởi tạo Git Repo và Push lên GitHub
Mở Terminal tại thư mục này và chạy các lệnh:
```bash
git init
git add .
git commit -m "feat: Initial DMCL REF daily price scraper with GitHub Actions"
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPO-NAME>.git
git push -u origin main
```
*(Khuyến nghị đặt repository ở chế độ **Private**).*

### Bước 2: Cài đặt 3 GitHub Secrets
Trên trang GitHub Repository của bạn:
1. Vào **Settings** -> **Secrets and variables** -> **Actions**.
2. Nhấn nút **New repository secret** và thêm lần lượt 3 biến:
   - `GOOGLE_WORKSPACE_CLIENT_ID`
   - `GOOGLE_WORKSPACE_CLIENT_SECRET`
   - `GOOGLE_WORKSPACE_REFRESH_TOKEN`
*(Giá trị lấy từ file `~/.config/gws/gws_env.sh` trên máy của bạn).*

### Bước 3: Chạy thử nghiệm ngay (Manual Trigger)
1. Trên GitHub repo, vào tab **Actions**.
2. Chọn workflow **DMCL Daily REF Price Scrape** ở thanh bên trái.
3. Nhấn **Run workflow** -> **Run workflow**.
4. Quá trình chạy mất khoảng 15 giây và Google Sheet sẽ tự động cập nhật số liệu mới nhất!
