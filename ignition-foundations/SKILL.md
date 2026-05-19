---
name: ignition-foundations
description: >-
  Conceptual grounding for Ignition 8.1 (SCADA platform by Inductive
  Automation): system.* scripting API surface, execution scopes, Jython 2.7
  behavior, and Perspective. This is a foundation skill — load it whenever a
  task plausibly touches Ignition: scripting, system.* calls, execution
  scope, Jython 2.7 / Java interop, tags or UDTs, Perspective
  bindings/props, expressions, named queries, messaging, or alarms. Loading
  is cheap and guessing an API signature or scope here is high-risk, so load
  it eagerly. Read this SKILL.md first; it is an index, not the answer — for
  any concrete signature, option list, or version-specific behavior, open the
  relevant references/ file and verify against docs.inductiveautomation.com
  before answering. Covers 8.1 with 8.1 to 8.3 version-sensitive notes
  flagged inline.
---

# Ignition Foundations

## 平台定位

Ignition 是 Inductive Automation 的工業應用平台,常用於 SCADA,並可延伸到
HMI、報表、MES(SepaSoft 等第三方 module 建構於其上)。它是一個 server-centric
平台,不是函式庫或單機程式。

核心架構名詞與關係:

- Gateway:中央 server,執行 Gateway-scope script、tag、資料庫連線、專案託管
- Designer:開發工具,在此編輯專案;Designer 自身也會執行 code(Script
  Console),但那是 Designer scope,不等於 Gateway
- Vision Client / Perspective Session:兩種前端執行環境。Vision Client 跑在
  client JVM;Perspective Session 跑在 Gateway 上(不是瀏覽器),透過瀏覽器呈現
- scripting 語言是 Jython 2.7,跑在 JVM 上

此節僅校準最基本理解。具體 fact(scope 可用 API、binding 種類、signature 等)
在 `references/` 子文件,不在此展開。

## 紀律提醒

- reference 子文件是索引與 mental model,不是最終答案。具體 API
  signature、method 名、回傳結構、option 列舉、版本特定行為,一律以
  docs.inductiveautomation.com 為終點 —— skill 內的概念總結不足以作為
  最終答覆來源。不要因為「reference 已有簡短描述」就略過查 docs;那段
  描述的作用是讓你知道該查什麼、去哪查,不是替代查證
- 不要憑記憶湊 signature 或 method 名
- 版本敏感:本 skill 以 8.1 為主。8.1 → 8.3 之間有變動的 API/概念,子文件以
  「Version sensitivity」段標出;陳述版本特定行為時必須帶版本
- 分辨平台標準行為與客戶自製 framework。客戶 project 內的封裝(自製 library、
  命名慣例)不屬平台知識,不要當成 Ignition 內建來陳述
- 未經官方文件或高可信來源驗證的內容,明確標示為推測,不寫成斷言
- scope 是最常見誤判來源:回答 scripting 問題前先確定 code 跑在哪個 scope
- plausibly 屬本 skill 範圍(定位 / 這是什麼 / 跑在哪個 scope / 去哪
  查證)但 reference 無錨點、索引也帶不到的問題:不可回「找不到」或憑
  記憶答而停。先去 docs.inductiveautomation.com 查證;查證後仍判斷
  skill 缺概念錨點,主動向 user 標明「這可能是 skill coverage gap」,
  簡述主題、缺口、最終哪個官方來源答出,供 user 回饋。但 user 要的是
  本 skill 刻意排除的 how-to / signature / option / troubleshooting 時
  不算 gap,指向官方 docs 即可,不誤報

## Reference 索引

用任務反查子文件:

- 想知道某功能屬哪個 `system.*` 子模組、在哪個 scope 可用 → 讀
  `references/system-api-map.md`
- 要判斷 code 跑在哪個 scope、Project Library 在各 scope 的可見性 → 讀
  `references/scopes-lifecycle.md`
- 處理 Jython 2.7 / Java 整合 / 為何 numpy 不能 import / Java exception 捕捉 →
  讀 `references/jython-27-gotcha.md`
- 處理 Perspective binding、props vs custom vs session、transform 順序 → 讀
  `references/perspective-basics.md`
- 處理 expression 與 scripting/SQL 的分別、expression function 目錄、
  qualified value / quality → 讀 `references/expression-and-quality.md`
- 處理 UDT(parameter/inheritance)、tag provider vs history provider、
  tag group rate、tag event script scope/threading → 讀
  `references/tag-system.md`
- 處理 Named Query 參數安全、binding/Transaction Group、Query Browser → 讀
  `references/data-and-named-queries.md`
- 處理 system.util.sendMessage vs system.perspective.sendMessage、message
  handler async、Gateway Event Script → 讀 `references/messaging-and-events.md`
- 需要 Alarming pipeline / Security level / Redundancy / Store&Forward /
  Project Inheritance / SFC 等平台服務的校準 → 讀
  `references/platform-services.md`
- 不確定某事實要 user 用 Designer 哪個工具驗證 → 讀
  `references/verification-tools.md`
- 要去 docs 查、不知道查哪個 section 或 URL 怎麼構造 → 讀
  `references/docs-decision.md`

## 標準動作

明確分兩類。Claude 在對話中不可把需要 user 操作的動作寫成自己能跑。

Claude 可直接執行:

- 不確定某 API signature/scope → 查 docs.inductiveautomation.com 對應頁
  (URL pattern 見 `references/docs-decision.md`)
- 需要某主題的概念性 mental model → view 對應 `references/` 子文件
- 不確定版本特定行為 → 查對應版本 docs 與 8.1→8.3 Release Notes,並在回答中
  標版本

Suggested user actions(需 user 在 GUI 操作,Claude 只能提示):

- 不確定某 API 是否實際存在於此版本 → 請 user 在 Designer 的 Script Console
  跑 `dir(...)` / import 測試(Script Console 是 Designer scope,結果不代表
  Gateway/Client scope)
- 不確定 tag 是否存在、其 datatype/quality → 請 user 在 Tag Browser 檢視
- Gateway-scope script 錯誤未現於 Console → 請 user 看 Gateway Status >
  Diagnostics > Logs,或 wrapper logs

詳見 `references/verification-tools.md` 的「症狀 → 工具」對照與
Claude/USER 標註。
