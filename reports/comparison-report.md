# Ignition 能力擴充包比較報告:ignition-copilot vs ignition-foundations

前提說明:本報告以 runtime-agnostic 知識資產為基準,只評內容品質與實用價值,不計載入機制、entry point、巢狀結構等部署因素。兩包設計類別不對等(foundations 是概念校準;copilot 是 authoring framework + PRP 編排 + validators),報告分「全景比較」與「聚焦重疊知識層」兩段,結尾給結論與取捨建議。所有行數為實讀後的量級估計,非精確值。

---

## 第一段:全景比較(整包對整包)

### 規模與構成

| 項目 | ignition-foundations | ignition-copilot |
|---|---|---|
| 總量級 | 約 1,300 行 | 約 11,000+ 行 |
| 構成 | SKILL.md + 11 個 reference | copilot-instructions + README + TODO + knowledge/(13 檔)+ 5 個 skill(SKILL.md + references + Python validators) |
| 性質 | 純概念校準 | knowledge(what is true)/ skill(what to do)/ ground-truth(this project)三層 + PRP 編排 |
| 可執行資產 | 無 | 5 支 Python validator(jython / sql_lint / named_query / tag_json / prp)+ new_prp 產生器 |
| 距離產物 | 遠(刻意)。輸出是「該信什麼、去哪查、請 user 做什麼」 | 近(tags/SQL/scripting)。輸出是 artifact + validator + 誠實降級報告 |

量級差約 8 倍,但這不是「誰比較完整」的問題,而是兩者解的是不同問題:foundations 解「不要讓模型對 Ignition 亂下斷言」,copilot 解「把 Ignition artifact 做出來且不幻覺欄位」。

### 涵蓋範圍(廣度)

兩者廣度互有領先,不是包含關係:

- foundations 獨有的廣度:平台服務概念層——Alarm Notification Pipeline、Security Levels / Identity Provider、Redundancy、Project Inheritance、SFC、Store and Forward、Transaction Group、Gateway Network。copilot 的 knowledge/ 完全沒有這些主題的概念檔(TODO.md 把 alarm pipelines 等列為未來 skill,等於概念層也缺)。
- copilot 獨有的廣度:`system.db/tag/util/perspective` 的 function matrix 與 code pattern、Ignition data type catalog + 四大 PLC 協定(S7 / Modbus / AB Logix / OPC UA)的 register→type 對照、5 dialect SQL 矩陣、historian / alarm-journal 的 SQL schema、PRP 規劃與執行的完整流程紀律。foundations 完全沒有這些。

結論:foundations 是「平台全景的薄校準」,廣但淺,且涵蓋 copilot 刻意 defer 的服務概念;copilot 是「三個 domain 的厚實作 + 編排」,在它覆蓋的範圍內極深,範圍外直接承認沒有。

### 資訊密度與深度

- foundations:概念密度高,每檔 85–120 行,幾乎零 code。一行一個校準點或一個誤判修正,沒有冗餘。深度停在「mental model + 該去 docs 哪頁」,刻意不進 signature。
- copilot:資訊密度與深度都顯著更高,且形態多元——function matrix 表、before/after code、決策樹、output contract、可執行 validator、完整 worked example(走完 7-step / 7-phase)。tag-json-schema.md 單檔 460+ 行,對照真實 export 標註每個欄位 verified / inferred;performance.md、historian-queries.md 含可直接調整的 SQL template 與 EXPLAIN 程序。

深度上 copilot 全面領先,代價是維護面大 8 倍。

### 正確性紀律(epistemics)— 這是兩包最值得對比的維度

兩者反幻覺意識都強,但錨點不同,風險輪廓也不同:

foundations 的錨是官方文件:

- 幾乎每個事實陳述都附 docs.inductiveautomation.com 的具體頁面 URL,逐行可回溯。
- 明確標示「未在本次 build 中逐字驗證」的內容為推測(例:expression quality propagation、numpy 不可用標為 community-confirmed 非 docs verbatim 並附 forum URL)。
- 每檔結尾有 8.1→8.3 Version sensitivity,陳述版本特定行為必帶版本。
- 明確區分 [CLAUDE](可自行查 docs)與 [USER](需在 Designer/Gateway GUI 操作),禁止把 user 動作寫成自己能跑。
- 由於它根本不斷言 signature,幾乎沒有「產出可被執行但其實錯」的風險面。

copilot 的錨是 ground-truth + confidence gate:

- 三級 ground-truth 優先序、Verified/Inferred 強制二分、confidence marker(HIGH/MEDIUM/LOW + ACK)、Known unknown 顯式標註、validator 內建 ground-truth 欄位覆蓋的反幻覺偵測。anti-sycophancy.md 是這套紀律的核心。
- 但有實質風險面:數個核心 schema 自承為 inferred——tag-json-schema 的 `valueSource` 除 opc/memory 外全部未觀測(expr/db/derived/reference 是問號)、UDT 繼承未觀測、historian 欄位與 alarm-journal 欄位整檔標 inferred。在 ground-truth 缺席時,這些會輸出「parse 得過但 import 失敗」的 artifact;validator 只擋結構不擋語意。
- 對官方文件的逐點引用遠少於 foundations,主要靠「對你的部署驗證 / 貼一筆 row 來」。

