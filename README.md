# Analyst Report Dashboard

FnGuide 리포트를 수집하고 일자별 스냅샷으로 집계해 보여주는 FastAPI 대시보드입니다.

## 현재 구조

- 서버: FastAPI
- 대시보드: `/dashboard`
- 헬스 체크: `/health`
- 수동 업데이트: `ingest -> publish`
- 정적 HTML export 기능: 제거됨

## 주요 규칙

- 같은 종목에서 같은 증권사의 리포트는 1건으로 집계
- 같은 증권사의 한글/영문 중복 리포트도 1건 처리
- IPO 성격 리포트는 집계 제외
- Spotlight와 섹터 요약은 FnGuide 목록의 파란 bullet summary 사용
- 여러 리포트가 있으면 summary 문장을 합치고 문장 단위로 중복 제거
- Spotlight 카드에는 `애널리스트 n명`을 직접 노출하지 않음

## 로컬 실행

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m playwright install
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

접속 주소:

- `http://127.0.0.1:8000/dashboard`
- `http://127.0.0.1:8000/health`

## 작업 명령

수집:

```bash
.\.venv\Scripts\python.exe -m app.jobs.run_ingest
```

발행:

```bash
.\.venv\Scripts\python.exe -m app.jobs.run_publish --date 2026-03-09
```

`run_publish`는 종목/섹터/대시보드 스냅샷만 재생성합니다.

## Koyeb 배포

이 저장소는 `Dockerfile` 기반 Koyeb Web Service로 배포할 수 있습니다.

권장 환경 변수:

- `APP_ENV=production`
- `LOG_LEVEL=INFO`
- `ENABLE_PLAYWRIGHT_FALLBACK=false`

현재 무료 배포 구성은 별도 Postgres 없이 SQLite를 사용합니다. 따라서 재배포나 인스턴스 재시작 시 데이터가 사라질 수 있습니다.

## 테스트

```bash
.\.venv\Scripts\python.exe -m pytest
```

## 참고

- 대시보드는 스냅샷 기반입니다. 집계 규칙 변경 후 기존 날짜를 다시 반영하려면 해당 날짜로 `publish`를 다시 실행해야 합니다.
- 스냅샷 `created_at`은 UTC naive로 저장되고, 표시 시 서울 시간으로 변환합니다.
- 현재 Spotlight hover 정보는 브라우저 기본 `title` 툴팁 방식입니다.
