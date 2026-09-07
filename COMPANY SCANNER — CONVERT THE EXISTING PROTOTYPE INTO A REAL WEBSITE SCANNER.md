# COMPANY SCANNER — CONVERT THE EXISTING PROTOTYPE INTO A REAL WEBSITE SCANNER

Bạn đang được cung cấp một prototype có sẵn:

`Company-Scanner-Prototype-Ui.html`

hoặc:

`Company-Scanner-Prototype-Ui (1).html`

Hãy đọc code hiện tại trước khi sửa.

Prototype hiện tại là giao diện demo cho một công cụ:

> **Quét thông tin doanh nghiệp cho IT Outsourcing**

Mục tiêu của task này là:

> **Giữ nguyên giao diện prototype càng nhiều càng tốt, nhưng thay toàn bộ dữ liệu mô phỏng bằng dữ liệu lấy thật từ website mà user nhập.**

---

# 1. MỤC TIÊU THỰC TẾ

User nhập:

```text
https://www.company.co.kr
```

Sau đó app:

```text
URL
 ↓
Truy cập website thật
 ↓
Tìm các trang liên quan
 ↓
Đọc nội dung
 ↓
Trích xuất thông tin
 ↓
Hiển thị kết quả
```

Chỉ cần trả về những thông tin hữu ích cho **IT outsourcing sales**.

---

# 2. THÔNG TIN CẦN LẤY

## A. COMPANY

Chỉ cần:

- Tên công ty
- Địa chỉ
- Số điện thoại
- Lĩnh vực hoạt động
- Website

Không cần cố thu thập tất cả thông tin doanh nghiệp.

Nếu không tìm thấy:

```text
Not found
```

---

# 3. KEY CONTACTS

Không lấy toàn bộ ban lãnh đạo.

Mục tiêu là tìm **người có khả năng liên quan đến quyết định sử dụng dịch vụ IT/software**.

Tối đa:

**3 người.**

Ưu tiên:

```text
1. CTO
2. CIO
3. IT 책임자
4. 개발 책임자
5. 개발본부장
6. 개발팀장
7. IT Director
8. CEO / 대표이사 / 대표
```

Nếu có CTO thì ưu tiên CTO.

Nếu không có người phụ trách IT/development thì lấy CEO/대표이사.

Không cần lấy:

```text
CFO
CMO
HR
인사
회계
총무
영업
마케팅
```

trừ khi người đó đồng thời giữ vai trò IT hoặc là CEO/대표.

Output:

```text
KEY CONTACTS

김민수
CTO

박철수
대표이사
```

Mỗi người phải có:

- Name
- Position
- Source URL

---

# 4. IT RECRUITMENT

Chỉ tìm tuyển dụng liên quan đến IT/software.

Ưu tiên:

```text
개발자
소프트웨어 개발
백엔드
프론트엔드
풀스택
웹 개발
앱 개발
모바일 개발
AI
머신러닝
데이터
클라우드
DevOps
QA
PM
PO
```

Không lấy các job không liên quan IT:

```text
영업
마케팅
회계
인사
총무
생산
물류
고객상담
```

Tối đa:

**10 IT jobs.**

Mỗi job:

```text
Title
Position
Location
Employment type
Deadline nếu có
Short description nếu có
Source URL
```

---

# 5. CRAWLER

Crawler phải thực sự truy cập website.

Không được giả lập việc crawl bằng timer.

Không được sử dụng mock data.

Không được chỉ thay URL trong một object dữ liệu mẫu.

Crawler nên:

1. Fetch homepage.
2. Parse HTML.
3. Tìm các link quan trọng.
4. Crawl các trang liên quan.
5. Extract information.

Giới hạn:

```text
MAX_PAGES = 20
MAX_DEPTH = 2
TIMEOUT = 15 seconds
```

Không crawl vô hạn.

---

# 6. PRIORITY PAGES

Từ homepage, ưu tiên tìm các trang có URL hoặc anchor text liên quan đến:

### Company

```text
회사
회사소개
기업
기업소개
회사정보
회사개요
about
company
```

### Contact

```text
연락처
오시는길
찾아오시는길
주소
contact
location
```

### Management

```text
대표
대표이사
CEO
경영진
임원
조직
조직도
CTO
CIO
개발책임자
```

### Recruitment

```text
채용
채용공고
채용정보
인재채용
인재영입
채용안내
career
careers
jobs
recruitment
```

Không cần crawl toàn bộ website.

---

# 7. DOMAIN ISOLATION

Đây là yêu cầu bắt buộc.

Nếu user nhập:

```text
https://company-a.co.kr
```

thì scan phải thuộc về:

```text
company-a.co.kr
```

Không được lấy dữ liệu của:

```text
company-b.co.kr
fpt.com
google.com
```

hoặc bất kỳ công ty nào khác.

