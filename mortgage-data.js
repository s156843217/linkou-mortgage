/* mortgage-data.js — 房貸試算頁資料
   排除：土地、車位、親友／股東特殊交易、預售屋、海砂屋
   依路名對照商圈後統計，單價單位：萬元／坪（不含車位）
   ※ LINKOU_ZONES 由 update_prices.py 自新北開放平臺 API 自動產生（含資料截止月份），請勿手改該區塊
*/

// <<AUTO-ZONES-START>>  ← 此區塊由 update_prices.py 自動產生，請勿手改
// ── 林口各商圈每坪單價（自動更新：2026-09-01；資料截至 民國115年06月，近一年共 697 筆） ──
// 來源：新北市政府資料開放平臺 不動產買賣實價登錄（每 10 日更新）
// 商圈分配：門牌座標 × 商圈多邊形（點在多邊形），跨區路自動切分
// 僅集合住宅（大樓/華廈/公寓）；已排除透天厝/別墅、車位、特殊交易
// medPrice：中位數（萬/坪）｜priceRange：[Q1,Q3]｜ageMed：屋齡中位數｜roomMed：房數中位數
// indoorPct：室內(主建物+附屬+陽台)/扣車位登記坪數 之中位數
const LINKOU_ZONES = [
  { name: "三井Outlet", medPrice: 57.6, priceRange: [47.5, 66.0], count: 146, ageMed: 12, roomMed: 3, indoorPct: 0.675 },
  { name: "南勢", medPrice: 55.4, priceRange: [51.8, 57.5], count: 113, ageMed: 1, roomMed: 3, indoorPct: 0.672 },
  { name: "家樂福商圈", medPrice: 50.4, priceRange: [45.9, 56.9], count: 280, ageMed: 11, roomMed: 3, indoorPct: 0.679 },
  { name: "北側", medPrice: 44.9, priceRange: [41.5, 51.0], count: 77, ageMed: 11, roomMed: 2, indoorPct: 0.689 },
  { name: "林口舊市區", medPrice: 37.1, priceRange: [28.6, 45.7], count: 58, ageMed: 24, roomMed: 3, indoorPct: 0.735 },
  { name: "麗園國小", medPrice: 27.9, priceRange: [25.9, 34.0], count: 23, ageMed: 41, roomMed: 3, indoorPct: 0.844 },
];
// <<AUTO-ZONES-END>>

// <<AUTO-TYPES-START>>  ← 此區塊由 update_prices.py 自動產生，請勿手改
// ── 林口 成屋／預售／透天 三類行情（自動更新：2026-09-01；近一年） ──
// 來源：新北開放平臺 實價登錄 — 成屋(ACCE802D，透天同源用建物型態拆出)、預售(9238CCC2)
// 單價=(總價−車位價)/不含車位坪/10000（與地段表同口徑）；預售排除解約、無屋齡
// calc=true 可依預算精準試算坪數；false 樣本少、僅作總價門檻參考
const LINKOU_TYPES = [
  { key: "resale", name: "成屋", sub: "電梯大樓／華廈", tag: "看屋即入住",
    unit: 50.9, unitRange: [43.3, 57.4], totalMed: 1820, ageMed: 11, pingMed: 35.2, roomMed: 3,
    n: 699, window: "近一年", calc: true,
    note: "現成可看實屋、可立即入住，屋齡中位約 11 年。" },
  { key: "presale", name: "預售屋", sub: "興建中／全新", tag: "全新可分期",
    unit: 62.9, unitRange: [57.5, 68.2], totalMed: 2027, ageMed: null, pingMed: 27.9, roomMed: 2,
    n: 657, window: "近一年", calc: true,
    note: "全新、可依工程期分期付款；單價約比成屋高三成，需等交屋。" },
  { key: "house", name: "透天／別墅", sub: "獨棟含土地", tag: "樣本少·參考",
    unit: 46.8, unitRange: [40.1, 51.0], totalMed: 3880, threshold: 3000, ageMed: 18, pingMed: 88.4, roomMed: 4,
    n: 62, window: "近一年", calc: false,
    note: "總價門檻約 3,000 萬起、中位約 3,880 萬；近一年林口僅 62 筆成交，僅供方向參考。" },
];
// <<AUTO-TYPES-END>>
