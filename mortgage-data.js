/* mortgage-data.js — 房貸試算頁資料
   排除：土地、車位、親友／股東特殊交易、預售屋、海砂屋
   依路名對照商圈後統計，單價單位：萬元／坪（不含車位）
   ※ LINKOU_ZONES 由 update_prices.py 自新北開放平臺 API 自動產生（含資料截止月份），請勿手改該區塊
*/

// <<AUTO-ZONES-START>>  ← 此區塊由 update_prices.py 自動產生，請勿手改
// ── 林口各商圈每坪單價（自動更新：2026-06-19；資料截至 民國115年04月，近一年共 697 筆） ──
// 來源：新北市政府資料開放平臺 不動產買賣實價登錄（每 10 日更新）
// 商圈分配：門牌座標 × 商圈多邊形（點在多邊形），跨區路自動切分
// medPrice：中位數（萬/坪）｜priceRange：[Q1,Q3]｜ageMed：屋齡中位數｜roomMed：房數中位數
// indoorPct：室內(主建物+附屬+陽台)/扣車位登記坪數 之中位數
const LINKOU_ZONES = [
  { name: "三井Outlet", medPrice: 57.5, priceRange: [47.4, 65.7], count: 144, ageMed: 12, roomMed: 3, indoorPct: 0.675 },
  { name: "南勢", medPrice: 54.5, priceRange: [47.3, 56.6], count: 94, ageMed: 7, roomMed: 3, indoorPct: 0.672 },
  { name: "家樂福商圈", medPrice: 50.2, priceRange: [45.6, 56.8], count: 273, ageMed: 11, roomMed: 3, indoorPct: 0.679 },
  { name: "北側", medPrice: 45.5, priceRange: [42.4, 50.7], count: 73, ageMed: 11, roomMed: 2, indoorPct: 0.698 },
  { name: "林口舊市區", medPrice: 41.0, priceRange: [30.3, 49.0], count: 84, ageMed: 19, roomMed: 3, indoorPct: 0.882 },
  { name: "麗園國小", medPrice: 31.2, priceRange: [26.5, 36.9], count: 29, ageMed: 31, roomMed: 3, indoorPct: 0.847 },
];
// <<AUTO-ZONES-END>>

// ── 林口各總價區間對應房產類型（供試算結果快速提示用） ───────
// 格式：{ min, max, label, summary }
const LINKOU_PRODUCTS = [
  {
    min: 0, max: 1000,
    label: "1,000 萬以下",
    summary: "老市區公寓或套房為主・屋齡約 36 年・約 22 坪・1 房",
  },
  {
    min: 1000, max: 1400,
    label: "1,000–1,400 萬",
    summary: "中古華廈或住宅大樓・屋齡約 15 年・約 27 坪・2 房",
  },
  {
    min: 1400, max: 1800,
    label: "1,400–1,800 萬",
    summary: "住宅大樓為主・屋齡約 11 年・約 31 坪・2 房",
  },
  {
    min: 1800, max: 2500,
    label: "1,800–2,500 萬",
    summary: "近年新成屋・屋齡約 8 年・約 38 坪・3 房",
  },
  {
    min: 2500, max: 3500,
    label: "2,500–3,500 萬",
    summary: "新成屋大坪數・屋齡約 8 年・約 57 坪・3 房",
  },
  {
    min: 3500, max: 99999,
    label: "3,500 萬以上",
    summary: "大坪數住宅大樓或透天厝・屋齡約 11 年・約 94 坪・3 房以上",
  },
];
