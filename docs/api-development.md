# MoveValue API 개발 메모

## 현재 구현

MoveValue는 웹 화면과 추천 계산 API를 같은 Python 서버에서 제공한다. 외부 패키지 없이 실행되므로 공모전 심사·데모 환경에서 재현성이 높다.

```bash
python3 api/movevalue_api.py --port 5173
```

접속 URL은 `http://127.0.0.1:5173/`이다.

실제 주소 검색과 대중교통 경로는 서버 환경변수로 API 키를 주입한다. 키는 코드, 문서, 커밋에 저장하지 않는다.

```bash
export KAKAO_REST_API_KEY="카카오 REST API 키"
export ODSAY_API_KEY="ODsay API 키"
export TMAP_APP_KEY="TMAP appKey"
export SEOUL_OPEN_API_KEY="서울 열린데이터광장 인증키"
python3 api/movevalue_api.py --port 5173
```

## 데이터 파이프라인

`scripts/build_real_dataset.py`는 서울시 열린데이터광장의 `서울시 부동산 전월세가 정보` 2025년 파일을 내려받고, 15~85㎡ 거래를 생활권 법정동 기준으로 집계한다. 통근시간, 생활 SOC, 안전·환경은 `scripts/movevalue_adapters.py`의 어댑터가 채운다.

```bash
python3 scripts/build_real_dataset.py
```

산출물은 `data/areas.actual.json`이며, 원천 ZIP은 `data/raw/`에 보관한다. `data/raw/`는 용량과 원천 데이터 재배포 이슈를 줄이기 위해 Git에서 제외한다.

통근시간은 `ODSAY_API_KEY` 또는 `MOVEVALUE_ODSAY_API_KEY`가 설정되어 있으면 대중교통 경로 API를 호출하고, 키가 없거나 호출이 실패한 목적지는 기존 검증 테이블로 폴백한다.

```bash
ODSAY_API_KEY=발급키 python3 scripts/build_real_dataset.py
```

생활 SOC는 병의원·학교·공원 좌표 스냅샷을 생활권 대표역 기준 반경 1.6km로 집계해 `serviceScore`, `socSummary`, `evidence.socCounts`에 저장한다. 안전·환경은 치안시설·CCTV 집계점·도시대기 측정망·공원 접근성을 반경 1.8km 기준으로 결합해 `safetyScore`, `carbonScore`, `safetyEnvSummary`, `evidence.safetyEnvCounts`에 저장한다.

주거 데이터는 생활권별 중앙값뿐 아니라 `rentExamples`도 만든다. 각 생활권은 월세 중앙값에 가까운 월세 예시 3건과 전세 중앙값에 가까운 전세 예시 1건을 포함하며, 상세 지번·건물명 없이 계약월·법정동·면적·보증금·월세·건물용도·층만 제공한다.

웹 실행 중 사용자가 입력하는 집/회사 경로 검증은 `api/route_adapters.py`가 담당한다. 이 런타임 어댑터는 Kakao 주소 검색, ODsay 대중교통 경로, TMAP 대중교통 경로, 거리 기반 폴백을 같은 응답 형식으로 정규화한다.

서울 아파트 단지 지도 레이어는 `api/apartment_adapters.py`가 담당한다. `SEOUL_OPEN_API_KEY`가 있으면 서울 열린데이터광장 `OpenAptInfo` 전체 단지를 live API로 불러오고, 키가 없거나 호출에 실패하면 `data/apartments.seoul.snapshot.json`으로 폴백한다. 현재 커밋된 스냅샷은 sample 키 제한으로 2,876건 중 5건 미리보기만 포함한다.

```bash
SEOUL_OPEN_API_KEY=발급키 python3 scripts/build_apartment_snapshot.py
```

부동산 상세 대시보드는 `api/property_model.py`와 `api/property_adapters.py`가 담당한다. OpenAptInfo 실데이터 필드와 서울시 2025 전월세 생활권 집계를 결합해 단지 상세, 가격 추정, 전세 위험 신호, AI 요약을 생성한다. 매매 실거래가·공시가격은 국토교통부/공동주택 공시가격 API 키 연계 전까지 `dataStatus`에 추정으로 표시한다.

