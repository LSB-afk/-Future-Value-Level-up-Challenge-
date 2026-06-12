# MoveValue 작업 일지 및 다음 작업

기준일: 2026-06-11 · 저장소: https://github.com/LSB-afk/-Future-Value-Level-up-Challenge-

## 한 줄 요약

MoveValue는 서울시 2025 전월세 실데이터(매칭 114,319건) 기반으로 주거비·통근시간·생활 SOC·안전환경을 함께 점수화해 생활권을 추천하는 국토교통 데이터 서비스 프로토타입이다. 웹 화면과 추천 API가 같은 Python 서버에서 동작한다.

## 완료된 작업

### 데이터·API 기반 (커밋 7480bec까지)

- `scripts/build_real_dataset.py`: 서울 열린데이터광장 전월세 파일 다운로드 → 15~85㎡ 거래를 생활권 법정동 기준 집계 → `data/areas.actual.json` 생성 (생활권 9개)
- `api/movevalue_api.py`: 외부 패키지 없는 Python 표준 라이브러리 서버. `/api/health`, `/api/areas`, `/api/recommendations` + 정적 웹앱 서빙
- 추천 점수: 예산·목적지·가구 유형·가중치 기반, 항목별 점수 공개 (설명 가능성)
- `deliverables/MoveValue_참가신청서_기획서_초안.docx` 생성 및 렌더링 검수

### 서비스 고도화 (커밋 81d8e45)

- **실제 지도**: Leaflet 1.9.4 + OpenStreetMap 타일(API 키 불필요). 마커 9개 점수별 색상·크기, 팝업(생활권명·순위·통근시간·월세 중앙값·종합점수), 카드↔마커 양방향 선택 연동, 타일 실패 시 분포도 폴백
- **상단 메뉴**: 추천·통근검증·지도·데이터 근거·API·사업모델·제출자료 sticky 내비게이션 + 탭형 화면 전환 + API 연결 상태 pill, 모바일 가로 스크롤
- **데이터 근거 섹션**: 생활권별 매칭 거래 건수·월세/보증금/전세 중앙값 표(합계 114,319건), 출처 명시, MVP 프록시 한계 고지
- **API 섹션**: 엔드포인트 3종 설명, curl 예시, B2B/B2G 확장 방향
- **사업모델 섹션**: B2C/B2B/B2G/데이터 마켓 카드 + ①~④ 밸류체인 + 데이터 생태계 기여
- **제출자료 섹션**: DOCX 위치, 문서 경로, 개인정보·서명 직접 확인 안내
- **추천 UX**: 카드별 한 줄 추천 근거, "전체 후보 9개 중 상위 6개" + 전체 보기 토글, 재계산 로딩 디밍, 점수 항목 툴팁, 억 단위 금액 표기
- **버그 수정**: 모바일 가로 오버플로 (그리드 아이템 `min-width:auto` 기본값이 640px 표를 페이지 밖으로 밀어내던 문제 → `min-width:0`)
- **문서 갱신**: README, service-model, data-sources, api-development(지도 교체 가이드 포함), verification(전체 재검증), product-roadmap(신규)

### 검증 완료 (docs/verification.md 상세)

- 정적 검사(node/json/py_compile), API 응답, 데스크톱 브라우저(콘솔 오류 0건), 모바일 375px(오버플로 0개) 모두 통과

### 데이터 정밀도 1차 고도화

- `scripts/movevalue_adapters.py`: ODsay 대중교통 경로 API 어댑터 추가. `ODSAY_API_KEY` 또는 `MOVEVALUE_ODSAY_API_KEY`가 없으면 기존 통근시간 테이블로 자동 폴백
- 생활 SOC 점수: 병의원·학교·공원 좌표 스냅샷을 생활권 대표역 반경 1.6km로 집계해 `serviceScore`/`socScore` 생성
- `data/areas.actual.json`: 생활권 9개, 전월세 매칭 114,319건 유지. 각 생활권에 `socSummary`, `evidence.socCounts`, `evidence.commuteMode` 추가
- 웹 메뉴: 스크롤 앵커 방식에서 탭형 화면 전환으로 변경. 추천/지도/데이터 근거/API/사업모델/제출자료 중 한 화면만 표시
- 웹 데이터 근거: 생활권별 SOC 집계 수치와 통근 폴백 상태 표시

