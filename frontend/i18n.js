/* 다국어 처리 — 기본 언어는 한국어(ko), 베트남어(vi)로 전환 가능.
   Đa ngôn ngữ — mặc định tiếng Hàn (ko), có thể chuyển sang tiếng Việt (vi).

   HTML: data-i18n / data-i18n-placeholder / data-i18n-title 속성 사용
   JS  : t("key", { param: value }) 사용 */

const DEFAULT_LANG = "ko";
const SUPPORTED_LANGS = ["ko", "vi"];
const LANG_STORAGE_KEY = "company-scanner-lang";

const DICT = {
  ko: {
    // -- 공통 -------------------------------------------------------------
    "brand.subtitle": "IT 아웃소싱을 위한 기업 정보 스캐너",
    "nav.scan": "새 스캔",
    "nav.saved": "저장된 기업",
    "footer.note": "Company Scanner • IT 아웃소싱 리드 발굴 • 입력한 웹사이트에서만 데이터를 수집합니다 — 데이터가 없으면 찾을 수 없음",
    "common.notFound": "찾을 수 없음",
    "common.source": "출처",
    "lang.ko": "한국어",
    "lang.vi": "Tiếng Việt",

    // -- 스캔 페이지 ---------------------------------------------------------
    "scan.title": "Company Scanner",
    "scan.heading": "Korean IT Company Scanner",
    "scan.description": "기업 웹사이트 주소를 입력하면 홈페이지에 접속해 회사 소개·연락처·채용 페이지를 찾아 기업명, 주소, 전화번호, 이메일, IT 경영진, IT 채용 공고를 추출합니다.",
    "scan.placeholder": "웹사이트 주소를 입력하세요",
    "scan.button": "스캔 시작",
    "scan.buttonBusy": "스캔 중...",
    "scan.limits": "실제 크롤러, 공개 데이터만 수집 — 최대 20페이지 · 깊이 2 · 타임아웃 15초, 입력한 도메인만 스캔합니다.",

    "scan.card.company": "기업 정보",
    "scan.card.companyDesc": "기업명, 주소, 전화번호, 업종",
    "scan.card.contacts": "주요 담당자",
    "scan.card.contactsDesc": "CTO, CIO, CEO — 최대 3명",
    "scan.card.jobs": "IT 채용",
    "scan.card.jobsDesc": "최대 10건 + 출처 링크",

    // -- 진행 단계 ----------------------------------------------------------
    "stage.homepage": "홈페이지 접속 중...",
    "stage.company": "회사 소개 페이지 찾는 중...",
    "stage.contact": "연락처 정보 찾는 중...",
    "stage.management": "경영진 정보 찾는 중...",
    "stage.recruitment": "채용 정보 찾는 중...",
    "stage.extract": "정보 추출 중...",
    "stage.done": "완료.",

    // -- 결과 --------------------------------------------------------------
    "result.done": "스캔 완료",
    "result.summary": "출처: {website} • {pages}개 페이지 크롤링",
    "result.save.idle": "데이터베이스에 저장",
    "result.save.saving": "저장 중...",
    "result.save.saved": "저장됨",
    "result.save.error": "다시 저장",
    "result.json.show": "JSON 보기",
    "result.json.hide": "JSON 숨기기",
    "result.json.heading": "Structured JSON Output",
    "result.json.copy": "복사",

    "result.company.heading": "기업 정보",
    "result.company.desc": "{pages}개 페이지에서 추출",
    "result.company.openSite": "웹사이트 열기",
    "result.company.address": "본사 주소",
    "result.company.phone": "전화번호",
    "result.company.email": "이메일",
    "result.company.industry": "사업 분야",
    "result.company.website": "웹사이트",

    "result.contacts.heading": "주요 담당자",
    "result.contacts.desc": "CTO / CIO / IT 우선 — 최대 3명",
    "result.contacts.empty": "주요 담당자를 찾을 수 없습니다.",

    "signal.High": "높음",
    "signal.Medium": "보통",
    "signal.Low": "낮음",
    "signal.None": "없음",
    "signal.label": "IT 채용: {level}",

    "result.jobs.heading": "IT 채용",
    "result.jobs.desc": "웹사이트에서 IT 포지션 {count}건 발견",
    "result.jobs.empty": "IT 채용 정보를 찾을 수 없습니다.",

    "result.sources.heading": "데이터 출처",
    "result.sources.desc": "스캔한 도메인의 {count}개 페이지",

    // -- 오류 --------------------------------------------------------------
    "error.invalid_url": "URL이 올바르지 않습니다.",
    "error.unreachable": "웹사이트에 접속할 수 없습니다.",
    "error.timeout": "웹사이트 응답 시간이 초과되었습니다.",
    "error.blocked": "웹사이트가 요청을 차단했습니다.",
    "error.internal": "스캔에 실패했습니다.",
    "error.disconnected": "스캔 중 서버 연결이 끊겼습니다.",
    "error.saveFailed": "데이터베이스에 저장하지 못했습니다.",
    "error.saveFailedDetail": "서버 창을 확인한 뒤 다시 시도하세요.",
    "error.openSavedFailed": "저장된 기업을 열 수 없습니다.",
    "error.openSavedFailedDetail": "데이터베이스에서 삭제되었을 수 있습니다.",

    // -- 저장된 기업 페이지 ---------------------------------------------------
    "saved.title": "저장된 기업 — Company Scanner",
    "saved.heading": "저장된 기업",
    "saved.description": "스캔 후 데이터베이스에 저장한 모든 기업입니다. {view} 버튼을 누르면 다시 스캔하지 않고 전체 결과를 볼 수 있습니다.",
    "saved.listHeading": "목록",
    "saved.loading": "불러오는 중...",
    "saved.searchPlaceholder": "기업명, 이메일, 업종, 웹사이트로 검색...",
    "saved.refresh": "새로고침",
    "saved.export": "내보내기",
    "saved.exportCsv": "Excel 내보내기 (.csv)",
    "saved.exportJson": "전체 JSON 내보내기 (.json)",

    "saved.col.name": "기업명",
    "saved.col.address": "주소",
    "saved.col.phone": "전화번호",
    "saved.col.email": "이메일",
    "saved.col.industry": "업종",
    "saved.col.website": "웹사이트",
    "saved.col.hiring": "IT 채용",
    "saved.col.updated": "업데이트",

    "saved.count": "데이터베이스에 {total}개 기업",
    "saved.countFiltered": "\"{query}\" 검색 결과 {shown}/{total}개 기업",
    "saved.empty": "저장된 기업이 없습니다. \"새 스캔\"에서 웹사이트를 스캔한 뒤 \"데이터베이스에 저장\"을 누르세요.",
    "saved.emptyFiltered": "검색어와 일치하는 기업이 없습니다.",
    "saved.action.view": "보기",
    "saved.action.delete": "삭제",
    "saved.confirmDelete": "\"{name}\"을(를) 데이터베이스에서 삭제할까요?",
    "saved.thisCompany": "이 기업",
    "saved.jobsUnit": "{count}건",
    "saved.loadFailed": "목록을 불러오지 못했습니다. 서버를 확인한 뒤 새로고침을 누르세요.",
    "saved.deleteFailed": "삭제하지 못했습니다. 잠시 후 다시 시도하세요.",
    "saved.exportFailed": "JSON 내보내기에 필요한 전체 데이터를 불러오지 못했습니다.",

    // -- CSV 머리글 ---------------------------------------------------------
    "csv.name": "기업명",
    "csv.address": "주소",
    "csv.phone": "전화번호",
    "csv.email": "이메일",
    "csv.industry": "업종",
    "csv.website": "웹사이트",
    "csv.hiring": "IT 채용",
    "csv.jobCount": "IT 포지션 수",
    "csv.contactCount": "주요 담당자 수",
    "csv.updated": "업데이트",
  },

  vi: {
    // -- Chung -------------------------------------------------------------
    "brand.subtitle": "Quét thông tin doanh nghiệp cho IT Outsourcing",
    "nav.scan": "Quét mới",
    "nav.saved": "Công ty đã lưu",
    "footer.note": "Company Scanner • Lead generation cho IT Outsourcing • Dữ liệu chỉ lấy từ website bạn nhập — không có dữ liệu = Not found",
    "common.notFound": "Not found",
    "common.source": "Nguồn",
    "lang.ko": "한국어",
    "lang.vi": "Tiếng Việt",

    // -- Trang quét ---------------------------------------------------------
    "scan.title": "Company Scanner",
    "scan.heading": "Korean IT Company Scanner",
    "scan.description": "Nhập website công ty, hệ thống sẽ truy cập trang chủ, tìm trang giới thiệu, liên hệ và tuyển dụng để trích xuất tên, địa chỉ, SĐT, email, lãnh đạo IT và tin tuyển dụng IT.",
    "scan.placeholder": "Hãy nhập địa chỉ web",
    "scan.button": "Quét ngay",
    "scan.buttonBusy": "Đang quét...",
    "scan.limits": "Crawler thật, chỉ dữ liệu công khai — tối đa 20 trang · độ sâu 2 · timeout 15s, chỉ quét đúng domain bạn nhập.",

    "scan.card.company": "Thông tin công ty",
    "scan.card.companyDesc": "Tên, địa chỉ, SĐT, lĩnh vực",
    "scan.card.contacts": "Key contacts",
    "scan.card.contactsDesc": "CTO, CIO, CEO — tối đa 3",
    "scan.card.jobs": "Tuyển dụng IT",
    "scan.card.jobsDesc": "Tối đa 10 vị trí + link nguồn",

    // -- Tiến trình ---------------------------------------------------------
    "stage.homepage": "Đang truy cập trang chủ...",
    "stage.company": "Đang tìm trang công ty...",
    "stage.contact": "Đang tìm thông tin liên hệ...",
    "stage.management": "Đang tìm ban lãnh đạo...",
    "stage.recruitment": "Đang tìm tuyển dụng...",
    "stage.extract": "Đang trích xuất thông tin...",
    "stage.done": "Hoàn thành.",

    // -- Kết quả ------------------------------------------------------------
    "result.done": "Đã quét xong",
    "result.summary": "Nguồn: {website} • {pages} trang đã crawl",
    "result.save.idle": "Lưu vào database",
    "result.save.saving": "Đang lưu...",
    "result.save.saved": "Đã lưu",
    "result.save.error": "Lưu lại",
    "result.json.show": "Xem JSON",
    "result.json.hide": "Ẩn JSON",
    "result.json.heading": "Structured JSON Output",
    "result.json.copy": "Copy",

    "result.company.heading": "Thông tin công ty",
    "result.company.desc": "Trích xuất từ {pages} trang đã crawl",
    "result.company.openSite": "Mở website",
    "result.company.address": "Địa chỉ trụ sở",
    "result.company.phone": "Điện thoại",
    "result.company.email": "Email",
    "result.company.industry": "Lĩnh vực hoạt động",
    "result.company.website": "Website",

    "result.contacts.heading": "Key contacts",
    "result.contacts.desc": "Ưu tiên CTO / CIO / IT — tối đa 3 người",
    "result.contacts.empty": "Key contacts not found.",

    "signal.High": "Cao",
    "signal.Medium": "Trung bình",
    "signal.Low": "Thấp",
    "signal.None": "Không",
    "signal.label": "IT Hiring: {level}",

    "result.jobs.heading": "Tuyển dụng IT",
    "result.jobs.desc": "{count} vị trí IT tìm thấy trên website",
    "result.jobs.empty": "No IT recruitment information found.",

    "result.sources.heading": "Nguồn dữ liệu",
    "result.sources.desc": "{count} trang thuộc domain đã quét",

    // -- Lỗi ----------------------------------------------------------------
    "error.invalid_url": "URL không hợp lệ.",
    "error.unreachable": "Không truy cập được website.",
    "error.timeout": "Website phản hồi quá lâu.",
    "error.blocked": "Website đã chặn yêu cầu.",
    "error.internal": "Quét thất bại.",
    "error.disconnected": "Mất kết nối tới server khi đang quét.",
    "error.saveFailed": "Không lưu được vào database.",
    "error.saveFailedDetail": "Kiểm tra cửa sổ server rồi thử lại.",
    "error.openSavedFailed": "Không mở được công ty đã lưu.",
    "error.openSavedFailedDetail": "Có thể công ty này đã bị xoá khỏi database.",

    // -- Trang công ty đã lưu -------------------------------------------------
    "saved.title": "Công ty đã lưu — Company Scanner",
    "saved.heading": "Công ty đã lưu",
    "saved.description": "Toàn bộ công ty đã quét và lưu vào database. Bấm {view} để mở lại kết quả đầy đủ mà không phải quét lại.",
    "saved.listHeading": "Danh sách",
    "saved.loading": "Đang tải...",
    "saved.searchPlaceholder": "Tìm theo tên, email, lĩnh vực, website...",
    "saved.refresh": "Làm mới",
    "saved.export": "Xuất",
    "saved.exportCsv": "Xuất Excel (.csv)",
    "saved.exportJson": "Xuất JSON đầy đủ (.json)",

    "saved.col.name": "Tên công ty",
    "saved.col.address": "Địa chỉ",
    "saved.col.phone": "Số điện thoại",
    "saved.col.email": "Email",
    "saved.col.industry": "Lĩnh vực",
    "saved.col.website": "Website",
    "saved.col.hiring": "IT Hiring",
    "saved.col.updated": "Cập nhật",

    "saved.count": "{total} công ty trong database",
    "saved.countFiltered": "{shown}/{total} công ty khớp \"{query}\"",
    "saved.empty": "Chưa có công ty nào. Sang trang \"Quét mới\", quét một website rồi bấm \"Lưu vào database\".",
    "saved.emptyFiltered": "Không có công ty nào khớp từ khoá.",
    "saved.action.view": "Xem",
    "saved.action.delete": "Xoá",
    "saved.confirmDelete": "Xoá \"{name}\" khỏi database?",
    "saved.thisCompany": "công ty này",
    "saved.jobsUnit": "{count} vị trí",
    "saved.loadFailed": "Không tải được danh sách. Kiểm tra server rồi bấm Làm mới.",
    "saved.deleteFailed": "Không xoá được. Thử lại sau.",
    "saved.exportFailed": "Không tải được dữ liệu đầy đủ để xuất JSON.",

    // -- Tiêu đề CSV ---------------------------------------------------------
    "csv.name": "Tên công ty",
    "csv.address": "Địa chỉ",
    "csv.phone": "Số điện thoại",
    "csv.email": "Email",
    "csv.industry": "Lĩnh vực",
    "csv.website": "Website",
    "csv.hiring": "IT Hiring",
    "csv.jobCount": "Số vị trí IT",
    "csv.contactCount": "Số key contacts",
    "csv.updated": "Cập nhật",
  },
};