## 엔드포인트

### `GET /api/health`

데이터 파일 로딩 상태, 후보 생활권 수, 경로·주소·서울 열린데이터 API 키 설정 여부를 확인한다. 키 값은 반환하지 않고 `true/false`만 반환한다.

### `GET /api/areas`

정규화된 생활권 후보 전체를 반환한다. 웹앱은 초기 지도 범위와 데이터 출처 표시를 위해 이 엔드포인트를 먼저 호출한다.

주요 추가 필드:

| 필드 | 설명 |
| --- | --- |
| `rentExamples` | 생활권 안의 실제 전월세 공개파일 기반 후보 거래 예시 |
| `socSummary` | 병원·학교·공원 반경 집계 |
| `safetyEnvSummary` | 치안시설·CCTV·대기측정망·공원 접근성 집계 |
| `representativeAddress` | 통근 루트 검증 기본값으로 쓰는 생활권 대표 주소 |

### `GET /api/recommendations`

사용자 조건을 기반으로 생활권 추천 랭킹을 반환한다.

쿼리 파라미터:

| 이름 | 예시 | 설명 |
| --- | --- | --- |
| `budget` | `70` | 월 주거 예산, 만원 단위 |
| `destination` | `gangnam` | 주요 목적지. `gangnam`, `yeouido`, `seoulStation`, `digital`, `pangyo` 지원 |
| `persona` | `single` | 가구 유형. `single`, `commuter`, `newlywed`, `senior` 지원 |
| `commuteWeight` | `35` | 통근 점수 가중치 |
| `costWeight` | `30` | 주거비 점수 가중치 |
| `serviceWeight` | `20` | 생활 SOC 점수 가중치 |
| `safetyWeight` | `15` | 안전·환경 점수 가중치 |
| `limit` | `9` | 반환 개수 (기본 8, 웹앱은 지도 마커 9개를 위해 9 요청) |

예시:

```bash
curl 'http://127.0.0.1:5173/api/recommendations?budget=70&destination=gangnam&persona=single&commuteWeight=35&costWeight=30&serviceWeight=20&safetyWeight=15&limit=9'
```

응답의 각 결과에는 `reasonText`가 포함된다. 예: `강남 업무지구까지 24분, 월세 중앙값 57만원, 병원 2개·학교 3개·공원 2개, 치안시설 2개·CCTV 62대 근거로 1인 청년에게 예산 내 생활권입니다.`

### `GET /api/geocode`

주소, 후보 생활권명, 목적지명, 직접 좌표 입력을 좌표 객체로 변환한다. 웹앱 기본값으로 쓰는 생활권 대표 주소와 주요 목적지 주소는 API 키 없이 로컬 좌표로 매칭된다.

쿼리 파라미터:

| 이름 | 예시 | 설명 |
| --- | --- | --- |
| `query` | `서울 광진구 화양동` | 후보 생활권명, 역명, 목적지명, 대표 주소, 상세 주소, 또는 `37.5405,127.0692` 좌표 |

동작:

- 후보 생활권명·역명·목적지명·대표 주소는 로컬 데이터에서 즉시 매칭한다.
- 좌표 문자열은 API 키 없이 파싱한다.
- 사용자가 입력한 상세 주소는 `KAKAO_REST_API_KEY` 또는 `MOVEVALUE_KAKAO_REST_API_KEY`가 있을 때 Kakao Local API로 변환한다.

예시:

```bash
curl 'http://127.0.0.1:5173/api/geocode?query=서울%20광진구%20화양동'
```

### `GET /api/commute-route`

집 위치와 회사 위치를 받아 통근 경로를 계산한다. `provider=auto`이면 ODsay를 먼저 시도하고 실패하면 TMAP을 시도한다. 둘 다 사용할 수 없으면 거리 기반 추정 폴백을 반환한다.

쿼리 파라미터:

| 이름 | 예시 | 설명 |
| --- | --- | --- |
| `origin` | `서울 광진구 화양동` | 집 위치. 주소, 후보 생활권명, 역명, 좌표 가능 |
| `destination` | `gangnam` | 기본 목적지 ID. `gangnam`, `yeouido`, `seoulStation`, `digital`, `pangyo` 지원 |
| `destinationQuery` | `서울 강남구 테헤란로 ...` | 회사 주소 또는 좌표. 있으면 기본 목적지 대신 사용 |
| `provider` | `auto` | `auto`, `odsay`, `tmap` |

