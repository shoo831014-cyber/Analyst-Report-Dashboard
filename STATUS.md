# STATUS

## 현재 상태

- 기준 작업일: `2026-03-13`
- GitHub 저장소 연결 완료
- Koyeb 무료 Web Service 배포 완료
- 외부 URL 접속 확인 완료
- `/health`, `/dashboard`, 수동 업데이트 동작 확인 완료

## 최근 정리 내용

- Koyeb 배포용 `Dockerfile` 추가
- `scripts/koyeb-start.sh` 추가
- `ENABLE_PLAYWRIGHT_FALLBACK` 설정 추가
- 정적 HTML export 기능 제거
- `/api/v1/dashboard/export` 제거
- `run_publish`에서 export 단계 제거

## 현재 운영 가정

- DB는 별도 Postgres 없이 SQLite 사용
- 과거 데이터 영속 보관은 하지 않음
- 인스턴스 재시작/재배포 후 데이터가 사라질 수 있음
- 필요 시 `수동 업데이트`로 최신 데이터 재생성

## 검증

- `.\.venv\Scripts\python.exe -m pytest tests/test_health.py tests/test_ingest_service.py`
- Koyeb 배포 로그에서 `alembic upgrade head`, `uvicorn`, health check 통과 확인

## 다음 후보 작업

- 수동 업데이트 UX 문구 정리
- Koyeb 운영 안내 문서 보강
- SQLite 임시 운영 가정에 맞는 UI 문구 정리
