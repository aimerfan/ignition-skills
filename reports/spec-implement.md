# 最終報告 — Ignition+Sepa Skill 建置

Spec:Notion「Ignition+Sepa Skill 實作 Spec」
(https://www.notion.so/3628ebada94581ac824cf524bde24d4a)。建置日 2026-05-16。

涵蓋初始 §5 baseline 建置,以及後續經 user 核可的 §6.2-3b 深度探索 pass。
本報告反映最終狀態。

## 1. 目錄樹

```
ignition-foundations/
├── SKILL.md
└── references/
    ├── system-api-map.md
    ├── scopes-lifecycle.md
    ├── jython-27-gotcha.md
    ├── perspective-basics.md
    ├── verification-tools.md
    ├── docs-decision.md
    ├── expression-and-quality.md      (discovery pass)
    ├── tag-system.md                  (discovery pass)
    ├── data-and-named-queries.md      (discovery pass)
    ├── messaging-and-events.md        (discovery pass)
    └── platform-services.md           (discovery pass)

sepasoft-foundations/
├── SKILL.md
└── references/
    ├── isa88-alignment.md
    ├── mes-api-map.md
    ├── ebr-data-model.md
    ├── batch-lifecycle.md
    ├── path-syntax.md
    ├── verification-tools.md
    ├── docs-decision.md
    ├── equipment-model.md             (discovery pass)
    ├── phases.md                      (discovery pass)
    └── mes-object-model.md            (discovery pass)
```

合計 23 檔(2 SKILL.md + 21 references:11 ignition + 10 sepasoft)。其中 8 個
標 (discovery pass) 的檔案為 §6.2-3b 深度探索 pass 新增(見 §9)。
結構符合 spec §2.1 / §2.2 的彈性精神(允許新增 §5 以外子文件)。
`.claude/PROGRESS.md` 與 `.playwright-mcp/` 為 build scratch,非交付物,不列入
skill 結構。

## 2. 各檔主題與來源 URL 數

ignition-foundations(來源:docs.inductiveautomation.com,另 1 條 IA forum):

| 檔案 | 主題 | 約來源 URL 數 |
|---|---|---|
| system-api-map.md | system.* 子模組目錄、各子模組用途+scope、protocol 清單、8.1→8.3 差異 | 4 |
| scopes-lifecycle.md | 三個 script scope、Designer/Script Console scope、script 類型→scope、Project Library 可見性/生命週期、誤區 | 4 |
| jython-27-gotcha.md | Jython 2.7/JVM、Java import 慣用法、Java exception 捕捉、Java date vs datetime、無 C-extension、stdlib caveat | 6 |
| perspective-basics.md | View/Component/Property/Binding/Session、prop 類別、session prop、binding 種類、transform 順序、陷阱 | 6 |
| verification-tools.md | Script Console、Output Console、Tag Browser、Gateway logs、wrapper logs、症狀→工具、CLAUDE/USER 標註 | 6 |
| docs-decision.md | 站點結構、Appendix 分節、查得到 vs 查不到、URL pattern、SPA caveat、版本 pin | 3 |
| expression-and-quality.md | expression≠scripting≠SQL、expression function 目錄、runScript caveat、qualified value/qualityOf | 5 |
| tag-system.md | Tag Provider vs History Provider、UDT def/instance/`{P}` 參數、Tag Group 三模式、tag event script scope+8.1.32 變更 | 5 |
| data-and-named-queries.md | Named Query Value vs QueryString(prepared-stmt 安全、不可用於 table/col)、Transaction Group、Query Browser 1000-row | 4 |
| messaging-and-events.md | system.util.sendMessage vs system.perspective.sendMessage、message handler async/scope、Gateway Event Script 類型 | 4 |
| platform-services.md | alarm pipeline/escalation、Security Level/IdP、redundancy(config 限 Master)、project inheritance、SFC、store&forward;OPC/Reporting/GatewayNet 點名 | 7 |

sepasoft-foundations(來源:docs.sepasoft.com,另 www.sepasoft.com):

| 檔案 | 主題 | 約來源 URL 數 |
|---|---|---|
| isa88-alignment.md | ISA-88 四層、collapse 規則、Recipe=Procedure、物理 vs 程序、Templates 非階層、誤區 | 5 |
| mes-api-map.md | system.mes.* 目錄、system.mes.batch 子命名空間、module 需求對應、scope 通則 | 5 |
| ebr-data-model.md | EBR 定義/類型、官方介面(getBatchEBR/getRecipeEBR)、tag collector+vertical table、getParameterValue 解析 | 5 |
| batch-lifecycle.md | command/state enum、Master vs Control recipe、addEntry+START 啟動、parent/child、template copy/link、參數傳播 | 4 |
| path-syntax.md | base syntax、`/` `{}` `:` `.` token、實例、出現場合、誤區 | 2 |
| verification-tools.md | Batch Phase Manager、Batch Recipe Editor、Script Console+searchMESObjects、症狀→工具、CLAUDE/USER 標註 | 5 |
| docs-decision.md | 站點/ClickHelp、分節、查得到 vs 查不到、SPA `#!` caveat、Release Notes 位置、SP-gating | 4 |
| equipment-model.md | Production Equipment Model、Process Cell/Unit/Unit Class、Equipment Manager、rename=新 instance 陷阱、OPC path 耦合、保留字元 | 1 |
| phases.md | phase=最低工作層、Equipment vs Non-Equipment、base phase 目錄、Script/Timer/Document、PLI vs Auto、安全警示 | 2 |
| mes-object-model.md | AbstractMESObject、link/UUID 解析、Formula vs Recipe(1:1、3.81.11 RC1+)、排程 vs batch queue | 3 |

## 3. §5 以外納入的主題(供 user review / 刪減)

初始建置時順帶納入(opportunistic):

- isa88-alignment:ISA-106(continuous process 程序自動化)— SepaSoft recipe
  與 ISA-88 並列引用
- isa88-alignment / batch-lifecycle:Template linked vs unlinked 行為與 SP
  版本邊界(3.81.12 SP4/SP5、4.83.1 SP4/SP5)
- mes-api-map:system.mes.batch 子命名空間明確列舉(formula/phase/queue/
  recipe/unit/unitclass);sibling system.*(recipe、ws、barcode.scanner、
  instrument)
- ebr-data-model:BatchControlRecipe/BatchControlLogic 組成;getParameterValue
  idle-vs-running 解析;getEntryLinks 分頁
- batch-lifecycle:addEntry 完整參數集;Enterprise parent/child 指令限制與
  process-cell targeting 方法
- verification-tools(sepa):Batch Phase Manager Base Phase Type / Exposed
  欄;Batch Recipe Editor 元件屬性;phase→recipe 傳播版本 gate(3.81.11
  RC2 / SP9)
- docs-decision(sepa):MES 4.0 / Ignition 8.3 發布(2025-09-16)、Release
  Notes URL

§6.2-3b 深度探索 pass 系統性新增(8 個新檔,清單見 §9 — 這是供你刪減的
discovery inventory)。

## 4. 驗證結果(§8,最終狀態,含探索後重驗)

- §8.1 結構 — GREEN。23 檔皆存在且非空;兩份 SKILL.md 有 YAML frontmatter +
  §3 五部分;兩份 SKILL.md Reference 索引與實際 references/ 完全一致
  (11 與 10);相對路徑可解析。
- §8.1 URL 可達 — GREEN。初始抽樣 11 條(6 IA WebFetch + 5 Sepasoft
  Playwright);探索後另抽樣 10 條新來源(6 IA + 4 Sepasoft)。皆可達,
  均達 ≥10 要求。
- §8.2 內容抽查 — GREEN。初始 IA 6/6 verbatim 複驗通過、Sepasoft 5 頁標題與
  內容相符;探索後 IA 6/6 新 fact verbatim 複驗通過、Sepasoft 4/4 頁標題+
  內容相符。命中率 ~100%,遠高於 80% §6.4 門檻。未觸發中斷。
- §8.3 覆蓋迴圈 — GREEN。初始 ~21 個 LLM 易錯題 + 探索後 ~16 個新主題易錯題
  評估;每題皆有 sourced 事實或正確「查 docs / 請 user 驗證」指向。各一輪,
  無 gap。
- §8.4 跨環境 — GREEN。全檔為純 markdown;grep `/mnt/skills`、`~/.claude`、
  `/home`、`C:\Users`、`/Users`、`D:/repo`、`file://`、`compatibility:`、
  `allowed-tools:` 在兩個 skill(含新檔)皆無 match。frontmatter 僅
  name+description。跨 skill 引用為散文、無 hardlink。

整體:GREEN,附帶 §5 所列的待補/pointer 項(依 spec §6.1/§6.3 為刻意設計,
非失敗)。

## 5. 已知未驗證 / 待補項

- ebr-data-model.md:坊間說的「default 取 last entry、begin 類取 first」
  extraction rule 官方 docs 未見 verbatim;改記錄 docs 實有的
  live-vs-persisted(controller active+loaded vs BatchControlLogic)規則,
  並明標 first/last 說法未驗證。
- ebr-data-model.md:「internal DB schema 非公開契約」框為 guidance/推論
  (與已記錄的 purge API 及 component/scripting 存取一致),非 doc 引用。
- jython-27-gotcha.md:NumPy/pandas/SciPy 不可用來源為 IA 官方 forum primer
  (§6.1 高可信社群),明標為社群確認非 docs verbatim。per-module Jython
  stdlib 差異標「在 Script Console 驗證」,未斷言。
- sepasoft verification-tools.md:Designer Project Browser「MES Scripts /
  Batch Scripts」資料夾名未取得 verbatim,標「請在 Designer 確認」。
- expression-and-quality.md:quality 透過 expression tree 的傳播未斷言
  (僅 qualityOf 有 verbatim),標 verify。
- platform-services.md:Gateway Network / OPC UA vs DA-HDA / Reporting 為
  刻意 pointer(只點名,符合 index 哲學與 §9.3 廣度控制),非詳細斷言。

無覆蓋 gap(每個 §5 baseline 主題皆涵蓋;docs 無明確陳述者改為「verify」)。

## 6. 版本覆蓋(Ignition 8.1→8.3;SepaSoft forward)

- Ignition:system-api-map 標 8.3 新增(system.eventstream、system.historian、
  system.kafka、system.secrets)與 system.gui / system.nav 在 8.3 索引消失為
  版本敏感(未斷言為移除 — 標需對 8.3 docs / Release Notes 查證)。
  scopes-lifecycle、jython、perspective、docs-decision、以及探索新檔皆帶
  Version sensitivity 段,pin 8.1 並指向 8.3 + Release Notes。
- SepaSoft:每個 reference 帶 SP-gated 版本註(例 3.81.6 RC1、3.81.10 SP7、
  3.81.11 RC1/RC2/SP9、3.81.12 SP2/SP4/SP5、4.83.1 SP4/SP5);docs-decision
  指向 MES 3.x vs 4.0 / Ignition 8.3 與 Release Notes 下載位置。

## 7. 過程中非預期狀況與處理

- Harness:初始無 Chrome MCP;user 安裝 Playwright MCP(重設為 headless)。
  docs.inductiveautomation.com 經 WebFetch 可取;docs.sepasoft.com 是
  ClickHelp SPA,須 Playwright(navigate → wait_for/title → snapshot
  `target: article` 以避開龐大 content-tree)。`#!` hashbang URL 須等 SPA
  route resolve 才讀。
- 許多 SepaSoft 子模組 landing 頁(與 Ignition system.tag/date)是 function-
  list 頁、無 summary 句;用功能性描述並標註,絕不杜撰成引用。
- spec 指名的「Referencing Parameters」章節存在於
  /articles/user-manual/referencing-parameters-in-batch-recipes,path-syntax
  完整涵蓋。
- 一個 batch-lifecycle 待補(phase/param 傳播)後以 Using Parameters 頁的
  sourced 事實回填。
- 權限模型:依 user 指示,settings.json allowlist 僅 network-read(WebFetch
  域名、WebSearch、唯讀 Playwright navigate/snapshot/close/wait_for);
  file/bash 跟隨 active mode。
- §6.2-3b 探索 pass:Ignition recon 用 Explore subagent 唯讀測繪(只做
  section→URL map,不抽 fact 以保 §6.1);Sepasoft 逐 cluster 第一手抓。
  依 user 決策維持 §9.3(非 Batch 只點名、8.3 只標註)。

## 8. 建議 user 後續

- 在乾淨 Claude session(Code 與 chat 各一)載入兩個 skill,用 §8.3 風格題目
  測 trigger 與 reference 命中。
- review §3 / §9 的 §5 以外主題,刪減超出範圍者。
- 決定 §5 未驗證項:接受「verify」框架,或在實際 Designer / EBR Viewer 確認
  後收緊文字。
- 核可後手動部署到 user-level skill 路徑(依 spec §2,建置刻意不自行部署)。
- 部署前後可刪 `.claude/PROGRESS.md` 與 `.playwright-mcp/`(build scratch)。

## 9. §6.2-3b 深度探索 pass — discovery inventory(供刪減)

user 核可的計畫決策:Sepasoft 非 Batch module 維持 §9.3 只點名;
Ignition 8.1→8.3 維持只標註;新主題直接 fold 進兩個 skill;範圍內不設數量
上限,以內容判斷停止。

新增 reference 檔(以下全為 §5 baseline 以外,皆為刪減候選):

ignition-foundations(+5):

| 檔案 | 主題 | 約來源 URL 數 |
|---|---|---|
| expression-and-quality.md | expression≠scripting≠SQL(無 statement/變數)、expression function 14 類目錄、runScript caveat、qualifiedValue/qualityOf | 5 |
| tag-system.md | Tag Provider vs History Provider、UDT def/instance/`{P}`、Tag Group Direct/Driven/Leased、tag event script Gateway scope + 8.1.32 Value Changed 變更 | 5 |
| data-and-named-queries.md | Named Query Value vs QueryString(prepared-stmt 安全、不可用於 table/col、injection)、Transaction Group、Query Browser 1000-row 預設 | 4 |
| messaging-and-events.md | system.util.sendMessage vs system.perspective.sendMessage、component message handler async/scope、Gateway Event Script 類型 | 4 |
| platform-services.md | alarm pipeline/escalation、Security Level/IdP、redundancy(config 限 Master)、project inheritance、SFC、store&forward;OPC/Reporting/GatewayNet 點名 | 7 |

sepasoft-foundations(+3):

| 檔案 | 主題 | 約來源 URL 數 |
|---|---|---|
| equipment-model.md | Production Equipment Model、Process Cell/Unit/Unit Class、Equipment Manager、rename=新 instance 陷阱、OPC-path 耦合、isProductionModuleStarted、保留字元 | 1 |
| phases.md | phase=最低工作層;Equipment vs Non-Equipment;base phase 目錄(Allocate/Document/Equipment/E-Signature/Script/Timer 等);PLI vs Auto;安全警示 | 2 |
| mes-object-model.md | AbstractMESObject、link/UUID 解析、Formula vs Recipe(1:1 對 Master、3.81.11 RC1+)、排程 vs batch queue | 3 |

探索後重驗結果已併入 §4(全 GREEN);新增的 verify/pointer 項已併入 §5。
