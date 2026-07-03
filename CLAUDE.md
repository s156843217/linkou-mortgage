# CLAUDE.md — linkou-mortgage（房貸獨立測試站・退役中）

> ⚠ **不要在這個 repo 開發新功能。** 這是房貸試算的獨立測試副本，已排定 **2026 年 7 月底關站改跳轉頁**。
> 房貸頁的開發請去 `C:\repo\my-project`（過渡期）或 `C:\repo\linkou-toolbox`（收斂後）。
> 通用守則見 `~/.claude/CLAUDE.md`；SOP 見 `C:\repo\linkou-toolbox\docs\`。

## 基本事實

- 線上：https://s156843217.github.io/linkou-mortgage/ （push `main` → Pages 自動上線）。

## 自動更新 pipeline（**2026-07-03 已遷入 toolbox**，這裡只剩舊副本）

- 整合站 linkou-toolbox 已有自己的同套 pipeline，且抓自己的 linkou-data.js；**房貸數字的真相來源已改為 toolbox**。
- 本 repo 的 cron 保留到關站（讓獨立站數字撐到最後），關站時只需刪 `.github/workflows/update-prices.yml`。
- ⚠ 本 repo 的 `update_prices.py` 仍抓學區獨立站（linkou-school-zone master）的 raw 檔——所以那個 repo 在本站關掉前不能刪。

- 運作方式：每月 1 號（台灣 04:00）自動跑 `update_prices.py`，抓新北開放平台 API → 算各商圈近一年單價 → 覆寫 `mortgage-data.js` 的 `<<AUTO-ZONES-START>>`～`END` 段 → 自動 commit+push。
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
