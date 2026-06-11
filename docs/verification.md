# Verification Log

확인일: 2026-06-11 (서비스 고도화 반영)

## 정적 검사

- `node --check app/app.js` 통과
- `python3 -m json.tool data/areas.actual.json` 통과
- `python3 -m py_compile api/movevalue_api.py scripts/build_real_dataset.py scripts/build_application_docx.py` 통과

## API 검증

- API 서버 실행: `python3 api/movevalue_api.py --port 5173`
- `GET /api/health`: `ok=true`, 생활권 9개, 2025 서울시 전월세 출처 메타 포함
- `GET /api/recommendations?...&limit=9`: 9개 랭킹 반환, `meta.totalCandidates=9`, 1위 건대입구 89점(기본 조건)
- `GET /` 루트 웹 페이지 `200 OK`

## 브라우저 검증 (데스크톱)

- OpenStreetMap 실제 지도 타일 표시 확인
- 생활권 마커 9개 표시, 점수별 색상(상위권 녹색/검토권 금색/미달 적색)·크기 구분
- 마커 팝업: 생활권명, 순위, 목적지 통근시간, 월세 중앙값, 종합점수 표시
- 카드 클릭 → 지도 마커 선택·팝업 연동 확인 (신림 카드 → 신림 마커 88점 팝업)
- 마커 클릭 → 카드 선택·상세 패널 연동 확인 (마곡나루 마커 → 9위/9개 표시)
- "전체 후보 9개 중 상위 6개" 표기와 전체 보기 토글 동작
- 추천 카드별 한 줄 근거 표시 ("주거비·생활 SOC 강점 · 예산 내 후보 · 1인 청년 적합" 등)
- 목적지를 판교로 변경 → 추천 재계산 확인
- 예산 70→50만원 변경 → 1위가 신림으로 교체, "예산 7만원 초과 주의" 근거 갱신 확인
- 데이터 근거 표: 생활권 9개 + 합계 114,319건, 월세·보증금·전세 중앙값(억 단위 변환 포함) 표시
- API/사업모델/제출자료 섹션 렌더링 확인
- 상단 메뉴 스크롤 연동(데이터 근거 영역 진입 시 활성 메뉴 전환) 확인
- 브라우저 콘솔 오류·경고: 없음

## 브라우저 검증 (모바일 375px, Chrome 디바이스 에뮬레이션)

- 단일 컬럼 스택 레이아웃: 조건 → 지도 → 추천 → 상세 → 섹션 순
- `document.scrollWidth == 375`, 가로 오버플로 요소 0개 확인
- 데이터 근거 표는 가로 스크롤 컨테이너로 격리, API 예시 코드 블록도 자체 스크롤
- 상단 메뉴 가로 스크롤 동작, 활성 상태 표시 확인
- 카드·콜아웃 텍스트 잘림 없음

## 수정된 결함

- 모바일에서 데이터 근거 표(min-width 640px)가 그리드 아이템의 `min-width:auto` 기본값 때문에 페이지 전체를 밀어내던 가로 오버플로를 `main > *, .workspace > .panel { min-width: 0 }`으로 수정.

## 확인된 제한

- 현재 주거비는 서울시 2025 전월세 파일의 15~85㎡ 거래 중앙값 기반이다.
- 통근시간은 주요 목적지별 MVP 검증용 테이블이며, 배포 단계에서는 대중교통 경로 API 또는 GTFS 기반 라우팅으로 교체해야 한다.
- 생활 SOC, 안전, 환경 점수 일부는 MVP 프록시다. 추후 생활시설·안전·대기·녹지 공공데이터 어댑터를 추가해야 한다.
- 지도 타일은 OpenStreetMap 공개 타일을 사용하며, 운영 배포 시 VWorld 등으로 교체를 권장한다 (`docs/api-development.md` 참고).
- 전화번호, 서명, 개인정보 수집·이용 동의 체크는 신청자가 제출 전 직접 기재해야 한다.

## 이전 확인 (2026-06-11 데이터 구축 시)

- `python3 scripts/build_real_dataset.py` 실행 성공: `data/areas.actual.json` 9개 생활권 생성
- `deliverables/MoveValue_참가신청서_기획서_초안.docx` 재생성 및 렌더링 검수 (`qa/docx-render/page-1.png` ~ `page-4.png`)
