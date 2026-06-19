/* mortgage-data.js — 房貸試算頁資料
   資料來源：內政部實價登錄 近一年（114Q1～115Q1，買賣成交，林口區住宅）
   排除：土地、車位、親友／股東特殊交易、預售屋、海砂屋
   依路名對照商圈後統計，單價單位：萬元／坪（不含車位）
   ※ 北側商圈樣本數不足（近一年僅 11 筆），維持前期數字供參考
*/

// <<AUTO-ZONES-START>>  ← 此區塊由 update_prices.py 自動產生，請勿手改
// ── 林口各商圈每坪單價（自動更新：2026-06-19；資料截至 民國115年04月，近一年共 662 筆） ──
// 來源：新北市政府資料開放平臺 不動產買賣實價登錄（每 10 日更新）
// medPrice：中位數（萬/坪）｜priceRange：[Q1,Q3]｜ageMed：屋齡中位數｜roomMed：房數中位數
// indoorPct：室內(主建物+附屬+陽台)/扣車位登記坪數 之中位數
const LINKOU_ZONES = [
  { name: "三井Outlet", medPrice: 54.7, priceRange: [48.7, 64.8], count: 100, ageMed: 12, roomMed: 3, indoorPct: 0.679 },
  { name: "南勢", medPrice: 55.0, priceRange: [50.8, 56.7], count: 85, ageMed: 7, roomMed: 3, indoorPct: 0.668 },
  { name: "家樂福商圈", medPrice: 50.3, priceRange: [43.5, 55.9], count: 234, ageMed: 12, roomMed: 3, indoorPct: 0.68 },
  { name: "北側", medPrice: 45.1, priceRange: [31.5, 53.4], count: 17, ageMed: 18, roomMed: 3, indoorPct: 0.685 },
  { name: "林口舊市區", medPrice: 47.1, priceRange: [39.4, 56.4], count: 150, ageMed: 13, roomMed: 3, indoorPct: 0.702 },
  { name: "麗園國小", medPrice: 41.8, priceRange: [30.5, 47.7], count: 76, ageMed: 18, roomMed: 3, indoorPct: 0.723 },
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
