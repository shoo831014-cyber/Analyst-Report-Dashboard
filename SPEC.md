# SPEC.md

## 제품 개요
- FnGuide 리포트를 일자별로 수집하고, 종목/섹터/투자의견 기준으로 정리한 대시보드를 제공한다.

## 주요 기능

### 1. 일자별 스냅샷 대시보드
- 특정 날짜의 리포트 집계 결과를 스냅샷으로 보관한다.
- 대시보드는 스냅샷 기준으로 렌더링한다.
- 최근 발행된 날짜 목록을 상단에서 전환할 수 있다.

### 2. 종목 중복 제거 규칙
- 집계 기준 dedupe key는 `같은 종목 + 같은 증권사`다.
- 같은 증권사에서 같은 종목에 대해 한글/영문 리포트를 같이 발행해도 `1건`으로 본다.
- 대표 케이스는 최신 `report_date`, `collected_at`, `id` 기준으로 선택한다.

### 3. IPO 리포트 제외 규칙
- 아래 조건에 해당하면 집계에서 제외한다.
  - 제목에 `IPO` 포함
  - 종목코드가 `6자리 숫자`가 아님
- 이 규칙은 수집, 스냅샷, 리포트 목록 API에 공통 적용한다.

### 4. Spotlight Top3
- 당일 가장 많이 언급된 상위 3개 종목을 표시한다.
- 카드에는 아래 정보를 포함한다.
  - 종목명, 종목코드
  - 리포트 수
  - 평균 목표주가
  - 전일종가
  - 평균 상승여력
  - 의견 분포
  - 제공처 수
- 하단 핵심 내용은 FnGuide 목록의 파란 bullet summary를 사용한다.
- 여러 리포트가 있으면 summary를 모두 합치고, 문장 단위 중복 제거 후 표시한다.
- 카드 하단에는 `제공처 n곳`만 표시한다.
- `제공처 n곳` hover 시 제공처명과 애널리스트명을 간단히 보여준다.
- 상단 메타라인과 하단 footnote에는 `애널리스트 n명` 숫자를 직접 노출하지 않는다.

### 5. 섹터별 리포트 현황
- 종목 섹터는 첨부 엑셀의 `E열(대분류)` 우선으로 분류한다.
- 아래 섹터는 집계 시 통합한다.
  - `에너지`, `유틸리티` → `에너지/유틸리티`
  - `자유소비재`, `필수소비재` → `소비재`
  - `의료`, `헬스케어`, `바이오` → `헬스케어/바이오`
- 아래 종목은 예외적으로 강제 매핑한다.
  - `리브스메드` → `헬스케어/바이오`
  - `알지노믹스` → `헬스케어/바이오`
- 섹터 카드에는 아래 컬럼을 표시한다.
  - 종목
  - 의견
  - 목표가
  - 전일종가
  - 상승여력
  - 핵심 내용
- 종목명은 줄바꿈 없이 한 줄로 표시한다.
- 핵심 내용은 summary 기반으로 더 짧게 요약해 보여주며, UI에서는 2줄 clamp를 적용한다.
- 폰트와 패딩은 가로 스크롤을 줄이도록 기존보다 축소했다.

### 6. 수동 업데이트
- 대시보드 헤더에 `수동 업데이트` 버튼이 있다.
- 실행 시점의 서울 날짜를 기준으로 데이터를 갱신한다.
- 처리 순서:
  - `IngestService.run(snapshot_date=today_kst)`
  - `SnapshotService.publish(today_kst)`
  - `ExportService.export_dashboard_html(...)`
- 진행 중 상태 문구와 스피너를 보여준다.
- 완료 후 마지막 업데이트 시각을 헤더에 표시하고 해당 날짜 대시보드로 이동한다.

### 7. 다크 모드
- 대시보드 헤더에 테마 토글 버튼이 있다.
- `다크 모드`와 `라이트 모드`를 즉시 전환할 수 있다.
- 현재 선택한 테마는 브라우저 `localStorage`의 `dashboardTheme`에 저장한다.
- 저장된 값이 없으면 시스템 다크모드 선호를 사용한다.

### 8. Windows 실행 파일
- 서버 실행용 Windows 단일 실행 파일을 제공한다.
- 파일 경로: `dist/AnalystReportDashboardServer.exe`
- 실행 시:
  - 앱 작업 디렉터리를 실행 파일 위치로 맞춘다.
  - FastAPI 서버를 기동한다.
  - 기본 브라우저로 `/dashboard`를 연다.
- 번들 안의 템플릿/정적 자원은 런타임 경로 해석기로 로딩한다.

## 주요 엔드포인트
- `GET /dashboard`
- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/dates`
- `GET /api/v1/dashboard/companies`
- `GET /api/v1/dashboard/sectors`
- `GET /api/v1/dashboard/export`
- `POST /api/v1/dashboard/update`

## 데이터 저장
- 원본 리포트: `ReportRawMeta`
- 종목 요약: `DailyCompanySummary`
- 섹터 요약: `DailySectorSummary`
- 대시보드 스냅샷: `DailyDashboardSnapshot`
- `summary_lines_json`에 FnGuide 목록 summary bullet를 저장한다.
- Spotlight hover 정보용으로 회사별 `provider_details`를 스냅샷 payload에 포함한다.

## 런타임/배포
- 일반 개발 실행:
  - `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- EXE 빌드:
  - `.\.venv\Scripts\pyinstaller.exe pyinstaller_server.spec --noconfirm --clean`

## UI 상태 표시
- 헤더에 아래 상태를 노출한다.
  - 진행 상태 문구
  - 마지막 업데이트 시각
- 마지막 업데이트 시각은 스냅샷 `created_at`을 서울시각 문자열로 변환한 값이다.
