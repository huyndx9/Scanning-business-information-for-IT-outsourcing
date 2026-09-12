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

    // -- CRM ---------------------------------------------------------------
    "nav.crm": "CRM 리드",
    "crm.title": "CRM 리드 — Company Scanner",
    "crm.heading": "CRM 리드",
    "crm.description": "IT 아웃소싱 영업 파이프라인. 스캔 결과에서 바로 리드를 만들고, 담당자·예산·발주 시기·활동 기록을 한곳에서 관리합니다.",
    "crm.add": "리드 추가",
    "crm.import": "파일 가져오기",
    "crm.export": "내보내기",
    "crm.exportCsv": "Excel 내보내기 (.csv)",
    "crm.exportJson": "JSON 내보내기 (.json)",
    "crm.search": "회사, 담당자, 전화, 이메일, 사업자번호 검색...",
    "crm.count": "리드 {total}건",
    "crm.countFiltered": "리드 {shown}/{total}건 표시",
    "crm.empty": "아직 리드가 없습니다",
    "crm.emptyDesc": "\"리드 추가\"로 직접 입력하거나, 파일을 가져오거나, 스캔 결과에서 \"CRM 리드로 추가\"를 누르세요.",
    "crm.emptyFiltered": "조건에 맞는 리드가 없습니다.",
    "crm.hot": "HOT",
    "crm.overdueTag": "연체",
    "crm.people": "{count}명",
    "crm.bridge": "한국어 브릿지",
    "crm.unit.eok": "억",
    "crm.unit.man": "만",

    "crm.kpi.pipeline": "총 파이프라인",
    "crm.kpi.pipelineSub": "진행 중 {count}건",
    "crm.kpi.winRate": "수주율",
    "crm.kpi.winRateSub": "수주 {won} / 종료 {closed}건",
    "crm.kpi.newMonth": "이번 달 신규 리드",
    "crm.kpi.newMonthSub": "HOT {count}건",
    "crm.kpi.overdue": "연체 처리 필요",
    "crm.kpi.overdueSub": "다음 액션 날짜가 지났습니다",
    "crm.kpi.overdueNone": "연체 없음",

    "crm.filter.all": "전체",
    "crm.filter.hot": "HOT 80점 이상",
    "crm.filter.overdue": "연체",
    "crm.filter.thisWeek": "이번 주 일정",
    "crm.filter.allAssignees": "담당 영업: 전체",
    "crm.view.table": "테이블",
    "crm.view.kanban": "칸반",
    "crm.kanban.hidden": "실패 · 보류 리드는 테이블 보기에서 상태 필터로 확인하세요. 카드를 끌어 상태를 바꿀 수 있습니다.",

    "crm.col.company": "회사",
    "crm.col.contact": "담당자",
    "crm.col.source": "유입경로",
    "crm.col.tech": "기술스택",
    "crm.col.budget": "예산",
    "crm.col.timing": "발주 예정",
    "crm.col.score": "점수",
    "crm.col.status": "상태",
    "crm.col.next": "다음 액션",
    "crm.col.created": "생성일",

    "crm.status.new": "신규",
    "crm.status.contacted": "접촉",
    "crm.status.meeting": "미팅·니즈 파악",
    "crm.status.proposal": "제안·견적",
    "crm.status.negotiation": "협상·계약 검토",
    "crm.status.won": "수주",
    "crm.status.lost": "실패",
    "crm.status.hold": "보류",

    "crm.rank.staff": "사원",
    "crm.rank.assistant": "대리",
    "crm.rank.manager": "과장",
    "crm.rank.deputy": "차장",
    "crm.rank.general": "부장",
    "crm.rank.director": "이사",
    "crm.rank.md": "상무",
    "crm.rank.evp": "전무",
    "crm.rank.svp": "부사장",
    "crm.rank.ceo": "대표이사",
    "crm.rank.cto": "CTO (최고기술책임자)",
    "crm.rank.cio": "CIO (최고정보책임자)",
    "crm.rank.other": "기타",

    "crm.source.scanner": "스캐너",
    "crm.source.referral": "소개",
    "crm.source.exhibition": "전시회",
    "crm.source.linkedin": "LinkedIn",
    "crm.source.wanted": "원티드",
    "crm.source.saramin": "사람인",
    "crm.source.jobkorea": "잡코리아",
    "crm.source.coldcall": "콜드콜",
    "crm.source.website": "홈페이지 문의",
    "crm.source.naver": "네이버",
    "crm.source.other": "기타",

    "crm.project.dispatch": "파견",
    "crm.project.contract": "도급",
    "crm.project.si": "SI 구축",
    "crm.project.sm": "SM 유지보수",
    "crm.project.odc": "ODC 전담팀",
    "crm.project.other": "기타",

    "crm.size.enterprise": "대기업",
    "crm.size.midsize": "중견기업",
    "crm.size.sme": "중소기업",
    "crm.size.startup": "스타트업",
    "crm.size.public": "공공기관",

    "crm.lost.price": "가격",
    "crm.lost.schedule": "일정",
    "crm.lost.competitor": "경쟁사 선택",
    "crm.lost.inhouse": "내부 개발",
    "crm.lost.budget": "예산 취소",
    "crm.lost.language": "언어·소통 우려",
    "crm.lost.other": "기타",

    "crm.activity.call": "전화",
    "crm.activity.email": "이메일",
    "crm.activity.kakao": "카카오톡",
    "crm.activity.meeting": "미팅",
    "crm.activity.proposal": "제안서 발송",
    "crm.activity.quote": "견적서 발송",
    "crm.activity.other": "기타",
    "crm.activity.heading": "활동 기록",
    "crm.activity.add": "기록",
    "crm.activity.notePlaceholder": "내용 (예: 김 부장 통화, 11월 발주 예정)",
    "crm.activity.empty": "아직 활동 기록이 없습니다. 전화·이메일·미팅을 남기면 마지막 접촉일이 갱신됩니다.",
    "crm.activity.lastContact": "마지막 접촉: {date}",
    "crm.activity.lastContactShort": "마지막 접촉",

    "crm.form.titleAdd": "리드 추가",
    "crm.form.titleAddSub": "회사명만 있어도 저장할 수 있습니다. 나머지는 나중에 채우세요.",
    "crm.form.titleEdit": "유입경로: {source} · 업데이트 {date}",
    "crm.form.sectionCompany": "회사",
    "crm.form.sectionContact": "담당자",
    "crm.form.sectionDeal": "프로젝트",
    "crm.form.sectionSales": "영업 관리",
    "crm.form.company": "회사명",
    "crm.form.biz": "사업자등록번호",
    "crm.form.size": "기업 규모",
    "crm.form.website": "웹사이트",
    "crm.form.industry": "업종",
    "crm.form.competitor": "현재 협력사 · 경쟁사",
    "crm.form.competitorHint": "기존 개발 협력사, 경쟁 제안사",
    "crm.form.contactName": "담당자명",
    "crm.form.rank": "직급",
    "crm.form.department": "부서",
    "crm.form.departmentHint": "개발팀, IT기획, 구매...",
    "crm.form.kakao": "카카오톡 ID",
    "crm.form.phone": "회사 전화",
    "crm.form.mobile": "휴대폰",
    "crm.form.email": "이메일",
    "crm.form.project": "사업 유형",
    "crm.form.source": "유입경로",
    "crm.form.tech": "기술스택",
    "crm.form.techHint": "Java, Spring, AWS (쉼표로 구분)",
    "crm.form.budget": "예산 (KRW)",
    "crm.form.budgetHint": "예: 1억 5000만, 150000000",
    "crm.form.teamSize": "필요 인원",
    "crm.form.expectedStart": "발주 예정 시기",
    "crm.form.bridgeSe": "한국어 브릿지 SE 필요",
    "crm.form.status": "상태",
    "crm.form.assignee": "담당 영업",
    "crm.form.lostReason": "실패 사유",
    "crm.form.nextAction": "다음 액션",
    "crm.form.nextActionHint": "예: 견적서 발송, 2차 미팅 제안",
    "crm.form.nextDate": "다음 액션 날짜",
    "crm.form.memo": "메모",
    "crm.form.save": "저장",
    "crm.form.saving": "저장 중...",
    "crm.form.cancel": "취소",
    "crm.form.delete": "삭제",
    "crm.form.scoreWhy": "점수 산출 근거",
    "crm.form.fromScanner": "스캔 결과 보기",
    "crm.form.naver": "네이버에서 검색",

    "crm.score.hiring": "IT 채용 중",
    "crm.score.rank": "의사결정 직급",
    "crm.score.email": "이메일 확보",
    "crm.score.phone": "전화 확보",
    "crm.score.kakao": "카카오톡 확보",
    "crm.score.budget": "예산",
    "crm.score.source": "유입경로",
    "crm.score.project": "사업 유형 확정",
    "crm.score.biz": "사업자번호 확인",
    "crm.score.timing": "발주 임박",
    "crm.score.team": "팀 단위 수요",

    "crm.import.title": "CSV · JSON에서 리드 가져오기",
    "crm.import.drop": "CSV 또는 JSON 파일을 여기에 끌어다 놓거나 클릭하여 선택",
    "crm.import.hint": "한국어 Excel(CP949) CSV도 그대로 지원 · 열 이름: 회사명, 담당자명, 직급, 전화, 이메일, 예산 등",
    "crm.import.sample": "샘플 CSV 다운로드",
    "crm.import.valid": "유효",
    "crm.import.dup": "중복",
    "crm.import.err": "오류",
    "crm.import.total": "전체 {count}행",
    "crm.import.commit": "{count}건 가져오기",
    "crm.import.done": "{count}건의 리드를 추가했습니다.",
    "crm.import.failed": "파일을 가져오지 못했습니다. 형식을 확인하세요.",
    "crm.import.rowError": "{row}행: {code}",

    "crm.error.company_required": "회사명은 필수입니다.",
    "crm.error.email_invalid": "이메일 형식이 올바르지 않습니다.",
    "crm.error.file_invalid": "파일을 읽을 수 없습니다. CSV 또는 JSON 배열이어야 합니다.",
    "crm.error.saveFailed": "저장하지 못했습니다. 서버를 확인한 뒤 다시 시도하세요.",
    "crm.error.loadFailed": "리드를 불러오지 못했습니다.",

    "crm.bulk.selected": "{count}건 선택",
    "crm.bulk.status": "상태 일괄 변경...",
    "crm.bulk.delete": "삭제",
    "crm.bulk.clear": "선택 해제",
    "crm.confirmDelete": "선택한 {count}건의 리드를 삭제할까요?",
    "crm.confirmDeleteOne": "\"{name}\" 리드를 삭제할까요? 활동 기록도 함께 삭제됩니다.",

    "crm.lead.addFromScan": "CRM 리드로 추가",
    "saved.action.lead": "리드",
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

    // -- CRM ---------------------------------------------------------------
    "nav.crm": "CRM Lead",
    "crm.title": "CRM Lead — Company Scanner",
    "crm.heading": "CRM Lead",
    "crm.description": "Pipeline bán hàng IT outsourcing. Tạo lead thẳng từ kết quả quét, quản lý người liên hệ, ngân sách, thời điểm 발주 và nhật ký hoạt động ở một chỗ.",
    "crm.add": "Thêm lead",
    "crm.import": "Nhập từ file",
    "crm.export": "Xuất",
    "crm.exportCsv": "Xuất Excel (.csv)",
    "crm.exportJson": "Xuất JSON (.json)",
    "crm.search": "Tìm công ty, liên hệ, SĐT, email, mã số DN...",
    "crm.count": "{total} lead",
    "crm.countFiltered": "Hiển thị {shown}/{total} lead",
    "crm.empty": "Chưa có lead nào",
    "crm.emptyDesc": "Bấm \"Thêm lead\" để nhập tay, nhập từ file, hoặc bấm \"Thêm vào CRM\" ngay trên kết quả quét.",
    "crm.emptyFiltered": "Không có lead nào khớp bộ lọc.",
    "crm.hot": "HOT",
    "crm.overdueTag": "Quá hạn",
    "crm.people": "{count} người",
    "crm.bridge": "Cần bridge SE",
    "crm.unit.eok": "억",
    "crm.unit.man": "만",

    "crm.kpi.pipeline": "Tổng pipeline",
    "crm.kpi.pipelineSub": "{count} lead đang mở",
    "crm.kpi.winRate": "Tỉ lệ thắng",
    "crm.kpi.winRateSub": "Thắng {won} / đóng {closed}",
    "crm.kpi.newMonth": "Lead mới tháng này",
    "crm.kpi.newMonthSub": "{count} lead HOT",
    "crm.kpi.overdue": "Quá hạn cần xử lý",
    "crm.kpi.overdueSub": "Đã qua ngày hành động tiếp",
    "crm.kpi.overdueNone": "Không có quá hạn",

    "crm.filter.all": "Tất cả",
    "crm.filter.hot": "HOT ≥ 80 điểm",
    "crm.filter.overdue": "Quá hạn",
    "crm.filter.thisWeek": "Lịch tuần này",
    "crm.filter.allAssignees": "Sales: tất cả",
    "crm.view.table": "Bảng",
    "crm.view.kanban": "Kanban",
    "crm.kanban.hidden": "Lead Thua · Tạm dừng xem ở chế độ Bảng bằng bộ lọc trạng thái. Kéo thẻ để đổi trạng thái.",

    "crm.col.company": "Công ty",
    "crm.col.contact": "Liên hệ",
    "crm.col.source": "Nguồn",
    "crm.col.tech": "Công nghệ",
    "crm.col.budget": "Ngân sách",
    "crm.col.timing": "Dự kiến 발주",
    "crm.col.score": "Điểm",
    "crm.col.status": "Trạng thái",
    "crm.col.next": "Hành động tiếp",
    "crm.col.created": "Ngày tạo",

    "crm.status.new": "Mới",
    "crm.status.contacted": "Đã liên hệ",
    "crm.status.meeting": "Họp · khảo sát nhu cầu",
    "crm.status.proposal": "Đề xuất · báo giá",
    "crm.status.negotiation": "Đàm phán · rà soát HĐ",
    "crm.status.won": "Thắng (수주)",
    "crm.status.lost": "Thua",
    "crm.status.hold": "Tạm dừng",

    "crm.rank.staff": "사원 (Nhân viên)",
    "crm.rank.assistant": "대리 (Chuyên viên)",
    "crm.rank.manager": "과장 (Trưởng nhóm)",
    "crm.rank.deputy": "차장 (Phó phòng)",
    "crm.rank.general": "부장 (Trưởng phòng)",
    "crm.rank.director": "이사 (Giám đốc)",
    "crm.rank.md": "상무 (GĐ điều hành)",
    "crm.rank.evp": "전무 (GĐ cấp cao)",
    "crm.rank.svp": "부사장 (Phó TGĐ)",
    "crm.rank.ceo": "대표이사 (TGĐ)",
    "crm.rank.cto": "CTO",
    "crm.rank.cio": "CIO",
    "crm.rank.other": "Khác",

    "crm.source.scanner": "Scanner",
    "crm.source.referral": "Giới thiệu",
    "crm.source.exhibition": "Triển lãm",
    "crm.source.linkedin": "LinkedIn",
    "crm.source.wanted": "Wanted",
    "crm.source.saramin": "Saramin",
    "crm.source.jobkorea": "JobKorea",
    "crm.source.coldcall": "Cold call",
    "crm.source.website": "Website inbound",
    "crm.source.naver": "Naver",
    "crm.source.other": "Khác",

    "crm.project.dispatch": "파견 (Phái cử)",
    "crm.project.contract": "도급 (Khoán việc)",
    "crm.project.si": "SI (Xây dựng hệ thống)",
    "crm.project.sm": "SM (Vận hành, bảo trì)",
    "crm.project.odc": "ODC (Team chuyên trách)",
    "crm.project.other": "Khác",

    "crm.size.enterprise": "Tập đoàn lớn (대기업)",
    "crm.size.midsize": "DN cỡ vừa (중견기업)",
    "crm.size.sme": "DN nhỏ và vừa (중소기업)",
    "crm.size.startup": "Startup",
    "crm.size.public": "Cơ quan công (공공기관)",

    "crm.lost.price": "Giá",
    "crm.lost.schedule": "Tiến độ",
    "crm.lost.competitor": "Chọn đối thủ",
    "crm.lost.inhouse": "Tự phát triển",
    "crm.lost.budget": "Huỷ ngân sách",
    "crm.lost.language": "Lo ngại ngôn ngữ · giao tiếp",
    "crm.lost.other": "Khác",

    "crm.activity.call": "Gọi điện",
    "crm.activity.email": "Email",
    "crm.activity.kakao": "KakaoTalk",
    "crm.activity.meeting": "Họp",
    "crm.activity.proposal": "Gửi đề xuất",
    "crm.activity.quote": "Gửi báo giá",
    "crm.activity.other": "Khác",
    "crm.activity.heading": "Nhật ký hoạt động",
    "crm.activity.add": "Ghi",
    "crm.activity.notePlaceholder": "Nội dung (vd: gọi 부장 Kim, dự kiến 발주 tháng 11)",
    "crm.activity.empty": "Chưa có hoạt động. Ghi lại cuộc gọi, email, họp để cập nhật ngày liên hệ gần nhất.",
    "crm.activity.lastContact": "Liên hệ gần nhất: {date}",
    "crm.activity.lastContactShort": "Liên hệ gần nhất",

    "crm.form.titleAdd": "Thêm lead",
    "crm.form.titleAddSub": "Chỉ cần tên công ty là lưu được, phần còn lại bổ sung sau.",
    "crm.form.titleEdit": "Nguồn: {source} · cập nhật {date}",
    "crm.form.sectionCompany": "Công ty",
    "crm.form.sectionContact": "Người liên hệ",
    "crm.form.sectionDeal": "Dự án",
    "crm.form.sectionSales": "Quản lý bán hàng",
    "crm.form.company": "Tên công ty",
    "crm.form.biz": "Mã số DN (사업자등록번호)",
    "crm.form.size": "Quy mô",
    "crm.form.website": "Website",
    "crm.form.industry": "Lĩnh vực",
    "crm.form.competitor": "Vendor hiện tại · đối thủ",
    "crm.form.competitorHint": "Đối tác phát triển hiện tại, đối thủ cùng chào",
    "crm.form.contactName": "Tên liên hệ",
    "crm.form.rank": "Chức vụ (직급)",
    "crm.form.department": "Phòng ban",
    "crm.form.departmentHint": "개발팀, IT기획, 구매...",
    "crm.form.kakao": "KakaoTalk ID",
    "crm.form.phone": "Điện thoại công ty",
    "crm.form.mobile": "Di động",
    "crm.form.email": "Email",
    "crm.form.project": "Hình thức dự án",
    "crm.form.source": "Nguồn",
    "crm.form.tech": "Công nghệ",
    "crm.form.techHint": "Java, Spring, AWS (cách nhau bằng dấu phẩy)",
    "crm.form.budget": "Ngân sách (KRW)",
    "crm.form.budgetHint": "vd: 1억 5000만, 150000000",
    "crm.form.teamSize": "Số nhân sự cần",
    "crm.form.expectedStart": "Dự kiến 발주 (tháng)",
    "crm.form.bridgeSe": "Cần bridge SE tiếng Hàn",
    "crm.form.status": "Trạng thái",
    "crm.form.assignee": "Sales phụ trách",
    "crm.form.lostReason": "Lý do thua",
    "crm.form.nextAction": "Hành động tiếp",
    "crm.form.nextActionHint": "vd: gửi báo giá, đề xuất họp lần 2",
    "crm.form.nextDate": "Ngày hành động tiếp",
    "crm.form.memo": "Ghi chú",
    "crm.form.save": "Lưu",
    "crm.form.saving": "Đang lưu...",
    "crm.form.cancel": "Huỷ",
    "crm.form.delete": "Xoá",
    "crm.form.scoreWhy": "Cách tính điểm",
    "crm.form.fromScanner": "Xem kết quả quét",
    "crm.form.naver": "Tìm trên Naver",

    "crm.score.hiring": "Đang tuyển IT",
    "crm.score.rank": "Cấp ra quyết định",
    "crm.score.email": "Có email",
    "crm.score.phone": "Có điện thoại",
    "crm.score.kakao": "Có KakaoTalk",
    "crm.score.budget": "Ngân sách",
    "crm.score.source": "Nguồn",
    "crm.score.project": "Đã rõ hình thức dự án",
    "crm.score.biz": "Mã số DN hợp lệ",
    "crm.score.timing": "Sắp 발주",
    "crm.score.team": "Nhu cầu cả team",

    "crm.import.title": "Nhập lead từ CSV · JSON",
    "crm.import.drop": "Kéo thả file CSV hoặc JSON vào đây, hoặc bấm để chọn",
    "crm.import.hint": "Hỗ trợ CSV từ Excel Hàn (CP949) · tên cột: 회사명, 담당자명, 직급, 전화, 이메일, 예산... hoặc tiếng Việt/Anh",
    "crm.import.sample": "Tải CSV mẫu",
    "crm.import.valid": "Hợp lệ",
    "crm.import.dup": "Trùng",
    "crm.import.err": "Lỗi",
    "crm.import.total": "Tổng {count} dòng",
    "crm.import.commit": "Nhập {count} lead",
    "crm.import.done": "Đã thêm {count} lead.",
    "crm.import.failed": "Không nhập được file. Kiểm tra lại định dạng.",
    "crm.import.rowError": "Dòng {row}: {code}",

    "crm.error.company_required": "Tên công ty là bắt buộc.",
    "crm.error.email_invalid": "Email không đúng định dạng.",
    "crm.error.file_invalid": "Không đọc được file. Cần CSV hoặc mảng JSON.",
    "crm.error.saveFailed": "Không lưu được. Kiểm tra server rồi thử lại.",
    "crm.error.loadFailed": "Không tải được danh sách lead.",

    "crm.bulk.selected": "Đã chọn {count}",
    "crm.bulk.status": "Đổi trạng thái hàng loạt...",
    "crm.bulk.delete": "Xoá",
    "crm.bulk.clear": "Bỏ chọn",
    "crm.confirmDelete": "Xoá {count} lead đã chọn?",
    "crm.confirmDeleteOne": "Xoá lead \"{name}\"? Nhật ký hoạt động cũng bị xoá theo.",

    "crm.lead.addFromScan": "Thêm vào CRM",
    "saved.action.lead": "Lead",
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