### 사용자 통근 루트 검증

- `api/route_adapters.py`: Kakao 주소 검색, ODsay/TMAP 대중교통 경로 API, 거리 기반 폴백을 같은 응답 형식으로 정규화
- `api/movevalue_api.py`: `/api/geocode`, `/api/commute-route` 추가. `/api/areas`와 `/api/recommendations`는 생활권 대표 주소와 목적지 대표 주소도 반환
- 통근검증 화면: 추천 화면과 분리된 독립 메뉴로 집 주소·회사 주소를 입력해 총 소요시간, 환승, 도보, 요금, 단계별 경로 확인
- 주소 기반 UX: 기본 입력값을 좌표가 아닌 `서울 광진구 화양동`, `서울 강남구 역삼동` 같은 대표 주소로 표시. 대표 주소는 API 키 없이 로컬 좌표로 변환하고, 상세 주소 검색은 Kakao REST 키가 있을 때 사용
- 지도: 통근 루트 계산 결과를 출발·도착 좌표선으로 표시. 실제 API 경로 좌표가 있으면 해당 좌표를 사용하고, 폴백이면 점선으로 표시

### 설득력 보완 2차

- `scripts/build_real_dataset.py`: 생활권별 전월세 실거래 예시 4건 추가. 공개파일에서 상세 지번·건물명은 제외하고 계약월·법정동·면적·보증금·월세·건물용도·층만 표시
- `scripts/movevalue_adapters.py`: 안전·환경 점수를 MVP 프록시에서 치안시설·CCTV 집계점·도시대기 측정망·공원 접근성 스냅샷 결합으로 교체
- `api/movevalue_api.py`: `/api/recommendations` 결과에 `reasonText` 추가. 예: 강남 24분, 월세 57만원, 병원·학교·공원·치안시설·CCTV 수치를 한 문장으로 반환
- 웹 상세 근거: 실거래 예시, 안전·환경 근거, ODsay/TMAP 키 감지 안내 표시
- 사업모델: 네이버부동산·다방·직방 대비 "매물 검색"이 아니라 생활권 추천/API/B2G 리포트 엔진이라는 차별 문구 강화

### 추천·통근검증 UX 정리

- 추천 카드 우측의 종합점수 숫자와 점수바를 제거해 카드가 순위·실거주 판단 근거 중심으로 읽히도록 정리
- 통근 루트 검증을 추천 화면 우측 보조 패널에서 `통근검증` 독립 메뉴로 이동
- 통근검증 화면 안에서 검증 생활권을 바로 바꾸는 드롭다운을 추가해 추천 화면으로 돌아가지 않고 후보지별 집-회사 경로를 비교할 수 있게 개선

### 서울 아파트 단지 지도 레이어

- `scripts/build_apartment_snapshot.py`: 서울 열린데이터광장 `OpenAptInfo`를 호출해 단지명, 주소, 좌표, 세대수, 동수, 사용승인일, 주차대수만 정규화하는 스냅샷 생성기 추가
- `api/apartment_adapters.py`: `SEOUL_OPEN_API_KEY`, `SEOUL_API_KEY`, `MOVEVALUE_SEOUL_OPEN_API_KEY` 환경변수 기반 live API 호출과 스냅샷 폴백, bounds/zoom 기반 클러스터링 구현
- `api/movevalue_api.py`: `/api/apartments` 추가, `/api/health`에 아파트 레이어 데이터 상태와 서울 열린데이터 키 감지 상태 표시
- 웹 지도: `서울 아파트 단지 표시` 토글, 지도 상태 배지, 단지·클러스터 마커, 단지 팝업(주소·세대수·동수·사용승인일·주차대수) 추가
- 현재 커밋 스냅샷: 공식 sample 키 제한으로 2,876건 중 5건 미리보기만 포함. 실제 전체 단지 표시는 `SEOUL_OPEN_API_KEY` 설정 후 같은 코드 경로로 동작

