#!/usr/bin/env python3
"""심층 캐러셀 · 폭스바겐그룹 조향 나사 리콜 후속 (2026-09-26)
템플릿: 2026-09-24-sozialbetrug.py 와 같은 구조. 실행하면 out-<파일명>/deep-NN.jpg 생성.
사실 출처: 하이제·ADAC·ZDF·티온라인·kfz-betrieb·인프랑켄 (9월 25~26일 보도)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import make_social as ms

OUT = os.path.join(HERE, "out-" + os.path.splitext(os.path.basename(__file__))[0])

EXTRA = """
.kicker{font-family:var(--disp);font-weight:800;font-size:24px;letter-spacing:.2em;color:var(--faint);margin-bottom:22px;}
.head.sm{font-size:68px;margin-bottom:34px;}
.list{list-style:none;}
.list li{display:flex;gap:26px;padding:24px 0;border-top:2px solid var(--line);}
.list li:last-child{border-bottom:2px solid var(--line);}
.list .n{font-family:var(--serif);font-style:italic;font-size:44px;color:var(--faint);min-width:56px;line-height:1.2;}
.list .t{font-size:38px;font-weight:800;line-height:1.3;margin-bottom:8px;}
.list .d{font-size:31px;line-height:1.5;color:var(--soft);font-weight:500;}
.list.tight li{padding:18px 0;} .list.tight .t{font-size:35px;} .list.tight .d{font-size:29px;}
.src{font-size:24px;color:var(--faint);margin-top:24px;line-height:1.5;}
.hook .head{font-size:92px;}
.hook .date{font-family:var(--disp);font-weight:700;font-size:30px;margin-top:40px;color:var(--soft);}
.chk p{line-height:1.75;}
.desc,.list .d,.interp p,.head,.src{word-break:keep-all;}
.list.brand .n{min-width:84px;}
"""

def top(pg, total):
    return f"""<div class="top">
    <span class="pill"><span class="ko">독일</span><span class="en">GERMANY</span></span>
    <span class="pg">{pg:02d} / {total:02d}</span></div>"""

FOOT = '<div class="foot"><span class="bn">나침반 · 심층</span><span class="u">2026. 09. 26</span></div>'

def page(pg, total, inner, cls=""):
    return f'<section class="slide {cls}">{top(pg,total)}<div class="mid">{inner}</div>{FOOT}</section>'

def items(rows, cls=""):
    return f'<ul class="list {cls}">' + "".join(
        f'<li><span class="n">{n}</span><div><div class="t">{t}</div><div class="d">{d}</div></div></li>'
        for n, t, d in rows) + "</ul>"

T = 10
slides = [
    page(1, T, """<div class="kicker">심층 · 후속</div>
<h2 class="head">폭스바겐<br>조향 리콜<br>내 차도?</h2>
<p class="desc">골프·티구안·아우디 Q3에 이어 세아트 두 차종도 같은 문제로 리콜됩니다. 내 차가 대상인지 확인하는 법과 할 일을 정리했습니다.</p>
<div class="date">2026년 9월 26일 기준</div>""", "hook"),

    page(2, T, """<div class="kicker">한 줄 요약</div>
