# Cách làm việc trong dự án này

## Định hướng trước, code sau

Với **mọi yêu cầu** của người dùng, trả lời định hướng trước và **dừng lại chờ đồng ý**
rồi mới code. Chỉ bỏ qua bước này với sửa lỗi nhỏ mà người dùng đã chỉ đích danh
(lỗi chính tả, một dòng sai) — và nói rõ là đang bỏ qua.

Câu trả lời định hướng ngắn gọn, tiếng Việt, theo khung:

1. **Kết luận một dòng** — đồng ý / không / một phần, kèm đề xuất của mình.
2. **Vì sao nên** — 2–4 gạch đầu dòng, dựa trên code hiện có và quy trình sales IT
   offshore tại Hàn (không nói chung chung).
3. **Vì sao không làm theo cách hiển nhiên kia** — nó vỡ hoặc rối ở đâu.
4. **Hình dung cụ thể** — sketch nhỏ: URL, bố cục tab, trường dữ liệu, bảng.
5. **Đánh đổi** người dùng cần biết.
6. **Công sức ước lượng** và câu chốt "Bạn gật thì tôi làm."

Khi người dùng gật ("ok làm luôn"), code trọn vẹn: test (`python backend/test_scanner.py`,
`python backend/check_i18n.py`), thử thật trong trình duyệt, cập nhật README vi/ko và
ảnh (`python backend/take_screenshots.py`), commit rồi push.

## Nguyên tắc của app

- Chỉ dữ liệu công khai lấy từ đúng website đã nhập; không có dữ liệu mẫu / mặc định /
  suy đoán; thiếu thì "찾을 수 없음" và nếu biết lý do thì nói lý do.
- Giao diện mặc định tiếng Hàn, có tiếng Việt; mọi chuỗi qua `frontend/i18n.js`.
- Không commit `data/`, `*.db` (repo public, chứa dữ liệu công ty đã quét).
- Không dùng `window.confirm/alert` (bị chặn trong trình duyệt nhúng) — dùng
  `askConfirm()` và `toast()` sẵn có.