### 부동산 상세 대시보드

- `api/property_model.py`, `api/property_adapters.py`: 단지 클릭 상세 모델, 가격 미리보기, 거래 추이, 전세 위험 신호, AI 요약, 질의응답 응답 생성 추가
- `api/movevalue_api.py`: `/api/property-detail`, `/api/property-agent` 추가
- `api/apartment_adapters.py`: 지도 단지/클러스터 응답에 `pricePreview` 추가. 단지 라벨에 추정 매매가와 전세가율 표시 가능
- 웹 지도: 개별 단지 가격 라벨 마커, 클릭 시 상세 대시보드, 거래 추이 SVG, 위험 신호 점검, 단지 비교표, AI Agent 폼, 모바일 1열 대시보드 구현
- 문서: `docs/real-estate-dashboard.md`에 레퍼런스 조사, 데이터 진실성 구분, API 구조, 공공 데이터 연계 계획 기록
- 현재 한계: 매매가·공시가격·거래 추이는 API 키 없이도 프로토타입 검증이 가능하도록 생활권 전월세 집계 기반 추정값으로 표시. 화면과 문서에서 `실데이터/추정/연계 예정`을 구분

### 지도 베이스 리디자인

- `#map` 화면을 카드형 섹션에서 풀스크린 지도 대시보드로 전환
- 왼쪽 사이드바: MoveValue 로고, 화면 이동 링크, 매칭 조건, 레이어 토글, 추천 생활권 TOP 5, 현재 지도 내 아파트 리스트
- 오른쪽 지도: 전체 Leaflet 지도, 플로팅 제목 카드, 플로팅 범례, 생활권 원형 점수 마커, 아파트 가격 라벨 마커
- 단지 클릭 시 지도 위 오른쪽 드로어로 상세 부동산 대시보드 표시
- `body.is-map-view` 상태에서 전역 헤더·내비게이션·푸터를 숨겨 참고 이미지처럼 지도 중심 화면으로 구성

### 시스템 아키텍처 문서화

- `architecture/` 폴더를 별도 생성해 시스템 컨텍스트, 컨테이너/컴포넌트 구조, 데이터 흐름, 사용자 플로우, API 시퀀스, 배포·보안 기준을 분리 정리
- Mermaid 다이어그램으로 추천 흐름, 통근검증 live API/폴백, 아파트 단지 지도 레이어, 부동산 상세 대시보드, AI Agent 응답 흐름을 GitHub에서 바로 확인 가능하게 작성
- README 현재 산출물에 `architecture/` 항목을 추가해 심사·발표 시 기술 구조 문서로 바로 이동할 수 있게 연결

## 다음 작업 (우선순위순)

### P0. 제출 마감 전 직접 처리 (사람 확인 필요)

1. `deliverables/MoveValue_참가신청서_기획서_초안.docx`에 개인정보·전화번호·서명·동의 항목 직접 기재 (`제출 전 기재` 표시 위치)
2. 기획서 본문이 최신 구현(실제 지도, 7개 섹션, 한 줄 근거, 독립 통근검증 화면)과 일치하는지 확인 — 필요 시 `python3 scripts/build_application_docx.py` 재실행 후 문구 갱신
3. 공모전 접수 사이트 요구 양식(HWPX 등) 변환 여부 확인

### P1. 데이터 정밀도 (선정 후 1~2개월, docs/product-roadmap.md 1단계)

1. ODsay/TMAP API 키 운영, live API 실검증, 호출 캐시, 실패 로그, 혼잡도, 첫차·막차
2. 생활 SOC 좌표 스냅샷 → 서울 열린데이터광장 API 기반 전체 자동 갱신, 편의시설 카테고리 추가
3. 안전·환경 스냅샷 → CCTV 원천, 범죄안전지수, 대기질, 녹지율 전체 커버리지 자동 갱신
4. 전월세 월별 증분 갱신 배치 + 국토교통부 실거래가 API 병행
5. 서울 공동주택 단지 전체 갱신 배치 + 건축물대장/공간데이터 기반 건물 폴리곤 타일 검토

