# OSS Summary Catalog — 日本語

[English](oss-summary-catalog.md) | **日本語**

現在 `oss-update-watch` の台帳に登録されている45 OSSについて、「何のためのOSSか」「主に何をするものか」が短時間で把握できるように整理した一覧です。説明は各ローカルcheckoutのREADME・package metadataを優先して作成しています。

更新監視の状態やローカル差分はこの文書には固定せず、`oss-update-watch` 本体の `Check updates` を正本とします。

## 01. addyosmani/agent-skills

- **Repo:** `addyosmani/agent-skills`
- **Local usage:** `agent-skills` / direct
- **概要:** AIコーディングエージェント向けの実務用Engineering Skill集です。設計、計画、実装、検証、レビュー、出荷までの進め方や品質ゲートを再利用可能なSkillとして定義し、毎回プロンプトで手順を説明しなくても、エージェントが一定の開発作法を守りやすくするための教材・運用ルール集です。

## 02. affaan-m/ECC

- **Repo:** `affaan-m/ECC`
- **Local usage:** `ECC` / direct
- **概要:** AIコーディングエージェントに、単発のコード生成ではなく「計画→テスト→実装→レビュー→検証→記憶→改善」の開発サイクルを持たせる総合ハーネスです。多数の専用Agent、Skill、Command、Hook、Memory、継続学習、安全性チェックをまとめ、Claude CodeやCodexなどへ一式の開発運用を追加します。

## 03. agno-agi/agentos-docker

- **Repo:** `agno-agi/agentos-docker`
- **Local usage:** `agentos` / fork
- **概要:** AI Agentを常時動かすためのAgentOS実行環境・デプロイ構成です。作成したAgentをAPI、MCP、Slackなど複数の入口から提供し、同じAgentバックエンドを複数フロントエンドで利用できるようにします。Agent作成、評価、実行、管理UIまで含む「Agentをサービスとして運用する」ための土台です。

## 04. agno-agi/agno

- **Repo:** `agno-agi/agno`
- **Local usage:** `agno` / fork
- **概要:** AI AgentやAgent Teamを構築し、サービスとして実行・管理するためのPython系フレームワーク／ランタイムです。Agentのツール利用、知識、メモリ、ワークフローを組み合わせ、APIとして起動したりWeb UIから管理したりできます。Agentそのものだけでなく、Agent Platform全体を組み立てる用途を想定しています。

## 05. anthropics/skills

- **Repo:** `anthropics/skills`
- **Local usage:** `anthropics-skills` / direct
- **概要:** AnthropicによるAgent Skillsの公式実装例・Skill集です。特定作業の手順、スクリプト、参考資料をフォルダ単位にまとめ、ClaudeなどのAgentが必要なときだけ読み込んで専門作業を再現できるようにします。文書作成、データ処理、社内手順などを「繰り返し使える能力」として外付けするための形式です。

## 06. battersea-dynamics/trading-agent

- **Repo:** `battersea-dynamics/trading-agent`
- **Local usage:** `trading-agent` / direct
- **概要:** 学習目的で作られたマルチAgent型の短期株式トレーディングシステムです。CrewAIで複数Agentを協調させ、Gemini、Alpaca、Finnhubなどを使って市場・ニュース・取引判断を組み立てます。README上ではAlpacaのpaper trading専用として設計され、実資金を使わずにAgent型売買ロジックを検証する構成です。

## 07. ChromeDevTools/chrome-devtools-mcp

- **Repo:** `ChromeDevTools/chrome-devtools-mcp`
- **Local usage:** `chrome-devtools-mcp` / direct
- **概要:** AI Agentから実ChromeをChrome DevTools経由で操作・解析できるMCPサーバーです。ページ操作だけでなく、DOM、Console、Network、PerformanceなどDevToolsの情報へアクセスできるため、ブラウザ自動化、Webアプリのデバッグ、表示不具合の調査、性能分析をAIに任せる用途に向いています。MCPなしで使えるCLIも備えます。

## 08. deepseek-ai/deepseek-harness

