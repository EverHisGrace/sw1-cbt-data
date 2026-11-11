#!/usr/bin/env python3
"""공공데이터포털 '한국산업인력공단_국가자격 시험일정 조회 서비스' API에서
사회복지사 1급 시험일을 찾아 exam-dates.json 을 갱신한다.
환경변수 DATA_GO_KR_KEY 에 공공데이터포털 인증키(Decoding 키)를 넣어 실행."""
import json, os, re, sys, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import date

KEY = os.environ.get("DATA_GO_KR_KEY", "").strip()
# 신 API(2026 기준): 한국산업인력공단_국가자격 시험일정 조회 서비스 (data.go.kr/data/15074408)
URL = "https://apis.data.go.kr/B490007/qualExamSchd/getQualExamSchdList"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exam-dates.json")
NAME = re.compile(r"사회복지사\s*1급")

def call(year):
    q = urllib.parse.urlencode({"serviceKey": KEY, "numOfRows": 300, "pageNo": 1,
                                "dataFormat": "json", "implYy": year, "qualgbCd": "S"})
    req = urllib.request.Request(f"{URL}?{q}", headers={"User-Agent": "sw1cbt"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def rows(raw):
    t = raw.decode("utf-8", "replace").lstrip()
    if t.startswith("{"):  # JSON 응답도 처리
        j = json.loads(t)
        body = j.get("response", j)
        code = str(body.get("header", {}).get("resultCode", "00"))
        if code not in ("", "00"):
            raise RuntimeError(f"API 오류 {code}: {body.get('header', {}).get('resultMsg')}")
        items = (body.get("body") or {}).get("items") or []
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        for it in items:
            yield {k: str(v).strip() for k, v in it.items()}
        return
    root = ET.fromstring(raw)
    code = (root.findtext(".//resultCode") or "").strip()
    if code not in ("", "00"):
        raise RuntimeError(f"API 오류 {code}: {root.findtext('.//resultMsg')}")
    for it in root.iter("item"):
        yield {c.tag: (c.text or "").strip() for c in it}

def ymd(s):
    s = re.sub(r"\D", "", str(s or ""))
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) >= 8 else None

def lookup():
    """올해·내년 국가전문자격 일정에서 사회복지사 1급만 골라 {회차: 정보}"""
    found, seen = {}, []
    y = date.today().year
    for year in (y - 1, y, y + 1):
        try:
            for r in rows(call(year)):
                desc = r.get("description", "")
                seen.append(f"{year}: {desc}")
                if not NAME.search(desc):
                    continue
                m = re.search(r"제\s*(\d+)\s*회", desc)
                d = ymd(r.get("docExamStartDt"))
                if m and d:
                    found[int(m.group(1))] = {"n": int(m.group(1)), "d": d,
                        "reg": [ymd(r.get("docRegStartDt")), ymd(r.get("docRegEndDt"))],
                        "pass": ymd(r.get("docPassDt"))}
        except Exception as e:
            print(f"{year}년 조회 실패: {e}", file=sys.stderr)
    return found, seen

def main():
    if not KEY:
        sys.exit("DATA_GO_KR_KEY 가 없습니다")
    found, seen = lookup()
    if not found:
        print("사회복지사 1급 일정을 찾지 못했습니다. 받은 설명 일부:", *seen[:40], sep="\n")
        return
    data = json.load(open(OUT, encoding="utf-8"))
    old = {e["n"]: e for e in data.get("exams", [])}
    old.update(found)
    data["exams"] = sorted(old.values(), key=lambda e: e["n"])
    data["updated"] = date.today().isoformat()
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("갱신:", *[f"제{e['n']}회 {e['d']}" for e in data["exams"]], sep="\n")

if __name__ == "__main__":
    main()
