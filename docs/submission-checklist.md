# 제출 전 수정 필요 체크리스트

## 사람 확인 필요

- 참가신청서의 신청자 연락처, 주소, 서명, 개인정보 수집·이용 동의 체크
- 실제 제출일과 신청인 서명일 기입
- 협력기업을 실제로 기재할 경우 담당자 동의와 연락처 확인
- 공모전 제출 파일명과 PDF 변환본 확인

## 기술 검증 필요

- `KAKAO_REST_API_KEY`로 상세 주소 검색 live 검증
- `ODSAY_API_KEY` 또는 `TMAP_APP_KEY`로 실제 대중교통 경로 live 검증
- `SEOUL_OPEN_API_KEY`로 서울 OpenAptInfo 전체 단지 로딩 검증
- `MOLIT_SERVICE_KEY`로 국토교통부 매매/전월세 실거래가 단지명 매칭 검증
- 공동주택 공시가격 PNU/호별 식별자 매핑 설계 확정
- 건축물대장 API로 층수, 용도, 위반건축물 여부 연계 검토

## 문서 표현 주의

- 구현되지 않은 기능은 `구현 예정` 또는 `확장 예정`으로 표기
- 전세 위험 신호는 법적 판정처럼 표현하지 않기
- API 키는 문서와 코드에 직접 쓰지 않기
- 원천 대용량 데이터는 `data/raw/`에만 두고 Git에 커밋하지 않기
- 네이버부동산, 호갱노노 등 민간 서비스는 UX 참고로만 언급하고 스크래핑하지 않았음을 명시

## 제출자료 패키지

- `deliverables/MoveValue_참가신청서_보강본.docx`
- `deliverables/screenshots/*.png`
- `docs/github-latest-analysis.md`
- `docs/system-flow-summary.md`
- `docs/mermaid-diagrams.md`
- `docs/submission-screenshots.md`
- `docs/data-sources.md`
