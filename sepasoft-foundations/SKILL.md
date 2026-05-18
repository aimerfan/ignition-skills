---
name: sepasoft-foundations
description: >-
  Conceptual grounding for the SepaSoft Batch Procedure module on Ignition
  (MES, ISA-88 batch): ISA-88 four-layer model, system.mes.* API surface, EBR
  data model, batch lifecycle/state machine, and SepaSoft parameter path
  syntax. Use when a task involves SepaSoft batch recipes, phases, EBR data,
  system.mes scripting, or any question about Batch Procedure behavior where
  guessing structure or an API would be risky. Read this SKILL.md first, then
  selectively open the referenced files under references/ for the topic at
  hand. Based on current stable release with known forward changes flagged
  inline.
---

# SepaSoft Foundations

## 平台定位

SepaSoft 是建構於 Ignition 平台上的 MES module suite,不是獨立產品。它分成多個
module:Batch Procedure、OEE/Downtime、SPC、Track & Trace、Business Connector
等。本 skill 聚焦 Batch Procedure module;其他 module 只在
`references/mes-api-map.md` 點到名,不深入。

核心架構名詞與關係:

- 跑在 Ignition Gateway 上,scripting API 在 `system.mes.*` 命名空間
- 程序模型對齊 ISA-88 四層:Procedure / Unit Procedure / Operation / Phase
  (頂層 Procedure 即 Recipe)
- 物理模型獨立於程序模型:Process Cell / Unit;執行時 Unit 與 Unit Procedure
  一對一
- 一個 batch 執行的是由 Master Recipe 產生的 Control Recipe;執行歷史經
  EBR(Electronic Batch Record)介面存取

此節僅校準最基本理解,具體 fact 在 `references/` 子文件。

## 紀律提醒

- 不確定的 `system.mes.*` signature/行為,去 docs.sepasoft.com 查,不憑記憶
- 版本敏感性極強:SepaSoft 行為大量以 service pack 為界(例 3.81.12 SP5、
  4.83.1 SP5、MES 3.0 vs 4.0)。陳述行為必帶版本,並參照
  www.sepasoft.com/downloads 的 Release Notes
- 分辨 ISA-88 標準 / SepaSoft 平台行為 / 客戶自製 recipe・phase。客戶命名的
  特定 phase、recipe、batch 不屬平台知識
- internal DB schema、vertical table 結構不是公開契約,不要建議 raw SQL,也不
  要把內部結構當穩定事實陳述
- 未經官方文件或高可信來源驗證的內容,標為推測或待補,不寫成斷言

## Reference 索引

用任務反查子文件:

- 處理 batch 階層、不確定 Recipe/Procedure/Unit Procedure/Operation/Phase
  關係或誤把 folder/Master-Control 當階層 → 讀 `references/isa88-alignment.md`
- 要知道某功能屬哪個 `system.mes.*` 子模組、需要哪個 module → 讀
  `references/mes-api-map.md`
- 處理 EBR / 參數歷史 / tag collector / 為何同名多筆 → 讀
  `references/ebr-data-model.md`
- 處理 batch 執行狀態、command/state、Master vs Control recipe、template
  copy/link → 讀 `references/batch-lifecycle.md`
- 解讀或撰寫參數路徑、`{}` placeholder、`:` 與 `.` 的分別 → 讀
  `references/path-syntax.md`
- 處理 Process Cell/Unit/Unit Class、Equipment Manager、rename 陷阱、
  equipment path / OPC 耦合 → 讀 `references/equipment-model.md`
- 處理 phase 種類(equipment vs non-equipment)、base phase 目錄、Script/
  Timer/Document phase、PLI vs Auto handshake → 讀 `references/phases.md`
- 處理 AbstractMESObject / MESObjectLink / UUID 解析、Formula vs Recipe、
  排程 vs batch queue → 讀 `references/mes-object-model.md`
- 不確定 batch/recipe/phase 結構要 user 用哪個 SepaSoft 工具驗證 → 讀
  `references/verification-tools.md`
- 要去 docs.sepasoft.com 查、SPA 抓取注意事項、Release Notes → 讀
  `references/docs-decision.md`

## 標準動作

明確分兩類。Claude 不可把需要 user 操作的動作寫成自己能跑。

Claude 可直接執行:

- 不確定 `system.mes.*` signature/行為 → 查 docs.sepasoft.com 對應頁
  (clean URL pattern 與 SPA 注意事項見 `references/docs-decision.md`)
- 需要某主題 mental model → view 對應 `references/` 子文件
- 不確定版本特定行為 → 查 docs 內 Note/Warning 版本註記,並參照
  www.sepasoft.com/downloads Release Notes,回答中標版本

Suggested user actions(需 user 在 GUI 操作,Claude 只能提示):

- 不確定某 phase 是內建 base type 還是使用者建立 → 請 user 在 Batch Phase
  Manager 看該 phase 的 Base Phase Type 欄
- 不確定某 step 的 parameter 細節或 recipe 結構 → 請 user 在 Batch Recipe
  Editor 開該 recipe 檢視
- 不確定某 MES 物件是否存在 → 請 user 在 Designer Script Console 跑
  `system.mes.searchMESObjects`

詳見 `references/verification-tools.md` 的「症狀 → 工具」對照與
CLAUDE/USER 標註。