<h2 class="head sm">핸들을 잡아주는<br>나사가 녹슬 수 있다</h2>
<p class="desc">조향장치를 차체에 고정하는 나사에 습기와 제설용 소금이 스며들어 녹이 생길 수 있습니다. 나사가 끊어지면 최악의 경우 핸들이 듣지 않을 수 있습니다.</p>
<div class="interp"><div class="lb">지금까지</div><p>연방자동차청에 보고된 <b>사고·부상은 없습니다</b>. 폭스바겐은 실제 손상이 대상 차의 최대 1% 정도로 봅니다.</p></div>"""),

    page(3, T, '<div class="kicker">대상 차종 (제작 기간)</div>' + items([
        ("VW", "골프·골프 바리안트·티구안·투란·카디", "2013년 9월 24일 ~ 2024년 7월 1일 제작. 독일&nbsp;약&nbsp;89만&nbsp;6천&nbsp;대."),
        ("AU", "아우디 Q3", "2017년 10월 31일 ~ 2024년 5월 23일 제작. 독일&nbsp;약&nbsp;5만&nbsp;9천&nbsp;대."),
        ("SE", "세아트 아테카·타라코", "2016년 4월 ~ 2024년 9월 제작. 독일&nbsp;약&nbsp;4만&nbsp;4천&nbsp;대."),
    ], "brand") + '<p class="src">※ 같은 차종·연식이라도 모두 대상은 아닙니다. 차대번호로 확인해야 합니다.<br>※ 스코다도 대상이라는 보도가 있으나, 26일 오전까지 차종은 공식 확인되지 않았습니다.</p>'),

    page(4, T, '<div class="kicker">확인 방법</div>' + items([
        ("01", "차대번호(FIN) 찾기", "17자리 번호입니다. 차량등록증(Zulassungsbescheinigung Teil I)의 E칸이나 앞유리 아래쪽에 있습니다."),
        ("02", "제조사에 전화", "차대번호와 리콜 코드를 말하면 대상인지 알려줍니다. 번호는 다음 장에 있습니다."),
        ("03", "공식 정비소 방문", "브랜드 공식 정비소(Vertragswerkstatt)에서 차대번호로 조회하고 예약까지 할 수 있습니다."),
        ("04", "연방자동차청 리콜 목록", "kba.de의 리콜 데이터베이스(Rückrufdatenbank)에서 참조번호로 내용을 볼 수 있습니다."),
    ], "tight")),

    page(5, T, '<div class="kicker">전화번호 · 리콜 코드</div>' + items([
        ("VW", "폭스바겐 0800 8655792436", "리콜 코드 48VS · 연방자동차청 참조번호 17016R"),
        ("AU", "아우디 0800 2834 7378 423", "리콜 코드 48LG · 연방자동차청 참조번호 17014R"),
        ("SE", "세아트 06150 107 9991", "리콜 코드 48T7"),
    ], "brand") + '<p class="src">※ 0800 번호는 독일 내 무료 전화입니다. 독일어가 부담되면 차대번호와 리콜 코드를 적어 정비소에 보여 주세요.</p>'),

    page(6, T, '<div class="kicker">수리는 이렇게</div>' + items([
        ("01", "무료, 1시간 안팎", "녹슨 나사를 부식에 강한 새 나사로 바꿉니다. 비용은 제조사가 부담합니다."),
        ("02", "편지가 옵니다", "제조사가 등록된 차 주인 주소로 안내문을 보냅니다. 받으면 정비소에 예약하세요."),
        ("03", "예약은 부품 입고 뒤", "정비소에 부품이 들어와야 예약이 잡힙니다. 아직 구체적인 일정은 나오지 않았습니다."),
        ("04", "그동안 운행은 가능", "폭스바겐은 수리 전에도 계속 타도 된다고 밝혔습니다. 다만 아래 증상이 있으면 예외입니다."),
    ], "tight")),

    page(7, T, """<div class="kicker">이런 증상이면 바로 멈추세요</div>
<h2 class="head sm">핸들이 이상하면<br>운전하지 마세요</h2>
<p class="desc">✔ 핸들이 전보다 헐겁게 놀 때<br>✔ 핸들 느낌이 갑자기 달라졌을 때<br>✔ 앞바퀴 쪽에서 딸깍·덜컹 소리가 날 때</p>
<div class="interp"><div class="lb">이럴 땐</div><p>차를 세우고 직접 몰고 가지 말고 <b>정비소나 긴급출동</b>을 부르세요. 나사는 주차처럼 핸들을 크게 돌릴 때 부러질 수 있다고 합니다.</p></div>"""),

    page(8, T, '<div class="kicker">한인에게는? 상황별</div>' + items([
        ("A", "중고로 샀거나 이사했다면", "안내문은 차량 등록 주소로 갑니다. 주소 변경이 늦었다면 편지를 기다리지 말고 직접 확인하세요."),
        ("B", "리스·회사 차라면", "수리 예약은 리스 회사나 회사 차량 담당자에게 먼저 문의하세요."),
        ("C", "귀국·판매를 앞뒀다면", "수리를 마치고 정비 기록을 받아 두세요. 팔 때 리콜 여부를 묻는 경우가 많습니다."),
        ("D", "한국에도 차가 있다면", "한국 판매분 리콜은 26일 기준 확인되지 않았습니다. 자동차리콜센터(car.go.kr)에서 차대번호로 조회하세요."),
    ], "tight") + '<p class="src">※ 보도 내용을 바탕으로 한 나침반의 해석입니다.</p>'),

    page(9, T, """<div class="kicker">정리하면</div>
<h2 class="head sm">차대번호 하나로<br>확인부터</h2>
<p class="desc">사고 보고는 없고 수리는 무료입니다. 다만 안전 관련 리콜을 끝까지 받지 않으면 운행 정지까지 갈 수 있다고 현지 언론은 전합니다.</p>
<div class="interp chk"><div class="lb">지금 챙길 3가지</div><p>✔ 등록증에서 <b>차대번호</b> 확인<br>✔ 제조사 전화·정비소로 <b>대상 여부</b> 조회<br>✔ 안내문 오면 <b>무료 수리 예약</b></p></div>"""),

    ms.outro_slide(),
]

def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".jpg"):
            os.remove(os.path.join(OUT, f))
    ms.IMG = OUT
    fail = ms.render_set(slides, 1080, 1350, "deep", EXTRA)
    print("fail", fail, sorted(os.listdir(OUT)))

if __name__ == "__main__":
    main()
