# 林口房貸試算（測試版）

林口置產工具箱中「房貸試算」單頁工具的**獨立線上測試版**，供自己、家人與少數客戶先測試介面與試算結果。

- 線上網址：https://s156843217.github.io/linkou-mortgage/
- 純前端（HTML + CSS + 原生 JS），無建置流程，直接開 `index.html` 即可執行。

## 檔案

- `index.html` — 介面與試算邏輯（由主專案 `my-project/mortgage.html` 複製改名；導覽列已移除跨頁死連結）
- `mortgage-data.js` — 林口各地段單價等參考資料
- `style.css` — 共用樣式（由主專案根目錄複製）

## 注意

這是主專案 `my-project` 的一份**複製**，非同一份。主專案改完不會自動更新，需手動同步後再 `git push`（GitHub Pages 約 1 分鐘重建）。測到正式 OK 後，會與學區、租約整合進一站式正式網站，此測試 repo 屆時功成身退。