- **Repo:** `deepseek-ai/deepseek-harness`
- **Local usage:** `deepseek-harness` / direct
- **概要:** DeepSeek AIが開発するオープンソースのAgent Harnessです。LLMを単に呼び出すのではなく、Agentとしてツールを使わせ、タスクを進行させるための実行基盤を提供します。CLIやWeb側の構成も含む開発者向けプレビュー段階のプロジェクトで、Agent実行系やワークフローを研究・拡張する土台として利用できます。

## 09. DeusData/codebase-memory-mcp

- **Repo:** `DeusData/codebase-memory-mcp`
- **Local usage:** `codebase-memory-mcp` / direct
- **概要:** コードベース全体をTree-sitterとLSPで解析し、関数、クラス、呼び出し関係、HTTP route、サービス間リンクなどを永続Knowledge Graphとして持つローカルCode Intelligenceエンジンです。AI AgentはMCP経由で構造検索や影響範囲調査を高速に行え、ファイルを1枚ずつ読むより少ないtokenで大規模repoを把握できます。

## 10. DietrichGebert/ponytail

- **Repo:** `DietrichGebert/ponytail`
- **Local usage:** `ponytail` / direct
- **概要:** AIコーディングエージェントの「必要以上に大きく作る」傾向を抑えるためのSkill／ルールセットです。新しい依存や抽象化を増やす前に、標準機能や小さな実装で十分かを判断させ、安全性を落とさずにLOC、token、コスト、実装時間を減らすことを狙います。YAGNIや単純化をAgent運用へ組み込む用途です。

## 11. different-ai/openwork

- **Repo:** `different-ai/openwork`
- **Local usage:** `openwork` / fork
- **概要:** AIのSkill、MCP、接続サービス、作業フローを複数のAgentや端末で共有するためのオープンソースDesktop Appです。Claude CoworkやCodex系の作業環境に近い専用Workspaceを持ちつつ、Codex、Claude Code、Cursorなど既存AgentからOpenWork MCPを介して同じ能力セットを再利用することもできます。

## 12. dsh-external/dsh_workflow

- **Repo:** `dsh-external/dsh_workflow`
- **Local usage:** `dsh-external-workflow` / direct
- **概要:** DeepSeek Harness系のAgent実行を、単発処理ではなく継続可能なWorkflowとして扱うための外部ワークフロー層です。Runの状態保持、手順の分割、再開、検証などを持たせ、長い開発タスクを複数段階で進めやすくすることが主目的です。DSHをOrchestratorとして使う際の実行・進行管理を補う位置づけです。

## 13. Egonex-AI/Understand-Anything

- **Repo:** `Egonex-AI/Understand-Anything`
- **Local usage:** `Understand-Anything` / fork
- **概要:** コード、ドキュメント、Knowledge Baseを解析して対話可能なKnowledge Graphへ変換するツールです。構造をグラフとして可視化し、検索や質問を通じて「どこに何があり、どう関係しているか」を把握しやすくします。Claude Code、Codex、Cursor、Copilot、Gemini CLIなど複数Agentと組み合わせたコード理解用途を想定しています。

## 14. FiloSottile/age

- **Repo:** `FiloSottile/age`
- **Local usage:** `age` / direct
- **概要:** 小さく扱いやすい設計を重視したファイル暗号化ツール／ライブラリです。公開鍵方式やパスフレーズによる暗号化をシンプルなCLIで行え、SOPSなど他ツールの暗号鍵バックエンドとしても広く使われます。PGPより操作を単純化しつつ、設定ファイルやバックアップなどを安全に暗号化する用途に適しています。

## 15. Finesssee/Win-CodexBar

- **Repo:** `Finesssee/Win-CodexBar`
- **Local usage:** `Win-CodexBar` / direct
- **概要:** WindowsのSystem TrayからAIコーディングサービスの利用量や残量を確認するDesktop Appです。複数サービスのUsage／Quota情報を小さな常駐UIに集約し、各社Dashboardを毎回開かなくても利用状況を把握できるようにします。macOS向けCodexBarの考え方をWindows向けTauri＋Reactアプリとして展開したものです。

