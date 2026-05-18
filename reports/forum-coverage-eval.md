# ignition-foundations Skill — Forum 涵蓋率評估報告

評估日:2026-05-16。受評對象:`D:\repo\ignition-skills\ignition-foundations\`
(SKILL.md + 11 個 references)。`sepasoft-foundations` 不在本次範圍。

## 1. 方法

- 來源:`https://forum.inductiveautomation.com/c/ignition/6`,經 Discourse
  JSON API(`/c/ignition/6.json?page=0..6`)取 7 頁,去重後池子 199 個 topic。
- 抽樣:Python `random.seed(20260516)` + `random.sample`,抽 50 個,排除
  置頂 meta topic(id 12 / 9267)。樣本與 seed 記於
  `.claude/eval/sample50.txt`,可完整重現。
- 每個 topic 經 WebFetch 取原始發問(OP),由 5 個並行 subagent 依統一準則
  評估,逐題明細在 `.claude/eval/result_batch{1..5}.md`。

評分準則(對「這個 skill 是 conceptual-grounding 而非 troubleshooting DB」
的設計定位判定,刻意從嚴):

- FULL:skill 的 mental model / API map / scope 推理 / 驗證路由,直接且
  充分回答問題核心,答案實質正確且無臆造。
- PARTIAL:skill 給出正確框架與正確 docs/Designer 路由,但問題真正卡住的
  那一點(特定 component 行為、特定 driver、特定 8.3 行為)skill 只標
  「去查」而未承載。
- NONE:對問題核心無相關 grounding,屬 skill 刻意排除或僅點名的範圍。

抽樣偏差須先聲明:樣本取自分類的「latest」分頁,結構上偏向近期 8.3.x
topic。全時段隨機抽樣的 8.1 概念題占比應較高,FULL/PARTIAL 會略升。本報告
數字僅對「近期 forum 流量」這個母體成立,N=50 單次抽樣。

## 2. 總體結果

| 等級 | 數量 | 占比 |
|---|---|---|
| FULL | 1 | 2% |
| PARTIAL | 26 | 52% |
| NONE | 23 | 46% |
| FULL+PARTIAL(有效貢獻) | 27 | 54% |

單一數字會誤導,須用兩個鏡頭讀:

- 鏡頭 A「能否實質解決 forum 提問」:FULL 僅 2%。作為 forum 問答覆蓋率,
  分數低 —— 但這符合 skill 設計,它本就不是用來解 forum troubleshooting。
- 鏡頭 B「是否表現正確(不臆造、正確路由或正確婉拒)」:50 題中無任何一題
  skill 會產生錯誤或臆造的答案。23 個 NONE 全部落在 skill 明示排除的範圍,
  正確行為是婉拒並路由,而非硬答。沒有出現「該答卻答錯」。

關鍵正面發現:23 個 NONE 中,沒有任何一題是 skill 自身知識域(scope、
system.* 語意、Jython、binding 概念)內「應涵蓋卻漏掉」的真實 gap。全部是
driver / 環境 / licensing / UI how-to / 版本 bug 確認 / 非問題。在它宣稱的
範圍內,本次抽樣未發現覆蓋缺口。

## 3. PARTIAL 的一致形態

26 個 PARTIAL 幾乎是同一個 pattern:skill 提供正確的概念框架與正確路由,
在問題真正的「最後一哩」(特定 component property、特定 driver、特定
8.3.x 行為)停手,因為那違反 skill 的 §6.1 sourced-fact 紀律與 index 哲學。
這是設計預期的 modal 結果,不是缺陷。

其中約 5 題屬「近 FULL」:skill 已承載 load-bearing 概念,只差最後判斷或
具體值未給,概念核心其實決定性地幫上忙:

- 115465 Recipe 管理 → Transaction Group vs scripting 架構框架正確
- 115498 多 DB 連線 → 「每個 DB 連線各自一套 Store&Forward」是核心事實
- 111163 Designer 可跑 runtime 報錯 → Designer vs runtime scope 模型正中
- 115549 歷史 tag 不顯示 → Tag Provider vs History Provider 區分正中
- 114714 Perspective JS 注入 → server-side 模型 + 平台 vs 第三方界線正確

若把 FULL + 近 FULL 視為「概念核心決定性命中」,實質約 12%;能貢獻正確
框架/路由者 54%。

唯一 FULL(115396 Historic vs Basic Tag Group 是否獨立運作)是 skill 的
原型適用題:純概念、無版本依賴、無 component 細節。`tag-system.md` 的
Tag Group 執行模式 + provider/historian 獨立性,直接且充分回答。forum 上
這類純概念題比例不高,是 FULL 偏低的結構原因。