응답 핵심 필드:

| 필드 | 설명 |
| --- | --- |
| `provider` | 실제 사용된 제공자. `odsay`, `tmap`, `fallback` |
| `mode` | `live_api` 또는 `estimated_fallback` |
| `summary.totalMinutes` | 총 소요시간 |
| `summary.transferCount` | 환승 횟수 |
| `summary.totalWalkMeters` | 총 도보 거리 |
| `summary.fare` | 예상 요금 |
| `steps` | 도보·버스·지하철 등 단계별 이동 요약 |
| `coordinates` | 지도 경로선 표시용 좌표 |

예시:

```bash
curl 'http://127.0.0.1:5173/api/commute-route?origin=서울%20광진구%20화양동&destinationQuery=서울%20강남구%20역삼동&provider=auto'
```

### `GET /api/apartments`

서울시 공동주택 아파트 정보 기반 지도 레이어를 반환한다. 지도 화면은 현재 지도 bounds와 zoom을 넘겨 받아 단지 개별 마커 또는 클러스터 마커를 렌더링한다.

쿼리 파라미터:

| 이름 | 예시 | 설명 |
| --- | --- | --- |
| `bounds` | `37.45,126.80,37.70,127.18` | `south,west,north,east` 순서의 지도 화면 범위 |
| `zoom` | `11` | Leaflet 현재 줌. 낮은 줌에서는 클러스터링 |
| `cluster` | `true` | `false`이면 개별 단지만 반환 |
| `limit` | `5000` | 반환 전 필터링 최대 건수 |
| `district` | `송파구` | 선택 자치구만 필터링 |
| `q` | `파인타운` | 단지명·주소·동 검색 |

응답 핵심 필드:

| 필드 | 설명 |
| --- | --- |
| `meta.sourceMode` | `live_api`, `snapshot`, `snapshot_fallback` |
| `meta.complete` | 전체 데이터 여부. 현재 sample 스냅샷은 `false` |
| `meta.totalRecords` | 공식 API가 알려준 총 단지 수 |
| `meta.availableRecords` | 현재 서버가 좌표와 함께 보유한 단지 수 |
| `features[].type` | `apartment` 또는 `cluster` |
| `features[].households` | 단지 또는 클러스터 총 세대수 |
| `features[].pricePreview` | 지도 가격 라벨용 추정 매매가, 전세가율, 위험 신호 등급 |

예시:

```bash
curl 'http://127.0.0.1:5173/api/apartments?bounds=37.45,126.80,37.70,127.18&zoom=11&cluster=true'
```

### `GET /api/property-detail`

지도에서 선택한 단지의 상세 대시보드 데이터를 반환한다.

쿼리 파라미터:

| 이름 | 예시 | 설명 |
| --- | --- | --- |
| `id` | `A15275101` | OpenAptInfo 단지 ID |
| `q` | `개봉건영` | 단지명·주소 검색. `id`가 없을 때 사용 |

응답 핵심 필드:

| 필드 | 설명 |
| --- | --- |
| `detail.name`, `detail.address` | 단지명과 주소 |
| `detail.approvalYear`, `detail.households`, `detail.areaOptions` | 사용승인연도, 세대수, 면적 옵션 |
| `detail.price` | 최근 매매가·전세가·월세·공시가격·주변 평균·전세가율 |
| `detail.transactions` | 최근 12개월 매매/전세 추이 |
| `detail.risk` | 전세 위험 신호 점수, 등급, 항목별 근거 |
| `detail.lifestyle` | 생활권 교통/SOC/안전/환경 정보 |
| `detail.aiSummary` | 장점, 단점, 주의사항, 추천 여부 |
| `detail.dataStatus` | 실데이터, 추정, 연계 예정 필드 구분 |

예시:

```bash
curl 'http://127.0.0.1:5173/api/property-detail?id=A15275101'
```

### `GET /api/property-agent`

