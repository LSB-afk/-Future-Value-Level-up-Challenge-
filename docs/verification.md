# Verification Log

확인일: 2026-06-26 (GitHub 최신 커밋 분석 + 제출자료 고도화 + 화면 캡처 + 신청서 렌더 검증)

## 참가신청서 제출자료 검증 (2026-06-26)

- GitHub `origin/main` 최신 커밋 `212f41c Refine apartment matching prototype` 기준으로 코드와 문서를 분석했다.
- `docs/github-latest-analysis.md`: 최근 커밋 로그, 현재 구현 현황 요약표, 주요 컴포넌트, 라우팅 구조, 데이터 처리 로직, 구현/미완성 기능 구분을 작성했다.
- `docs/system-flow-summary.md`: 전체 서비스 아키텍처, 사용자 입력, 지도 추천, 부동산 상세 대시보드, 전세 위험 신호, AI Agent, 데이터 파이프라인, 외부 API, 확장 모듈 구조를 정리했다.
- `docs/mermaid-diagrams.md`: 전체 시스템 아키텍처, 사용자 플로우, 서비스 시퀀스, 데이터 파이프라인, AI Agent 의사결정, 지도 대시보드, 전세 위험 점검, 생활권 점수 산정, 공공데이터/API 연계 Mermaid 9종을 작성했다.
- `docs/submission-screenshots.md`: 10개 필수 화면별 화면명, 기능 목적, 사용자 행동, 시스템 결과, 참가신청서 삽입 문장을 정리했다.
- `deliverables/screenshots/`: 메인 화면, 조건 입력, 추천 결과, 지도 추천, 단지 상세 대시보드, 가격/전세가율/위험 지표, 후보 비교, 전세 위험 신호, AI Agent, 모바일 화면 10장을 캡처했다.
- 브라우저 캡처 검증: Playwright 기반 캡처 시 콘솔 오류 없음(`[]`)을 확인했다.
- `scripts/build_application_docx.py`: 참가신청서 양식 흐름을 유지하면서 서비스 개요, 핵심 기능, 차별성, 데이터 출처, 구현 현황, 점수 가중치, 위험 기준, 협력 방안, 기대효과, 일정, 예산, 로드맵을 표와 화면 중심으로 재작성했다.
- `deliverables/MoveValue_참가신청서_보강본.docx`: 제출용 보강본 생성 완료.
- DOCX 렌더링: `render_docx.py deliverables/MoveValue_참가신청서_보강본.docx --output_dir qa/docx-render-submission --emit_pdf`로 12페이지 PNG와 PDF 변환 성공.
- 렌더 검수: 12개 페이지를 육안 확인했고 표/이미지/서약 확인/개인정보 확인 섹션에서 큰 텍스트 중첩이나 잘림이 없음을 확인했다.
- 정적 검사: `node --check app/app.js`, `python3 -m json.tool data/areas.actual.json`, `python3 -m json.tool data/apartments.seoul.snapshot.json`, 주요 API/스크립트 `py_compile` 통과.
- live 연동 폴백 검사: `python3 scripts/verify_live_integrations.py` 결과 `ok=true`, 외부 키 미설정 환경에서 통근 경로 `provider=fallback`, 아파트 데이터 `sourceMode=snapshot`, 부동산 가격 `sourceMode=public_area_proxy` 확인.
- API 스모크: `/api/health`, `/api/property-detail?id=A15275101`, `/api/property-agent?id=A15275101&question=...`가 모두 `ok=true` 응답. Agent 응답은 가격/통근/위험/주변 입지/확인 필요 서류 근거 그룹을 반환.
- 제출 전 남은 수동 확인: 전화번호, 서명, 개인정보 수집·이용 동의 체크, 실제 API 키 기반 live 검증 결과 반영.

확인일: 2026-06-12 (실제 API live 검증 구조 + 부동산 가격 어댑터 + 지도 UX/Agent 근거 보강)

## 실제 API live 검증 구조 및 지도 UX 검증 (2026-06-12)

