# MoveValue 데이터 소스 계획

MoveValue는 공모전 제출용 프로토타입부터 실제 공공데이터 스냅샷을 사용한다. 현재 구현은 서울시 2025 전월세 파일을 내려받아 생활권별 주거비 중앙값을 만들고, 생활 SOC는 병원·학교·공원 좌표를 생활권 반경으로 집계한다. 통근시간은 대중교통 경로 API 어댑터를 우선 사용하도록 설계했으며, API 키가 없는 심사 환경에서는 검증용 테이블로 자동 폴백한다.

## 현재 구현 데이터

| 구분 | 데이터 | 활용 | 구현 상태 |
| --- | --- | --- | --- |
| 주거 비용 | 서울시 부동산 전월세가 정보 2025 파일 | 월세, 보증금, 전세 중앙값 | `scripts/build_real_dataset.py`에서 다운로드·정규화 |
| 역사 좌표 | 서울시 역사마스터 정보 | 생활권 대표역 좌표 검증 | 데이터 출처 메타와 좌표 기준으로 반영 |
| 통근 시간 | ODsay 대중교통 경로 API 어댑터 + 기존 통근시간 테이블 | 추천 점수의 통근 항목 | `ODSAY_API_KEY` 또는 `MOVEVALUE_ODSAY_API_KEY` 설정 시 API 호출, 키 없거나 실패하면 테이블 폴백 |
| 사용자 통근 루트 | Kakao 주소 검색 + ODsay/TMAP 대중교통 경로 API | 사용자가 입력한 집·회사 간 실제 경로, 환승, 도보, 요금 확인 | `api/route_adapters.py` 런타임 호출. 키가 없으면 후보지·목적지명/좌표 입력과 거리 기반 폴백 |
| 생활 SOC | 서울시 병의원 위치 정보, 서울시 학교 기본정보, 서울시 주요 공원현황 좌표 스냅샷 | 반경 1.6km 병원·학교·공원 접근성 점수 | `scripts/movevalue_adapters.py`의 좌표 카탈로그를 반경 집계 |
| 안전·환경 | 환승 접근성과 생활권 성격 기반 프록시 | 안전·환경 항목 | MVP 프록시, 추후 안전·대기·녹지 데이터 결합 |

## 어댑터 구현 상태

### 통근시간 어댑터

- 구현 파일: `scripts/movevalue_adapters.py`
- 기본 동작: `ODSAY_API_KEY`가 있으면 `searchPubTransPathT` 방식의 출발지·도착지 좌표 기반 대중교통 경로 시간을 요청한다.
- 폴백: 키가 없거나 특정 목적지 호출이 실패하면 기존 생활권별 통근시간 테이블 값을 사용한다.
- 산출 필드: `commuteMinutes`, `evidence.commuteSource`, `evidence.commuteMode`, `evidence.commuteFallbackUsed`, `evidence.commuteFallbackDestinations`
- 현재 재생성 결과: 로컬 환경에 API 키가 없어 9개 생활권 모두 `table_fallback`으로 기록했다. 코드 구조는 실 API 키 투입 즉시 같은 `data/areas.actual.json` 포맷으로 갱신된다.

### 사용자 통근 루트 어댑터

- 구현 파일: `api/route_adapters.py`
- 주소 검색: `KAKAO_REST_API_KEY` 또는 `MOVEVALUE_KAKAO_REST_API_KEY`가 있으면 Kakao Local API로 주소를 좌표화한다.
- 경로 계산: `ODSAY_API_KEY` 또는 `TMAP_APP_KEY`가 있으면 실제 대중교통 경로 API를 호출한다.
- 폴백: 키가 없거나 호출 실패 시 거리 기반 추정 경로를 반환하되, 응답의 `provider=fallback`, `mode=estimated_fallback`, `notice`, `errors`로 한계를 표시한다.
- 산출 필드: `summary.totalMinutes`, `summary.transferCount`, `summary.totalWalkMeters`, `summary.fare`, `steps`, `coordinates`

### 생활 SOC 어댑터

- 구현 파일: `scripts/movevalue_adapters.py`
- 집계 반경: 생활권 대표역 좌표 기준 1,600m
- 집계 항목: 병의원, 학교, 공원
- 점수화: 카테고리별 반경 내 시설 수, 가장 가까운 시설까지의 거리, 환승 노선 수 보조치를 결합해 `serviceScore`/`socScore`로 저장한다.
- 산출 필드: `socSummary`, `evidence.socSource`, `evidence.socCounts`, `evidence.socNearestFacilities`, `evidence.socFacilityRecords`

## 우선 연계 데이터

