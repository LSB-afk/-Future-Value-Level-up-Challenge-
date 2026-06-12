# MoveValue 데이터 소스 계획

MoveValue는 공모전 제출용 프로토타입부터 실제 공공데이터 스냅샷을 사용한다. 현재 구현은 서울시 2025 전월세 파일을 내려받아 생활권별 주거비 중앙값과 표시용 실거래 예시를 만들고, 생활 SOC는 병원·학교·공원 좌표를 생활권 반경으로 집계한다. 안전·환경은 치안시설·CCTV 집계점·도시대기 측정망·공원 접근성을 결합한다. 통근시간은 대중교통 경로 API 어댑터를 우선 사용하도록 설계했으며, API 키가 없는 심사 환경에서는 검증용 테이블로 자동 폴백한다.

## 현재 구현 데이터

| 구분 | 데이터 | 활용 | 구현 상태 |
| --- | --- | --- | --- |
| 주거 비용 | 서울시 부동산 전월세가 정보 2025 파일 | 월세, 보증금, 전세 중앙값, 후보 매물/전월세 예시 | `scripts/build_real_dataset.py`에서 다운로드·정규화. 상세 지번·건물명 제외 |
| 아파트 단지 | 서울시 공동주택 아파트 정보 `OpenAptInfo` | 지도 위 아파트 단지 위치, 세대수, 동수, 사용승인일, 주차대수 표시 | `api/apartment_adapters.py`와 `/api/apartments` 구현. `SEOUL_OPEN_API_KEY`가 있으면 전체 단지 live 호출, 없으면 sample 제한 스냅샷 폴백 |
| 부동산 가격 | 국토교통부 아파트 매매·전월세 실거래가 API | 단지 상세 클릭 시 최근 매매가·전세가·월세 live 보정 | `api/real_estate_price_adapters.py` 구현. 공공데이터포털 키가 있으면 법정동 코드+계약년월로 조회, 키/매칭 없으면 생활권 기반 추정 폴백 |
| 역사 좌표 | 서울시 역사마스터 정보 | 생활권 대표역 좌표 검증 | 데이터 출처 메타와 좌표 기준으로 반영 |
| 통근 시간 | ODsay 대중교통 경로 API 어댑터 + 기존 통근시간 테이블 | 추천 점수의 통근 항목 | `ODSAY_API_KEY` 또는 `MOVEVALUE_ODSAY_API_KEY` 설정 시 API 호출, 키 없거나 실패하면 테이블 폴백 |
| 사용자 통근 루트 | Kakao 주소 검색 + ODsay/TMAP 대중교통 경로 API | 사용자가 입력한 집·회사 간 실제 경로, 환승, 도보, 요금 확인 | `api/route_adapters.py` 런타임 호출. 키가 없으면 후보지·목적지명/좌표 입력과 거리 기반 폴백 |
| 생활 SOC | 서울시 병의원 위치 정보, 서울시 학교 기본정보, 서울시 주요 공원현황 좌표 스냅샷 | 반경 1.6km 병원·학교·공원 접근성 점수 | `scripts/movevalue_adapters.py`의 좌표 카탈로그를 반경 집계 |
| 안전·환경 | 치안시설, CCTV 집계점, 도시대기 측정망, 공원 좌표 스냅샷 | 안전·환경 항목 | `scripts/movevalue_adapters.py`의 스냅샷 점수 어댑터 |

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

### 매물 단위 전월세 예시

- 구현 파일: `scripts/build_real_dataset.py`
- 원천: 서울시 2025 부동산 전월세가 정보 CSV
- 추출 기준: 생활권 법정동별 15~85㎡ 거래 중 월세 중앙값에 가까운 월세 예시 3건과 전세 중앙값에 가까운 전세 예시 1건
- 개인정보·상세 위치 보호: 지번, 본번·부번, 건물명은 제외하고 계약월, 법정동, 전월세 구분, 면적, 보증금, 월세, 건물용도, 층만 저장
- 산출 필드: `rentExamples`, `evidence.rentExampleCount`, `evidence.rentExamplePrivacy`