## 16. getsops/sops

- **Repo:** `getsops/sops`
- **Local usage:** `sops` / direct
- **概要:** YAML、JSON、ENV、INI、binaryなどの設定ファイルを、構造を保ったまま暗号化してGit管理しやすくするSecrets管理ツールです。age、PGP、AWS/GCP/Azure等のKMSと連携し、必要な人・環境だけが復号できます。暗号化ファイルを通常の設定ファイルに近い感覚で編集できるのが特徴です。

## 17. Git-Agni/prod-FARM-IOS-Core

- **Repo:** `Git-Agni/prod-FARM-IOS-Core`
- **Local usage:** `prod-FARM-IOS-Core` / direct
- **概要:** 複数の実iPhone/iPadを登録・監視し、定期タスクを実行するためのiOS Device Farm基盤です。WDA/Appium監督、ライブ映像、遠隔入力、PostgreSQLスケジューラ、繰り返しJob、実行履歴、Dashboard/APIをまとめています。TikTok自動化Pluginも含み、物理iOS端末を継続運用するための参考実装です。

## 18. google-labs-code/design.md

- **Repo:** `google-labs-code/design.md`
- **Local usage:** `design.md` / direct
- **概要:** AIコーディングエージェントへDesign Systemを正確に伝えるための `DESIGN.md` 形式仕様です。YAML front matterに色・Typography・Radius等のmachine-readable tokenを置き、Markdown本文にデザイン意図を記述します。lint、WCAG contrast確認、2版のdiffも行え、AIが見た目のルールを継続的に守るための共通フォーマットになります。

## 19. google-labs-code/stitch-skills

- **Repo:** `google-labs-code/stitch-skills`
- **Local usage:** `stitch-skills` / direct
- **概要:** Google StitchをAIコーディングAgentから使いやすくするAgent Skills／Plugin集です。Design、Build、Utility系のSkillをまとめ、Codex、Claude Code、Cursor、Gemini CLIなどからUI設計やComponent生成のワークフローを再利用できます。Stitchで作ったデザインと実装側Agentを橋渡しするための公式系ツール群です。

## 20. h4ckf0r0day/obscura

- **Repo:** `h4ckf0r0day/obscura`
- **Local usage:** `obscura` / direct
- **概要:** Rustで実装された軽量Headless Browserエンジンです。V8でJavaScriptを実行し、Chrome DevTools Protocolを提供することで、AI AgentやWeb scraping用途からChrome互換の操作を行えます。Puppeteer／Playwrightとの互換性を意識しつつ、一般的なHeadless Chromeより小さいメモリ消費を目指す独立Browser Runtimeです。

## 21. Hitheshkaranth/OpenTerminalUI

- **Repo:** `Hitheshkaranth/OpenTerminalUI`
- **Local usage:** `OpenTerminalUI` / direct
- **概要:** Trader、Researcher、Quant Team向けのオープンソース金融Terminal UIです。Python/FastAPIバックエンドとReactフロントエンドを組み合わせ、市場データや調査情報を専用Dashboardで扱うための基盤を提供します。Bloomberg系Terminalのような「金融情報を一か所で確認・分析する作業画面」をOSSで構築したい場合の参考になります。

## 22. leonxlnx/taste-skill

- **Repo:** `leonxlnx/taste-skill`
- **Local usage:** `taste-skill` / direct
- **概要:** AIが生成するFrontendにありがちな凡庸な見た目を避け、より洗練されたUIを作らせるためのDesign Skillです。レイアウト、余白、Typography、色、Componentの選び方などに「Taste」の基準を与え、よくあるAI生成風デザインを減らすことを狙います。UI実装時のデザイン判断をAgentへ追加するルールセットです。

## 23. letta-ai/letta

- **Repo:** `letta-ai/letta`
- **Local usage:** `letta-upstream-review` / direct
- **概要:** 長期Memoryを持つStateful AgentプロジェクトLetta（旧MemGPT）の入口となるrepositoryです。現在の実装本体は `letta-ai/letta-code` へ移っており、このrepoはProject紹介と旧V1 Serverのarchive参照が中心です。Lettaの思想、移行先、過去実装を追うためのupstream landing repositoryという位置づけです。

