# 나침반 — 재외한인 아침 브리핑 파이프라인

매일 새벽, 재외한인에게 필요한 뉴스를 **수집 → 요약·해석 → 이중 팩트체크 → 발행**
하는 자동화 파이프라인 + 데이터 연동형 사이트.

## 구성

```
config.py            지역/카테고리/모델/발행규칙 (한 곳에서 관리)
schema.py            단계 간 데이터 구조(pydantic)
pipeline/
  collect.py         ① 수집 + ② 선별   — 📰 취재 기자 (웹 검색)
  draft.py           ③ 요약·해석        — ⚖️ 법률 해설가
  factcheck.py       ④⑤ 이중 팩트체크   — 🔎 A + 🔎 B (독립: 다른 모델)
  gate.py            ⑥ 발행/보류 판정
  publish.py         ⑦ 사이트 생성 + 아카이브 적재
  run.py             오케스트레이터(CLI)
  llm.py             Claude 호출 헬퍼(공식 SDK)
site/
  template.html      데이터 연동형 셸(<!--FEED--> / <!--ARCHIVE--> 치환)
  index.html         생성물(발행 결과)
data/
  sample_raw.json    오프라인 데모용 하루치 뉴스(2026-07-25)
  issue-XXXX.json    호별 데이터(발행분·보류분·검증 로그)
  index.json         아카이브 인덱스(누적)
```

## 빠른 시작

```bash
pip install -r requirements.txt

# 1) API 없이: 샘플로 전체 흐름 재현 → site/index.html 생성
python -m pipeline.run --mock

# 2) 실제: 웹 검색으로 수집하고 이중 팩트체크까지 (ANTHROPIC_API_KEY 필요)
python -m pipeline.run
python -m pipeline.run --regions de kr --date 2026-07-25 --number 6
```

생성된 `site/index.html` 을 브라우저로 열면 됩니다. (상단 Today / Archive / Community)

## 이중 팩트체크 (핵심)

- **팩트체커 A**(opus)와 **팩트체커 B**(sonnet — *일부러 다른 모델*)가 **독립적으로**
  원문을 대조합니다. 같은 실수를 공유하지 않게 하려는 설계입니다.
- **발행 조건**: A·B 모두 PASS + 각자 확신도 ≥ `MIN_CONFIDENCE` + 출처 ≥ `MIN_SOURCES`.
- 하나라도 어긋나면 **HOLD** → 사람(편집장) 검토 큐(`issue-XXXX.json` 의 `held`)로.
- 모든 판정은 호 데이터에 감사 로그로 남습니다.

## 매일 자동 실행

크론/스케줄러에서 매일 06:00 실행 →

```bash
0 6 * * *  cd /path/to/nachimban && python -m pipeline.run >> run.log 2>&1
```

발행(사이트 갱신)과 07:00 이메일/푸시 발송은 호스팅·메일 연동이 필요합니다
(별도 단계).

## 주의

- AI 요약은 **초안**입니다. 법률·복지 뉴스라 실발행 전 **사람 팩트체커의 최종 확인**을
  권장합니다(파이프라인이 HOLD로 걸러도 마지막 승인은 사람).
- `site/template.html` 에는 데모용 흑백 이미지가 base64로 내장돼 있습니다.
  실제 운영 시 라이선스 뉴스 사진으로 교체하세요.
- 모델 기본값은 `claude-opus-4-8`. 변경은 `config.py` 또는 환경변수(.env.example 참고).
