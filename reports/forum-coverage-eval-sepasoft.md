# sepasoft-foundations Skill — Forum 涵蓋率評估報告

評估日:2026-05-16。受評對象:`D:\repo\ignition-skills\sepasoft-foundations\`
(SKILL.md + 10 個 references)。準則與前次 `ignition-foundations`
評估一致(FULL / PARTIAL / NONE),另依使用者指示加入「抽選時排除 skill
不適用 topic」的 in-scope gate。

## 1. 方法與一個須先聲明的事實

來源 `https://forum.inductiveautomation.com/tag/sepasoft`:Discourse JSON
分頁 page 0–2 共約 64 個 topic,page 3 以後為空。指定來源無法抽到 150。

依使用者決策「擴大來源湊到 150」+「排除 skill 不適用 topic」,執行:

- 廣抓:sepasoft tag 3 頁 + `tag/mes`、`tag/batch`(皆 404 不存在)+ 多組
  Discourse `search.json`(sepasoft / system.mes / recipe / phase / EBR /
  batch queue 等,含分頁)。去重後 SepaSoft 相關唯一 topic **201 個**。
  期間遇 forum HTTP 429 限流,停止再抓清單,以此為實際可得最大集。
- 粗過濾:以標題關鍵詞排除明確 out-of-scope(OEE/Downtime、SPC、
  Track&Trace、Web Services/SOAP、SAP/ERP/Business Connector、barcode、
  licensing/install、generic 非 MES noise)→ 粗排除 138,留 **63 個
  candidate**。
- 精過濾 + 普查:63 個 candidate **全部**做評估(census,非抽樣 —— 因
  in-scope 母體已遠小於 150)。每題由 subagent 抓 OP 後,先做 OP 層級
  in-scope 判定;真正 out-of-scope 標 **EXCLUDED**,排除於涵蓋率分母。

結論:**150 在此 forum 結構上不可達**。即使窮盡廣抓,SepaSoft 相關唯一
topic 僅 201;扣除非 Batch / install / licensing 後,真正落在
sepasoft-foundations(Batch Procedure)範圍內的只有 **29 個**。報告對 29
做涵蓋率統計,並據實記錄 150 的落差,而非以 out-of-scope 內容湊數
(那會違反使用者「排除不適用」的指示且使數字失真)。

抽樣偏差與限度:N=29 in-scope(census,非抽樣,無 seed)。粗過濾為標題式,
精過濾由 OP 內容修正。fetch 採逐一 + 429 退避,7 批皆回報無 FETCH_FAILED,
資料品質可靠。

## 2. 總體結果

63 個 candidate 普查:

| 等級 | 數量 |
|---|---|
| EXCLUDED(OP 判定為不適用) | 34 |
| FULL | 4 |
| PARTIAL | 24 |
| NONE | 1 |

對 in-scope 母體(29 = FULL+PARTIAL+NONE):

| 等級 | 數量 | 占 in-scope |
|---|---|---|
| FULL | 4 | 13.8% |
| PARTIAL | 24 | 82.8% |
| NONE | 1 | 3.4% |
| FULL+PARTIAL(有效貢獻) | 28 | 96.6% |

兩個鏡頭:

- 鏡頭 A「能否實質解決 in-scope 提問」:FULL 13.8%。低,但符合 skill 作為
  conceptual-grounding 的設計。
- 鏡頭 B「在適用範圍內是否表現正確」:28/29 提供正確框架或正確路由,
  唯一 NONE(82391)是真實 gap;零臆造、零錯答。在 skill 宣稱的 Batch
  範圍內,本次普查的覆蓋幾乎完整。

唯一 FULL 之外的近 FULL 同樣存在(skill 概念核心決定性命中、僅最後具體值
留待查證):79913(removeEntry + 禁 raw SQL + searchMESObjects 直接答到
明問)、77977(Enterprise vs site 執行拓樸直接解釋 docs 警語)、85678
(PLI/Auto State handling 模型 + enums 命中正確診斷軸)。

## 3. 四個 FULL

- **95446** Transfer In/Out Phase 作用 → `phases.md` base-phase 目錄直接、
  充分回答(Sync_Group、與 Synchronize 配對),sourced 非臆造
- **89184** batch script TypeError → `ebr-data-model.md` 指出
  getParameterValueAsString 首參須為 BatchQueueEntry,`path-syntax.md` 給出
  `:step.Complete` 路徑式,兩個問題都直接解掉
- **68508** Unit Procedure 可否 loop → `isa88-alignment.md` 的 ISA-88 階層 /
  validation 模型直接說明為何 UP/Operation 不可置於 loopback
- **91333** 去哪學 SepaSoft → `docs-decision.md` 路由問題,直接正確

四個 FULL 全部落在 skill 的概念核心(ISA-88 / base phase / EBR API /
docs 路由),印證 skill 在其設計靶心上有效。

## 4. PARTIAL 形態(24)

與 `ignition-foundations` 評估完全相同的 pattern:skill 給出正確的概念框架
與正確 docs/Designer 工具路由,在問題真正卡住處(特定 signature、
SP-version 行為、engine-state fault)停手,標「verify in docs」。這是
§6.1 sourced-fact 紀律與 index 哲學的設計預期結果,非缺陷。典型:

- 80761 path syntax 完全命中,但 enum 型參數解析行為 verify-only
- 97216 / 80325 AbstractMESObject version-on-save 模型解釋 error class,
  但 getBatchBOM/setBatchBOM enum 驗證契約 verify-only
- 103928 / 85678 / 68509 PLI/Auto command-state + Exposed UDT 模型正確,
  但具體 cascade 成因 / 延遲 root cause verify-only