兩者紀律都不是裝飾,是設計核心。差別在:foundations 用「不斷言 + 全程引用」把風險壓到接近零但實用性也低;copilot 用「敢斷言 + 標記信心 + validator」換取高實用性,但留下 inferred-schema 這個真實風險區,且該風險只在 ground-truth 被填充後才真正關閉。

### 維護負擔與內部一致性

- foundations:面小(1,300 行),doc-anchored,隨官方文件演進即可,內部未見矛盾。
- copilot:面大(11,000+ 行),ground-truth 依賴尚未兌現(多個 validator 設計成「ground-truth 累積後才收緊」),且發現一處內部不同步——TODO.md(狀態日期 2026-04-26)仍把 `ignition-scripting` 列在 Layer 2 待辦,但該 skill 已完整存在(SKILL.md + anti-patterns + validate_jython.py,task-routing.md 也標 Available)。roadmap 與現況脫節,屬可修正的小瑕疵,但反映大體積帶來的同步成本。

---

## 第二段:聚焦重疊知識層(apples-to-apples)

兩包真正可直接對比的是這幾個共同主題。逐項對照:

| 主題 | foundations | copilot |
|---|---|---|
| Scope / lifecycle | `scopes-lifecycle.md`:三 scope 模型 + Designer 第四 context,逐句引 docs,誤判 state→correction | `scope-semantics.md`:四 scope 表 + 「5 秒 blocking call 在各 scope 的後果」表 + 三種 cross-scope async pattern 含 code |
| Jython 2.7 | `jython-27-gotcha.md`:聚焦 JVM 本質、Java exception 捕捉、numpy 為何不可,附 docs/forum URL | `jython-limits.md`:Python3 缺失特性對照表 + quick-scan grep regex + Java interop code |
| Tag 系統 | `tag-system.md`:provider vs historian、UDT param、tag group 三模式、8.1.32 行為變更帶版本 | `tag-concepts.md` + `tag-json-schema.md`:概念 + 對照真實 export 的 JSON schema(verified/inferred 標註) |
| system.* API | `system-api-map.md`:只給 submodule × scope 目錄,明說不給 signature,逐列附 docs URL | `system-{db,tag,util,perspective}-api.md`:function matrix + signature + code pattern + 跨 scope 行為 |
| Expression / SQL 分界 | `expression-and-quality.md` + `data-and-named-queries.md`:三語言分界、Value vs QueryString 參數安全,引 docs | `dialects.md` + sql skill:5 dialect 矩陣 + 注入防護 code |

共同主題上的形態差異是穩定的:foundations 是「doc 引用 + 誤判修正,零 code,可逐點回溯官方來源」;copilot 是「同概念 + signature + code pattern + 決策表,實用但一級引用少且部分 inferred」。

兩者在重疊層是互補而非替代:foundations 提供可回溯官方來源的校準骨幹(適合在「會不會錯」上當權威);copilot 提供把概念落到 code 的應用擴張(適合在「怎麼做」上當依據)。把 copilot 的 system-*-api code pattern 配 foundations 的 system-api-map scope 來源,是比單用任一邊更穩的組合。

---

## 結論與取捨建議

### 結論

兩包不是同一層的競品,是知識堆疊的兩層:foundations 是 epistemic / 概念骨幹,copilot 是應用 / 產出層。以 runtime-agnostic 知識資產衡量:

- 作為「防止對 Ignition 亂斷言、校準推理」的資產:foundations 是更緊、更低風險、可信度更高的一份——每個事實有來源、推測有標記、版本有界定,且涵蓋 copilot 概念層缺的平台服務。
- 作為「實際產出 Ignition artifact」的資產:copilot 在它覆蓋的三個 domain 遠更有能力,但帶 inferred-schema 風險與 8 倍維護面,且該風險要等 ground-truth 填充才真正關閉。
- 純看內容品質(本基準):foundations 的「品質/風險比」較優(密度低但近乎零誤導);copilot 的「能力/風險比」較優(能力高但有可量化的 inferred 風險區)。

### 取捨建議

1. 不要二選一、不要整併。兩者一併保留,分層使用:foundations 當常駐的概念/epistemic 背板(成本低、風險低),copilot 的 knowledge/ + 三個 domain skill 當需求觸發的 authoring 層。整包合併會讓 foundations 的低風險特性被 copilot 的體積與 inferred 風險稀釋。

2. 若硬要單選,依目標分流:目標是「讓模型對 Ignition 講話不出錯、由人來做」→ 選 foundations;目標是「模型要產 tag/SQL/Jython」→ 選 copilot,但必須先填 ground-truth,否則 inferred-schema 風險不可接受。

3. 可立即執行的互補補強(高價值、低風險):
   - 把 copilot 的 PLC→type 對照與 5 dialect 矩陣這類「穩定且可引用」的事實,吸收進 foundations——它們是 foundations 目前缺、且不增加風險的硬事實。
   - copilot 的三個 inferred schema(tag-json-schema 的 valueSource 其餘 token、historian-schema、alarm-journal-schema)應採用 foundations 的逐點官方引用紀律,或在 ground-truth pin 之前一律不得輸出 import-ready 物。
   - 修正 TODO.md 與現況的脫節(ignition-scripting 已落地但仍列待辦)。

4. foundations 的最大弱點是它對 copilot 已深耕的三個 domain 只給概念不給落地;copilot 的最大弱點是 Perspective views 完全沒有(TODO.md 自承為 the largest gap)且 L2/L3 verification loop 結構性斷裂。兩個弱點不重疊,這也是「分層保留」優於「擇一」的實證理由。