Có thể follow các subdomain thực sự thuộc cùng company nếu cần, nhưng phải kiểm tra domain.

---

# 8. NO MOCK DATA

Prototype hiện tại có dữ liệu mẫu để demo UI.

Ví dụ dữ liệu FPT hoặc các company/job mẫu trong source code chỉ được dùng để demo.

Khi app chạy thật:

**PHẢI LOẠI BỎ mock data khỏi scan flow.**

Không được:

```text
if crawler fails:
    return FPT
```

Không được:

```text
defaultCompany
sampleCompany
mockCompany
fallbackCompany
```

Không được dùng dữ liệu scan trước để trả về cho URL mới.

Mỗi URL phải tạo kết quả từ website thực tế tương ứng.

---

# 9. NO-DATA FALLBACK

Nếu website không có thông tin:

```text
Company name: Not found
Address: Not found
Phone: Not found
Key contacts: Not found
IT recruitment: Not found
```

Tuyệt đối không lấy dữ liệu của công ty khác để lấp vào.

Nguyên tắc:

> **Accuracy > Completeness**

Thà trả về `Not found` còn hơn trả về dữ liệu sai.

---

# 10. SOURCE VALIDATION

Mọi thông tin quan trọng phải có source.

Ví dụ:

```text
Company
Hyperinfo

Source:
https://www.hyperinfo.co.kr/company
```

Contact:

```text
김민수
CTO

Source:
https://www.hyperinfo.co.kr/company
```

Job:

```text
Backend Developer

Source:
https://www.hyperinfo.co.kr/careers/backend
```

Nếu không xác định được source từ target website:

→ không hiển thị dữ liệu đó như dữ liệu thật.

---

# 11. COMPANY IDENTITY VALIDATION

Không chỉ lấy title của homepage rồi coi đó chắc chắn là tên công ty.

Hãy kiểm tra nhiều tín hiệu nếu có:

- page title
- meta description
- footer
- company introduction
- contact page
- address
- phone
- canonical URL
- domain

Mục tiêu:

> Đảm bảo dữ liệu được extract thực sự thuộc website user nhập.

Nếu thông tin mâu thuẫn:

→ ưu tiên nguồn chính thức hơn.

Nếu không thể xác định:

→ `Not found`.

Không suy đoán.

---

# 12. KOREAN WEBSITE

Website mục tiêu chủ yếu là website Hàn Quốc.

Phải xử lý tốt:

```text
UTF-8
EUC-KR
CP949
```

Không để lỗi tiếng Hàn.

Ví dụ không được xuất hiện:

```text
ì°ë¦¬íì¬
```

---

# 13. JAVASCRIPT

Ưu tiên:

```text
HTTP request
+
HTML parser
```

Nếu HTML ban đầu không chứa nội dung cần thiết vì website render bằng JavaScript:

→ sử dụng Playwright.

Không dùng Playwright cho mọi page.

---

# 14. AI

AI chỉ được dùng để **hiểu và cấu trúc nội dung đã crawl**.

AI không được sử dụng kiến thức bên ngoài để bổ sung thông tin.

Ví dụ:

Website không ghi CTO.

AI không được trả:

```text
CTO: 김민수
```

chỉ vì model biết hoặc đoán công ty có người này.

AI chỉ được extract từ:

```text
Crawled content
+
Target website
```

Nếu không có:

```text
null
```

---

# 15. SIMPLE IT HIRING SIGNAL

Có thể giữ một tín hiệu đơn giản để hỗ trợ sales.

```text
IT Hiring
```

Rule:

```text
5+ IT jobs → High
2–4 IT jobs → Medium
1 IT job → Low
0 → None
```

Không cần điểm 0–100.

Không cần AI scoring.

Không cần Fit Score.

---

# 16. FRONTEND

**Giữ nguyên UI hiện tại của prototype.**

Không redesign toàn bộ.

Giữ:

- Header
- URL input
- Scan button
- Scan progress
- Company information card
- Key contacts section
- Recruitment section
- Source links
- JSON viewer
- Export JSON
- Export CSV

Prototype hiện tại đã có các thành phần này.

Chỉ thay:

```text
MOCK DATA
```

bằng:

```text
REAL CRAWLED DATA
```

---

# 17. SCAN PROGRESS

Giữ workflow progress hiện tại nhưng phải phản ánh trạng thái thật.

Ví dụ:

```text
Đang truy cập trang chủ...
```

```text
Đang tìm trang công ty...
```

```text
Đang tìm thông tin liên hệ...
```

```text
Đang tìm ban lãnh đạo...
```

```text
Đang tìm tuyển dụng...
```

```text
Đang trích xuất thông tin...
```

```text
Hoàn thành.
```

Không sử dụng fake `setInterval()` chỉ để tạo cảm giác đang scan.

---

# 18. ERROR HANDLING

Nếu website không truy cập được:

```text
Unable to access website.
```

