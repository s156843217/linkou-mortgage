# -*- coding: utf-8 -*-
"""
update_prices.py — 自動更新林口房貸頁地段單價
============================================================================
流程：
  1. 從「新北市政府資料開放平臺」API 抓不動產買賣實價登錄（全新北滾動快照）
  2. 篩出林口區、住宅、近一年、排除土地/車位/特殊交易
  3. 商圈分配（兩段式）：
       (a) 主：用門牌查 HOUSE 取「座標」→ 看落在哪個商圈多邊形內（點在多邊形）。
           這能正確處理「同一條路跨兩個商圈」（如文化北路二段跨北側／家樂福）。
       (b) 備援：HOUSE 查不到座標時，退回 road_zone_map.csv 的路名→商圈。
  4. 各商圈算 單價中位數 / IQR / 屋齡 / 房數 / 室內佔比
  5. 覆寫 mortgage-data.js 中 <<AUTO-ZONES-START>>～<<AUTO-ZONES-END>> 之間

設計重點：
  - 只用 Python 標準庫，不需 pip install（雲端 GitHub Actions 最穩、最快）。
  - HOUSE 門牌座標表「線上」從學區 repo 直接抓（永遠最新、不留過期複製檔）；
    抓不到時自動降級為純 road_zone_map.csv（不中斷）。
  - 商圈多邊形 林口價格地圖.geojson 是「你畫的區域」，放在本 repo 當快照；重畫後換檔即可。
  - 「近一年」以「資料本身最新一筆日期」往回推一年（非系統時鐘），避免快照落後抓到 0 筆。
  - 找不到標記、或篩完無資料時，直接中止且不覆寫（保留舊資料）。

執行：python update_prices.py
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
PAGE_SIZE = 5000
MAX_PAGES = 40
PING_M2 = 3.305785
MIN_COUNT = 3

# 學區 repo 的門牌座標表（線上抓，永遠最新）
HOUSE_URL = ("https://raw.githubusercontent.com/"
             "s156843217/linkou-school-zone/master/linkou-data.js")

DATA_JS = Path("mortgage-data.js")
ROAD_MAP = Path("road_zone_map.csv")                 # 備援用
GEOJSON = Path("林口價格地圖.geojson")                # 你畫的商圈多邊形

ZONE_ORDER = ["三井Outlet", "南勢", "家樂福商圈", "北側", "林口舊市區", "麗園國小"]
RESIDENTIAL = {"住家用", "住商用"}
SPECIAL = ["親友", "二親等", "特殊關係", "急售", "債務", "拍賣", "法拍",
           "贈與", "含增建", "毛胚", "含裝潢", "含傢俱", "含家具", "瑕疵"]

# rps 欄位：rps01 交易標的｜rps02 門牌｜rps07 交易年月日｜rps12 主要用途
#   rps14 建築完成年月｜rps15_area 建物面積｜rps16 房｜rps21 總價｜rps24_area 車位面積
#   rps25 車位總價｜rps26 備註｜rps28/29/30 主建物/附屬/陽台


# ── 通用工具 ──────────────────────────────────────────────
def num(x):
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def roc_int(s):
    s = (s or "").strip()
    return int(s) if s.isdigit() and len(s) >= 6 else None


def roc_year(s):
    s = (s or "").strip()
    if len(s) < 5:
        return None
    try:
        return int(s[:-4])
    except ValueError:
        return None


# ── 門牌解析 / 取座標（移植自學區 index.html 的 parseHouse / houseLookup） ──
_FW = str.maketrans("０１２３４５６７８９－～／　", "0123456789-~/ ")


def to_half(s):
    return (s or "").translate(_FW)


def parse_house(addr):
    """正規化地址，拆出 road / lk(巷-弄) / num。對不到回 None。"""
    a = to_half(addr).strip()
    if "林口" in a:
        a = re.sub(r"^.*林口區", "", a)
    a = re.sub(r"^\d{3}", "", a)
    a = re.sub(r"(新北市|臺北市|台北市)", "", a)
    a = re.sub(r"[一-鿿]+[村里]", "", a)   # 去 X村 / X里
    a = re.sub(r"\d+鄰", "", a).strip()
    m = re.search(r"\d", a)
    if not m:
        return None
    road = re.sub(r"[\s\-,，、]", "", a[:m.start()]).strip()
    if not road:
        return None
    rest = a[m.start():]
    ml = re.search(r"(\d+)\s*巷", rest)
    mz = re.search(r"(\d+)\s*弄", rest)
    lane = ml.group(1) if ml else ""
    alley = mz.group(1) if mz else ""
    r2 = re.sub(r"\d+\s*巷", "", rest)
    r2 = re.sub(r"\d+\s*弄", "", r2).replace("之", "-")
    mn = re.search(r"(\d+(?:-\d+)?)", r2)
    if not mn:
        return None
    return {"road": road, "lk": lane + "-" + alley, "num": mn.group(1)}


def dec_coord(val):
    """HOUSE 值 "里|鄰*緯偏,經偏" → (lat, lon)；無座標回 None。"""
    codes, _, co = val.partition("*")
    if not co:
        return None
    a, _, b = co.partition(",")
    try:
        return (25.0 + float(a) / 100000, 121.3 + float(b) / 100000)
    except ValueError:
        return None


def house_coord(addr, house):
    """查 HOUSE 取門牌座標 (lat, lon)；查不到回 None。"""
    p = parse_house(addr)
    if not p:
        return None
    node = house.get(p["road"])
    if not node:
        return None
    lk, n = p["lk"], p["num"]
    sub = node.get(lk)
    if sub:
        if n in sub:                                  # 巷弄號完全命中
            d = dec_coord(sub[n])
            if d:
                return d
        base = n.split("-")[0]                         # 同巷弄、同基底號
        for k, v in sub.items():
            if k.split("-")[0] == base:
                d = dec_coord(v)
                if d:
                    return d
    for s2 in node.values():                           # 退一步：忽略巷弄
        if n in s2:
            d = dec_coord(s2[n])
            if d:
                return d
    return None


# ── 點在多邊形（射線法），商圈多邊形來自你畫的 geojson ───────
def point_in_ring(lon, lat, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > lat) != (yj > lat)) and \
           (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def zone_of(lon, lat, zones):
    for name, ring in zones:
        if point_in_ring(lon, lat, ring):
            return name
    return None


def load_zones():
    gj = json.loads(GEOJSON.read_text(encoding="utf-8"))
    zones = []
    for f in gj.get("features", []):
        g = f.get("geometry") or {}
        if g.get("type") == "Polygon":
            ring = [(c[0], c[1]) for c in g["coordinates"][0]]  # [lon, lat]
            zones.append((f["properties"].get("name", "?"), ring))
    return zones


def load_house():
    """從學區 repo 線上抓 linkou-data.js，解析出 HOUSE 物件。失敗回 {}。"""
    try:
        req = Request(HOUSE_URL, headers={"User-Agent": "linkou-mortgage-bot/1.0"})
        with urlopen(req, timeout=60) as r:
            txt = r.read().decode("utf-8")
        for line in txt.splitlines():
            if line.startswith("const HOUSE = "):
                body = line[len("const HOUSE = "):].rstrip().rstrip(";")
                return json.loads(body)
        print("⚠ 線上 linkou-data.js 找不到 HOUSE 行，降級為純路名對照")
    except Exception as e:                              # noqa: BLE001
        print(f"⚠ 抓 HOUSE 失敗（{e}），降級為純路名對照")
    return {}


# ── 抓 API ────────────────────────────────────────────────
def fetch_all():
    rows = []
    for p in range(MAX_PAGES):
        url = f"{API}?page={p}&size={PAGE_SIZE}"
        req = Request(url, headers={"User-Agent": "linkou-mortgage-bot/1.0"})
        with urlopen(req, timeout=120) as r:
            chunk = json.loads(r.read().decode("utf-8"))
        rows.extend(chunk)
        print(f"  page={p} 取得 {len(chunk)} 筆（累計 {len(rows)}）")
        if len(chunk) < PAGE_SIZE:
            break
    return rows


def road_of(addr):
    """備援用：粗抽路名（去「…區」前綴、取到第一個半/全形數字前）。"""
    s = re.sub(r"^.*?區", "", addr or "")
    m = re.match(r"([^0-9０-９]+)", s)
    return m.group(1).strip() if m else ""


# ── 主流程 ────────────────────────────────────────────────
def build_zones():
    print("載入商圈多邊形 …")
    zones = load_zones()
    print(f"  {len(zones)} 個商圈：{[z[0] for z in zones]}")

    print("線上抓 HOUSE 門牌座標表 …")
    house = load_house()
    print(f"  HOUSE 路名數：{len(house)}")

    road_zone = {}
    with open(ROAD_MAP, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            r = (row.get("路名") or "").strip()
            if r:
                road_zone[r] = (row.get("商圈") or "").strip()

    print("抓取新北開放平臺 API …")
    raw = fetch_all()
    print(f"全新北累計 {len(raw)} 筆")

    cand = []
    by_coord = by_fallback = unmatched = 0
    miss_roads = {}
    for r in raw:
        if r.get("district") != "林口區":
            continue
        if "建物" not in (r.get("rps01") or ""):
            continue
        if (r.get("rps12") or "") not in RESIDENTIAL:
            continue
        if any(k in (r.get("rps26") or "") for k in SPECIAL):
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
        unit = (total - park_price) / 10000 / house_ping
        if unit <= 0:
            continue

        addr = r.get("rps02")
        # 商圈分配：先座標+多邊形，退回路名對照
        zone = None
        coord = house_coord(addr, house) if house else None
        if coord:
            zone = zone_of(coord[1], coord[0], zones)   # (lon, lat)
            if zone:
                by_coord += 1
        if not zone:
            road = road_of(addr)
            zone = road_zone.get(road)
            if zone:
                by_fallback += 1
            else:
                unmatched += 1
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

    print(f"商圈分配：座標命中 {by_coord}、路名備援 {by_fallback}、未命中丟棄 {unmatched}")
    if miss_roads:
        top = sorted(miss_roads.items(), key=lambda kv: -kv[1])[:10]
        print("  未命中路名（前 10）：" + "  ".join(f"{r}×{n}" for r, n in top))

    # 近一年（以資料最新日回推）
    max_d = max(c["date"] for c in cand)
    cutoff = max_d - 10000
    recs = [c for c in cand if c["date"] >= cutoff]
    print(f"林口住宅 {len(cand)} 筆；近一年（{cutoff}~{max_d}）取 {len(recs)} 筆")

    # 去極端值 1%~99%
    units = sorted(c["unit"] for c in recs)
    lo, hi = percentile(units, 0.01), percentile(units, 0.99)
    recs = [c for c in recs if lo <= c["unit"] <= hi]

    out = []
    for name in ZONE_ORDER:
        g = [c for c in recs if c["zone"] == name]
        if len(g) < MIN_COUNT:
            print(f"  {name}: 樣本 {len(g)} 不足，略過")
            continue
        u = sorted(c["unit"] for c in g)
        ages = [c["age"] for c in g if c["age"] is not None]
        rooms = [c["rooms"] for c in g if c["rooms"] is not None]
        indoors = sorted(c["indoor"] for c in g if c["indoor"] is not None)
        out.append({
            "name": name,
            "medPrice": round(statistics.median(u), 1),
            "q1": round(percentile(u, 0.25), 1),
            "q3": round(percentile(u, 0.75), 1),
            "count": len(g),
            "ageMed": round(statistics.median(ages)) if ages else 0,
            "roomMed": round(statistics.median(rooms)) if rooms else 0,
            "indoorPct": round(statistics.median(indoors), 3) if indoors else 0,
        })
        print(f"  {name}: med={out[-1]['medPrice']} n={len(g)}")

    if not out:
        sys.exit("⚠ 無任何商圈達樣本門檻，中止（不覆寫）")
    return out, max_d


def percentile(sorted_vals, q):
    if not sorted_vals:
        return None
    i = q * (len(sorted_vals) - 1)
    lo = int(i)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = i - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


# ── 覆寫 mortgage-data.js ────────────────────────────────
def write_js(zones, max_d):
    today = date.today().isoformat()
    total_n = sum(z["count"] for z in zones)
    data_month = f"民國{str(max_d)[:3]}年{str(max_d)[3:5]}月"

    out = []
    out.append("// <<AUTO-ZONES-START>>  ← 此區塊由 update_prices.py 自動產生，請勿手改")
    out.append(f"// ── 林口各商圈每坪單價（自動更新：{today}；資料截至 {data_month}，"
               f"近一年共 {total_n} 筆） ──")
    out.append("// 來源：新北市政府資料開放平臺 不動產買賣實價登錄（每 10 日更新）")
    out.append("// 商圈分配：門牌座標 × 商圈多邊形（點在多邊形），跨區路自動切分")
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
    new, n = re.subn(r"// <<AUTO-ZONES-START>>.*?// <<AUTO-ZONES-END>>",
                     lambda _m: block, content, flags=re.S)
    if n == 0:
        sys.exit("⚠ 找不到 <<AUTO-ZONES-START/END>> 標記，未變更")
    DATA_JS.write_text(new, encoding="utf-8")
    print(f"✅ 已更新 {DATA_JS}（{len(zones)} 商圈，{total_n} 筆，資料截至 {data_month}）")


def main():
    zones, max_d = build_zones()
    write_js(zones, max_d)


if __name__ == "__main__":
    main()