- 서버 실행: `python3 api/movevalue_api.py --port 5173 --quiet`
- `GET /api/health`: `ok=true`, 생활권 9개, `integrations={odsay:false,tmap:false,kakao:false,seoulOpenApi:false,molitTrade:false,molitRent:false,publicPrice:false}` 반환 확인
- `python3 scripts/verify_live_integrations.py`: 키 미설정 환경에서도 실패하지 않고 `ok=true` 반환. Kakao 주소검색은 `not_configured_or_no_result`, 통근 루트는 `provider=fallback`, `mode=estimated_fallback`, 총 27분·요금 1,550원·단계 3개 반환
- 같은 스크립트에서 서울 아파트 데이터는 `sourceMode=snapshot`, `totalRecords=2876`, `availableRecords=5`, `complete=false`로 확인. 실제 `SEOUL_OPEN_API_KEY` 주입 시 전체 수집 경로로 전환 가능
- 같은 스크립트에서 부동산 가격 어댑터는 `molitTrade.mode=not_configured`, `molitRent.mode=not_configured`, `publicPrice.mode=not_configured`로 확인. 키 값은 출력하지 않음
- `GET /api/apartments?zoom=13&destination=gangnam`: 단지 `pricePreview`에 매매가 라벨, 전세가율, 위험 등급, 생활권 기준 통근시간(`commuteMinutes`, `commuteLabel`) 포함 확인
- `GET /api/property-detail?id=A15275101`: `price.liveStatus`, `risk.contractChecklist`, `socRadius`, 전세 위험 신호, 생활권 정보, 데이터 연계 상태 반환 확인
- `GET /api/property-agent?id=A15275101&question=전세%20들어가도%20괜찮아?`: `basisGroups`가 `가격 근거`, `통근 근거`, `위험 근거`, `생활권 근거`, `확인 필요 서류`로 구조화되어 반환 확인
- 브라우저 지도 검증: 생활권 마커 9개, 현재 화면 단지 마커 2개, Leaflet 타일 20개 이상 렌더링, 콘솔 오류 없음
- 지도 라벨 필터 검증: `매매가` 기본값에서 `위험도`, `통근시간`으로 전환 시 마커 라벨과 범례 문구가 즉시 변경됨
- 단지 목록 클릭 검증: `개봉건영` 선택 시 오른쪽 부동산 상세 대시보드 열림, 가격 정보, 실거래 API 상태, 거래 추이 SVG, 전세 위험 신호, 계약 전 확인 체크리스트, 생활권 정보, 비교표, AI Agent 폼 표시
- 선택 단지 생활 SOC 반경 검증: `선택 단지 생활 SOC 반경` 체크 상태에서 1.6km 원이 지도에 표시되고, 체크 해제 시 원이 제거됨
- AI Agent UI 검증: `이 아파트 전세 들어가도 괜찮아?` 입력 후 답변, 가격 근거, 통근 근거, 위험 근거, 생활권 근거, 확인 필요 서류 그룹이 화면에 표시됨
- DOCX 제출자료 검증: `scripts/build_application_docx.py`로 `deliverables/MoveValue_참가신청서_기획서_초안.docx` 재생성 후 `render_docx.py`로 4개 페이지 PNG와 PDF 렌더링, 육안 확인에서 텍스트 잘림·중첩 없음

## 시스템 아키텍처 문서 검증 (2026-06-12)

- `architecture/` 폴더에 인덱스, 시스템 아키텍처, 데이터 흐름, 사용자 플로우, API 시퀀스, 배포·보안 문서 생성 확인
- `find architecture -type f | sort`로 문서 6개 생성 확인
- `rg -n '```mermaid' architecture`로 Mermaid 다이어그램 블록 30개 생성 확인
- `git diff --check` 통과

## 부동산 지도 대시보드 검증

