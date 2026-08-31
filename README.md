# Company Scanner

Quét thông tin doanh nghiệp từ website thật, phục vụ sales IT Outsourcing.

Nhập URL → app truy cập website thật, crawl các trang liên quan (giới thiệu, liên hệ,
ban lãnh đạo, tuyển dụng) và trích xuất thông tin có ích cho sales. Không có mock data:
mỗi URL là một lần scan độc lập, không tìm thấy thì trả `Not found`.

## Chạy app

Double-click `run.bat` (Windows) hoặc chạy `./run.sh` (Linux/macOS).

Launcher sẽ: kiểm tra Python → tự cài dependencies nếu thiếu → chọn port trống
(8000, bận thì 8001, 8002...) → tự mở trình duyệt. Cửa sổ in ra địa chỉ app, ví dụ:

```
App dang chay tai:  http://127.0.0.1:8000
```

Nếu trình duyệt không tự mở, copy đúng địa chỉ đó vào trình duyệt.
Nhấn Ctrl+C trong cửa sổ đen để dừng app.

Muốn ép một port cụ thể:

```bash
python start.py 8080
```

### Không mở được app?

Cửa sổ `run.bat` giữ nguyên khi có lỗi — đọc dòng `[LOI]` trong đó. Các trường hợp hay gặp:

| Hiện tượng | Cách xử lý |
|---|---|
| `[LOI] Khong tim thay Python` | Cài Python 3.10+, khi cài nhớ tick "Add python.exe to PATH" |
| Dừng ở bước cài dependencies | Chạy tay: `python -m pip install -r backend/requirements.txt` |
| Cửa sổ báo port bận rồi nhảy sang 8001 | Bình thường — dùng đúng địa chỉ mà cửa sổ in ra |
| Mở `localhost:8000` nhưng trắng trang / không kết nối | App chưa chạy, hoặc còn tiến trình python cũ giữ port. Đóng hết cửa sổ đen cũ rồi chạy lại `run.bat` |
| Windows hỏi Firewall | Chọn Allow — app chỉ chạy nội bộ trên 127.0.0.1 |

Dọn tiến trình cũ còn treo (PowerShell):

