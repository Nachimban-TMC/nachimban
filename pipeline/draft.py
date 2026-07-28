"""③ 요약·해석 — ⚖️ 법률 해설가 (AI).

후보 뉴스를 카드용 제목/요약/'쉬운 해석'으로 다듬는다. 법률 조언이 아니라
'쉽게 풀어주는' 수준(단정·과장 금지, 확인 필요한 부분은 그렇게 표시).
"""
from __future__ import annotations

import config
from schema import Candidate, Draft, NewsItem
from pipeline import llm

_SYSTEM = (
    "당신은 재외한인 뉴스의 법률 해설가입니다. 어려운 법률·행정 뉴스를 "
    "해외 거주 한국인이 이해할 수 있게 쉬운 말로 풉니다. 규칙:\n"
    "- 사실만. 원문에 없는 수치/날짜/요건을 만들지 말 것.\n"
    "- 'interp'(쉬운 해석)에는 '나에게 미치는 영향'과 실천 팁을 담고, "
    "가장 중요한 핵심어 1~2개를 <b>…</b>로 감쌀 것.\n"
    "- 법률 자문이 아님. 단정적 조언 대신 '확인하세요' 같은 안내형 표현."
)


def draft_item(c: Candidate) -> NewsItem:
    # 사건·사고에 '법 조항 해설'을 붙이면 어색하다. 그날의 1면 뉴스는
    # 해석의 각도를 '현지에 사는 한인이 지금 뭘 해야 하는가'로 바꾼다.
    if c.category == "general":
        interp_ask = ("interp: '현지 한인에게' 2문장 이내 — 지금 무엇을 조심하거나 "
                      "확인해야 하는지(해당 지역 통행·안전·행정 영향 등). "
                      "법 조항 해설로 쓰지 말 것. 핵심어는 <b>…</b>. "
                      "사상자 수·경위는 확인된 것만, 단정하지 말 것")
    else:
        interp_ask = "interp: '쉬운 해석' 2문장 이내, 핵심어는 <b>…</b>"

    user = f"""아래 뉴스를 카드용으로 다듬어 주세요.

[지역] {c.region}
[카테고리] {c.category}
[헤드라인] {c.headline}
[요약] {c.summary}
[핵심 날짜] {c.effective_date}
[출처] {c.source_name} / {', '.join(c.source_urls)}

- head: 25자 내외의 카드 제목(한글)
- desc: 2~3문장 한글 요약
- {interp_ask}
- read_min: 예상 읽기 분(1~5)"""
    d: Draft = llm.structured(_SYSTEM, user, Draft, model=config.MODEL_LEGAL)
    return NewsItem(
        region=c.region,
        category=c.category,
        head=d.head,
        desc=d.desc,
        interp=d.interp,
        source=c.source_name,
        read=d.read_min,
        url=c.source_urls[0] if c.source_urls else "#",
        source_urls=c.source_urls,
    )
