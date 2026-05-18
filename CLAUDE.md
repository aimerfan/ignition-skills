# CLAUDE.md

本 repo 是 **Ignition + SepaSoft skill 知識資產的維護工作區**(非應用程式碼庫)。交付物是兩個給 Claude 載入的 user-level skill:`ignition-foundations`、`sepasoft-foundations`。初版已建置完成並通過驗證,目前進入維護階段。

本檔是這個 repo 的設計憲法,維護階段的權威來源。**權威順序:本檔 + 各 SKILL.md 與 skill 現況 > 一切其他文件。** 規則之間衝突時以本檔為準;本檔與 skill 現況衝突時,以現況為事實、修正本檔。

歷史出處:初版依 Notion「Ignition+Sepa Skill 實作 Spec」
(https://www.notion.so/3628ebada94581ac824cf524bde24d4a)建置。該 spec 是建置指引,**維護階段不再是權威來源**,僅供查設計原意(rationale);它可能已被刪除或隨使用回饋過時。下文約束已從 spec 抽離為本 repo 的原生規則,不依賴 spec 存在。

**現況刻意偏離 spec 是正常的維護結果,不是待修正的錯誤。** 維護期依使用回饋推翻建置期 spec 條目是被允許且預期的;凡現況與 spec 衝突,一律以現況為準,**不得以「spec 當初規定 X」為由把現況回退**。要再改現況,須有新的、更強的證據並重新與 user 確認 —— spec 不構成這種證據。

## 設計定位(最重要,易被誤改)

這兩個 skill 是 **conceptual grounding / 防臆造的概念地基**,不是 troubleshooting 知識庫,也不是 artifact 產生器。

- 目標:讓 Claude 不亂下斷言、知道去哪查證、知道何時請 user 在 GUI 操作
- 刻意**不**承載:component how-to、driver 排錯、版本 bug 確認、detailed signature、option list、SQL schema、客戶自製 framework
- `reports/` 的 forum 覆蓋率 FULL 偏低是**設計預期**(skill 本就不為解 forum 題而設計),引用該數字必須附此定位

被要求「補更多細節」時先判斷是否違反此定位。塞 signature / option list / how-to 進來會破壞下述廣度控制與來源紀律;若確實要擴張承載範圍,屬設計層決策,須先與 user 確認,不要當成順手補強。

## 來源紀律(最易被違反)

- 寫入 skill 的內容**只接受**:官方文件(docs.inductiveautomation.com / docs.sepasoft.com)、高可信社群來源(IA Forum / Sepasoft Community 官方或認證身分發言)
- **排除**:Claude 訓練資料(連 hypothesis 起點都不用)、blog、未驗證 SO、未署名留言
- 無合格來源時標「待補」或「未驗證觀察」並附 URL,**絕不憑記憶補斷言**
- 每個 fact 配來源 URL;單一引述不超過原文 50%,不大段轉述
- 新增或修改 fact 前 self-check:有合格來源?來源實際支持此陳述?是否版本特定(是則標版本)?三者有一不過就標待補,不寫成斷言

## 必須排除的內容

特定 client / project / server / gateway / tag provider 名稱;客戶自製 framework(屬 project file 層,非 skill 層);特定 phase / recipe / batch / view 命名;SQL table / column 名(internal 細節);任何訓練資料中未經驗證的內容。

## 已知的刻意偏離

description 採 pushy 寫法(推翻 spec §10.2)、SKILL.md 紀律段把 reference 定位為索引非答案(具體 signature/option/版本行為一律以官方 docs 為終點)—— 兩項皆依 2026-05 回饋刻意為之,適用兩個 skill,屬上述「正常維護結果」,依據與全程記於 `reports/feedback-2026-05-18.md`。

## 跨環境與格式約束

兩個 skill 在 Claude Code 與 claude.ai chat 兩環境共用(user 手動同步部署),內容須完全通用:

- 絕不寫死絕對路徑(`/mnt/skills/...`、`~/.claude/...`、`C:\Users\...`、`file://`)
- frontmatter **只用** `name` + `description`,不加 `compatibility` / `allowed-tools` 等環境特定欄位
- 不假設 bash / code execution 能力,只能假設 view tool(兩環境的安全最小集)
- 檔名 / 資料夾名:lowercase + hyphen,無空格 / 特殊字元 / Unicode
- **SKILL.md 主文件四節(平台定位 / 紀律提醒 / Reference 索引 / 標準動作)用繁體中文;`references/` 子文件用英文**;code / API 名 / 檔名 / 配置值一律原文
- SKILL.md 的 Reference 索引必須與實際 `references/` 檔案完全一致;改子文件結構(拆 / 合 / 重命名)時須同步更新索引
- 版本敏感:Ignition pin 8.1,8.1→8.3 變動標 inline「Version sensitivity」;SepaSoft pin 當前 stable,SP-gated 行為必帶版本號;任何版本特定行為一律帶版本

## 維護動作須知

- `ignition-copilot/` 是 `reports/comparison-report.md` 的外部比較對象,**非本 repo 交付物,勿改**
- `.claude/eval*/`、`.playwright-mcp/`、`.claude/PROGRESS.md` 是建置 scratch,非交付物
- 不自行部署到 `~/.claude/skills/`;user 人工檢核後手動部署
- 內容重驗須實際 fetch 官方 docs 比對;docs.sepasoft.com 是 ClickHelp SPA,須 Playwright(navigate→wait_for→snapshot,`#!` URL 要等 route resolve),docs.inductiveautomation.com 可用 WebFetch
- 不打包(維持原始檔結構),不跑 skill-creator 的 eval / packaging / description optimization 流程
- `reports/` 下既有報告反映建置時狀態;若內容隨維護演進,更新報告或標註過時,不要讓它與 skill 現況靜默不一致
