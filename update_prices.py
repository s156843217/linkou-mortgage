# -*- coding: utf-8 -*-
"""
update_prices.py — 自動更新林口房貸頁地段單價
============================================================================
流程：
  1. 從「新北市政府資料開放平臺」API 抓不動產買賣實價登錄（全新北滾動快照）
  2. 篩出林口區、住宅、近一年、排除土地/車位/特殊交易
  3. 用 road_zone_map.csv（路名→商圈）把每筆分配到商圈
  4. 各商圈算 單價中位數 / IQR / 屋齡 / 房數 / 室內佔比
  5. 覆寫 mortgage-data.js 中 <<AUTO-ZONES-START>>～<<AUTO-ZONES-END>> 之間的內容

設計重點：
  - 只用 Python 標準庫，不需 pip install（雲端 GitHub Actions 最穩、最快）。
  - 「近一年」是以「資料本身最新一筆的日期」往回推一年，而非系統時鐘，
    避免快照落後時抓到 0 筆。
  - 找不到 <<AUTO-ZONES>> 標記、或篩完無資料時，直接中止且不覆寫（保留舊資料）。

執行：python update_prices.py
資料來源：https://data.ntpc.gov.tw/ 資料集 ACCE802D-58CC-4DFF-9E7A-9ECC517F78BE
"""
from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

# ── 設定 ──────────────────────────────────────────────────
API = ("https://data.ntpc.gov.tw/api/datasets/"
       "ACCE802D-58CC-4DFF-9E7A-9ECC517F78BE/json")
PAGE_SIZE = 5000          # 單頁筆數（API 上限）
MAX_PAGES = 40            # 安全上限，避免無限翻頁（40×5000=20 萬筆）
PING_M2 = 3.305785        # 1 坪 = 3.305785 平方公尺
MIN_COUNT = 3             # 商圈樣本數低於此不輸出（樣本太少不可信）

DATA_JS = Path("mortgage-data.js")
ROAD_MAP = Path("road_zone_map.csv")

# 輸出商圈順序（沿用 mortgage-data.js 既有順序）
ZONE_ORDER = ["三井Outlet", "南勢", "家樂福商圈", "北側", "林口舊市區", "麗園國小"]

RESIDENTIAL = {"住家用", "住商用"}   # 只看住宅，排除純商辦/工業
SPECIAL = ["親友", "二親等", "特殊關係", "急售", "債務", "拍賣", "法拍",
           "贈與", "含增建", "毛胚", "含裝潢", "含傢俱", "含家具", "瑕疵"]

# rps 欄位對照（新北 open data 英文代碼 → 意義）
#   rps01 交易標的 ｜ rps02 門牌 ｜ rps07_yyymmddroc 交易年月日(民國)
#   rps11 建物型態 ｜ rps12 主要用途 ｜ rps14_yyymmddroc 建築完成年月(民國)
#   rps15_area 建物移轉總面積 ｜ rps16_quantity 格局-房 ｜ rps21 總價元
#   rps24_area 車位面積 ｜ rps25 車位總價 ｜ rps26 備註
#   rps28_area 主建物 ｜ rps29_area 附屬建物 ｜ rps30_area 陽台


# ── 工具函式 ──────────────────────────────────────────────
def num(x):
    """轉成 float，轉不動回 None。"""
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def roc_int(yyymmdd):
    """民國 YYYMMDD 字串轉整數；空值/非數字回 None。"""
    s = (yyymmdd or "").strip()
    return int(s) if s.isdigit() and len(s) >= 6 else None


def roc_year(yyymmdd):
    """從民國 YYYMMDD 取民國年。"""
    s = (yyymmdd or "").strip()
    if len(s) < 5:
        return None
    try:
        return int(s[:-4])
    except ValueError:
        return None


def road_of(addr):
    """從門牌取路名：去掉「…區」前綴，取到第一個半/全形數字前。
       例：新北市林口區文化三路二段４１巷１２３號 → 文化三路二段"""
    s = re.sub(r"^.*?區", "", addr or "")     # 砍到第一個「區」
    m = re.match(r"([^0-9０-９]+)", s)         # 取數字前的路名（含「段」）
    return m.group(1).strip() if m else ""