```bash
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'uvicorn|start.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Playwright là tuỳ chọn, chỉ dùng cho website render bằng JavaScript. Muốn bật:

```bash
python -m playwright install chromium
```

Không cài cũng chạy được — app sẽ đọc HTML tĩnh và bỏ qua bước render.

## Quét từ command line

```bash
python backend/scan_cli.py https://www.hyperinfo.co.kr
```

In ra đúng JSON mà API trả về; tiến trình crawl in ở stderr.

## Chạy test

```bash
python backend/test_scanner.py
```

Test offline (không cần mạng): encoding tiếng Hàn, domain isolation, chặn SSRF,
lọc key contacts / tin tuyển dụng IT, và trường hợp không có dữ liệu.

## Cấu trúc

```
backend/app/security.py    Kiểm tra URL, chặn localhost / private IP / metadata IP
backend/app/crawler.py     Crawl thật: fetch, encoding, domain isolation, Playwright
backend/app/extractor.py   Trích xuất công ty / key contacts / tuyển dụng IT
backend/app/storage.py     SQLite: luu / liet ke / mo lai / xoa cong ty
backend/app/main.py        FastAPI: /api/scan, /api/scan/stream (SSE), /api/companies, 2 trang
start.py                   Launcher: kiểm tra môi trường, chọn port, mở trình duyệt
backend/scan_cli.py        Quét từ terminal
backend/test_scanner.py    Test offline
frontend/index.html        Trang "Quét mới" (giữ nguyên layout của prototype)
frontend/saved.html        Trang "Công ty đã lưu"
frontend/app.js            Dùng chung 2 trang: gọi API, render kết quả, export, danh sách
frontend/tailwind.css      CSS compiled lấy nguyên từ prototype
frontend/app.css           Vài class bổ sung prototype chưa build (màu IT Hiring, lỗi)
```

`Company-Scanner-Prototype-Ui (1).html` được giữ nguyên làm UI reference, app không dùng file này.

## Hai trang

Điều hướng nằm ở góc phải header, có mặt trên cả hai trang:

| Trang | URL | Nội dung |
|---|---|---|
| Quét mới | `/` | Nhập URL, quét, xem kết quả, lưu vào database |
| Công ty đã lưu | `/saved` | Danh sách toàn bộ công ty trong database |

Số trên nút "Công ty đã lưu" là số công ty đang có.

## Lưu vào database

Quét xong bấm **"Lưu vào database"** (nút cạnh "Xem JSON").

Trang `/saved` hiển thị bảng:

| Cột | Nội dung |
|---|---|
| Tên công ty | `company.name` |
| Địa chỉ | `company.address` |
| Số điện thoại | `company.phone` |
| Email | `company.email`, bấm để soạn thư |
| Lĩnh vực | `company.industry` |
| Website | Domain, bấm mở website trong tab mới |
| IT Hiring | Mức tín hiệu kèm số lượng, ví dụ `High · 8 vị trí` |
| Cập nhật | Ngày quét/lưu gần nhất |

Ô tìm kiếm lọc theo tên, email, lĩnh vực, website hoặc địa chỉ. Mỗi dòng có nút **Xem**
(mở `/?company=<id>` — trang quét hiển thị lại toàn bộ kết quả đã lưu, cả key contacts,
tin tuyển dụng và source link, không phải quét lại) và **Xoá** (có xác nhận trước).

Database là SQLite, mặc định ở `data/companies.db`. Đổi chỗ lưu bằng biến môi trường
`SCANNER_DB`. Khoá theo domain: quét lại cùng website sẽ **cập nhật** dòng cũ chứ không
tạo bản trùng, nên danh sách luôn là thông tin mới nhất của từng công ty.

Muốn xoá sạch database: đóng app rồi xoá thư mục `data/`.

## Xuất file

Nút **Xuất** nằm ở trang `/saved`, xuất **đúng những dòng đang hiển thị** — đang lọc thì
chỉ xuất phần khớp, nên muốn lấy riêng một công ty thì gõ tên công ty đó vào ô tìm kiếm
rồi xuất. Tên file kèm luôn từ khoá đang lọc.

| Định dạng | Nội dung |
|---|---|
| Excel (.csv) | Một dòng mỗi công ty: tên, địa chỉ, SĐT, email, lĩnh vực, website, IT Hiring, số vị trí IT, số key contacts, ngày cập nhật. Có BOM để Excel đọc đúng tiếng Hàn |
| JSON đầy đủ (.json) | Toàn bộ kết quả scan của từng công ty: key contacts, tin tuyển dụng, source URL |

## API

`POST /api/scan` với body `{"url": "..."}` → JSON kết quả.

`GET /api/scan/stream?url=...` → Server-Sent Events, phát tiến trình thật của crawler
(`homepage` → `company` → `contact` → `management` → `recruitment` → `extract` → `done`),
kết thúc bằng event `result` hoặc `scan_error`. Frontend dùng endpoint này nên thanh
tiến trình phản ánh đúng việc crawler đang làm, không phải timer giả.

Kết quả:

```json
{
  "company":        { "name": "", "address": "", "phone": "", "email": "", "industry": "", "website": "" },
  "company_sources":{ "name": "", "address": "", "phone": "", "email": "", "industry": "" },
  "key_contacts":   [ { "name": "", "position": "", "source_url": "" } ],
  "it_recruitment": [ { "title": "", "position": "", "location": "", "employment_type": "",
                        "deadline": "", "description": "", "source_url": "" } ],
  "sales_signal":   { "it_hiring": "High | Medium | Low | None" },
  "sources":        [],
  "scanned_url":    "",
  "pages_crawled":  0
}
```

Field nào không tìm được sẽ là `null` và UI hiển thị `Not found`.
`company_sources` là URL bằng chứng cho từng field (yêu cầu source validation).

Các endpoint của database:

| Method | Endpoint | Việc |
|---|---|---|
| POST | `/api/companies` | Lưu kết quả scan (body `{"result": {...}}`), upsert theo domain |
| GET | `/api/companies` | Danh sách tóm tắt, mới cập nhật xếp trước |
| GET | `/api/companies?full=1` | Như trên, kèm toàn bộ kết quả scan (dùng khi xuất JSON) |
| GET | `/api/companies/{id}` | Tóm tắt + toàn bộ kết quả scan đã lưu |
| DELETE | `/api/companies/{id}` | Xoá một công ty |

## Giới hạn crawl

| | |
|---|---|
| MAX_PAGES | 20 |
| MAX_DEPTH | 2 |
| TIMEOUT | 15s / request |

Chỉ crawl domain của URL đã nhập (kể cả subdomain của chính domain đó). Link sang
domain khác — kể cả blog, portal tuyển dụng ngoài — đều bị loại. Ngoài link trên
trang, crawler còn đọc `sitemap.xml` để tìm trang tuyển dụng không có trong menu.

**Đọc footer trước.** Website Hàn gần như luôn đặt 상호 / 대표이사 / 주소 / 전화 /
이메일 / 사업자등록번호 ở footer, lặp trên mọi trang. App đọc vùng footer (thẻ
`<footer>`, `<address>`, class/id chứa "footer", cộng phần cuối trang) trước khi đọc
toàn bộ nội dung — vừa chính xác hơn (tránh địa chỉ chi nhánh hay số điện thoại của
đối tác trong bản tin), vừa nhanh hơn. Nếu footer trang chủ đã có đủ địa chỉ + điện
thoại + email thì crawler hạ ưu tiên các trang liên hệ/giới thiệu và dồn hạn mức trang
cho ban lãnh đạo và tuyển dụng — phần hay thiếu.

**Với site không đặt thông tin ở trang chủ**, crawler làm thêm 3 việc:

1. **Dùng hết hạn mức trang** — sau khi đi hết các trang ưu tiên, nếu còn hạn mức thì
   đọc tiếp các trang cùng domain (ưu tiên trang nông), bỏ qua trang tin/blog/thư viện ảnh.
2. **Phân loại lại theo nội dung** — trang có `모집분야`, `입사지원`, `지원자격`... được
   coi là trang tuyển dụng dù link không có từ khoá nào; tin IT chỉ được đọc từ trang
   tuyển dụng nên bước này quyết định tìm được hay không.
3. **Khử trùng lặp theo URL đích và theo nội dung** — nhiều site redirect URL không tồn
   tại về trang chủ; CMS Hàn còn phục vụ cùng một trang dưới nhiều tham số URL. Không
   khử thì cả hạn mức 20 trang bị đốt vào các bản sao.
4. **Đọc `<frame>` / `<iframe>`** — site kiểu cũ để trang chủ rỗng và nhét toàn bộ nội
   dung lẫn menu vào frame; không mở frame thì crawl dừng ngay ở trang đầu.

## Quy tắc trích xuất

**Company** — tên lấy từ nhiều tín hiệu (JSON-LD, `og:site_name`, nhãn `상호/회사명`,
dòng copyright, `<title>`) rồi chấm điểm, ưu tiên nguồn chính thức và tên khớp domain.
Địa chỉ ưu tiên trụ sở chính (`본사`) và cắt bỏ phần Tel/Fax dính chung dòng.
Điện thoại ưu tiên số cố định có nhãn, loại số fax.

**Email** ưu tiên link `mailto:` và trường có nhãn, và **chỉ nhận email thuộc domain
công ty hoặc hộp thư miễn phí** — trang tin/PR trên website công ty thường kèm email
nhà báo ở domain khác, lấy vào là sai. App cũng giải mã được **Cloudflare Email
Protection** (`data-cfemail` / `/cdn-cgi/l/email-protection#...`) — rất nhiều site Hàn
đặt sau Cloudflare, email vẫn hiển thị công khai cho khách truy cập nhưng trong HTML bị
thay bằng chuỗi mã hoá.