## 24. letta-ai/letta-code

- **Repo:** `letta-ai/letta-code`
- **Local usage:** `letta-code-upstream-review` / direct
- **概要:** Memory、Identity、長期的な経験を持つStateful Agentを作るためのAgent Harnessです。対話型Terminal Agentとして使うだけでなく、常時起動して自律的に働くAgentにも利用できます。Agent自身がMemory、Skill、Prompt、拡張Modを更新しながら長期間適応していく設計が特徴で、Lettaの現行実装本体です。

## 25. mattpocock/skills

- **Repo:** `mattpocock/skills`
- **Local usage:** `mattpocock-skills` / direct
- **概要:** 実際のSoftware Engineering作業で日常利用することを目的にしたAgent Skills集です。特定の一発回答ではなく、設計、実装、調査、デバッグ、品質確認といったEngineering作業の進め方をAgentへ与えるための再利用可能なSkill群として公開されています。AIに実務的な開発判断や手順を追加する参考資料として使えます。

## 26. mem0ai/mem0

- **Repo:** `mem0ai/mem0`
- **Local usage:** `mem0-local` / direct
- **概要:** AI AgentやAssistantへ長期Memoryを追加するためのMemory Layerです。会話やユーザー情報から保存すべき事実を抽出し、後の会話で検索・再利用できる形に管理します。Personalizationや継続Agent向けに、Memoryの追加・検索・更新・削除をAPI化しており、Cloudだけでなくself-host構成でも利用できます。

## 27. mem0ai/mem0-mcp

- **Repo:** `mem0ai/mem0-mcp`
- **Local usage:** `mem0-mcp-official-archive` / direct
- **概要:** Mem0のMemory機能をMCP経由でClaude、Cursor、VS Codeなどから使えるようにしたStandalone MCP Serverです。ただし現在このrepositoryは公式にarchiveされ、active maintenanceは終了しています。現行のMem0 MCPはCloud-hosted版へ移行しているため、現在は旧実装の構造確認や互換性調査の参考資料として見る位置づけです。

## 28. microsoft/UFO

- **Repo:** `microsoft/UFO`
- **Local usage:** `UFO` / direct
- **概要:** Microsoft Research系のGUI／Desktop操作Agent基盤です。UFO2はWindows OSとアプリをAIが操作するDesktop AgentOS、UFO3は複数端末をDAGベースで協調させるMulti-Device Agent Galaxyへ発展しています。画面上の操作をAgentへ任せるComputer Use、Windows深度統合、端末間Task orchestrationの研究・実装基盤です。

## 29. nextlevelbuilder/ui-ux-pro-max-skill

- **Repo:** `nextlevelbuilder/ui-ux-pro-max-skill`
- **Local usage:** `ui-ux-pro-max-skill` / direct
- **概要:** AI AgentへUI/UX設計知識を追加するDesign Skillです。多数のUI style、配色、Typography、業種別ルールを検索でき、Project要件からDesign Systemを自動提案するGeneratorも備えます。Webだけでなく複数Framework／Platformで、Agentが見た目・Accessibility・Responsive設計を一貫して判断するための知識ベースとして使えます。

## 30. oraios/serena

- **Repo:** `oraios/serena`
- **Local usage:** `serena` / direct
- **概要:** AIコーディングAgentへIDE相当のSemantic Code操作を与えるMCP Toolkitです。LSPなどを利用してSymbol単位で定義、参照、実装、Rename、Refactor、Debugを扱えるため、単純な文字列検索よりコードの意味を保った操作ができます。大規模CodebaseでのNavigationやCross-file修正を効率化する「Agent用IDE層」です。

## 31. pbakaus/impeccable

