# ignition-skills

兩個給 Claude 載入的 user-level skill,用來校準 Claude 對 Ignition / SepaSoft 的回答,**不是** troubleshooting 知識庫,也**不是** code 產生器。

- `ignition-foundations/` — Ignition 8.1(SCADA)。SKILL.md + 11 references
- `sepasoft-foundations/` — SepaSoft Batch Procedure(MES, ISA-88)。SKILL.md + 10 references

## 這是什麼 / 為什麼

讓 Claude 講 Ignition / SepaSoft 時:不憑記憶亂下斷言、知道去哪查官方 docs、知道何時該請 user 在 Designer GUI 驗證。每個 fact 都附官方來源 URL,沒來源就標「待補」而非硬掰。

刻意只做概念校準,不承載 signature / option list / how-to / 客戶自製 framework。所以 forum 覆蓋率報告裡 FULL 命中率低是設計預期,不是缺陷 —— 細節見 `reports/`。

## 狀態

初版已完成並通過驗證(`reports/spec-implement.md`,全 GREEN),目前是**維護階段**。尚未部署 —— 部署方式是 user 人工檢核後,手動把兩個資料夾複製到 user-level skill 路徑(`~/.claude/skills/`),repo 本身不自動部署。

## 維護前先讀

`CLAUDE.md` 是這個 repo 的設計憲法與權威來源(來源紀律、排除清單、格式約束、語言策略)。改任何 skill 內容前先讀它。一句話版:**新增 fact 必附合格官方來源,不確定就標待補,絕不憑記憶補。**

## 目錄

- `ignition-foundations/`, `sepasoft-foundations/` — 交付物
- `reports/` — 建置 final report + 兩份 forum 覆蓋率評估 + 與 ignition-copilot 的比較
- `ignition-copilot/` — 外部比較對象,**非交付物,勿改**
- `CLAUDE.md` — 維護憲法
- 初版建置依據是一份 Notion spec,現已降級為歷史 rationale,維護階段以本 repo 現況為準(細節見 `CLAUDE.md` 開頭)