## 5. 唯一的 NONE(真實 gap)

**82391 Attaching File or File Path to Electronic Batch Record**:skill 把
EBR 嚴格建模為 parameter / processing data(`ebr-data-model.md`),對
檔案 / 文件附加完全無 grounding,只能說明「EBR 是什麼」,答不到附加需求。
這是 29 個 in-scope 中唯一 skill 給不出相關概念的題。屬可考慮補強點,但
須注意:附檔到 EBR 偏 feature/how-to,可能本就在 conceptual-grounding 的
刻意範圍外 —— 列為觀察,是否補由使用者決定。

## 6. 母體結構觀察(對 forum 的事實)

- SepaSoft 相關唯一 topic 全 forum 僅約 201;真正 Batch Procedure
  in-scope 僅 29(≈14%)。SepaSoft 在此 forum 的流量壓倒性地由
  非 Batch module(OEE/Downtime、SPC、Track&Trace、Web Services、
  Business Connector)、install/licensing/module-faulted、Production
  model 啟動問題構成。
- 標題式粗過濾後的 63 candidate,OP 層級精判定有 34(54%)實為
  out-of-scope —— 連「看起來像 Batch」的標題,實質多為 install fault、
  `system.recipe`(Ignition 自帶非 SepaSoft)、OEE Equipment State Class、
  Production Model 不啟動。純 Batch Procedure 概念題在整個可得語料中稀少。
- 推論:任何「在此 forum 對 sepasoft-foundations 做大樣本涵蓋率」的要求,
  受語料上限制約,N 無法接近 150;29 已是窮盡廣抓後的實際 in-scope 上限。

## 7. Reference 命中分布(in-scope 29 的主要 ref)

| reference 檔 | 命中數 | 備註 |
|---|---|---|
| equipment-model.md | 7 | 多為 production-model 啟動/解析框架 |
| mes-object-model.md | 6 | link/UUID 解析、version-on-save |
| batch-lifecycle.md | 5 | command/state、Enterprise/site、template |
| phases.md | 4 | 含 1 FULL(95446) |
| ebr-data-model.md | 4 | 含 1 FULL(89184)、1 NONE(82391) |
| path-syntax.md | 1 | 80761 |
| isa88-alignment.md | 1 | FULL(68508) |
| docs-decision.md | 1 | FULL(91333) |
| mes-api-map.md | 0(主) | 大量 EXCLUDED 題的 name-drop 路由基礎,非主題承載 |
| verification-tools.md | 0(主) | 101728/98462 的次要路由支援 |

equipment-model / mes-object-model / batch-lifecycle 承擔過半 in-scope
負載。`mes-api-map.md` 與 `verification-tools.md` 從不作為主要 ref,但在
EXCLUDED 題的「這屬非 Batch module,路由出去」判斷中被反覆引用 —— 它們的
價值是邊界界定與橫向路由,符合設計,不應據此刪減。

## 8. 與 ignition-foundations 評估的對照

| 指標 | ignition(N=50,未預過濾) | sepasoft(N=29 in-scope,census) |
|---|---|---|
| FULL | 2% | 13.8% |
| FULL+PARTIAL | 54% | 96.6% |
| NONE | 46%(幾乎全為 out-of-scope) | 3.4%(1 題,真實 gap) |

差異主因是分母而非 skill 品質:ignition 評估含大量 out-of-scope 流量,
sepasoft 依指示先排除不適用。把母體限縮到「適用題」後,兩個 skill 呈現
一致行為 —— 在靶心上 FULL 命中、其餘以正確框架+路由貢獻、極少真實 gap、
零臆造。sepasoft 的 strict-FULL 13.8% 約為 ignition 未過濾 2% 的 7 倍,
正是「移除 out-of-scope 雜訊後」應出現的結果,佐證兩 skill 同一設計成立。

## 9. 結論與建議

- 作為「forum 問答覆蓋率」(in-scope):FULL 13.8%、有效貢獻 96.6%。
- 作為「Batch Procedure 防臆造概念地基 + 正確路由 + 正確界定非 Batch
  範圍」:29 題僅 1 真實 gap、零錯答,符合設計目標。EXCLUDED 34 題中
  skill 一致正確地辨識為非 Batch 並路由出去,邊界紀律有效。
- 報告數字須恆附定位:此 skill 價值在 Batch Procedure 的正確 mental
  model 與正確查證路由,並能擋掉 SepaSoft 生態中大量非 Batch 流量,不在
  取代 SepaSoft 解題或涵蓋 OEE/SPC/T&T/Web Services。

建議:

- 不建議在此 forum 追求 N=150 的 sepasoft 涵蓋率:語料上限使 in-scope
  ≤~29,150 不可達;若需更大 N,須改用 SepaSoft 官方 forum
  (forum.sepasoft.com)或官方支援案例庫為來源(屬範圍/來源決策,留給
  使用者)。
- 唯一真實 gap(82391,EBR 檔案附加)是否補強由使用者定;判斷點是「附檔
  到 EBR」算 conceptual grounding 還是 how-to —— 若維持 conceptual-only
  的設計,此題保持 NONE 是可接受的範圍選擇。
- 粗過濾的 54% 誤含率說明 SepaSoft 語料品質分散;若日後重評,建議直接
  以 OP 層級 in-scope 判定取代標題式粗過濾。

逐題明細:`.claude/eval2/res_b{1..7}.md`;pool 與分類:
`.claude/eval2/pool_raw.txt`、`candidates.txt`、`excluded.txt`。
前次 ignition 報告 `forum-coverage-eval.md` 與 skill 建置交付物
`report.md` 未被更動。
