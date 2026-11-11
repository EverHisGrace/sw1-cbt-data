#!/usr/bin/env python3
"""공공데이터포털 '한국산업인력공단_국가전문자격 시험 시행일정 정보' API에서
사회복지사 1급 시험일을 찾아 exam-dates.json 을 갱신한다.
환경변수 DATA_GO_KR_KEY 에 공공데이터포털 인증키(Decoding 키)를 넣어 실행."""
import json, os, re, sys, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import date

KEY = os.environ.get("DATA_GO_KR_KEY", "").strip()
URL = "http://openapi.q-net.or.kr/api/service/rest/InquiryTestDatesNationalProfessionalQualificationSVC/getList"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exam-dates.json")
NAME = re.compile(r"사회복지사\s*1급")

def call(series):
    q = urllib.parse.urlencode({"serviceKey": KEY, "seriesCd": series})
    with urllib.request.urlopen(f"{URL}?{q}", timeout=20) as r:
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
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if s and len(s) >= 8 else None

def main():
    if not KEY:
        sys.exit("DATA_GO_KR_KEY 가 없습니다")
    found, seen = {}, []
    series_list = [os.environ["SERIES_CD"]] if os.environ.get("SERIES_CD") else [f"{i:02d}" for i in range(1, 100)]
    for s in series_list:
        try:
            for r in rows(call(s)):
                desc = r.get("description", "")
                seen.append(f"{s}: {desc}")
                if not NAME.search(desc):
                    continue
                m = re.search(r"제?\s*(\d+)\s*회", desc)
                d = ymd(r.get("examstartdt") or r.get("EXAM_START_DT") or r.get("examStartDt", ""))
                if m and d:
                    found[int(m.group(1))] = {
                        "n": int(m.group(1)), "d": d,
                        "reg": [ymd(r.get("examregstartdt") or r.get("EXAM_REG_START_DT", "")),
                                ymd(r.get("examregenddt") or r.get("EXAM_REG_END_DT", ""))],
                        "pass": ymd(r.get("passstartdt") or r.get("PASS_START_DT", "")),
                        "series": s}
        except Exception as e:
            print(f"seriesCd={s} 건너뜀: {e}", file=sys.stderr)
    if not found:
        print("사회복지사 1급 일정을 찾지 못했습니다. 받은 회차 설명 일부:", *seen[:60], sep="\n")
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