Timeout:

```text
Website request timed out.
```

Website block crawler:

```text
Website blocked the request.
```

Không tìm thấy company:

```text
Company information not found.
```

Không tìm thấy contacts:

```text
Key contacts not found.
```

Không có IT recruitment:

```text
No IT recruitment information found.
```

Một trang lỗi không được làm toàn bộ scan crash.

---

# 19. SECURITY

User nhập URL tùy ý.

Chỉ cho phép:

```text
http://
https://
```

Chặn:

```text
localhost
127.0.0.1
0.0.0.0
169.254.169.254
private IP ranges
file://
```

Không bypass:

- CAPTCHA
- login
- authentication
- paywall
- anti-bot
- access control

Chỉ thu thập dữ liệu công khai.

---

# 20. BACKEND

Nếu prototype hiện tại là frontend-only, thêm backend đơn giản.

Ưu tiên:

```text
Python
FastAPI
httpx
BeautifulSoup / lxml
Playwright
```

Frontend hiện tại có thể giữ framework đang dùng.

**Không rewrite project chỉ để đổi framework.**

---

# 21. DATABASE

Không cần database cho MVP nếu chưa có nhu cầu.

Flow có thể đơn giản:

```text
POST /scan

URL
 ↓
Crawler
 ↓
Extractor
 ↓
JSON result
 ↓
Frontend
```

Không thêm PostgreSQL chỉ vì có thể cần trong tương lai.

---

# 22. RESULT DATA STRUCTURE

Backend nên trả JSON dạng đơn giản:

```json
{
  "company": {
    "name": "",
    "address": "",
    "phone": "",
    "industry": "",
    "website": ""
  },

  "key_contacts": [
    {
      "name": "",
      "position": "",
      "source_url": ""
    }
  ],

  "it_recruitment": [
    {
      "title": "",
      "position": "",
      "location": "",
      "employment_type": "",
      "deadline": "",
      "description": "",
      "source_url": ""
    }
  ],

  "sales_signal": {
    "it_hiring": "High"
  },

  "sources": []
}
```

Không thêm các field không cần thiết.

---

# 23. EXPORT

Giữ chức năng Export JSON và CSV hiện tại.

Nhưng export phải sử dụng **real scan result**.

Không export mock FPT data.

---

# 24. TEST

Sau khi hoàn thành, test bằng một website Hàn Quốc thực tế.

Ví dụ:

```text
http://www.hyperinfo.co.kr
```

Nếu website không truy cập được:

**không fake kết quả.**

Test thêm các trường hợp:

1. Website hoạt động bình thường.
2. Website redirect HTTP → HTTPS.
3. Website có tiếng Hàn.
4. Website có recruitment page.
5. Website không có recruitment.
6. Website dùng JavaScript.
7. Website không truy cập được.
8. URL không hợp lệ.

---

# 25. IMPORTANT — DO NOT OVER-ENGINEER

Đây là một MVP đơn giản.

Không xây:

```text
CRM
Login
Payment
Bulk scanning
Funding database
External company API
Microservices
Kubernetes
Kafka
Redis
Complex queue
Sales automation
Email automation
```

Không cần hệ thống scoring phức tạp.

Không cần database nếu chưa cần.

Mục tiêu:

```text
INPUT URL
     ↓
CRAWL WEBSITE
     ↓
EXTRACT USEFUL SALES INFORMATION
     ↓
DISPLAY RESULT
```

---

# 26. DEFINITION OF DONE

Task hoàn thành khi user có thể:

1. Nhập URL website.
2. Bấm Scan.
3. App thực sự truy cập website.
4. Crawl các trang liên quan.
5. Trả về tên công ty.
6. Trả về địa chỉ.
7. Trả về số điện thoại.
8. Trả về lĩnh vực.
9. Tìm tối đa 3 IT key contacts.
10. Tìm IT recruitment nếu có.
11. Hiển thị source URL.
12. Hiển thị IT Hiring signal.
13. Export JSON.
14. Export CSV.
15. Không bao giờ trả dữ liệu của một công ty khác.

---

# FINAL RULE

Prototype hiện tại là **UI reference**, không phải nguồn dữ liệu.

Hãy giữ giao diện hiện tại và thay thế logic mock bằng crawler thật.

Nguyên tắc quan trọng nhất:

> **Mỗi URL = một company scan độc lập.**

> **Chỉ trả dữ liệu có bằng chứng từ target website.**

> **Không có dữ liệu = Not found.**

> **Không được dùng mock/sample/fallback data để hoàn thành kết quả.**

> **Không cần thu thập nhiều dữ liệu; chỉ thu thập dữ liệu hữu ích cho IT outsourcing sales.**

Bắt đầu bằng việc kiểm tra source code hiện tại, xác định phần mock data và scan logic hiện tại, sau đó sửa trực tiếp trên project.