Nếu site đăng email **dưới dạng ảnh** (vd hyperinfo.co.kr dùng `email-about.png`) thì
app trả `Not found` — không có chữ nào để trích, và app không OCR.

**Key contacts** — tối đa 3 người, ưu tiên CTO → CIO → IT 책임자 → 개발 책임자 →
개발본부장 → 개발팀장 → IT Director → CEO/대표이사. Bỏ CFO/CMO/HR/영업/마케팅 trừ khi
người đó đồng thời là CEO hoặc phụ trách IT. Để tránh dữ liệu sai, tên phải bắt đầu
bằng họ tiếng Hàn, không phải danh từ chung, và với chức danh mơ hồ như `대표` thì
chỉ nhận khi nằm cùng một dòng ngắn — nếu không, tên lãnh đạo công ty đối tác trong
bản tin PR sẽ bị nhận nhầm.

**IT recruitment** — tối đa 10 tin, chỉ lấy vị trí IT/software. Một tiêu đề chỉ chứa
từ khoá IT là chưa đủ: phải có dấu hiệu tuyển dụng (모집/채용/공고/개발자/engineer…)
hoặc block chứa loại hình / hạn nộp. Loại bỏ menu điều hướng và link sản phẩm.

**IT Hiring**: 5+ tin → High, 2–4 → Medium, 1 → Low, 0 → None.

Không dùng AI và không dùng kiến thức ngoài website: mọi giá trị đều trích từ HTML
đã crawl của đúng domain đó.

## Bảo mật

Chỉ chấp nhận `http://` và `https://`. Chặn localhost, 127.0.0.1, 0.0.0.0,
169.254.169.254, dải IP private, `file://`, và port lạ. Redirect được kiểm tra lại
ở từng bước nên không thể vòng qua để trỏ vào mạng nội bộ.

App chỉ đọc dữ liệu công khai và mặc định tôn trọng `robots.txt`. Nếu cần tắt cho
môi trường nội bộ: đặt biến môi trường `RESPECT_ROBOTS=0`. Tắt Playwright:
`ALLOW_PLAYWRIGHT=0`.

## Thông báo lỗi

| Tình huống | Thông báo |
|---|---|
| Không truy cập được / domain không phân giải | `Unable to access website.` |
| Timeout | `Website request timed out.` |
| Website chặn (401/403/429/451, robots) | `Website blocked the request.` |
| URL không hợp lệ / bị chặn | `Invalid URL.` kèm lý do |
| Không có contact | `Key contacts not found.` |
| Không có tin tuyển dụng IT | `No IT recruitment information found.` |

Một trang lỗi không làm hỏng cả lần scan — crawler bỏ qua trang đó và đi tiếp.