선택 단지와 질문을 받아 데이터 근거 기반 답변을 반환한다. 외부 LLM 호출 없이 프로토타입 내부 규칙으로 전세 안전성, 추천 이유, 더 안전한 비교 후보를 설명한다.

쿼리 파라미터:

| 이름 | 예시 | 설명 |
| --- | --- | --- |
| `id` | `A15275101` | OpenAptInfo 단지 ID |
| `question` | `비슷한 가격대의 더 안전한 지역을 찾아줘` | 사용자 질문 |

예시:

```bash
curl 'http://127.0.0.1:5173/api/property-agent?id=A15275101&question=비슷한%20가격대의%20더%20안전한%20지역을%20찾아줘'
```

응답은 `agent.answer`, `agent.basis`, `agent.suggestedComparisons`, `agent.disclaimer`를 포함한다. 전세 위험 신호 결과는 법적 판정이 아니라 계약 전 확인 체크리스트로 표현한다.

## 지도 구현과 제공자 교체

웹앱 지도는 API 키가 필요 없는 **Leaflet 1.9.4 + OpenStreetMap 타일**을 사용한다. 구현 위치는 `app/app.js`의 `initializeLeafletMap()`이며, 타일 레이어 한 줄만 바꾸면 다른 제공자로 교체할 수 있다. 서울 아파트 단지 레이어는 별도 `apartmentLayer`에 그려지므로, 지도 제공자를 바꿔도 `/api/apartments` 응답 구조는 유지할 수 있다.

- **VWorld**: `L.tileLayer("https://api.vworld.kr/req/wmts/1.0.0/{API_KEY}/Base/{z}/{y}/{x}.png")` — 국토교통부 제공, 발급 키 필요. 공공 서비스 신뢰도 측면에서 1순위 교체 후보.
- **카카오/네이버 지도**: 자체 JS SDK를 사용하므로 Leaflet 마커 로직을 SDK 마커 API로 옮겨야 한다. `renderLeafletMap()`의 마커 데이터(좌표·점수·선택 상태)는 그대로 재사용 가능하다.
- 타일 로딩이 실패하거나 Leaflet 스크립트가 차단된 환경에서는 좌표 비례 분포도 폴백(`renderFallbackMap()`)이 자동으로 동작한다.

API 키가 필요한 제공자는 키를 코드에 하드코딩하지 않고 환경 변수 또는 서버 측 프록시로 주입한다.

## 확장 방향

- 교통: 현재는 ODsay/TMAP 경로 API 어댑터와 집-회사 통근 루트 검증 UI를 구현했다. API 키가 없으면 주요 업무지구별 통근시간 테이블 또는 거리 기반 폴백으로 동작한다. 배포 단계에서는 키 운영, 호출 캐시, 혼잡도, 첫차·막차, GTFS 기반 라우팅 옵션을 추가한다.
- 생활 SOC: 현재는 병의원·학교·공원 좌표 스냅샷 반경 집계다. 다음 단계에서는 서울 열린데이터광장 API 키 기반 전체 자동 갱신과 편의시설 카테고리 확장을 추가한다.
- 안전·환경: 현재는 치안시설·CCTV 집계점·도시대기 측정망·공원 접근성 스냅샷 기반이다. 다음 단계에서는 원천 API 자동 갱신, 행정동 전체 커버리지, 범죄안전지수·녹지율 보정치를 추가한다.
- 주거: 현재는 서울시 2025 전월세 파일 기반 중앙값과 후보 거래 예시를 제공한다. 다음 단계에서는 월별 증분 갱신과 국토교통부 실거래가 API를 병행한다.
- 주거 지도 레이어: 현재는 서울시 공동주택 아파트 정보 단지 좌표를 표시한다. `SEOUL_OPEN_API_KEY`가 없으면 sample 제한 스냅샷으로 동작하며, 운영 단계에서는 전체 단지 갱신 배치와 건축물대장·공간데이터 기반 건물 폴리곤 타일을 검토한다.
- 클라이언트: iOS Swift 앱은 `/api/areas`와 `/api/recommendations`를 그대로 소비하는 구조로 확장한다.
- 수익화: 부동산·교통 플랫폼에는 추천 점수 API, 지자체에는 생활권 취약지 리포트 API로 제공한다.