- 지도 베이스 개편: `#map`을 왼쪽 360px 사이드바 + 오른쪽 전체 지도 캔버스 구조로 변경. 지도 화면에서는 전역 헤더/내비게이션/푸터를 숨기고 사이드바 내부 `랭킹 대시보드`, `부동산 현황` 링크로 이동
- 데스크톱 1600x900: `body.is-map-view=true`, 그리드 컬럼 `360px 1240px`, 지도 캔버스 높이 900px, 가로 오버플로 없음
- 데스크톱 지도 구성: 사이드바 추천 생활권 5개, 현재 화면 아파트 리스트 5개, 생활권 마커 9개, 아파트 가격 마커 5개, 플로팅 헤더와 플로팅 범례 표시
- 데스크톱 단지 클릭: 오른쪽 상세 드로어 560px, `개봉건영`, 위험 신호 6개, 비교표 1행 표시, 가로 오버플로 없음
- 모바일 잔여 뷰포트 390px 검증: 사이드바/지도 스택형 레이아웃, 추천 리스트 5개, 아파트 리스트 5개, 생활권 마커 9개, 아파트 가격 마커 5개, 가로 오버플로 없음
- `GET /api/property-detail?id=A15275101`: `ok=true`, 단지명 `개봉건영`, 주소, 사용승인연도 1994년, 세대수 209세대, 면적 옵션, 가격 정보, 12개월 거래 추이, 위험 신호 6개, 생활권 정보, AI 요약, 데이터 연계 상태 반환
- `GET /api/property-agent?id=A15275101&question=전세%20들어가도%20괜찮아?`: 전세가율 57.6%, 공시가격 대비 보증금 비율 102.3%, 등기부/보증보험/체납 확인 필요 문구 반환
- `GET /api/property-agent?id=A15275101&question=비슷한%20가격대의%20더%20안전한%20지역을%20찾아줘`: 더 낮은 위험 점수 후보 `송파파인타운13단지`, `우리유앤미` 제안
- `/api/apartments?...&cluster=false`: `features[].pricePreview`에 추정 매매가, 전세가율, 위험 신호 등급 포함 확인
- 지도 탭 초기 상태: Leaflet 실제 지도 표시, 단지 가격 라벨 마커 4개, 상태 배지 `제한 스냅샷 2,876개 중 현재 화면 4개`, 대시보드 기본 안내 문구 표시
- 단지 마커 클릭: `개봉건영` 상세 대시보드 열림, 위험 신호 배지 `낮음 · 41점`, 가격 카드, 거래 추이 SVG, 위험 신호 6개, 비교표 1행, AI Agent 폼 표시
- AI Agent 폼 입력 `비슷한 가격대의 더 안전한 지역을 찾아줘`: 대안 탐색 답변과 비교 후보 칩 표시
- 브라우저 콘솔 오류·경고: 없음
- 모바일 390px 지도 탭: 단지 가격 라벨 마커 5개, 가로 오버플로 없음
- 모바일 390px 단지 선택 상태: 상세 대시보드 1열 레이아웃, 위험 신호 6개, Agent 폼 1열, 가로 오버플로 없음

## 데이터 재생성

- `python3 scripts/build_real_dataset.py` 실행 성공
- `data/areas.actual.json` 생활권 9개 생성
- 서울시 2025 전월세 매칭 거래 합계 114,319건 유지
- 모든 생활권에 `socSummary`, `safetyEnvSummary`, `rentExamples`, `evidence.socCounts`, `evidence.safetyEnvCounts`, `evidence.commuteMode` 생성
- 현재 로컬 환경에는 `ODSAY_API_KEY`가 없어 통근시간은 9개 생활권 모두 `table_fallback`으로 기록
- 생활 SOC 집계 예시: 건대입구 병원 2·학교 3·공원 2, 마곡나루 병원 1·학교 4·공원 2, 상암DMC 병원 1·학교 3·공원 2
- 안전·환경 집계 예시: 건대입구 치안시설 2·CCTV 62대·공원 2, 신림 치안시설 1·CCTV 78대·공원 2
- 전월세 예시: 생활권별 4건 생성. 상세 지번·건물명 없이 계약월·법정동·면적·보증금·월세·건물용도·층만 저장
- `SEOUL_OPEN_API_KEY=sample python3 scripts/build_apartment_snapshot.py`로 `data/apartments.seoul.snapshot.json` 생성
- 서울시 공동주택 아파트 정보 `OpenAptInfo` 공식 총 건수 2,876건 확인. sample 키 제한으로 현재 스냅샷은 5건 미리보기이며 `meta.complete=false`

## 정적 검사

- `node --check app/app.js` 통과
- `python3 -m json.tool data/areas.actual.json` 통과
- `python3 -m json.tool data/apartments.seoul.snapshot.json` 통과
- `python3 -m py_compile api/movevalue_api.py api/route_adapters.py api/apartment_adapters.py api/property_model.py api/property_adapters.py api/real_estate_price_adapters.py scripts/build_real_dataset.py scripts/movevalue_adapters.py scripts/build_apartment_snapshot.py scripts/verify_live_integrations.py scripts/build_application_docx.py` 통과
- `git diff --check` 통과

## API 검증