### P2. 서비스 확장 (3~4개월, 로드맵 2단계)

- 후보 생활권 서울 전체 역세권 확대, VWorld 타일 전환 옵션, 조건 저장·후보 비교·알림, iOS 앱

### P3. 수익화 인프라 (5~6개월, 로드맵 3단계)

- API 키 발급·사용량 과금, B2G 리포트 PDF 생성기, 데이터 오픈마켓 구매·결합 파이프라인

## 이어서 작업할 때 쓰는 프롬프트

새 세션에서 아래를 그대로 붙여넣으면 맥락 없이 이어서 작업할 수 있다.

```text
MoveValue 프로젝트를 이어서 작업해줘.

[프로젝트 컨텍스트]
- 위치: ~/Desktop/국토교통 서비스 발굴 경연 (GitHub: LSB-afk/-Future-Value-Level-up-Challenge-, main 브랜치)
- MoveValue = 서울시 2025 전월세 실데이터(매칭 114,319건) 기반 주거-이동 통합 생활권 추천 웹/API 서비스. 2026 국토교통 서비스 발굴 경연 출품작.
- 실행: python3 api/movevalue_api.py --port 5173 → http://127.0.0.1:5173/ (외부 패키지 불필요)
- 현재 완성 상태: Leaflet+OSM 실제 지도(생활권 마커 9개, 서울 아파트 단지 레이어, 카드 양방향 연동), 상단 메뉴 7개(추천/통근검증/지도/데이터 근거/API/사업모델/제출자료), 데이터 근거 표, 추천 카드 한 줄 근거, 독립 통근검증 화면, 모바일 반응형까지 검증 완료. 상세는 docs/worklog.md와 docs/verification.md 참고.
- 최근 추가: 지도 단지 클릭 상세 대시보드, 가격 라벨 마커, 거래 추이 그래프, 전세 위험 신호 점검, 단지 비교, AI Agent 질의응답. 상세 설계는 docs/real-estate-dashboard.md 참고.

[이번에 할 일]
docs/product-roadmap.md 1단계(데이터 정밀도) 중 다음을 진행해줘:
1. 통근시간 MVP 테이블을 실제 대중교통 경로 기반으로 교체할 어댑터 구조 설계·구현 (API 키는 환경 변수로, 키 없으면 기존 테이블 폴백)
2. 생활 SOC 점수를 공공데이터(병원·학교·공원 좌표) 집계 기반으로 교체
3. 변경 후 data/areas.actual.json 재생성과 docs/data-sources.md, docs/verification.md 갱신
4. 서울 아파트 단지 레이어는 SEOUL_OPEN_API_KEY가 있으면 전체 OpenAptInfo 데이터로 갱신하고, 키가 없으면 sample 제한 스냅샷이라는 한계를 유지 표기

[제약 - 반드시 지킬 것]
- data/raw/ 원천 대용량 데이터는 커밋 금지 (.gitignore에 이미 등록)
- API 키 하드코딩 금지, 키 없는 환경에서도 폴백으로 동작해야 함
- 실데이터 기반 항목과 MVP 프록시 항목의 구분 표기를 화면·문서에서 유지
- 기존 화면 구조(메뉴/섹션)와 사용자가 만든 변경사항을 되돌리지 말 것

[검증]
- node --check app/app.js
- python3 -m json.tool data/areas.actual.json
- python3 -m json.tool data/apartments.seoul.snapshot.json
- python3 -m py_compile api/movevalue_api.py api/route_adapters.py api/apartment_adapters.py scripts/build_real_dataset.py scripts/movevalue_adapters.py scripts/build_apartment_snapshot.py
- 서버 실행 후 브라우저에서 지도 마커 9개, 아파트 단지 레이어, 카드↔마커 연동, 콘솔 오류 없음 확인
- 완료 후 Lore commit protocol(의도 한 줄 + Constraint/Rejected/Confidence/Scope-risk/Not-tested 트레일러)로 커밋하고 origin main에 push
```
