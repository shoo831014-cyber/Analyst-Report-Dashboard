# SPEC

## 제품 개요

- FnGuide 리포트를 수집한다.
- 종목/섹터/대시보드 스냅샷으로 집계한다.
- FastAPI 대시보드와 JSON API로 제공한다.

## 주요 기능

### 1. 대시보드

- `GET /dashboard`
- 최신 발행 스냅샷 또는 선택한 날짜 스냅샷을 렌더링한다.

### 2. 집계 규칙

- 같은 종목 + 같은 증권사는 1건 처리
- 한글/영문 중복 리포트도 같은 증권사면 1건 처리
- IPO 리포트 제외
- Spotlight/섹터 summary는 FnGuide bullet summary 기반

### 3. 수동 업데이트

- 대시보드 헤더의 버튼으로 실행
- 서울 기준 오늘 날짜로 아래 순서 수행
  - `IngestService.run(snapshot_date=today_kst)`
  - `SnapshotService.publish(today_kst)`

### 4. 다크 모드

- 헤더의 토글 버튼으로 전환
- 선택한 테마는 `localStorage.dashboardTheme`에 저장
- 저장값이 없으면 `prefers-color-scheme` 사용

## 주요 API

- `GET /health`
- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/dates`
- `GET /api/v1/dashboard/companies`
- `GET /api/v1/dashboard/sectors`
- `POST /api/v1/dashboard/update`
- `GET /api/v1/reports`

## 데이터 모델

- 원본 리포트: `ReportRawMeta`
- 종목 요약: `DailyCompanySummary`
- 섹터 요약: `DailySectorSummary`
- 대시보드 스냅샷: `DailyDashboardSnapshot`
- 작업 이력: `JobRun`

## 배포 메모

- 현재 배포 기준은 Koyeb Web Service
- 정적 export 기능은 사용하지 않음
- 무료 구성에서는 SQLite를 사용하므로 데이터 영속성은 보장하지 않음