def percentile(sorted_vals, q):
    """線性內插百分位（q 介於 0~1）。"""
    if not sorted_vals:
        return None
    i = q * (len(sorted_vals) - 1)
    lo = int(i)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = i - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


# ── 1. 抓 API（翻頁直到取完或達上限） ─────────────────────
def fetch_all():
    rows = []
    for p in range(MAX_PAGES):
        url = f"{API}?page={p}&size={PAGE_SIZE}"
        req = Request(url, headers={"User-Agent": "linkou-mortgage-bot/1.0"})
        with urlopen(req, timeout=120) as resp:
            chunk = json.loads(resp.read().decode("utf-8"))
        rows.extend(chunk)
        print(f"  page={p} 取得 {len(chunk)} 筆（累計 {len(rows)}）")
        if len(chunk) < PAGE_SIZE:      # 最後一頁
            break
    return rows


# ── 2~4. 篩選、分配商圈、統計 ─────────────────────────────
def build_zones():
    print("抓取新北開放平臺 API …")
    raw = fetch_all()
    print(f"全新北累計 {len(raw)} 筆")

    # 路名→商圈對照表
    road_zone = {}
    with open(ROAD_MAP, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            road = (row.get("路名") or "").strip()
            if road:
                road_zone[road] = (row.get("商圈") or "").strip()

    # 第一輪：篩林口住宅、算各欄位（先不做日期窗，之後用「資料最新日」回推）
    cand = []
    miss_roads = {}
    for r in raw:
        if r.get("district") != "林口區":
            continue
        if "建物" not in (r.get("rps01") or ""):      # 排除純土地
            continue
        if (r.get("rps12") or "") not in RESIDENTIAL:  # 只留住宅
            continue
        note = r.get("rps26") or ""
        if any(k in note for k in SPECIAL):            # 排除特殊交易
            continue

        d = roc_int(r.get("rps07_yyymmddroc"))
        total = num(r.get("rps21_amountsunitdollars"))
        area = num(r.get("rps15_area"))
        if d is None or not total or not area:
            continue

        park_area = num(r.get("rps24_area")) or 0.0
        park_price = num(r.get("rps25_amountsunitdollars")) or 0.0
        house_ping = (area - park_area) / PING_M2
        if house_ping <= 0:
            continue
        unit = (total - park_price) / 10000 / house_ping   # 萬/坪（不含車位）
        if unit <= 0:
            continue

        road = road_of(r.get("rps02"))
        zone = road_zone.get(road)
        if not zone:
            miss_roads[road] = miss_roads.get(road, 0) + 1
            continue

        ty, by = roc_year(r.get("rps07_yyymmddroc")), roc_year(r.get("rps14_yyymmddroc"))
        age = (ty - by) if (ty and by and ty >= by) else None
        rooms = num(r.get("rps16_quantity"))

        main_a = num(r.get("rps28_area")) or 0.0
        sub_a = num(r.get("rps29_area")) or 0.0
        bal_a = num(r.get("rps30_area")) or 0.0
        denom = area - park_area
        indoor = (main_a + sub_a + bal_a) / denom if denom > 0 else None

        cand.append({"date": d, "zone": zone, "unit": unit,
                     "age": age, "rooms": rooms, "indoor": indoor})

    if not cand:
        sys.exit("⚠ 林口住宅無資料，中止（不覆寫）")

    # 近一年：以「資料最新一筆」往回推一年（YYYMMDD 整數 −10000 ≈ 去年同日）
    max_d = max(c["date"] for c in cand)
    cutoff = max_d - 10000
    recs = [c for c in cand if c["date"] >= cutoff]
    print(f"林口住宅 {len(cand)} 筆；近一年（{cutoff}~{max_d}）取 {len(recs)} 筆")

    # 全域去極端值（單價 1%~99%）
    units = sorted(c["unit"] for c in recs)
    lo, hi = percentile(units, 0.01), percentile(units, 0.99)
    recs = [c for c in recs if lo <= c["unit"] <= hi]

    # 各商圈統計
    zones = []
    for name in ZONE_ORDER:
        g = [c for c in recs if c["zone"] == name]
        if len(g) < MIN_COUNT:
            print(f"  {name}: 樣本 {len(g)} 不足（<{MIN_COUNT}），略過")
            continue
        u = sorted(c["unit"] for c in g)
        ages = [c["age"] for c in g if c["age"] is not None]
        rooms = [c["rooms"] for c in g if c["rooms"] is not None]
        indoors = sorted(c["indoor"] for c in g if c["indoor"] is not None)
        zones.append({
            "name": name,
            "medPrice": round(statistics.median(u), 1),
            "q1": round(percentile(u, 0.25), 1),
            "q3": round(percentile(u, 0.75), 1),
            "count": len(g),
            "ageMed": round(statistics.median(ages)) if ages else 0,
            "roomMed": round(statistics.median(rooms)) if rooms else 0,
            "indoorPct": round(statistics.median(indoors), 3) if indoors else 0,
        })
        print(f"  {name}: med={zones[-1]['medPrice']} n={len(g)} "
              f"age={zones[-1]['ageMed']} indoor={zones[-1]['indoorPct']}")

    # 印出未命中路名，方便日後補進 road_zone_map.csv
    if miss_roads:
        top = sorted(miss_roads.items(), key=lambda kv: -kv[1])[:10]
        print("未命中路名（前 10，這些交易被丟棄）：")
        for road, n in top:
            print(f"    {n:>3}  {road}")

    if not zones:
        sys.exit("⚠ 無任何商圈達樣本門檻，中止（不覆寫）")
    return zones, max_d


# ── 5. 覆寫 mortgage-data.js ──────────────────────────────
def write_js(zones, max_d):
    today = date.today().isoformat()
    total_n = sum(z["count"] for z in zones)
    data_month = f"民國{str(max_d)[:3]}年{str(max_d)[3:5]}月"

    out = []
    out.append("// <<AUTO-ZONES-START>>  ← 此區塊由 update_prices.py 自動產生，請勿手改")
    out.append(f"// ── 林口各商圈每坪單價（自動更新：{today}；資料截至 {data_month}，"
               f"近一年共 {total_n} 筆） ──")
    out.append("// 來源：新北市政府資料開放平臺 不動產買賣實價登錄（每 10 日更新）")
    out.append("// medPrice：中位數（萬/坪）｜priceRange：[Q1,Q3]｜"
               "ageMed：屋齡中位數｜roomMed：房數中位數")
    out.append("// indoorPct：室內(主建物+附屬+陽台)/扣車位登記坪數 之中位數")
    out.append("const LINKOU_ZONES = [")
    for z in zones:
        out.append(
            f'  {{ name: "{z["name"]}", medPrice: {z["medPrice"]}, '
            f'priceRange: [{z["q1"]}, {z["q3"]}], count: {z["count"]}, '
            f'ageMed: {z["ageMed"]}, roomMed: {z["roomMed"]}, '
            f'indoorPct: {z["indoorPct"]} }},'
        )
    out.append("];")
    out.append("// <<AUTO-ZONES-END>>")
    block = "\n".join(out)

    content = DATA_JS.read_text(encoding="utf-8")
    new, n = re.subn(
        r"// <<AUTO-ZONES-START>>.*?// <<AUTO-ZONES-END>>",
        lambda _m: block,          # 用 lambda 避免反斜線跳脫問題
        content, flags=re.S,
    )
    if n == 0:
        sys.exit("⚠ 找不到 <<AUTO-ZONES-START/END>> 標記，未變更")
    DATA_JS.write_text(new, encoding="utf-8")
    print(f"✅ 已更新 {DATA_JS}（{len(zones)} 商圈，{total_n} 筆，資料截至 {data_month}）")


def main():
    zones, max_d = build_zones()
    write_js(zones, max_d)


if __name__ == "__main__":
    main()