- API 서버 실행: `python3 api/movevalue_api.py --port 5173`
- `GET /api/health`: `ok=true`, 생활권 9개, 2025 서울시 전월세 출처, ODsay 경로 API 어댑터 메타, 생활 SOC 데이터셋 메타, 안전환경 데이터셋 메타 포함
- `GET /api/health`: `apartments.sourceMode=snapshot`, `apartments.totalRecords=2876`, `apartments.availableRecords=5`, `apartments.complete=false`, `integrations.seoulOpenApi=false` 확인
- `GET /api/recommendations?...&limit=9`: 9개 랭킹 반환, `meta.totalCandidates=9`, 1위 건대입구 91점(기본 조건), `reasonText`에 강남 24분·월세 57만원·병원 2·학교 3·공원 2·치안시설 2·CCTV 62대 표시
- 1위 건대입구 응답: `rentExamples` 4건, `evidence.safetyEnvCounts={police:2, cctvClusters:1, cctv:62, park:2}`, `evidence.commuteMode=table_fallback`
- `GET /api/areas`: `meta.integrations={odsay:false,tmap:false,kakao:false}`, 생활권 ID 9개, `guro/gongdeok/gimpoairport` 대표 주소 정상 반환
- `GET /api/geocode?query=konkuk`: 건대입구 로컬 좌표(`source=known_location`) 반환
- `GET /api/geocode?query=서울%20광진구%20화양동`: 생활권 대표 주소 로컬 좌표(`source=known_address`) 반환
- `GET /api/commute-route?origin=서울%20광진구%20화양동&destinationQuery=서울%20강남구%20역삼동&provider=auto`: ODsay/TMAP 키 미설정 환경에서 `provider=fallback`, `mode=estimated_fallback`, 주소 라벨 유지, 총 27분, 요금 1,550원, 단계 3개 반환
- `GET /api/apartments?bounds=37.45,126.80,37.70,127.18&zoom=11&cluster=true`: `sourceMode=snapshot`, `filteredRecords=5`, `returnedFeatures=5`, 개봉건영·월계동원베네스트·우리유앤미·오금현대백조(임대)·송파파인타운13단지 반환
- `GET /api/apartments?q=%EC%86%A1%ED%8C%8C%ED%8C%8C%EC%9D%B8%ED%83%80%EC%9A%B4&zoom=16&cluster=false`: 단지명 검색으로 송파파인타운13단지 1건 반환
- `GET /api/apartments?district=%EC%86%A1%ED%8C%8C%EA%B5%AC&zoom=16&cluster=false`: 송파구 2건 반환
- `GET /` 루트 웹 페이지 `200 OK`
- `HEAD /app.js`: `Cache-Control: no-store` 확인. 개발·심사 중 최신 정적 파일 반영 지연을 방지

## 브라우저 검증 (데스크톱)