- **Repo:** `pbakaus/impeccable`
- **Local usage:** `impeccable` / direct
- **概要:** AIコーディングAgent向けのFrontend Design品質改善ツールです。1つのSkill、複数のDesign Command、Browser上での反復確認、AI生成UIにありがちな問題を見つけるdetector ruleを組み合わせます。`audit`、`critique`、`polish`、`animate`などの操作で、見た目だけでなくAccessibility、Responsive、Performanceも含めてUIを仕上げます。

## 32. petrkindlmann/qa-skills

- **Repo:** `petrkindlmann/qa-skills`
- **Local usage:** `qa-skills` / direct
- **概要:** AI AgentへQA／Test Engineeringの手順を追加するAgent Skills集です。Playwright、Cypress、API、Unit、Mobile、Visual Regression、Performance、Accessibility、Security、CI/CD、Bug triageなど約50種類のSkillを収録します。テストコード生成だけでなく、Risk-based Test StrategyやRegression設計までAgentに任せるための実務知識集です。

## 33. shiyu-coder/Kronos

- **Repo:** `shiyu-coder/Kronos`
- **Local usage:** `Kronos` / direct
- **概要:** 株価や暗号資産などのCandlestick（K-line）時系列を「金融市場の言語」として学習するオープンソースFoundation Modelです。一般的な時系列モデルではなく、高ノイズな金融価格系列に特化して事前学習され、将来のK-lineを予測する用途を想定しています。金融AIやMarket Forecast研究でのModel／推論基盤として利用できます。

## 34. signal-forge-lab/fable_madakana

- **Repo:** `signal-forge-lab/fable_madakana`
- **Local usage:** `fable_madakana` / direct
- **概要:** ChatGPT上のFable関連Threadを定期取得し、新しい通知だけを抽出・保存するWatcherです。取得済みmessage IDで重複を避けつつ、新規通知を蓄積し、必要に応じて過去分の再処理も行えます。Fableの「まだかな」を人が何度も確認する代わりに、更新有無を機械的に追跡するための小型監視自動化ツールです。

## 35. SikandarJODD/animations

- **Repo:** `SikandarJODD/animations`
- **Local usage:** `animations` / direct
- **概要:** Svelte 5向けのCopy & Paste型Animation Component集です。motion-sv、Tailwind CSS、shadcn-svelte registryを使い、文字、Hover、Transition、装飾演出など多数のComponentをそのままProjectへ追加できます。Animationを毎回ゼロから実装せず、完成済みUI演出をSvelte Projectへ素早く導入するための部品Libraryです。

## 36. SikandarJODD/cnblocks

- **Repo:** `SikandarJODD/cnblocks`
- **Local usage:** `cnblocks` / direct
- **概要:** Svelte 5＋shadcn-svelte＋Tailwind CSSで作られたProduction-ready UI Block集です。Hero、Pricing、Feature、CTAなど、SaaS、Product、Documentation、Landing Pageで頻出する大きめのSection単位を提供します。単一Componentより一段大きい「完成済みページ部品」をコピーして、Marketing UIを短時間で構築する用途に向いています。

## 37. SikandarJODD/sv-agentation

- **Repo:** `SikandarJODD/sv-agentation`
- **Local usage:** `sv-agentation` / direct
- **概要:** Svelte画面上で人が付けたUI Annotationを、AIコーディングAgentが理解できるStructured Contextへ変換するツールです。Inspectorで対象Elementを選び、コメントや選択範囲を記録し、Markdown／構造化PayloadとしてAgentへ渡せます。「この部分を直して」をDOM上の正確な対象情報付きで伝えるFrontend Review支援ツールです。

## 38. SikandarJODD/sv-table

- **Repo:** `SikandarJODD/sv-table`
- **Local usage:** `sv-table` / direct
- **概要:** Svelte 5／SvelteKit向けのData Table Componentと完成済みTable Block集です。TanStack Tableを土台に、検索、Faceted filter、日付・数値Range、Pagination、Sorting、Column visibility、Resize、Row action、CSV exportなどを部品化しています。管理画面の高機能Tableを短時間で組み立てる用途に向きます。

## 39. tauricresearch/tradingagents

