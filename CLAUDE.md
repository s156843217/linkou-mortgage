# CLAUDE.md — linkou-mortgage（房貸獨立測試站・退役中）

> ⚠ **不要在這個 repo 開發新功能。** 這是房貸試算的獨立測試副本，已排定 **2026 年 7 月底關站改跳轉頁**。
> 房貸頁的開發請去 `C:\repo\my-project`（過渡期）或 `C:\repo\linkou-toolbox`（收斂後）。
> 通用守則見 `~/.claude/CLAUDE.md`；SOP 見 `C:\repo\linkou-toolbox\docs\`。

## 基本事實

- 線上：https://s156843217.github.io/linkou-mortgage/ （push `main` → Pages 自動上線）。
- 但這個 repo 有一件**全生態系唯一**的東西：**實價登錄自動更新 pipeline**。

## ⚠ 自動更新 pipeline（關站前必須先遷移，見 DEPLOY.md 第 4 節）

- `.github/workflows/update-prices.yml`：每月 1 號（台灣 04:00）自動跑 `update_prices.py`，
  抓新北開放平台 API → 算各商圈近一年單價 → **覆寫 `mortgage-data.js` 的 `<<AUTO-ZONES-START>>`～`END` 段** → 自動 commit+push。
- 所以：**這裡的 `mortgage-data.js` 地段數字是全生態系最新的（真相來源）**，my-project 與 toolbox 的副本要從這裡人工搬數字回去。
- `update_prices.py` 會線上抓 `raw.githubusercontent.com/s156843217/linkou-school-zone/master/linkou-data.js` 取 HOUSE 門牌座標——**學區獨立站 repo 動之前必須先改這個 URL**。
- 手動觸發與驗證（本機無 Python，只能在雲端跑）：
  ```
  gh workflow run update-prices.yml
  gh run list --workflow=update-prices.yml --limit 1
  gh run watch <run-id> --exit-status
  ```
- Actions 自動 commit 後，本機要 `git pull` 才同步。

## 紅線

- `<<AUTO-ZONES-START>>`～`END` 之間**不准手改**（下次自動更新會蓋掉，改了也是白改）。
- 已拍板勿翻案（詳 `docs/DECISIONS.md`）：排除透天/別墅、商圈用門牌座標×多邊形、可購坪數含 1 車位 200 萬。