- 초기 `추천` 화면: `main > .anchor-target` 중 `recommend`만 표시, 추천 카드 6개, 데이터 근거 표 10행 렌더링
- 추천 카드 UI: 카드 우측 `91점` 같은 종합점수 텍스트와 하단 점수바 제거 확인. 카드 내부 `.score` 노드 0개, `.bar` 노드 0개, 카드 텍스트 내 `n점` 패턴 0개
- 추천 카드 문장: "강남 업무지구까지 24분, 월세 중앙값 57만원, 병원 2개·학교 3개·공원 2개, 치안시설 2개·CCTV 62대..." 형태의 숫자 기반 사유 표시
- 상세 근거 패널: `실거래 예시`, `안전·환경 근거`, 구체 추천 사유 표시
- 데이터 근거 표: SOC 근거와 안전·환경 컬럼 표시
- 상단 메뉴 7개 클릭 검증: `추천`, `통근검증`, `지도`, `데이터 근거`, `API`, `사업모델`, `제출자료` 각각 클릭 시 해당 섹션 1개만 표시
- OpenStreetMap 실제 지도 타일 표시 확인, `#map` 화면 단독 표시
- 생활권 마커 9개 표시, 점수별 색상(상위권 녹색/검토권 금색/미달 적색)·크기 구분
- 마커 팝업: 생활권명, 순위, 목적지 통근시간, 월세 중앙값, 종합점수 표시
- 카드 클릭 → 지도 마커 선택·팝업 연동 확인 (신림 카드 → 신림 마커 87점 팝업)
- 마커 클릭 → 카드 선택·상세 패널 연동 확인 (마곡나루 마커 → 7위/9개 표시, 전체 카드 9개 표시)
- `추천` 화면 내부에 `#routeContent`가 없고, `통근검증` 메뉴의 독립 `#route` 섹션에만 루트 UI가 존재하는 것 확인
- 통근 루트 검증 기본값: 검증 생활권 `1위 건대입구 · 서울 광진구`, 집 주소 `서울 광진구 화양동`, 회사 주소 `서울 강남구 역삼동` 표시. 좌표 문자열 대신 실제 주소 입력 중심으로 변경
- 검증 생활권 드롭다운 변경: `신림` 선택 시 집 주소 `서울 관악구 신림동`, 상세 순위 `2위 / 9개`, 선택 배지 `신림`으로 동기화되고 기존 루트 결과는 초기화됨
- 통근 루트 계산 클릭: 폴백 결과 카드 렌더링, 주소 라벨 `서울 광진구 화양동 → 서울 강남구 역삼동`, 요약 지표 4개(총 소요·환승·도보·요금), 단계 3개, 키 미설정 notice 표시, 에러 상태 없음
- 통근검증 화면: ODsay/TMAP 키 미설정 안내 표시. 키는 환경변수로만 감지하며 저장소에는 기록하지 않음
- `지도에서 보기` 클릭: `지도` 섹션만 표시, 마커 9개 유지, Leaflet SVG 경로 6개 렌더링, 폴백 경로선 표시 확인
- 지도 화면의 `서울 아파트 단지 표시` 토글 체크 상태 확인, 상태 배지 `제한 스냅샷 2,876개 중 현재 화면 4개` 표시
- 지도 화면에서 아파트 단지 마커 4개 표시. 팝업 예시: `개봉건영 서울특별시 구로구 고척로21나길 85-6 209세대 · 2개동 · 1994-05-09 분양 · 개별난방`
- 아파트 레이어 토글 OFF: 단지 마커 0개, 상태 `아파트 단지 레이어 꺼짐`
- 아파트 레이어 토글 ON: 단지 마커 4개 복귀, 상태 `제한 스냅샷 2,876개 중 현재 화면 4개`
- "전체 후보 9개 중 상위 6개" 표기와 전체 보기 토글 동작
- 추천 카드별 한 줄 근거 표시
- 데이터 근거 표: 생활권 9개 + 합계 114,319건, 월세·보증금·전세 중앙값(억 단위 변환 포함), SOC 근거, 안전환경 근거 컬럼 표시
- API/사업모델/제출자료 섹션 렌더링 확인
- 사업모델 섹션: 경쟁 서비스 대비 차별점 문구 표시. 매물 검색 중심 서비스와 달리 생활권 추천/API/B2G 리포트 엔진임을 명시
- 브라우저 콘솔 오류·경고: 없음

## 브라우저 검증 (모바일 375px)

- 초기 `추천` 화면: `recommend`만 표시, 카드 6개 렌더링
- 추천 카드 점수 텍스트·점수바 제거 확인
- `document.documentElement.scrollWidth == 375`, 페이지 가로 오버플로 없음
- 상세 패널 내 `실거래 예시`, `안전·환경 근거` 표시
- `통근검증` 화면 단독 표시, 검증 생활권 드롭다운·주소 기본값 유지, 상세 근거 내부 중첩 없음
- 통근 루트 계산 후 결과 에러 없음, 주소 라벨 유지, 요약 지표 4개·단계 3개 표시
- 상단 메뉴는 가로 스크롤 내비게이션으로 유지
- `지도` 화면: `map`만 표시, Leaflet 마커 9개, 통근 경로 SVG 3개, 지도 높이 487px로 표시
- `지도` 화면: 아파트 단지 마커 5개, 상태 배지 `제한 스냅샷 2,876개 중 현재 화면 5개`, 토글 체크 상태 유지
- 지도 화면에서도 `document.documentElement.scrollWidth == 375`
- 아파트 레이어 툴바 너비 317px, 상태 배지 너비 317px로 모바일 화면 내 정렬
- 브라우저 콘솔 오류·경고: 없음

## 수정된 결함