| 구분 | 데이터 | 활용 목적 | 제공/근거 |
| --- | --- | --- | --- |
| 주거 비용 | 국토교통부 아파트 전월세 실거래가 자료 | 월세·보증금 수준, 주거비 예측 | 공공데이터포털 |
| 주거 비용 | 국토교통부 아파트 매매 실거래가 자료 | 매매가, 주거비 지표 보정 | 공공데이터포털 |
| 위치 변환 | 브이월드/국토교통부 지오코더 API | 주소-좌표 변환, 생활권 매핑 | VWorld, 공공데이터포털 |
| 교통 접근성 | 전국도시철도역사정보표준데이터 | 역 위치, 환승, 노선 접근성 | 공공데이터포털, 철도산업정보센터 |
| 교통 데이터 유통 | 국가교통 데이터 오픈마켓 | 교통 수요·이동·민간 데이터 구매/판매 연계 | 국가교통 데이터 오픈마켓 |
| 행정·정책 | 국토교통부 데이터 통합채널 | 국토교통 데이터 탐색, 정책·활용사례 확인 | 국토교통부 |

## 데이터 결합 구조

1. 실거래가 데이터를 법정동·월 단위로 수집한다.
2. 지오코더로 매물·역·생활시설 주소를 좌표화한다.
3. 도시철도 역사와 교통 데이터로 통근 목적지까지의 이동시간·환승 가능성을 산출한다. 현재는 대중교통 경로 API 어댑터와 테이블 폴백을 함께 둔다.
4. 병의원, 학교, 공원 좌표를 생활권 반경으로 집계해 생활 SOC 접근성 점수로 결합한다.
5. 사용자의 예산, 통근 목적지, 가구 유형, 접근성 우선순위에 맞춰 설명 가능한 점수를 제공한다.

## 화면 내 데이터 근거 공개

웹 서비스의 "데이터 근거" 섹션은 `GET /api/areas` 응답의 `evidence` 필드를 그대로 표로 렌더링한다. 생활권별 매칭 거래 건수(총 114,319건), 법정동 범위, 월세·보증금·전세 중앙값, 반경 1.6km 생활 SOC 집계가 화면에서 확인되며, 상세 패널에서도 선택한 생활권의 실데이터 근거를 항목별로 보여준다.

## 프로토타입 데이터 한계

`data/areas.actual.json`은 실제 전월세 파일에서 생성한 현재 프로토타입의 기본 데이터다. `data/neighborhoods.json`은 이전 화면 흐름 검증용 샘플로만 남겨두며, 추천 웹앱과 API는 `areas.actual.json`을 우선 사용한다.

현재 한계는 기본 추천 데이터의 통근시간이 API 키 미설정 환경에서 테이블 폴백으로 생성된다는 점, 사용자 통근 루트가 키 없을 때 거리 기반 폴백이라는 점, 안전·환경 점수가 MVP 프록시라는 점이다. 이 한계는 웹 화면(데이터 근거 섹션, 점수 보조 문구, 통근 루트 결과 notice)에도 동일하게 고지한다. 배포 단계에서는 경로 API 키 운영, 호출 캐시, 혼잡도·첫차·막차, 안전·대기·녹지 공공데이터 어댑터를 추가한다.

## 참고 URL

- 국토교통부 아파트 전월세 실거래가: https://www.data.go.kr/data/15126474/openapi.do
- 국토교통부 아파트 매매 실거래가: https://www.data.go.kr/data/15126469/openapi.do
- VWorld Geocoder API: https://www.vworld.kr/dev/v4dv_geocoderguide2_s001.do
- 전국도시철도역사정보표준데이터: https://www.data.go.kr/data/15013205/standard.do
- 국가교통 데이터 오픈마켓: https://www.bigdata-transportation.kr/
- 국토교통부 데이터 통합채널: https://data.molit.go.kr/
- 서울시 부동산 전월세가 정보: https://data.seoul.go.kr/dataList/OA-21276/S/1/datasetView.do
- 서울시 역사마스터 정보: https://data.seoul.go.kr/dataList/OA-21232/S/1/datasetView.do
- ODsay 대중교통 길찾기 API 가이드: https://lab.odsay.com/guide/guide
- TMAP 대중교통 API: https://openapi.sk.com/products/detail?menuSeq=492&svcSeq=59
- Kakao Local 주소 검색 API: https://developers.kakao.com/docs/latest/ko/local/dev-guide#address-coord
- 서울시 병의원 위치 정보: https://data.seoul.go.kr/dataList/OA-20337/S/1/datasetView.do
- 서울시 학교 기본정보: https://data.seoul.go.kr/dataList/OA-20502/S/1/datasetView.do
- 서울시 주요 공원현황: https://data.seoul.go.kr/dataList/OA-394/S/1/datasetView.do