### 서울 아파트 단지 지도 레이어

- 구현 파일: `api/apartment_adapters.py`, `scripts/build_apartment_snapshot.py`
- 원천: 서울 열린데이터광장 `서울시 공동주택 아파트 정보` (`OpenAptInfo`)
- API 키: `SEOUL_OPEN_API_KEY`, `SEOUL_API_KEY`, `MOVEVALUE_SEOUL_OPEN_API_KEY` 중 하나를 환경변수로 설정한다.
- 런타임 동작: 키가 있으면 `/api/apartments`가 공식 API를 호출해 전체 단지를 정규화하고 메모리 캐시한다. 키가 없거나 호출 실패 시 `data/apartments.seoul.snapshot.json`으로 폴백한다.
- 현재 저장소 스냅샷: 공식 sample 키는 1~5행 미리보기만 허용하므로 2,876건 중 좌표가 있는 5건만 포함한다. 즉, 현재 커밋 상태는 전체 단지를 표시할 수 있는 구조 검증용이고, 전체 표시에는 서울 열린데이터광장 인증키가 필요하다.
- 산출 필드: `id`, `name`, `address`, `district`, `dong`, `lat`, `lng`, `households`, `buildingCount`, `approvalDate`, `housingType`, `heating`, `parkingCount`
- 지도 응답: `/api/apartments?bounds=south,west,north,east&zoom=11&cluster=true`는 현재 지도 화면 안의 단지 또는 클러스터를 반환한다.

### 부동산 상세 대시보드

- 구현 파일: `api/property_model.py`, `api/property_adapters.py`, `api/real_estate_price_adapters.py`, `app/app.js`
- 원천 실데이터: 서울시 공동주택 아파트 정보의 단지 기본 정보와 서울시 2025 전월세 실거래 생활권 집계
- live 보정 실데이터: 국토교통부 아파트 매매 실거래가 상세 자료와 아파트 전월세 실거래가 자료. `MOLIT_SERVICE_KEY`, `MOLIT_APT_TRADE_KEY`, `MOLIT_APT_RENT_KEY`, `PUBLIC_DATA_API_KEY` 중 키가 있으면 법정동 코드와 계약년월로 최근 9개월을 조회하고 단지명 매칭 기록을 가격에 반영한다.
- 연계 예정 실데이터: 공동주택 공시가격, 건축물대장, VWorld 지오코더/용도지역. 공시가격은 키 감지까지 구현했고, 값 보정은 PNU/공시가격 식별자 매핑 후 진행한다.
- 지도 표시: `/api/apartments`의 `features[].pricePreview`가 단지별 추정 매매가, 전세가율, 위험 신호 등급, 목적지 기준 통근시간을 포함한다. 화면에서는 라벨을 매매가·전세가율·위험도·통근시간으로 바꿔 볼 수 있다.
- 상세 응답: `/api/property-detail?id=A15275101`이 기본 정보, 가격 정보, 가격 API 연계 상태, 12개월 거래 추이, 전세 위험 신호, 계약 전 확인 체크리스트, 생활권 정보, SOC 반경, AI 요약, 데이터 연계 상태를 반환한다.
- AI Agent: `/api/property-agent?id=A15275101&question=...`이 전세 안전성, 추천 이유, 더 안전한 비교 후보 질문에 답하고 `가격 근거 / 통근 근거 / 위험 근거 / 생활권 근거 / 확인 필요 서류`로 근거를 구조화한다.
- 데이터 고지: 매매·전월세 live API 키가 없거나 단지명 매칭 기록이 없으면 생활권 전월세 집계 기반 추정값으로 생성한다. 화면의 `가격 API 연계 상태`와 `데이터 연계 상태`에서 실데이터/live/추정/연계 예정 여부를 구분한다.
- 위험 신호: 전세가율, 공시가격 대비 보증금, 주변 전세 중앙값 대비, 변동성, 건축물 노후도, 등기부 권리관계 미입력 여부를 점수화하고 등기부·보증보험·체납·신탁·위반건축물·전입/확정일자 확인 항목을 제공하되 법적 판정으로 표현하지 않는다.