- 모바일에서 데이터 근거 표(min-width 640px)가 그리드 아이템의 `min-width:auto` 기본값 때문에 페이지 전체를 밀어내던 가로 오버플로를 `main > *, .workspace > .panel { min-width: 0 }`으로 수정.
- 메뉴가 스크롤 앵커 방식이라 여러 섹션이 한 화면에 이어 보이던 문제를 탭형 화면 전환으로 수정.
- 생활 SOC가 환승·주거비 기반 프록시였던 문제를 병원·학교·공원 좌표 반경 집계로 교체.
- Leaflet 경로선 검증을 위해 마커 9개 수준에서 불필요한 Canvas 강제 렌더링을 제거하고 기본 SVG 렌더러를 사용하도록 수정.
- 사용자 통근 루트 계산을 API 키 없는 환경에서도 실패 화면이 아닌 명확한 거리 기반 폴백 결과로 표시하도록 수정.
- 통근 루트 입력 기본값이 좌표 문자열이라 사용자가 이해하기 어려웠던 문제를 대표 주소 기본값으로 수정.
- 통근 루트 검증 UI가 `상세 근거` 안에 들어가 화면 맥락이 섞이던 문제를 독립 화면으로 분리.
- 통근 루트 검증 UI가 추천 화면에 계속 붙어 있어 화면 밀도가 높던 문제를 `통근검증` 독립 메뉴로 분리.
- 추천 카드 우측 종합점수 숫자와 점수바가 카드 판단을 점수 위주로 보이게 하던 문제를 제거.
- 생활권 지도에 실제 주거 후보 단지 정보가 없어 추천 결과와 현실 주거 공급의 연결이 약했던 문제를 서울시 공동주택 아파트 정보 기반 지도 레이어로 보완.
- 안전·환경이 MVP 프록시로 남아 있던 약점을 치안시설·CCTV 집계점·도시대기 측정망·공원 접근성 스냅샷 점수로 교체.
- 생활권 추천이 추상적인 강점 문구에 머물던 문제를 통근시간·월세·SOC·안전환경 수치 기반 문장으로 교체.
- 생활권 단위 추천만 있고 후보 매물 설득력이 부족했던 문제를 개인정보성 상세주소 제외 전월세 실거래 예시로 보강.
- 브라우저가 이전 `app.js`를 캐시해 새 UI가 늦게 반영될 수 있어 정적 파일 응답에 `Cache-Control: no-store`를 추가.

## 확인된 제한

- 현재 주거비는 서울시 2025 전월세 파일의 15~85㎡ 거래 중앙값 기반이다.
- 통근시간은 ODsay 대중교통 경로 API 어댑터가 구현되어 있지만, 이번 검증 환경에서는 API 키가 없어 기존 테이블 폴백으로 생성됐다.
- 사용자 통근 루트는 Kakao 주소 검색, ODsay, TMAP 런타임 어댑터가 구현되어 있다. 이번 검증에서는 API 키를 환경변수로 주입하지 않아 실제 외부 호출은 수행하지 않았고, 로컬 대표 주소/후보명 해석과 거리 기반 폴백을 검증했다.
- 채팅으로 전달된 API 키는 저장소·문서·커밋에 기록하지 않았다. 실제 live API 검증은 `KAKAO_REST_API_KEY`, `ODSAY_API_KEY`, `TMAP_APP_KEY`를 로컬 환경변수로 설정한 별도 실행에서 수행해야 한다.
- 서울 아파트 단지 레이어는 서울 열린데이터광장 `OpenAptInfo` 어댑터와 `/api/apartments`가 구현되어 있다. 이번 검증에서는 `SEOUL_OPEN_API_KEY`를 주입하지 않아 sample 제한 스냅샷 5건으로 검증했다. 전체 2,876건 표시는 실제 `SEOUL_OPEN_API_KEY` 설정 후 같은 엔드포인트에서 확인해야 한다.
- 현재 지도 레이어는 단지 좌표 레벨이다. 건물별 폴리곤 전체 표시는 건축물대장·공간데이터 타일링을 별도 단계에서 검토한다.
- 생활 SOC는 서울 열린데이터광장 병의원·학교·공원 좌표 스냅샷 기반이다. 운영 단계에서는 API 키 기반 전체 자동 갱신과 편의시설 카테고리 확장이 필요하다.
- 안전·환경 점수는 공공데이터 스냅샷 기반으로 교체했다. 다만 원천 API 자동 갱신과 행정동 전체 커버리지는 추후 구현이 필요하다.
- 지도 타일은 OpenStreetMap 공개 타일을 사용하며, 운영 배포 시 VWorld 등으로 교체를 권장한다 (`docs/api-development.md` 참고).
- 전화번호, 서명, 개인정보 수집·이용 동의 체크는 신청자가 제출 전 직접 기재해야 한다.

## 이전 확인 (2026-06-11 데이터 구축 시)

- `python3 scripts/build_real_dataset.py` 실행 성공: `data/areas.actual.json` 9개 생활권 생성
- `deliverables/MoveValue_참가신청서_기획서_초안.docx` 재생성 및 렌더링 검수 (`qa/docx-render/page-1.png` ~ `page-4.png`)
