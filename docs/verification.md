# Verification Log

확인일: 2026-06-11 (데이터 정밀도 1차 + 사용자 통근 루트 검증 반영)

## 데이터 재생성

- `python3 scripts/build_real_dataset.py` 실행 성공
- `data/areas.actual.json` 생활권 9개 생성
- 서울시 2025 전월세 매칭 거래 합계 114,319건 유지
- 모든 생활권에 `socSummary`, `evidence.socCounts`, `evidence.socRadiusMeters`, `evidence.commuteMode` 생성
- 현재 로컬 환경에는 `ODSAY_API_KEY`가 없어 통근시간은 9개 생활권 모두 `table_fallback`으로 기록
- 생활 SOC 집계 예시: 건대입구 병원 2·학교 3·공원 2, 마곡나루 병원 1·학교 4·공원 2, 상암DMC 병원 1·학교 3·공원 2

## 정적 검사

- `node --check app/app.js` 통과
- `python3 -m json.tool data/areas.actual.json` 통과
- `python3 -m py_compile api/movevalue_api.py api/route_adapters.py scripts/build_real_dataset.py scripts/movevalue_adapters.py` 통과

## API 검증

- API 서버 실행: `python3 api/movevalue_api.py --port 5173`
- `GET /api/health`: `ok=true`, 생활권 9개, 2025 서울시 전월세 출처, ODsay 경로 API 어댑터 메타, 생활 SOC 데이터셋 메타 포함
- `GET /api/recommendations?...&limit=9`: 9개 랭킹 반환, `meta.totalCandidates=9`, 1위 건대입구 89점(기본 조건), `evidence.socCounts={hospital:2, school:3, park:2}`, `evidence.commuteMode=table_fallback`
- `GET /api/geocode?query=konkuk`: 건대입구 로컬 좌표(`source=known_location`) 반환
- `GET /api/geocode?query=서울%20광진구%20자양동`: Kakao 키 미설정 환경에서 `400 Bad Request`와 좌표 직접 입력 안내 반환
- `GET /api/commute-route?origin=37.5405,127.0692&destination=gangnam&provider=auto`: ODsay/TMAP 키 미설정 환경에서 `provider=fallback`, `mode=estimated_fallback`, 총 27분, 요금 1,550원, 단계 3개 반환
- `GET /` 루트 웹 페이지 `200 OK`
- `HEAD /app.js`: `Cache-Control: no-store` 확인. 개발·심사 중 최신 정적 파일 반영 지연을 방지

## 브라우저 검증 (데스크톱)

- 초기 `추천` 화면: `main > .anchor-target` 중 `recommend`만 표시, 추천 카드 6개, 데이터 근거 표 10행 렌더링
- 상단 메뉴 6개 클릭 검증: `추천`, `지도`, `데이터 근거`, `API`, `사업모델`, `제출자료` 각각 클릭 시 해당 섹션 1개만 표시
- OpenStreetMap 실제 지도 타일 표시 확인, `#map` 화면 단독 표시
- 생활권 마커 9개 표시, 점수별 색상(상위권 녹색/검토권 금색/미달 적색)·크기 구분
- 마커 팝업: 생활권명, 순위, 목적지 통근시간, 월세 중앙값, 종합점수 표시
- 카드 클릭 → 지도 마커 선택·팝업 연동 확인 (신림 카드 → 신림 마커 87점 팝업)
- 마커 클릭 → 카드 선택·상세 패널 연동 확인 (마곡나루 마커 → 7위/9개 표시, 전체 카드 9개 표시)
- 상세 패널 `실제 통근 루트 검증` UI 확인: 집 위치, 회사 위치, API 선택, 선택 생활권 좌표 사용, 통근 루트 계산 버튼 렌더링
- 통근 루트 계산 클릭: 폴백 결과 카드 렌더링, 요약 지표 4개(총 소요·환승·도보·요금), 단계 3개, 키 미설정 notice 표시, 에러 상태 없음
- `지도에서 보기` 클릭: `지도` 섹션만 표시, 마커 9개 유지, Leaflet SVG 경로 3개(점선 경로 1개 + 출발/도착점 2개), 폴백 경로선 `#b4872a` stroke 확인
- "전체 후보 9개 중 상위 6개" 표기와 전체 보기 토글 동작
- 추천 카드별 한 줄 근거 표시 ("주거비·생활 SOC 강점 · 예산 내 후보 · 1인 청년 적합" 등)
- 데이터 근거 표: 생활권 9개 + 합계 114,319건, 월세·보증금·전세 중앙값(억 단위 변환 포함), SOC 근거 컬럼 표시
- API/사업모델/제출자료 섹션 렌더링 확인
- 브라우저 콘솔 오류·경고: 없음

