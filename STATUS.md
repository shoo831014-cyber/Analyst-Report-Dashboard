# STATUS.md

## 현재 상태
- 기준일: `2026-03-09`
- 서버 상태: `http://127.0.0.1:8000/health` 정상 응답 확인
- 최근 반영 기능은 서버에 적용되어 있다.

## 완료된 작업

### 데이터 규칙
- 같은 종목 + 같은 증권사 중복 제거 반영
- 한글/영문 중복 리포트 1건 처리 반영
- IPO 리포트 제외 반영
- 비정형 종목코드 제외 반영

### FnGuide summary 처리
- FnGuide 목록의 파란 bullet summary 파싱 추가
- `summary_lines_json` 저장 추가
- 기존 데이터 재수집 시 summary backfill 지원
- Spotlight에서 종목별 summary dedupe 후 전체 표시
- 섹터 카드에서도 summary 기반 핵심 내용 표시

### Spotlight 제공처 표시
- Spotlight 카드에서 `애널리스트 n명` 표시 제거
- 상단 메타라인에서도 `애널리스트 n명` 제거
- 하단 `제공처 n곳`에 hover 시 `제공처 · 애널리스트` 정보 노출
- 회사별 제공처/애널리스트 상세 정보를 스냅샷 payload에 포함

### 섹터 처리
- 첨부 엑셀 `종목 구분_대분류10.xlsx`의 `E열` 기준 섹터 분류 반영
- `에너지`, `유틸리티`를 `에너지/유틸리티`로 통합
- `자유소비재`, `필수소비재`를 `소비재`로 통합
- `의료`, `헬스케어`, `바이오`를 `헬스케어/바이오`로 통합
- `리브스메드`, `알지노믹스`를 `헬스케어/바이오`로 강제 매핑
- 섹터 표에 `의견/목표가/전일종가/상승여력/핵심 내용` 표시
- 종목명 한 줄 고정
- 핵심 내용 2줄 제한
- 폰트/패딩 축소로 가로 스크롤 완화

### 다크 모드
- 헤더에 `다크 모드 / 라이트 모드` 토글 추가
- 브라우저 `localStorage`에 마지막 테마 선택 저장
- 저장값이 없으면 시스템 `prefers-color-scheme`를 따름
- 다크 테마용 색상 변수와 주요 카드/히트맵 오버라이드 반영

### 서버 실행 EXE
- `server_launcher.py` 기반 Windows 서버 실행기 추가
- PyInstaller 스펙 `pyinstaller_server.spec` 추가
- 번들 실행 시 템플릿/정적파일 경로를 찾도록 런타임 경로 처리 추가
- 생성 결과물: `dist/AnalystReportDashboardServer.exe`

### 수동 업데이트
- 헤더에 수동 업데이트 버튼 추가
- 버튼 클릭 시 서울 기준 오늘 날짜로 업데이트 실행
- 진행 중 문구 및 스피너 표시
- 완료 시 마지막 업데이트 시각 표시
- 완료 후 해당 날짜 대시보드로 이동

## 최근 검증 결과
- 테스트:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_view.py tests/test_snapshot_service.py`
  - 결과: `16 passed`
- 테스트:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_sector_service.py tests/test_snapshot_service.py`
  - 결과: `9 passed`
- 테스트:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_api.py tests/test_export_service.py`
  - 결과: `9 passed`
- PyInstaller 빌드 성공:
  - `.\.venv\Scripts\pyinstaller.exe pyinstaller_server.spec --noconfirm --clean`
  - 결과물: `dist/AnalystReportDashboardServer.exe`
- EXE 실행 후 헬스 체크 성공:
  - `http://127.0.0.1:8000/health`
  - `200 OK`
- 헤더 반영 확인:
  - `data-manual-update-status`
  - `data-last-updated-text`
  - `data-theme-toggle-button`
- Spotlight hover 정보 HTML 확인:
  - `title="DS투자증권 · 최태용"` 형태로 렌더링됨

## 현재 알려진 운영 메모
- 대시보드는 스냅샷 기반이므로 집계 규칙 변경 후 과거 날짜 화면을 맞추려면 해당 날짜를 재발행해야 한다.
- `pytest`는 시스템 PATH에 없을 수 있으므로 프로젝트 `.venv`의 Python으로 실행한다.
- `pyinstaller`는 프로젝트 `.venv`에 설치되어 있으며 필요 시 아래 명령으로 재빌드한다.
  - `.\.venv\Scripts\pyinstaller.exe pyinstaller_server.spec --noconfirm --clean`
- 서버 프로세스가 중복 기동되지 않도록 관리가 필요하다.
- 브라우저 기본 `title` 툴팁은 hover 후 잠시 정지해야 보일 수 있다. 필요하면 커스텀 툴팁으로 교체 가능하다.

## 다음 작업 후보
- 수동 업데이트 버튼에 상세 단계별 진행률 표시
- 마지막 업데이트 사용자/실행 결과 요약 표시
- Spotlight 제공처 hover를 브라우저 기본 툴팁 대신 커스텀 말풍선으로 교체
