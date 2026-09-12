"""Kiểm tra bản dịch: python backend/check_i18n.py
번역 검사 도구 — 화면에 보이는 문자열이 모두 i18n을 거치는지 확인합니다.

Ba việc:
1. Hai bảng từ điển (ko / vi) phải có cùng bộ khoá, và bản tiếng Hàn phải
   thực sự là tiếng Hàn.
2. Mọi khoá dùng trong HTML / app.js phải tồn tại trong từ điển, và không có
   khoá nào thừa.
3. Không còn chuỗi tiếng Việt viết thẳng trong HTML / app.js. Chú thích code
   được bỏ qua — đó là ghi chú cho lập trình viên, không hiển thị cho người dùng.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"

# Nguyên âm có dấu riêng của tiếng Việt — không xuất hiện trong tiếng Hàn/Anh.
VIETNAMESE_CHARS = re.compile(
    r"[ăâđêôơưĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩị"
    r"óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵÁÀẢÃẠÉÈẺẼẸÍÌỈĨỊÓÒỎÕỌÚÙỦŨỤÝỲỶỸỴ]"
)

HANGUL = re.compile(r"[가-힣]")

# Khoá cố ý giữ nguyên tiếng Anh: tên sản phẩm, nhãn kỹ thuật, tên ngôn ngữ.
KEEP_AS_IS = {
    "scan.title", "scan.heading", "saved.title", "result.json.heading",
    "lang.ko", "lang.vi", "saved.col.hiring", "csv.hiring",
    "result.company.email", "result.company.website",
    "saved.col.email", "saved.col.website", "csv.email", "csv.website", "batch.col.hiring",
    "crm.source.linkedin", "crm.hot", "crm.form.email", "crm.form.website",
}

failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)
    print("  FAIL " + message)


def ok(message: str) -> None:
    print("  ok   " + message)


def read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def dictionary_block(source: str, lang: str) -> str:
    """Trả về nguyên khối `<lang>: { ... }` trong DICT của i18n.js."""
    start = source.index(f"  {lang}: {{")
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index]
    raise AssertionError(f"khong doc duoc khoi {lang} trong DICT")


def string_literals(js: str) -> list[str]:
    """Mọi chuỗi trong file JS, bỏ qua chú thích.

    Phải duyệt từng ký tự: chú thích viết cùng dòng với code ("// kết quả
    thật") làm hỏng cách tách chuỗi bằng regex — dấu nháy hai bên chú thích
    bị ghép thành một chuỗi giả.
    """
    literals: list[str] = []
    index, length = 0, len(js)
    previous = ""       # ký tự có nghĩa gần nhất, để nhận ra regex literal
    while index < length:
        char = js[index]

        if char == "/" and index + 1 < length and js[index + 1] == "/":
            index = js.find("\n", index)
            if index == -1:
                break
            continue
        if char == "/" and index + 1 < length and js[index + 1] == "*":
            end = js.find("*/", index + 2)
            index = length if end == -1 else end + 2
            continue

        # Regex literal: /[&<>"']/g — dấu nháy bên trong không mở chuỗi.
        if char == "/" and (previous == "" or previous in "(,=:[!&|?{};+"):
            index += 1
            while index < length:
                if js[index] == "\\":
                    index += 2
                    continue
                if js[index] == "[":
                    close = js.find("]", index)
                    index = length if close == -1 else close + 1
                    continue
                if js[index] in "/\n":
                    break
                index += 1
            index += 1
            previous = "/"
            continue

        if char in "\"'`":
            quote = char
            index += 1
            start = index
            while index < length:
                if js[index] == "\\":
                    index += 2
                    continue
                if js[index] == quote:
                    break
                index += 1
            literals.append(js[start:index])
            index += 1
            previous = quote
            continue

        if not char.isspace():
            previous = char
        index += 1
    return literals


print("tu dien")
i18n_source = read("i18n.js")
ko_block = dictionary_block(i18n_source, "ko")
vi_block = dictionary_block(i18n_source, "vi")
ko_entries = dict(re.findall(r'^\s*"([\w.]+)":\s*"(.*?)",\s*$', ko_block, re.M))
vi_entries = dict(re.findall(r'^\s*"([\w.]+)":\s*"(.*?)",\s*$', vi_block, re.M))
ko_keys, vi_keys = set(ko_entries), set(vi_entries)

ok(f"tieng Han co {len(ko_keys)} khoa")
missing_vi = sorted(ko_keys - vi_keys)
missing_ko = sorted(vi_keys - ko_keys)
if missing_vi:
    fail(f"tieng Viet thieu khoa: {missing_vi}")
else:
    ok("tieng Viet du khoa")
if missing_ko:
    fail(f"tieng Han thieu khoa: {missing_ko}")
else:
    ok("tieng Han du khoa")

print("noi dung tieng Han")
not_translated = [key for key, value in ko_entries.items()
                  if key not in KEEP_AS_IS and not HANGUL.search(value)]
if not_translated:
    fail(f"khoa tieng Han chua co chu Hangul: {sorted(not_translated)}")
else:
    ok(f"{len(ko_entries) - len(KEEP_AS_IS & ko_keys)} ban dich deu co chu Hangul")

still_vietnamese = [key for key, value in ko_entries.items()
                    if key not in KEEP_AS_IS and VIETNAMESE_CHARS.search(value)]
if still_vietnamese:
    fail(f"ban tieng Han con chu tieng Viet: {sorted(still_vietnamese)}")
else:
    ok("ban tieng Han khong lan tieng Viet")

# -- Khoá dùng trong code có khớp từ điển không ----------------------------

print("khoa dung trong code")
app_js = read("app.js") + read("crm.js")
html = read("index.html") + read("saved.html") + read("crm.html")

used = set(re.findall(r'data-i18n(?:-placeholder|-title)?="([\w.]+)"', html))
# (?<![\w.]) để không dính vào createElement("a") hay closest("tr").
used |= set(re.findall(r'(?<![\w.])t\("([\w.]+)"', app_js))
used = {key for key in used if not key.endswith(".")}   # bỏ tiền tố ghép động

# Khoá ghép lúc chạy: t("stage." + id), t("result.save." + state), t("error." + code)
used |= {f"stage.{name}" for name in
         ("homepage", "company", "contact", "management", "recruitment", "extract", "done")}
used |= {f"result.save.{name}" for name in ("idle", "saving", "saved", "error")}
used |= {f"error.{name}" for name in
         ("invalid_url", "unreachable", "timeout", "blocked", "internal")}
used |= {f"signal.{name}" for name in ("High", "Medium", "Low", "None")}

# CRM: t(`crm.${group}.${code}`) voi cac danh sach trong crm.js
CRM_GROUPS = {
    "status": ("new", "contacted", "meeting", "proposal", "negotiation", "won", "lost", "hold"),
    "rank": ("staff", "assistant", "manager", "deputy", "general", "director", "md", "evp", "svp", "ceo", "cto", "cio", "other"),
    "source": ("scanner", "referral", "exhibition", "linkedin", "wanted", "saramin", "jobkorea", "coldcall", "website", "naver", "other"),
    "project": ("dispatch", "contract", "si", "sm", "odc", "other"),
    "size": ("enterprise", "midsize", "sme", "startup", "public"),
    "lost": ("price", "schedule", "competitor", "inhouse", "budget", "language", "other"),
    "activity": ("call", "email", "kakao", "meeting", "proposal", "quote", "other"),
    "score": ("hiring", "rank", "email", "phone", "kakao", "budget", "source", "project", "biz", "timing", "team"),
    "error": ("company_required", "email_invalid", "file_invalid"),
    "mail.subject": ("cold", "followup", "quote"),
    "mail.body": ("cold", "followup", "quote"),
}
used |= {"result.hint.image", "result.hint.form"}   # t("result.hint." + hint.type)
used |= {f"batch.status.{name}" for name in ("waiting", "running", "done", "saved", "error", "stopped")}
for group, codes in CRM_GROUPS.items():
    used |= {f"crm.{group}.{code}" for code in codes}
# EXPORT_FIELDS trong crm.js: [["company_name", "crm.form.company"], ...] -> t(key) luc xuat file
used |= set(re.findall(r'\["\w+", "(crm\.[\w.]+)"\]', read("crm.js")))

unknown = sorted(used - ko_keys)
if unknown:
    fail(f"code dung khoa khong co trong tu dien: {unknown}")
else:
    ok(f"{len(used)} khoa dung trong code deu ton tai")

unused = sorted(ko_keys - used)
if unused:
    fail(f"khoa thua khong ai dung: {unused}")
else:
    ok("khong co khoa thua")

# -- Còn chuỗi tiếng Việt viết thẳng không ---------------------------------

print("chuoi con sot")
for name in ("index.html", "saved.html", "crm.html"):
    body = re.sub(r"<!--.*?-->", "", read(name), flags=re.S)
    leftovers = [line.strip() for line in body.splitlines() if VIETNAMESE_CHARS.search(line)]
    if leftovers:
        fail(f"{name} con chuoi tieng Viet: {leftovers[:3]}")
    else:
        ok(f"{name} khong con chuoi tieng Viet")

for name in ("app.js", "crm.js"):
    leftovers = [text for text in string_literals(read(name)) if VIETNAMESE_CHARS.search(text)]
    if leftovers:
        fail(f"{name} con chuoi tieng Viet hien thi: {leftovers[:5]}")
    else:
        ok(f"{name} khong con chuoi tieng Viet hien thi")

print()
if failures:
    print(f"{len(failures)} loi:")
    for failure in failures:
        print("  -", failure)
    sys.exit(1)
print("tat ca kiem tra ban dich deu dat")
