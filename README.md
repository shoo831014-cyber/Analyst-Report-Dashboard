# Analyst Report Dashboard

FnGuide 기업분석 리포트를 수집·정리해 일자별 대시보드로 보여주는 FastAPI 애플리케이션입니다.

## 현재 기능
- 일자별 스냅샷 대시보드
- 종목/섹터/의견 기준 집계
- Spotlight Top3, 섹터별 리포트 현황, 상세 테이블
- FnGuide 목록의 파란 bullet summary 수집 및 노출
- 같은 종목 + 같은 증권사 리포트 `1건` 처리
- IPO성 리포트 제외
- 수동 업데이트 버튼
- 다크 모드
- Windows 서버 실행 `exe`

## 주요 규칙

### 중복 제거
- 같은 종목에서 같은 증권사의 리포트는 `1건`으로 집계합니다.
- 같은 증권사의 한글/영문 중복 리포트도 `1건`으로 처리합니다.

### IPO 제외
- 제목에 `IPO`가 포함되거나
- 종목코드가 `6자리 숫자`가 아니면
- 집계에서 제외합니다.

### summary 처리
- Spotlight와 섹터 카드의 핵심 내용은 FnGuide 목록의 파란 bullet summary를 사용합니다.
- 여러 리포트가 있으면 summary 문장을 모두 합친 뒤 문장 단위로 중복 제거합니다.

### 섹터 분류
- 기본 기준은 첨부 엑셀 `d:\backup01\Desktop\종목 구분_대분류10.xlsx`의 `E열(대분류)`입니다.
- 아래 섹터는 통합합니다.
  - `에너지`, `유틸리티` → `에너지/유틸리티`
  - `자유소비재`, `필수소비재` → `소비재`
  - `의료`, `헬스케어`, `바이오` → `헬스케어/바이오`
- 예외 종목:
  - `리브스메드` → `헬스케어/바이오`
  - `알지노믹스` → `헬스케어/바이오`

## 폴더 구조
```text
app/                애플리케이션 코드
alembic/            DB 마이그레이션
data/               db/export/snapshot/log 저장
tests/              테스트
dist/               빌드된 exe 출력
server_launcher.py  exe 실행용 엔트리포인트
pyinstaller_server.spec
```

## 로컬 실행

### 1) 가상환경
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2) 의존성 설치
```bash
pip install -e ".[dev]"
python -m playwright install
```

### 3) 서버 실행
```bash
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

접속 주소:
- `http://127.0.0.1:8000/dashboard`
- `http://127.0.0.1:8000/health`

## 작업 흐름

### 수집
```bash
.\.venv\Scripts\python.exe -m app.jobs.run_ingest
```

### 발행
```bash
.\.venv\Scripts\python.exe -m app.jobs.run_publish --date 2026-03-09
```

`run_publish`는:
- 종목/섹터/대시보드 스냅샷 재생성
- 정적 HTML export 생성
- export 경로 저장

생성 결과 예시:
- 파일: `data/exports/2026-03-09/dashboard.html`
- 정적 접근: `http://127.0.0.1:8000/exports/2026-03-09/dashboard.html`
- 메타 조회: `http://127.0.0.1:8000/api/v1/dashboard/export?date=2026-03-09`

## 수동 업데이트
- 대시보드 헤더의 `수동 업데이트` 버튼을 누르면 서울 기준 오늘 날짜로:
  - `ingest`
  - `publish`
  - `export`
  순서로 실행합니다.
- 진행 중 상태 문구와 마지막 업데이트 시각을 헤더에 표시합니다.

## 다크 모드
- 헤더의 테마 토글로 `다크 모드 / 라이트 모드`를 전환할 수 있습니다.
- 선택 상태는 브라우저 `localStorage`의 `dashboardTheme`에 저장됩니다.

## Windows EXE

### 실행
- 파일: `dist/AnalystReportDashboardServer.exe`
- 더블클릭하면 서버를 실행하고 브라우저에서 `/dashboard`를 엽니다.

### 재빌드
```bash
.\.venv\Scripts\pyinstaller.exe pyinstaller_server.spec --noconfirm --clean
```

## 테스트
```bash
.\.venv\Scripts\python.exe -m pytest
```

## 참고
- 대시보드는 스냅샷 기반입니다. 집계 규칙을 바꾼 뒤 기존 날짜 화면까지 반영하려면 해당 날짜를 다시 `publish`해야 합니다.
- Spotlight의 제공처 hover는 현재 브라우저 기본 `title` 툴팁을 사용합니다.
