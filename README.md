# 普通话 Podcast Studio

Công cụ chuyển văn bản tiếng Trung thành MP3 podcast chất lượng cao.
- Giọng Neural AI (Microsoft Edge TTS) — miễn phí hoàn toàn
- Xử lý văn bản dài không giới hạn (tự chia đoạn + ghép lại)
- 14 giọng đọc: Phổ thông, Đài Loan, Quảng Đông

---

## HƯỚNG DẪN CHẠY LOCAL (máy tính của bạn)

### Bước 1: Cài Python
Tải Python 3.10+ tại https://python.org/downloads
Khi cài trên Windows, tick chọn "Add Python to PATH"

### Bước 2: Cài ffmpeg (cần để ghép audio)

**Windows:**
1. Tải tại https://ffmpeg.org/download.html → Windows builds
2. Giải nén → copy thư mục vào C:\ffmpeg
3. Thêm C:\ffmpeg\bin vào PATH (System Environment Variables)

**macOS:**
```
brew install ffmpeg
```

**Ubuntu/Linux:**
```
sudo apt install ffmpeg
```

### Bước 3: Tải project về máy
```
git clone <URL_repo_của_bạn>
cd chinese-tts
```
Hoặc giải nén file zip vào thư mục bất kỳ.

### Bước 4: Cài thư viện Python
```
pip install -r requirements.txt
```

### Bước 5: Chạy server
```
python app.py
```

### Bước 6: Mở trình duyệt
Truy cập: http://localhost:5000

---

## DEPLOY LÊN RAILWAY (miễn phí, online 24/7)

### Bước 1: Tạo tài khoản
- Đăng ký tại https://railway.app (dùng GitHub account)

### Bước 2: Đẩy code lên GitHub
```
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/TEN_BAN/chinese-tts.git
git push -u origin main
```

### Bước 3: Deploy trên Railway
1. Vào railway.app → New Project → Deploy from GitHub repo
2. Chọn repo chinese-tts
3. Railway tự detect Python và deploy
4. Vào Settings → Generate Domain → lấy URL public

### Bước 4: Thêm ffmpeg buildpack
Trong Railway project → Settings → Build:
Thêm environment variable:
```
NIXPACKS_PKGS=ffmpeg
```

---

## CẤU TRÚC PROJECT

```
chinese-tts/
├── app.py          ← Flask backend
├── requirements.txt
├── Procfile        ← Dành cho Railway/Heroku
├── .gitignore
├── output/         ← File MP3 tạm (tự tạo, tự xóa)
└── static/
    └── index.html  ← Giao diện web
```

---

## GIỌNG ĐỌC CÓ SẴN

| ID | Tên | Giới tính | Phù hợp |
|---|---|---|---|
| zh-CN-XiaoxiaoNeural | 晓晓 | Nữ | Podcast tổng quát |
| zh-CN-YunxiNeural | 云希 | Nam | Podcast nam |
| zh-CN-YunyangNeural | 云扬 | Nam | Tin tức, báo chí |
| zh-TW-HsiaoChenNeural | 曉臻 | Nữ | Tiếng Đài Loan |
| zh-HK-HiuMaanNeural | 曉曼 | Nữ | Tiếng Quảng Đông |