### live API 검증 스크립트

- 구현 파일: `scripts/verify_live_integrations.py`
- 확인 범위: Kakao 주소 검색, ODsay/TMAP 통근 경로, 서울 OpenAptInfo 전체 단지, 국토교통부 매매·전월세 실거래가 live 보정
- 출력 원칙: 환경변수 설정 여부와 `mode=live_api`/폴백 상태만 표시하며 API 키 값은 출력하지 않는다.
- 실행 예시:

```bash
KAKAO_REST_API_KEY=... ODSAY_API_KEY=... TMAP_APP_KEY=... SEOUL_OPEN_API_KEY=... MOLIT_SERVICE_KEY=... \
  python3 scripts/verify_live_integrations.py
```

### 안전·환경 어댑터

- 구현 파일: `scripts/movevalue_adapters.py`
- 집계 반경: 생활권 대표역 좌표 기준 1,800m
- 집계 항목: 치안시설, CCTV 집계점, 공원 접근성, 자치구 도시대기 측정망 프로필
- 점수화: 반경 내 치안시설 수, CCTV 집계 대수, 가장 가까운 공원 거리, 자치구 대기·녹지 프로필을 결합해 `safetyScore`와 `carbonScore`를 산출한다.
- 산출 필드: `safetyEnvSummary`, `evidence.safetyEnvSource`, `evidence.safetyEnvCounts`, `evidence.safetyEnvNearestFacilities`, `evidence.airStation`

## 우선 연계 데이터

| 구분 | 데이터 | 활용 목적 | 제공/근거 |
| --- | --- | --- | --- |
| 주거 비용 | 국토교통부 아파트 전월세 실거래가 자료 | 월세·보증금 수준, 주거비 예측 | 공공데이터포털 |
| 주거 비용 | 국토교통부 아파트 매매 실거래가 상세 자료 | 매매가, 주거비 지표 보정 | 공공데이터포털 |
| 위치 변환 | 브이월드/국토교통부 지오코더 API | 주소-좌표 변환, 생활권 매핑 | VWorld, 공공데이터포털 |
| 교통 접근성 | 전국도시철도역사정보표준데이터 | 역 위치, 환승, 노선 접근성 | 공공데이터포털, 철도산업정보센터 |
| 교통 데이터 유통 | 국가교통 데이터 오픈마켓 | 교통 수요·이동·민간 데이터 구매/판매 연계 | 국가교통 데이터 오픈마켓 |
| 행정·정책 | 국토교통부 데이터 통합채널 | 국토교통 데이터 탐색, 정책·활용사례 확인 | 국토교통부 |

## 데이터 결합 구조

1. 실거래가 데이터를 법정동·월 단위로 수집한다.
2. 지오코더로 매물·역·생활시설 주소를 좌표화한다.
3. 도시철도 역사와 교통 데이터로 통근 목적지까지의 이동시간·환승 가능성을 산출한다. 현재는 대중교통 경로 API 어댑터와 테이블 폴백을 함께 둔다.
4. 병의원, 학교, 공원 좌표를 생활권 반경으로 집계해 생활 SOC 접근성 점수로 결합한다.
5. 치안시설, CCTV 집계점, 도시대기 측정망, 공원 접근성을 결합해 안전·환경 점수를 만든다.
6. 서울시 공동주택 아파트 단지 좌표를 지도 레이어로 겹쳐 생활권 추천 결과 주변의 실제 주거 후보 밀도를 확인한다.
7. 사용자가 단지를 클릭하면 공개 단지정보, 생활권 전월세 집계, 선택적으로 국토교통부 실거래가 live 보정 결과를 결합해 상세 대시보드와 전세 위험 신호 점검 결과를 보여준다.
8. 사용자의 예산, 통근 목적지, 가구 유형, 접근성 우선순위에 맞춰 설명 가능한 점수를 제공한다.

