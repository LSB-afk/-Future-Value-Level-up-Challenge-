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
- **상단 메뉴**: 추천·지도·데이터 근거·API·사업모델·제출자료 sticky 내비게이션 + 스크롤 위치 활성 표시 + API 연결 상태 pill, 모바일 가로 스크롤
- **데이터 근거 섹션**: 생활권별 매칭 거래 건수·월세/보증금/전세 중앙값 표(합계 114,319건), 출처 명시, MVP 프록시 한계 고지
- **API 섹션**: 엔드포인트 3종 설명, curl 예시, B2B/B2G 확장 방향
- **사업모델 섹션**: B2C/B2B/B2G/데이터 마켓 카드 + ①~④ 밸류체인 + 데이터 생태계 기여
- **제출자료 섹션**: DOCX 위치, 문서 경로, 개인정보·서명 직접 확인 안내
- **추천 UX**: 카드별 한 줄 추천 근거, "전체 후보 9개 중 상위 6개" + 전체 보기 토글, 재계산 로딩 디밍, 점수 항목 툴팁, 억 단위 금액 표기
- **버그 수정**: 모바일 가로 오버플로 (그리드 아이템 `min-width:auto` 기본값이 640px 표를 페이지 밖으로 밀어내던 문제 → `min-width:0`)
- **문서 갱신**: README, service-model, data-sources, api-development(지도 교체 가이드 포함), verification(전체 재검증), product-roadmap(신규)

### 검증 완료 (docs/verification.md 상세)

- 정적 검사(node/json/py_compile), API 응답, 데스크톱 브라우저(콘솔 오류 0건), 모바일 375px(오버플로 0개) 모두 통과

## 다음 작업 (우선순위순)

### P0. 제출 마감 전 직접 처리 (사람 확인 필요)

1. `deliverables/MoveValue_참가신청서_기획서_초안.docx`에 개인정보·전화번호·서명·동의 항목 직접 기재 (`제출 전 기재` 표시 위치)
2. 기획서 본문이 최신 구현(실제 지도, 6개 섹션, 한 줄 근거)과 일치하는지 확인 — 필요 시 `python3 scripts/build_application_docx.py` 재실행 후 문구 갱신
3. 공모전 접수 사이트 요구 양식(HWPX 등) 변환 여부 확인

### P1. 데이터 정밀도 (선정 후 1~2개월, docs/product-roadmap.md 1단계)

1. 통근시간 테이블 → 대중교통 경로 API(ODsay/TMAP) 또는 GTFS 라우팅 교체, 목적지 자유 입력
2. 생활 SOC 프록시 → 병원·학교·공원·편의시설 좌표 집계 어댑터
3. 안전·환경 프록시 → 안전등급·대기질·녹지율 공공데이터 어댑터
4. 전월세 월별 증분 갱신 배치 + 국토교통부 실거래가 API 병행

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
- 현재 완성 상태: Leaflet+OSM 실제 지도(마커 9개, 카드 양방향 연동), 상단 메뉴 6개(추천/지도/데이터 근거/API/사업모델/제출자료), 데이터 근거 표, 추천 카드 한 줄 근거, 모바일 반응형까지 검증 완료. 상세는 docs/worklog.md와 docs/verification.md 참고.

[이번에 할 일]
docs/product-roadmap.md 1단계(데이터 정밀도) 중 다음을 진행해줘:
1. 통근시간 MVP 테이블을 실제 대중교통 경로 기반으로 교체할 어댑터 구조 설계·구현 (API 키는 환경 변수로, 키 없으면 기존 테이블 폴백)
2. 생활 SOC 점수를 공공데이터(병원·학교·공원 좌표) 집계 기반으로 교체
3. 변경 후 data/areas.actual.json 재생성과 docs/data-sources.md, docs/verification.md 갱신

[제약 - 반드시 지킬 것]
- data/raw/ 원천 대용량 데이터는 커밋 금지 (.gitignore에 이미 등록)
- API 키 하드코딩 금지, 키 없는 환경에서도 폴백으로 동작해야 함
- 실데이터 기반 항목과 MVP 프록시 항목의 구분 표기를 화면·문서에서 유지
- 기존 화면 구조(메뉴/섹션)와 사용자가 만든 변경사항을 되돌리지 말 것

[검증]
- node --check app/app.js
- python3 -m json.tool data/areas.actual.json
- python3 -m py_compile api/movevalue_api.py scripts/build_real_dataset.py
- 서버 실행 후 브라우저에서 지도 마커 9개, 카드↔마커 연동, 콘솔 오류 없음 확인
- 완료 후 Lore commit protocol(의도 한 줄 + Constraint/Rejected/Confidence/Scope-risk/Not-tested 트레일러)로 커밋하고 origin main에 push
```