- **Repo:** `tauricresearch/tradingagents`
- **Local usage:** `tradingagents` / direct
- **概要:** LLMを複数の金融専門Agentに分け、協議させて投資判断を作るMulti-Agent Trading Frameworkです。Market／Fundamental／News／Sentiment Analyst、Bull/Bear Researcher、Trader、Risk Managerなどの役割を分離し、最終判断までGraphで接続します。各種LLM／Market Data providerを切り替えながら金融Agent研究やBacktestを行う基盤です。

## 40. trycua/cua

- **Repo:** `trycua/cua`
- **Local usage:** `cua` / direct
- **概要:** AIのComputer Useを大規模に実行・評価するためのオープンソース基盤です。OSを操作するDriver、複数環境を管理するFleet、Benchmark、Training／Evaluation／Data generation向け機能をまとめています。単一PCをマウス操作するだけでなく、Computer-use Agentの開発、学習用データ収集、複数OSでの再現テストまで扱う広いInfrastructureです。

## 41. vibheksoni/stealth-browser-mcp

- **Repo:** `vibheksoni/stealth-browser-mcp`
- **Local usage:** `stealth-browser-mcp` / direct
- **概要:** AI Agentから実Chrome系Browserを操作するためのMCP Serverで、nodriver、Chrome DevTools Protocol、FastMCPを組み合わせています。通常のAutomationが弾かれやすいCloudflare challenge、anti-bot check、login wallなどを越えて操作する用途を強く意識した実装で、Login済みProfileを使うWeb自動化にも向きます。

## 42. Waishnav/devspace

- **Repo:** `Waishnav/devspace`
- **Local usage:** `devspace` / fork
- **概要:** ChatGPTへCodex風のCoding Workspace操作を持ち込むための開発基盤です。Workspaceを開き、Repository内のFileを読み、編集やCommand実行などをAIから行えるようにして、通常のChatだけでは難しい継続的なCodebase作業を可能にします。この環境ではWorkbridgeのupstream系統としても関係する、Local Coding Tool／MCP基盤です。

## 43. wonderwhy-er/DesktopCommanderMCP

- **Repo:** `wonderwhy-er/DesktopCommanderMCP`
- **Local usage:** `DesktopCommanderMCP` / fork
- **概要:** AIからLocal PCのFile SystemとTerminalを操作するためのMCP Serverです。Fileの検索、読取、更新、Directory管理、Command実行など、開発作業で必要な「手」をAIへ渡します。専用のCode Intelligenceよりも汎用Local操作に重点があり、Chat AgentからPC上のProjectやScriptを直接扱わせたい場合の実行層として使えます。

## 44. xyTom/coding-tools-mcp

- **Repo:** `xyTom/coding-tools-mcp`
- **Local usage:** `coding-tools-mcp` / direct
- **概要:** AI Chat／AgentへCodebaseを安全に操作するためのMCP Tool群を提供するプロジェクトです。File読取・編集・検索・Command実行などCoding作業で必要なPrimitiveをまとめ、AIがLocal Repositoryへ直接手を入れられるようにします。特定IDEへ固定せず、MCP互換Clientへ共通のCoding操作面を追加する用途を狙った汎用実行Toolkitです。

## 45. yebof/quant-agent

- **Repo:** `yebof/quant-agent`
- **Local usage:** `quant-agent` / direct
- **概要:** 米国株向けのLLM Multi-Agent Quant Trading Systemです。Technical、Macro、News、SEC Filing、Portfolio、Risk、Position Management、Reflectionなど複数の専門Agentが協調し、Alpacaへ注文を渡します。LLM任せにせずPython側のRisk Filter、Stop、Position Size、監査可能なReasoning schemaを重ね、日次運用と振り返りまで自動化する構成です。

---

## 読み方の補足

- **direct**: そのrepositoryを比較的そのまま利用・参照しているもの。
- **fork**: upstreamとの差分を持つ、または独自変更を前提に扱っているもの。
- この文書は「何をするOSSか」の説明用です。**現在のVersion、Behind/Ahead/Diverged、更新有無は記載しません。** それらは `Fossight` の実行結果を参照してください。