## 4. NONE 的分布(23 題)

| 類別 | 數量 | topic id |
|---|---|---|
| 安裝 / OS / launcher / Docker / JDBC 環境 | 5 | 115419 115388 114082 111823 112045 |
| 第三方 PLC / OPC driver 連線排錯 | 5 | 115387 115330 115316 29052 115472 |
| 純 UI component / layout how-to | 4 | 30531 39781 115323 115250 |
| Licensing / trial / 模組安裝 | 2 | 115431 115452 |
| 版本特定 Designer-UI bug 確認 | 2 | 115544 115449 |
| 症狀堆疊 / 無明確問題 | 2 | 115528 115454 |
| 內部 log 訊息 runtime 診斷 | 1 | 49316 |
| WebDev 模組 endpoint 契約 | 1 | 115409 |
| 硬體 / 行動掃碼整合 | 1 | 115217 |

全部對應 SKILL.md「紀律提醒」與 references 明示的排除或僅點名項。NONE 不代表
skill 失誤,代表 forum 真實流量大量落在 skill 刻意不承擔的領域。

## 5. Reference 命中分布(FULL+PARTIAL 共 27 題的主要 ref)

| reference 檔 | 命中數 |
|---|---|
| tag-system.md | 7 |
| perspective-basics.md | 5 |
| platform-services.md | 5 |
| system-api-map.md | 3 |
| expression-and-quality.md | 3 |
| scopes-lifecycle.md | 2 |
| data-and-named-queries.md | 1 |
| jython-27-gotcha.md | 1 |
| messaging-and-events.md | 0 |

- tag-system / perspective-basics / platform-services 承擔過半的範圍內負載,
  與 forum 流量重心(tag/historian、Perspective、alarm/security/redundancy)
  一致。
- `verification-tools.md`、`docs-decision.md` 從未作為「主要 ref」出現,但在
  幾乎每個 PARTIAL 的答案裡作為路由基礎設施被引用 —— 它們的價值是橫向支援,
  不是主題承載,符合設計。
- `messaging-and-events.md` 本次 0 命中。N=50 單次抽樣,這是弱證據而非結論;
  可能是樣本變異,也可能該主題 forum 出現率本就偏低。建議下一輪擴大樣本再
  判斷,不建議據此刪減。

## 6. 對 forum 母體的結構性觀察

近期 forum 流量主要由四類構成:component/UI how-to、driver/PLC/OPC 連線、
版本特定 bug 與 8.3.x regression、安裝/環境/licensing。這四類恰好是
ignition-foundations 的明示排除區。因此:

- skill 在 forum 上的「有效可服務面」本質上小,集中在 FULL + 強 PARTIAL
  那一塊概念題。這是定位選擇,不是品質問題。
- 8.3 敏感度是與當前流量最大的結構落差。skill pin 8.1、8.3 只標
  「對 Release Notes 查證」。樣本中大量 8.3.x topic 因此落入 PARTIAL/NONE。
  若使用情境是協助近期 forum 風格的問題,這是最該被告知使用者的限制。

## 7. 結論與建議

- 作為「forum 問答覆蓋率」:低(實質解決 2%,有效貢獻 54%)。
- 作為「防臆造的概念地基 + 正確路由」:本次抽樣 50 題零錯答、零臆造、
  概念域內零真實 gap,符合設計目標。
- 兩者不矛盾:此 skill 的價值在「讓 Claude 不亂答 Ignition 問題並導向正確
  查證」,不在「取代 forum 解題」。報告的覆蓋率數字應永遠附帶此定位,單獨
  引用 2% 會嚴重誤導。

建議:

- 對使用者明確設定預期:此 skill 降低 Ignition 答題的錯誤率與臆造率,
  不提供 component how-to / driver 排錯 / 版本 bug 確認。
- 8.3:若實際使用偏近期版本,考慮是否值得從「只標查證」升級為承載部分
  已穩定的 8.1→8.3 差異(成本 vs §9.3 廣度控制取捨,屬範圍決策,留給
  使用者)。
- `messaging-and-events.md` 0 命中僅記錄為觀察,不建議據單次 N=50 行動。
- 如需更穩的數字,擴大到 N≥150 並改為全時段(非僅 latest 分頁)隨機抽樣,
  可降低對近期 8.3 流量的偏倚。

逐題明細:`.claude/eval/result_batch{1..5}.md`;樣本與 seed:
`.claude/eval/sample50.txt`、`.claude/eval/pool.txt`。
