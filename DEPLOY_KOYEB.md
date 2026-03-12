# Koyeb Deploy

이 저장소는 Koyeb `Web Service`로 가장 빨리 올릴 수 있다.

## 전제

- 저장소는 GitHub에 이미 올라가 있어야 한다.
- 현재 프로젝트는 FastAPI 서버 앱이다.
- 무료 테스트 배포는 가능하지만, `sqlite:///./data/app.db`는 컨테이너 재시작 시 데이터가 유지되지 않는다.
- 운영용으로는 Koyeb Postgres를 붙이고 `DATABASE_URL`을 설정하는 편이 맞다.

## 저장소에 포함된 배포 파일

- `Dockerfile`
- `.dockerignore`
- `scripts/koyeb-start.sh`

`koyeb-start.sh`는 아래를 수행한다.

1. 런타임 디렉터리 생성
2. `alembic upgrade head`
3. `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Koyeb에서 서비스 만들기

1. Koyeb 로그인
2. `Create Web Service`
3. GitHub 저장소 연결
4. 저장소: `shoo831014-cyber/Analyst-Report-Dashboard`
5. Branch: `main`
6. Builder: `Dockerfile`
7. Exposed port: `8000`
8. Instance type: `Free`

## 권장 환경 변수

- `APP_ENV=production`
- `LOG_LEVEL=INFO`
- `ENABLE_PLAYWRIGHT_FALLBACK=false`

운영용 DB를 붙일 때:

- `DATABASE_URL=<Koyeb Postgres connection string>`

## 첫 배포 후 확인

- `/health`
- `/dashboard`

## 주의

- `ENABLE_PLAYWRIGHT_FALLBACK=false`면 FnGuide requests 품질이 나쁜 날에는 수동 업데이트 결과가 일부 누락될 수 있다.
- `DATABASE_URL`을 지정하지 않으면 앱은 컨테이너 내부 SQLite를 사용하므로 재배포/재시작 후 데이터가 사라질 수 있다.