## 브라우저 검증 (모바일 375px)

- 초기 `추천` 화면: `recommend`만 표시, 카드 6개 렌더링
- `document.documentElement.scrollWidth == 375`, 페이지 가로 오버플로 없음
- `실제 통근 루트 검증` UI 표시, 통근 루트 계산 후 결과 에러 없음, 요약 지표 4개·단계 3개 표시
- 상단 메뉴는 가로 스크롤 내비게이션으로 유지
- `지도` 화면: `map`만 표시, Leaflet 마커 9개, 통근 경로 SVG 3개, 지도 높이 487px로 표시
- 지도 화면에서도 `document.documentElement.scrollWidth == 375`
- 브라우저 콘솔 오류·경고: 없음

## 수정된 결함

- 모바일에서 데이터 근거 표(min-width 640px)가 그리드 아이템의 `min-width:auto` 기본값 때문에 페이지 전체를 밀어내던 가로 오버플로를 `main > *, .workspace > .panel { min-width: 0 }`으로 수정.
- 메뉴가 스크롤 앵커 방식이라 여러 섹션이 한 화면에 이어 보이던 문제를 탭형 화면 전환으로 수정.
- 생활 SOC가 환승·주거비 기반 프록시였던 문제를 병원·학교·공원 좌표 반경 집계로 교체.
- Leaflet 경로선 검증을 위해 마커 9개 수준에서 불필요한 Canvas 강제 렌더링을 제거하고 기본 SVG 렌더러를 사용하도록 수정.
- 사용자 통근 루트 계산을 API 키 없는 환경에서도 실패 화면이 아닌 명확한 거리 기반 폴백 결과로 표시하도록 수정.
- 브라우저가 이전 `app.js`를 캐시해 새 UI가 늦게 반영될 수 있어 정적 파일 응답에 `Cache-Control: no-store`를 추가.

## 확인된 제한

- 현재 주거비는 서울시 2025 전월세 파일의 15~85㎡ 거래 중앙값 기반이다.
- 통근시간은 ODsay 대중교통 경로 API 어댑터가 구현되어 있지만, 이번 검증 환경에서는 API 키가 없어 기존 테이블 폴백으로 생성됐다.
- 사용자 통근 루트는 Kakao 주소 검색, ODsay, TMAP 런타임 어댑터가 구현되어 있다. 이번 검증에서는 API 키를 환경변수로 주입하지 않아 실제 외부 호출은 수행하지 않았고, 로컬 좌표/후보명 해석과 거리 기반 폴백을 검증했다.
- 채팅으로 전달된 API 키는 저장소·문서·커밋에 기록하지 않았다. 실제 live API 검증은 `KAKAO_REST_API_KEY`, `ODSAY_API_KEY`, `TMAP_APP_KEY`를 로컬 환경변수로 설정한 별도 실행에서 수행해야 한다.
- 생활 SOC는 서울 열린데이터광장 병의원·학교·공원 좌표 스냅샷 기반이다. 운영 단계에서는 API 키 기반 전체 자동 갱신과 편의시설 카테고리 확장이 필요하다.
- 안전, 환경 점수는 MVP 프록시다. 추후 안전·대기·녹지 공공데이터 어댑터를 추가해야 한다.
- 지도 타일은 OpenStreetMap 공개 타일을 사용하며, 운영 배포 시 VWorld 등으로 교체를 권장한다 (`docs/api-development.md` 참고).
- 전화번호, 서명, 개인정보 수집·이용 동의 체크는 신청자가 제출 전 직접 기재해야 한다.

## 이전 확인 (2026-06-11 데이터 구축 시)

- `python3 scripts/build_real_dataset.py` 실행 성공: `data/areas.actual.json` 9개 생활권 생성
- `deliverables/MoveValue_참가신청서_기획서_초안.docx` 재생성 및 렌더링 검수 (`qa/docx-render/page-1.png` ~ `page-4.png`)