function readStoredLang() {
  try {
    const stored = localStorage.getItem(LANG_STORAGE_KEY);
    if (stored && SUPPORTED_LANGS.includes(stored)) return stored;
  } catch (_) {
    // Trình duyệt chặn localStorage: dùng ngôn ngữ mặc định.
  }
  return DEFAULT_LANG;
}

let currentLang = readStoredLang();

/* t("saved.count", { total: 3 }) -> "데이터베이스에 3개 기업" */
function t(key, params) {
  const table = DICT[currentLang] || DICT[DEFAULT_LANG];
  let text = table[key];
  if (text === undefined) {
    // Thiếu bản dịch thì lấy tiếng Hàn, cuối cùng mới trả chính key.
    text = DICT[DEFAULT_LANG][key] !== undefined ? DICT[DEFAULT_LANG][key] : key;
  }
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      text = text.split(`{${name}}`).join(String(value));
    }
  }
  return text;
}

/* Điền lại mọi phần tử tĩnh có gắn data-i18n. */
function applyStaticTranslations() {
  document.documentElement.lang = currentLang;

  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.placeholder = t(element.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((element) => {
    element.textContent = t(element.dataset.i18nTitle);
  });

  document.querySelectorAll("[data-lang-btn]").forEach((button) => {
    button.classList.toggle("lang-active", button.dataset.langBtn === currentLang);
  });
}

function setLang(lang) {
  if (!SUPPORTED_LANGS.includes(lang) || lang === currentLang) return;
  currentLang = lang;
  try {
    localStorage.setItem(LANG_STORAGE_KEY, lang);
  } catch (_) {
    // Không lưu được thì vẫn đổi cho phiên hiện tại.
  }
  applyStaticTranslations();
  // app.js lắng nghe để vẽ lại phần nội dung động (kết quả, bảng đã lưu).
  window.dispatchEvent(new CustomEvent("langchange", { detail: { lang } }));
}

function getLang() {
  return currentLang;
}

window.t = t;
window.i18n = { t, setLang, getLang, applyStaticTranslations, SUPPORTED_LANGS, DEFAULT_LANG };

document.addEventListener("DOMContentLoaded", () => {
  applyStaticTranslations();
  document.querySelectorAll("[data-lang-btn]").forEach((button) => {
    button.addEventListener("click", () => setLang(button.dataset.langBtn));
  });
});