## 화면 내 데이터 근거 공개

웹 서비스의 "데이터 근거" 섹션은 `GET /api/areas` 응답의 `evidence` 필드를 그대로 표로 렌더링한다. 생활권별 매칭 거래 건수(총 114,319건), 법정동 범위, 월세·보증금·전세 중앙값, 반경 1.6km 생활 SOC 집계, 반경 1.8km 안전환경 집계가 화면에서 확인되며, 상세 패널에서도 선택한 생활권의 실거래 예시와 데이터 근거를 항목별로 보여준다.

## 프로토타입 데이터 한계

`data/areas.actual.json`은 실제 전월세 파일에서 생성한 현재 프로토타입의 기본 데이터다. `data/neighborhoods.json`은 이전 화면 흐름 검증용 샘플로만 남겨두며, 추천 웹앱과 API는 `areas.actual.json`을 우선 사용한다.

현재 한계는 기본 추천 데이터의 통근시간이 API 키 미설정 환경에서 테이블 폴백으로 생성된다는 점, 사용자 통근 루트가 키 없을 때 거리 기반 폴백이라는 점, 안전·환경이 자동 원천 API 갱신이 아닌 스냅샷 점수라는 점이다. 아파트 단지 레이어도 키 없는 커밋 상태에서는 sample 제한 때문에 5건 미리보기만 포함한다. 부동산 상세 가격은 국토교통부 매매·전월세 live 어댑터가 구현됐지만, 키가 없거나 단지명 매칭이 없으면 추정값을 유지한다. 공동주택 공시가격은 PNU/식별자 매핑 전이라 아직 live 값 보정 대상이 아니다. 이 한계는 웹 화면(데이터 근거 섹션, 점수 보조 문구, 통근 루트 결과 notice, 지도 레이어 상태 배지, 가격 API 연계 상태)에도 동일하게 고지한다. 배포 단계에서는 경로 API 키 운영, 호출 캐시, 혼잡도·첫차·막차, 안전·대기·녹지 전체 원천 API 자동 갱신, 서울 전체 공동주택 단지 갱신 배치, 공시가격·건축물대장 매핑을 추가한다.

## 참고 URL

- 국토교통부 아파트 전월세 실거래가: https://www.data.go.kr/data/15126474/openapi.do
- 국토교통부 아파트 매매 실거래가 상세 자료: https://www.data.go.kr/data/15126468/openapi.do?recommendDataYn=Y
- VWorld Geocoder API: https://www.vworld.kr/dev/v4dv_geocoderguide2_s001.do
- 전국도시철도역사정보표준데이터: https://www.data.go.kr/data/15013205/standard.do
- 국가교통 데이터 오픈마켓: https://www.bigdata-transportation.kr/
- 국토교통부 데이터 통합채널: https://data.molit.go.kr/
- 서울시 부동산 전월세가 정보: https://data.seoul.go.kr/dataList/OA-21276/S/1/datasetView.do
- 서울시 공동주택 아파트 정보: https://data.seoul.go.kr/dataList/OA-15818/S/1/datasetView.do
- 서울시 역사마스터 정보: https://data.seoul.go.kr/dataList/OA-21232/S/1/datasetView.do
- ODsay 대중교통 길찾기 API 가이드: https://lab.odsay.com/guide/guide
- TMAP 대중교통 API: https://openapi.sk.com/products/detail?menuSeq=492&svcSeq=59
- Kakao Local 주소 검색 API: https://developers.kakao.com/docs/latest/ko/local/dev-guide#address-coord
- 서울시 병의원 위치 정보: https://data.seoul.go.kr/dataList/OA-20337/S/1/datasetView.do
- 서울시 학교 기본정보: https://data.seoul.go.kr/dataList/OA-20502/S/1/datasetView.do
- 서울시 주요 공원현황: https://data.seoul.go.kr/dataList/OA-394/S/1/datasetView.do
