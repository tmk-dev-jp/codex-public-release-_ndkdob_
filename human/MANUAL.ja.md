# Codex対応・深層学習研究テンプレート運用マニュアル

## 1. このテンプレートの目的

このテンプレートは、深層学習研究を次の順序で反復するためのひな型です。

```text
仮説 → 計画監査 → 人間承認 → 実装 → pilot/fullの実装監査 → 決定的実行 → 完全性監査 → 主張評価 → 確定 → 証拠・記憶 → 次の仮説
```

計画監査は、主評価指標だけを上げても研究目的が改善しない抜け道を実装前に調べます。実装監査は学習前のコード、完全性監査は学習後の結果出所と計画遵守を調べます。決定的実行は固定条件をPythonで再現し、確定後は「どの条件まで言えるか」を証拠として残します。

設計上の中心は、Codexにリポジトリ全体や過去ログを毎回読ませず、現在の判断に必要な情報だけを渡すことです。

役割は次のように分離されています。

| 処理 | 担当 | 理由 |
|---|---|---|
| 仮説と実験計画 | Codexの計画Skill（定型の作業手順） | 判断と比較条件の明文化が必要 |
| 計画監査 | 読み取り専用Plan Auditor（独立監査役） | 指標ハック、比較不整合、評価データ混用を実装前に確認する |
| 実装 | リスク別の実装Agent一つ | 科学的に重要な箇所だけ高性能モデルを使い、通常実装の費用を抑える |
| pilot・fullの実装監査 | 読み取り専用Evaluator（独立評価役） | 学習前に計画忠実性、データ漏洩、loss、metric、再現性、変更範囲を確認する |
| sanity check・学習・集計 | Pythonプログラム | 決定的に実行でき、Agentを使う必要がない |
| smoke結果の簡易評価 | 通常のCodexセッション | 小規模確認なので独立Agentの費用が不要 |
| pilot・full結果の整合性監査と評価 | 読み取り専用Evaluator（独立評価役） | 数値の出所、計画遵守、リーク、主張範囲を実行者から独立して確認する |
| 失敗時の修正 | CodexのDebug Skill | エラーが発生した場合だけ起動する |
| 状態遷移 | Pythonスクリプト | 自然言語による誤遷移を防ぐ |

計画・実装・評価を常時稼働する三つの担当Agentには分けません。担当を増やすと、同じ目標やコードを複数の作業文脈へ読み込むため、処理量が増えます。通常は一つのCodexセッションで一つの作業段階だけ処理し、重要な評価だけ別の読み取り専用Evaluatorへ渡します。

---

## 2. 最初に理解するファイル

研究開始時に人間が直接確認する主要ファイルは次のとおりです。

| ファイル | 用途 |
|---|---|
| `research/GOAL.md` | 研究質問、結果を受けた判断、対象範囲、成功条件、研究全体を終える条件 |
| `research/PROPOSED_METHOD.md` | baselineではなく新規提案手法の現在形 |
| `research/STATE.json` | 現在の実験、フェーズ、予算、承認状態、無人ループの復帰用進捗 |
| `research/CLAIMS.jsonl` | 研究全体で支持、棄却、限定していく主張 |
| `research/QUEUE.json` | 次に実験化する仮説候補の一覧と優先度。実行中ジョブの一覧ではない |
| `research/DECISIONS.md` | 結果を受けて採用、棄却、限定した判断と理由 |
| `research/CONTEXT.md` | Codex向けに自動生成される短い現在地 |
| `research/ideas/IDEA_BANK.jsonl` | まだqueueへ上げていない案も含む、広い着想置き場 |
| `research/novelty/NOVELTY_CHECKS.jsonl` | 既存研究との差分確認と新規性リスク |
| `research/EVIDENCE.jsonl` | 完了結果、固定した判定規則との対応、支持範囲、不足証拠、監査判定をclaimへ結ぶ台帳 |
| `baselines/INDEX.json` | 登録済みbaselineの一覧 |
| `baselines/records/<ID>.json` | baseline資料、読取り許可範囲、実装予定先 |
| `experiments/DIGEST.md` | 完了済み実験の一行要約 |
| `experiments/LEDGER.jsonl` | 完了実験を後から比較・検索するための構造化台帳 |
| `experiments/active/<ID>/EXPERIMENT.md` | 現在の仮説、方法、結論、次方針 |
| `experiments/active/<ID>/PLAN_AUDIT.md` | 人間承認前に受理した計画監査 |
| `experiments/active/<ID>/INTEGRITY_AUDIT.md` | 受理済みの結果完全性監査。pilot・fullで使用 |
| `experiments/active/<ID>/SCOPE.json` | Codexが読む・書く・試験する正確なファイル一覧 |
| `experiments/active/<ID>/IMPLEMENTATION_AUDIT.md` | 受理済みの実行前実装監査。pilot・fullで使用 |
| `experiments/active/<ID>/DECISION_FACTS.json` | ロック済み規則から機械計算した比較値と判定状態 |
| `configs/experiments/<ID>.json` | 学習・評価条件 |
| `artifacts/results/<ID>/metrics.json` | 集約済み結果 |
| `artifacts/results/<ID>/manifest.json` | 再現性情報とハッシュ |

`research/CONTEXT.md`、`experiments/DIGEST.md`、結果ファイルはスクリプトが生成します。原則として手で編集しません。

このマニュアルでは、ファイル名、コマンド名、状態名、スキル名は英語のまま書きます。用語は次の意味で使います。

| 用語 | このマニュアルでの意味 |
|---|---|
| Skill | `$plan-experiment`のような、Codexに一つの作業手順を実行させる指示セット。一ターンでは原則一つだけ使う |
| experiment | 一つのコア仮説を判断する比較一式。複数の手法・条件・反復実行を含められます |
| run | 手法・条件・seedを指定した一回の実行。一実験の中に複数のrunを持てます |
| active experiment | 現在処理中の一件。完了するまで次の実験はactiveにしない |
| research branch | 同じ仕組みや手法案を追う一連の方向。複数実験を含み、停止条件を満たせば打ち切る |
| queue | 次に実験化する仮説候補の優先一覧。学習ジョブやCodex処理の待ち行列ではない |
| decision | 結果によって人間が変える行動。例は手法の採用、棄却、適用範囲の限定 |
| hypothesis / claim | hypothesisは今回試す予測、claimは複数の証拠で更新する研究上の主張 |
| baseline | 新しい手法の良し悪しを判断するため、同じ条件で比較する既存手法または過去実験 |
| proposed method | 現在検証中の新しい手法案。良い結果が出ても、自動的にbaselineへ置き換えない |
| primary metric | 成否判定に最優先で使う一つの数値。補助指標を見て後から差し替えない |
| metric gaming | primary metricだけを上げ、研究目的や実運用上の品質を改善しない抜け道 |
| diagnostic guardrail | その抜け道を検出する補助値。最大一つで、採用・昇格判定には使わない |
| alternative explanation | 提案した仕組みがなくても同じ結果を説明できる、最も有力な別の説明 |
| minimum discriminating evidence | 仮説とalternative explanationを見分けるために最低限必要な観測 |
| decision mode | 結果の判定方式。意味のある最小差で判定する`threshold`か、事前に定めた方向や形で判定する`trend`のどちらか |
| minimum meaningful effect | `threshold`方式で、採用判断を変えるほど意味がある最小改善量。単に0より良いという意味ではない |
| trend evidence rule | `trend`方式で、期待する方向や形、最低限必要な比較点、弱い・逆向き・混在・観測不足の扱いを結果より前に定めた規則 |
| falsifier | 出たら仮説を棄却または限定する、事前に決めた観測 |
| stop condition | 「何を止めるか」を伴う条件。`GOAL.md`では研究全体、実験記録では次の検証または研究枝を打ち切る条件 |
| stage | 実験規模。smokeは動作確認、pilotは有望性確認、fullは承認済み予算による最終評価 |
| phase | 一件の実験が今どの作業段階にあるか。例は計画中、実装済み、評価待ち |
| sanity check | 本格学習前に、入出力形状、loss、勾配、保存処理が最低限動くか調べる小テスト |
| locked plan | 結果を見る前に固定した仮説、比較条件、指標、対象ファイル。変更する場合は計画段階へ戻す |
| config | batch size、epoch数、モデル名など、その実験で固定する実行設定 |
| scope | 文脈で二種類ある。研究上のscopeは結論が当てはまる範囲、`SCOPE.json`はCodexが扱えるファイル範囲 |
| planning reads | 計画中に本文まで確認したPythonファイル。パスと必要理由を`SCOPE.json`へ先に記録する |
| implementation entry reads | 実装開始時に最初に本文を開くPythonファイル。全scopeを一括で読まないため、必要理由とともに少数へ限定する |
| implementation delta | 計画時に固定した「どこをどう変えるか」と、実装後に機械記録した変更前後のhash・Pythonシンボル。実装差分契約とも呼ぶ |
| split / seed | splitはモデル更新用のtrain、学習中の選択用のvalidation、最終評価用のtestへの分け方。seedは乱数を再現する固定値 |
| epoch / batch | epochは学習データを一巡する単位、batchは一回に処理するサンプルのまとまり |
| forward / loss / backward | 予測を計算する処理、予測誤差、その誤差から更新用の勾配を計算する処理 |
| leakage | test情報や同一サンプルが学習側へ混ざり、見かけの性能が高くなること |
| robustness | seed、split、データ群などが変わっても結論が保たれるかという頑健性 |
| checkpoint / artifact | checkpointは保存した学習済み重み、artifactはmetricsなど実験が生成したファイルの総称 |
| aggregate metrics | batchごとの履歴ではなく、実験全体を一つの値や少数の値へ集約した評価結果 |
| manifest / hash | manifestは実行条件と生成物の目録、hashは内容が後から変わっていないか確認する指紋値 |
| review bundle / Evaluator | bundleは監査に必要な情報だけの閉じた資料、Evaluatorはそれだけを読む独立評価役 |
| plan audit | 研究目的と主指標の対応、指標ハック、selectionと最終評価の分離、baseline比較を実装前に確認する監査 |
| implementation profile | 実装の科学的リスクを`mechanical`・`balanced`・`frontier`の三段階で固定したもの |
| implementation audit | pilot・fullの学習前に、計画忠実性、漏洩、loss、metric、再現性、変更範囲を確認する実装監査 |
| integrity audit | 数値の出所、固定計画への準拠、指標、データ漏洩、結論範囲を評価前に確認する完全性監査 |
| agent gate | Agent起動前に状態、承認、scope、hash、資料の鮮度、完成済み出力をスクリプトで検査する入口 |
| Mechanical rule status | 固定した数値規則の機械判定。`met`、`not_met`、`baseline_unavailable`、`trend_requires_interpretation`のいずれか |
| evidence | 実験結果をclaimへ結ぶ確定済み根拠。支持できる条件と、まだ支持できない条件を一緒に記録する |
| JSONL | 一行に一件のJSON記録を置く台帳形式。過去行を書き換えず、新しい記録を末尾へ追加する |

---

## 3. 研究開始前の準備

既存の研究ディレクトリがある場合は、別の場所に展開したテンプレートで`$migrate-research-project`を使えます。元の`.gitignore`で除外されるファイルは既定で読まず、移す内容と移行先を確認してから反映します。元データや過去の承認はコピーしません。具体的な依頼方法は[既存研究の移行手順](MIGRATE_RESEARCH.ja.md)を参照してください。

実験開始前は、次の順で一つずつSkillを使うと安全です。

```text
$discuss-research-theme    # 研究テーマ自体が未確定の場合だけ
$prepare-environment
$prepare-data-manifest
$define-research-intent
$register-source-baseline   # baseline資料がある場合だけ
```

`$discuss-research-theme`は、複数候補を判断への関連、反証可能性、データ、計算量、新規性の不確実性で比較する対話専用Skillです。人間がテーマを選ぶまでファイルを変更せず、選択後は`$initial-setup`または`$define-research-intent`へ引き渡します。

すべてをまとめて対話的に初期化したい場合は、従来どおり`$initial-setup`を使えます。ただし、手順を分けると、環境、データ、研究目的、baseline登録の未解決項目を混ぜずに確認できます。

### 3.1 展開とPython環境

ZIPを任意の場所へ展開し、リポジトリのルートへ移動します。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Windows PowerShellでは仮想環境の有効化だけ次へ置き換えます。

```powershell
.venv\Scripts\Activate.ps1
```

インストール後に構造とテストを確認します。

```bash
python scripts/validate.py
python -m pytest -q
```

テンプレート内のプログラムは途中経過を出力しません。正常時は`OK ...`を一行、異常時は標準エラーへ`ERROR ...`を一行だけ出します。`pytest`や`pip`など外部ツールの表示はこの制約の対象外です。

Codexに環境確認を手伝わせる場合は、リポジトリのルートで次のように依頼します。

```text
$prepare-environment を使って、Python、依存関係、validate、pytest、Git状態、Codex Hook設定を確認してください。
不足があれば、実行すべきコマンドだけを提示してください。インストールやGit操作はまだ実行しないでください。
```

### 3.2 Gitの初期化

設定、計画、実装差分を追跡するため、研究開始前にGitを初期化することを推奨します。

```bash
git init
git add .
git commit -m "Initialize research template"
```

チェックポイント、データ本体、生成結果は`.gitignore`の方針に従って管理してください。再現性に必要な設定、コード、データのマニフェスト、実験記録は追跡します。

### 3.3 Codex Hookの扱い

`.codex/hooks.json`には、Codexのターン終了時に`CONTEXT.md`を再生成し、構造検査を行う補助Hookが含まれています。このHookは次の実験や学習を自動開始しません。

プロジェクト内HookはCodex側で信頼確認を求められる場合があります。内容を確認して利用するか、不要なら`.codex/config.toml`でHookを無効化してください。Hookを使わなくても、各スクリプトが必要なコンテキスト更新を行うため研究サイクルは実行できます。

### 3.4 初期設定をCodexに手伝わせる

研究開始時に、人間がすべてのJSONを手で埋める必要はありません。リポジトリのルートでCodexを開き、次のように依頼できます。

```text
$prepare-data-manifest を使って、data/MANIFEST.jsonに必要なデータ事実を整理してください。
```

次のターンで研究目的と候補一覧を初期化します。

```text
$define-research-intent を使って、研究目的、最初のclaim、QUEUE、STATEを初期化してください。
```

baseline資料がある場合だけ、さらに別ターンで承認した範囲を登録します。

```text
$register-source-baseline を使って、承認した資料範囲を比較基準として登録してください。
```

Codexは、確定事実、仮定、未解決項目を分けて提示します。内容を確認してから、必要なファイルだけを更新させます。

回答例：

```text
研究目的: 論文Aの画像復元モデルを、手元の固定データ分割で再現できるか確認したい。
データ: data/raw/denoise/ に配置済み。分割は data/MANIFEST.json に記録する。
資料: REF-001 の論文PDFと、著者GitHubの models/network.py。
読んでよい範囲: 論文のAbstract、Method 3.1、Table 2、GitHubの models/network.py のみ。
指標: PSNRは大きいほど良い主評価指標。SSIMは補助指標。
最小効果: smokeでは有限lossとcheckpoint生成、pilotではbaseline比PSNR +0.1dB。
予算: smokeは1 epoch、各split 2 batchまで。
最初の目的: forward、loss、metrics保存まで通す。
```

未定の項目は「未定」と答えて構いません。未定のままでは実験計画を固定できない項目だけ、Codexが追加で確認します。

最初の仮説候補を置く場合は、単なる精度改善案ではなく、新規性の軸を一つ決めます。例えば、機構、条件、データ状況、目的関数、効率、頑健性、失敗モードのどこを新しく検証するのかを短く書きます。既存研究と同じ発想を別の名前で繰り返す候補は、計画前に修正します。

この段階でCodexにさせないことは次です。

- 論文やGitHub全体の読込み
- 外部資料の検索やダウンロード
- モデル実装
- 学習実行
- active experimentの作成

まとめて初期設定したい場合は、次の依頼でも構いません。

```text
$initial-setup を使って、この深層学習研究を初期設定してください。
研究目的、データ、ベースライン資料、読んでよい範囲、最初のsmoke実験の目的を対話で確認してください。
論文やGitHub全体を勝手に読まず、承認した範囲だけ使ってください。
```

---

## 4. データの準備

### 4.1 配置原則

```text
data/
├── raw/                 # 人間が用意する変更不可の原データ
├── processed/           # コードで再生成可能な加工データ
├── MANIFEST.example.json
└── README.md
```

原データは`data/raw/`へ置きます。学習コードから自動ダウンロードしません。自動ダウンロードを禁止する理由は、データ版の変化、ネットワーク依存、ライセンス不明瞭化、実験中の予期しない差替えを避けるためです。

加工データは`data/processed/`へ置きます。加工手順は再実行できるコードとして管理し、原データを上書きしないでください。

### 4.2 データマニフェスト

`data/MANIFEST.example.json`を`data/MANIFEST.json`へコピーし、少なくとも次を記入します。

データマニフェストは、データ本体ではなく、入手元、版、形状、分け方を記録した目録です。trainはモデル更新用、validationは学習中のモデル選択用、testは最後の評価用であり、test情報を学習や調整へ使いません。`shape`は配列の次元、`dtype`は数値の型を表します。

- データセットID
- 入手元とライセンス
- タスク種別
- 入力形状とdtype
- 教師情報の形式
- train、validation、testの件数
- 分割を再現するパスまたは規則
- データまたは分割インデックスのハッシュ
- 重複やリークの確認内容

Codexにはデータ本体を再帰的に読ませず、最初にこのマニフェストを読ませます。問題の確認に実サンプルが必要な場合だけ、正確なファイルや少数サンプルを`SCOPE.json`へ追加します。

Codexに支援させる場合は、次のように依頼します。

```text
$prepare-data-manifest を使って、data/MANIFEST.jsonを準備してください。
data/raw/を再帰的に読まず、私が指定したメタデータまたは少数サンプルだけを使ってください。
入手元、ライセンス、shape、split、hash、leakage checkの未解決項目を分けてください。
```

### 4.3 DataLoaderの実装

DataLoaderは、データを一定件数のまとまり（batch）にしてモデルへ渡す部品です。

基底クラスは`src/dl_research/data/base.py`にあります。実データ用クラスでは次を実装します。

- `setup()`：データセットと固定分割を構築する
- `train_loader()`：shuffleありの学習DataLoaderを返す
- `validation_loader()`：shuffleなしの検証DataLoaderを返す
- `test_loader()`：shuffleなしのテストDataLoaderを返す
- `metadata()`：件数、形状、分割、版などの短い情報だけを返す

新しいクラスは例えば次へ置きます。

```text
src/dl_research/data/my_dataset.py
```

その後、`src/dl_research/data/factory.py`へ明示的に登録します。factoryは設定中の名前を実際のDataLoaderクラスへ対応付ける選択表です。自動探索や暗黙importは使いません。factoryを明示することで、Codexが対象クラスを短時間で特定でき、意図しないクラス選択も防げます。

### 4.4 データ分割の固定

比較する手法間では、同じ条件について次を固定します。

- train、validation、testの分割
- 前処理
- ラベル定義
- 除外規則
- augmentationの基本方針
- 評価対象サンプル

仮説の検証に必要なデータ条件の違いは、`comparison.conditions`に事前登録し、全手法に同じ変更を適用して比較できます。一方、提案手法だけ分割や前処理を変えると、何による改善か判断できません。共通の評価基準の変更や別の仮説の検証は、別の実験IDで扱います。

---

## 5. 研究目標（GOAL）の設定

`research/GOAL.md`を編集します。長い背景説明ではなく、意思決定に必要な比較を明示します。

Codexに支援させる場合は、次のように依頼します。

```text
$define-research-intent を使って、research/GOAL.mdとCLAIMS.jsonlの初期案を作ってください。
Question、Decision、Scope、Success Criteria、Falsification、Stop Ruleを、実験結果で判断が変わる形にしてください。
未確定のbaselineやmetricは確定扱いにせず、未解決項目として残してください。
```

### 5.1 研究質問（Question）

悪い例：

```text
より良い画像分類モデルを作る。
```

良い例：

```text
固定したDATA-001の分割において、Model BはModel Aよりmacro F1を0.02以上改善するか。
```

比較対象、条件、指標、数値閾値または期待する傾向が分かる形にします。

### 5.2 結果を受けて変える行動（Decision）

結果に応じて何を変えるかを書きます。

```text
改善が再現されればModel Bを以後のbaselineとし、満たさなければModel Aを維持する。
```

結果が出ても意思決定が変わらない問いは、実験の優先度を下げます。

### 5.3 結論を適用する範囲（Scope）

対象と対象外を分けます。例えば、単一データセットの研究結果を別施設や別ドメインへ一般化しないことを明記します。

### 5.4 成功と判定する基準（Success Criteria）

少なくとも次を事前に決めます。

- primary metric
- maximizeまたはminimize
- decision mode
- 数値閾値、または期待する傾向と最低限必要な観測条件
- baseline
- seedやsplitなどの頑健性条件
- 計算予算

`threshold`は、採用判断を変える最小差を数値で置ける場合に使います。`trend`は、研究初期で妥当な差をまだ定められない一方、増加、減少、単調変化、U字、頭打ちなど、期待する形を事前に書ける場合に使います。`trend`では、比較する順序付き条件、最低限必要な比較点、弱い・逆向き・混在・観測不足をどう判定するかも固定します。

結果を見た後で指標、判定方式、閾値、期待する形を変更しないでください。曲線や群別値が必要なら、計画時に定めた集約値として`metrics.json`へ含めます。目視で都合のよい部分だけを傾向と呼びません。

### 5.5 反証条件と、何を止めるか

反証条件は「どの結果なら現在の仮説を棄却または限定するか」です。停止条件は「どの条件なら追加実験を増やさず、現在の研究枝または研究全体を終えるか」です。学習中のearly stoppingとは別物です。

例：

- pilotで改善量が0以下なら当該手法を棄却する
- 二回連続で新しい情報が得られなければ探索を止める
- GPU時間が上限を超えたら人間判断へ戻す
- 精度改善があるが推論時間の制約を超えた場合は適用範囲を限定する

---

## 6. 研究状態と、次に試す候補一覧（QUEUE）の設定

この章の内容は、`$define-research-intent`で`GOAL.md`と同時に整理できます。`STATE.json`は現在地と次の作業をスクリプトが判断するための管理ファイルです。実験開始前は`project_id`、`project_status`、`next_action`だけを初期設定の対象にし、処理中の実験（active experiment）は作りません。

### 6.1 STATE.json

最初に`research/STATE.json`の`project_id`を変更します。その他の状態値は原則としてスクリプトが更新します。

主な値は次のとおりです。

| 値 | 意味 |
|---|---|
| `active_experiment` | 現在処理中の実験ID |
| `phase` | 現在の作業段階。計画、実装、実行、監査、評価など |
| `stage` | 実験規模。smoke、pilot、fullのいずれか |
| `review_required` | 実行者とは別の読み取り専用Evaluatorによる監査・評価が必要か |
| `next_action.mode` | 次の一ターンで行う作業とSkillを示す値 |
| `baseline_experiment` | 現在の基準実験 |
| `approvals.full_training_experiment_id` | full実行を承認したID |
| `budgets` | 読込み量、実験数、記録長などの上限。計画本文は`max_experiment_plan_words`、結論本文は`max_experiment_conclusion_words`、生成コンテキストは`max_context_chars`で管理する |

`code_policy`は研究用コードの軽量方針を表します。自動再試行、進捗出力、バッチ・エポック履歴は無効です。

### 6.2 QUEUE.json

`research/QUEUE.json`は、今後試す可能性がある仮説を優先順に置く候補一覧です。ここに入れただけでは実験も学習も始まりません。上位から一件を選んで初めてactive experimentにします。

- 仮説
- 反証条件（どの観測なら候補を棄却または限定するか）
- 最小検証
- primary metric
- baseline
- 関連するclaim ID
- information gain（結果からどれだけ不確実性が減るか）
- decision impact（結果が採用・棄却判断をどれだけ変えるか）
- compute cost（必要な計算量）
- implementation risk（実装不具合や比較不能になる危険）

候補の優先順位は、概念的には次で判断します。

```text
優先度 ≈（情報利得 × 意思決定への影響）÷（計算費用 × 実装リスク）
```

値を厳密な科学指標として扱う必要はありません。同程度の候補から、低費用で次の判断を変えやすい実験を選ぶための補助です。

---

## 7. 論文、GitHub、Web記事、baselineの登録

論文調査は既定ではCodexに行わせません。検索、ダウンロード、OCR、全文要約は人間の明示指示がない限り実行しません。ただし実験計画を策定する場合だけ、容易に想像できる単語による簡易な先行研究検索を許可します。確認するのはタイトル、abstract、検索スニペット程度に限り、類似度の高い2、3件を上限にします。

`paper_knowledge/`に既存の論文知識グラフがある場合は、新しい検索より先に`$query-paper-knowledge`を使い、候補仮説に関係する局所的なquery packを作ります。グラフ更新を伴う調査は、人間が範囲を明示的に許可した時だけ`$research-paper-graph`で別フェーズとして実行します。調査依頼、取込み、検証、ビューワーの操作は`human/PAPER_KNOWLEDGE_MANUAL.ja.md`を参照してください。

画像タスクはテンプレート側で固定しません。分類、復元、超解像、セグメンテーションなどのタスク、モデル構造、指標は、人間が提供した論文、GitHub、Web記事の承認済み範囲に従って決めます。

```text
references/
├── inbox/        # 未整理のユーザー添付ファイル
├── originals/    # 安定した原本
├── records/      # 一文献一Markdownの構造化記録
├── templates/
│   └── REFERENCE.md
└── INDEX.json
```

baselineの登録先は次です。

```text
baselines/
├── AGENTS.md
├── INDEX.json
├── records/
│   └── BASE-001.json
└── templates/
    └── BASELINE.json
```

### 7.1 原本の配置

ユーザーが入手したPDFを`references/inbox/`へ置きます。採用する文献だけを安定したIDへ変更して`references/originals/`へ移します。

例：

```text
references/originals/REF-001.pdf
```

### 7.2 構造化記録

`references/templates/REFERENCE.md`をコピーして次を作ります。

```text
references/records/REF-001.md
```

既定で記録するのは次だけです。

- 書誌情報
- Abstractまたは忠実な短い要約
- 研究との関連
- 支持する点
- 相違または限界
- 追加読取りを許可した正確な節、ページ、図、表

一致する部分だけを残さず、反対結果、適用条件の違い、未検証範囲も分けて記録してください。

### 7.3 Codexに本文を読ませる場合

全文を渡すのではなく、例えば次のように範囲を限定します。

```text
REF-001のMethods 3.2、Table 2、Appendix Aだけを読み、C-003に関係する差異を記録する。
```

論文原本を通常コンテキストへ含めないことで、大幅なトークン消費を防ぎます。

### 7.4 baseline recordとは何か

baseline recordは、「どの資料を根拠に、どの範囲だけをCodexに読ませ、どの実装ファイルへ統合する予定か」を短く書いたJSONです。

例：

```json
{
  "schema_version": "1.0",
  "id": "BASE-001",
  "title": "User supplied image restoration baseline",
  "source": {
    "type": "paper",
    "reference_id": "REF-001",
    "url": null,
    "local_path": null,
    "approved_reading_scope": [
      "Abstract",
      "Method 3.1",
      "Table 2"
    ]
  },
  "implementation": {
    "integration_target": "src",
    "planned_paths": [
      "src/dl_research/models/baseline_model.py"
    ]
  },
  "experiment": {
    "task_from_source": "derive from approved source",
    "primary_metric": "psnr",
    "dataset_assumptions": "Use the fixed split in data/MANIFEST.json"
  },
  "notes": ""
}
```

ここで重要なのは、外部コードを丸ごと保管することではありません。Codexが読む資料範囲と、実装で触ってよい予定ファイルを明示することです。

### 7.5 コマンドでbaselineを登録する

手動で登録する場合は、次のコマンドを使います。

```bash
python scripts/register_baseline.py \
  --id BASE-001 \
  --title "User supplied image restoration baseline" \
  --source-type paper \
  --reference-id REF-001 \
  --scope "Abstract" \
  --scope "Method 3.1" \
  --scope "Table 2" \
  --implementation-path src/dl_research/models/baseline_model.py \
  --metric psnr \
  --dataset-assumption "Use the fixed split in data/MANIFEST.json"
```

GitHubを根拠にする場合も、リポジトリ全体ではなく読んでよいファイルを `--scope` に書きます。

```bash
python scripts/register_baseline.py \
  --id BASE-002 \
  --title "Author GitHub baseline" \
  --source-type github \
  --url "https://github.com/example/project" \
  --scope "models/network.py" \
  --scope "configs/baseline.yaml" \
  --implementation-path src/dl_research/models/github_baseline.py \
  --metric psnr \
  --dataset-assumption "Use local data/MANIFEST.json, not repository data download scripts"
```

成功すると、`baselines/records/BASE-001.json` のような記録が作られ、`baselines/INDEX.json` に追加されます。

### 7.6 Codexにbaseline登録を頼む場合

Codexへ頼む場合は、次のように依頼します。

```text
$register-source-baseline を使って、ユーザー提供資料をbaselineとして登録してください。
資料全体を読まず、REF-001のAbstract、Method 3.1、Table 2だけを読取り許可範囲にしてください。
実装予定先は src/dl_research/models/baseline_model.py です。
```

Codexは `scripts/register_baseline.py` を使い、スクリプトがbaseline IDやscopeの形式を検査します。

---

## 8. Codex向けファイルと言語方針

コード、設定、`AGENTS.md`、Skill、実験記録は英語で保存します。日本語の文書は`human/`配下に置き、人間への説明も日本語で行います。

この制約は`python scripts/validate.py`で検査されます。日本語が`human/`以外へ入るとエラーになります。

### 8.1 AGENTS.mdの階層

`AGENTS.md`は全ディレクトリへ機械的に置いていません。次のような、実際にCodexを開始する作業境界へだけ置きます。

- リポジトリ全体
- 計画
- 実装
- スクリプト
- データ
- 設定
- 実験記録
- 結果
- 参考文献
- 評価Bundle

Codexはリポジトリルートから現在の作業ディレクトリまでの指示を連結して読みます。そのため、無関係な深い階層へ大量に配置すると、作業開始位置によっては指示が増えるだけです。また、`AGENTS.md`や`SCOPE.json`は、作業上の指示・範囲指定であり、それ自体ではファイルを読めなくしません。実際のアクセス制限を設定する場合は、[参照境界の手動設定](AGENT_BOUNDARY.ja.md)を使います。

`STATE.json`には一つの`AGENTS.md`と連結後の文字数上限があり、`validate.py`が肥大化を検出します。長い手順はSkillへ分離され、必要なフェーズでだけ読み込まれます。

### 8.2 スキルを選ぶ情報と、実行時に読む情報

スキルはCodex向けの作業手順です。名前と短い説明は選択時に使い、本文や補足資料は作業に必要なものだけ読みます。例えば、既存グラフの検索は生成された要約を読み、グラフ全体やビューワーの手順書は読み込みません。

[OpenAIの記事](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)を参考に、適用条件を絞り、重複した手順と無条件の資料読込みを整理しています。

### 8.3 テンプレートの保守を依頼する

別のセッションへ作業を渡す場合は、`$handoff-maintenance`で目的・判断・残作業・確認結果を保存します。再開の入口は`maintenance/HANDOFF.md`です。保存後の変化を確認する方法は[機能アップデートの引き継ぎ](MAINTENANCE_HANDOFF.ja.md)を参照してください。

「スキルを修正して」のような依頼では、関係するファイルの編集、確認、修正に起因する不具合の解消まで進めます。実験の「1ターン最大3工程」は保守作業には適用しません。同じ範囲を何度も承認する必要はありません。

- 問題点だけ知りたい場合：`$review-research-loop`で「確認だけ。編集しないで」と依頼します。
- 修正も必要な場合：「見直して修正まで進めて」、または`$apply-research-loop-improvement`で対象と目的を伝えます。

文書だけの修正では、説明文の形式、参照先、既存validatorを確認します。実行処理を変更した場合は、影響するテストも実施します。学習や全テストの実行を毎回要求するものではありません。

実験計画の承認、独立監査、読込み量の上限、無人実行の明示的な依頼は引き続き必要です。保守の変更が進行中の実験の固定済み条件に影響する場合は、その扱いを人間に確認します。

---

## 9. 実験ステージ

### 9.1 smoke

目的は、科学的結論ではなく実装の最低限の成立確認です。

既定上限：

- 1 epoch
- train、validation、testは各2 batch以内
- 通常セッションで簡易評価

確認項目：

- DataLoaderが空でない
- 入出力shapeが一致する
- forwardが通る
- lossが有限
- backwardで勾配が生成される
- 勾配が有限
- checkpointと集約指標が保存される

### 9.2 pilot

目的は、full実験へ進む価値があるかを低費用で判断することです。

既定上限：

- 最大5 epoch
- trainは最大20 batch
- validation、testは各最大10 batch
- 独立Evaluatorによる完全性監査と評価

pilotで意味のある方向性が出ない場合、すぐfullへ進めず、仮説を棄却または限定します。

### 9.3 full

最終的な計算予算を使う実験です。`research/STATE.json`で対象実験IDを明示承認しない限り実行できません。

```bash
python scripts/approve_full.py --id EXP-003
```

fullへ進む前に次を満たしてください。

- smoke成功
- pilotで昇格条件を満たした
- baseline、データ分割、指標、checkpoint ruleが固定済み
- 必要なseed方針が決まっている
- 計算予算が承認されている
- 完全性監査と独立評価を行う

---

## 10. 一件の実験を作る

例として`EXP-001`を作ります。

```bash
python scripts/new_experiment.py --id EXP-001 --stage smoke
```

登録済みbaselineを使う場合は、`--baseline-id`を付けます。

```bash
python scripts/new_experiment.py --id EXP-001 --stage smoke --baseline-id BASE-001
```

`BASE-001`が登録されていない場合は、実験作成前にエラーになります。

```text
ERROR new-experiment: ValueError: unknown baseline ID: BASE-001
```

その場合は、先に `scripts/register_baseline.py` でbaselineを登録してください。

作成される主なファイルは次です。

```text
experiments/active/EXP-001/
├── AGENTS.md
├── EXPERIMENT.md
├── SCOPE.json
└── MANIFEST.json

configs/experiments/EXP-001.json
```

一度にアクティブにできる実験は一件です。別の実験を始める前に、現在の実験を確定してください。

---

## 11. 計画フェーズ

### 11.1 Codexへの指示例

計画は「研究全体で何を確かめる必要があるか」から逆算します。`GOAL.md`の`Evidence Strategy`に、最終的に示したいこと、必要な比較対象・条件、検証する順序、計算予算との釣合いを記録します。今回実行する一実験は、その一部です。

例えば「新手法が条件の変化に強いか」が目的なら、細かな設定を一つ変えるだけで終えず、既存手法との公平な比較、代表的な条件、別の説明を見分ける比較、必要な再確認を計画します。すべてを一度に実行する必要はありませんが、今回調べる範囲と、残りをいつ調べるかを明示します。予算が足りなければ、不十分な小実験で代用せず、目的や予算の見直しを相談します。

Codexをリポジトリルートで開始し、次のように指示します。

```text
$plan-experiment を使ってEXP-001を計画してください。研究目的に必要な比較と規模を先に整理し、今回と後続実験で集める証拠を分けてください。計画をlockした時点で停止し、実装や学習は行わないでください。
```

Skillは次だけを読みます。

- `research/CONTEXT.md`
- `research/GOAL.md`
- `experiments/DIGEST.md`
- 現在の`EXPERIMENT.md`
- 現在のconfig
- 現在の`SCOPE.json`
- configにbaseline IDがある場合は、`baselines/INDEX.json`と該当するbaseline record

### 11.2 EXPERIMENT.md

主要見出しは四つだけです。

```markdown
## Hypothesis
## Method
## Conclusion
## Issues and Next Direction
```

計画時に埋めるのは上二つです。

`Hypothesis`と`Method`は合計700語以内、`Conclusion`と`Issues and Next Direction`は合計400語以内です。`EXPERIMENT.md`全体に対する別の500語制限はありません。これにより計画と結論の双方に必要量を確保しつつ、各段階の冗長化を個別に防ぎます。生成される`research/CONTEXT.md`は従来どおり9,000文字以内です。

#### Hypothesis

- `Research objective`：この実験が研究全体のどの判断に役立つか
- `Study role`：動作確認の`feasibility`、主な効果を調べる`core`、仕組みを確かめる`mechanism`、条件が変わっても結果が保たれるか調べる`robustness`
- `Claim`：検証可能な予測
- `Rationale`：予測する理由
- `Alternative explanation`：提案機構がなくても同じ結果を説明できる、最も有力な別の説明
- `Minimum discriminating evidence`：仮説と別の説明を見分けるのに十分な観測。「最も安い小実験」という意味ではありません
- `Falsifier`：仮説を棄却または限定する結果
- `Primary metric`：主要評価指標と方向
- `Diagnostic guardrail`：`none`、または指標ハック検出だけに使いpromotionには使わない一つの補助値
- `Baseline`：比較対象となる実験ID、外部基準、またはnone
- `Decision mode`：`threshold`または`trend`
- `Minimum meaningful effect`：`threshold`で使う意味のある最小差。`trend`では`not_applicable`
- `Expected trend`：`trend`で期待する方向や形。`threshold`では`not_applicable`
- `Trend evidence rule`：`trend`で最低限必要な比較点と、弱い・逆向き・混在・観測不足の扱い。`threshold`では`not_applicable`
- `Novelty check`：登録済みbaselineや承認済み資料範囲を単純になぞっていない理由
- `Hypothesis policy check`：禁止された仮説立案に該当しない理由
- `Promotion rule`：次ステージへ進む条件

#### Method

- `Evidence coverage`：必要な比較や条件のうち、今回調べる範囲と、後続実験で調べる範囲・着手条件
- `Scale justification`：データ量、観測数、学習量、計算予算が今回の役割に十分で、過小でも過大でもない理由
- `Implementation`：比較する一まとまりの手法。成立に不可欠な複数の構成要素はまとめて実装できますが、無関係な改良は混ぜません
- `Implementation profile`：配線だけの`mechanical`、通常実装の`balanced`、科学的妥当性へ触れる`frontier`
- `Profile rationale`：その段階が研究品質を保つ最小コストである理由
- `Data control`：固定するデータ条件
- `Training`：stage、事前登録するseed、checkpoint、各実行と比較一式の計算上限
- `Evaluation`：baseline比較と判断規則

計画をlockする前に、登録済みbaselineや承認済みの論文・GitHub・Web記事の範囲を見て、その計画が既存研究を単純になぞっていないかを短く確認します。実験計画時だけ、容易に想像できる単語で簡易な先行研究検索をしてよく、対象は類似度の高い2、3件までです。論文全体の読込み、ダウンロード、リポジトリ全体の調査は行いません。

`smoke`はプログラムが動くかを確かめる小規模実行で、`Study role`は`feasibility`だけです。研究上の効果を示すには、目的に十分な規模の`pilot`または`full`を計画します。動作確認を通っただけでは手法を支持する証拠になりません。確認済みの実行経路を、理由なく毎回`smoke`からやり直す必要もありません。

構成要素を外して寄与を調べるアブレーションの網羅探索は後回しにします。ただし、主張と別の説明を見分けるために不可欠な比較は、最初の本検証から含めます。複数の構成要素をまとめて変えた場合、各要素の効果を個別に証明したことにはなりません。

一回の実行では事前に決めた一つのseedを使いますが、それだけで研究全体の信頼性が十分とは限りません。同じコア仮説に必要な比較・反復は、一実験の`comparison`にまとめられます。新しい仮説は別IDにします。良いseedの探索や目的のない条件追加は行いません。実行は一つずつで、計画の拡張は無人ループの起動許可にはなりません。

計画の規模は既存の計画監査で確認し、専用の追加エージェントは起動しません。`Research scale adequacy`は「研究目的に対して比較・観測・計算量が十分か」の確認欄です。必須項目の未記入や`smoke`の区分違反はスクリプトで拒否し、説明内容の科学的な妥当性は監査者が判断します。

特定の仮説立案を禁止したい場合は、計画前に次を使います。

```text
$configure-hypothesis-policy を使って、禁止したい仮説の種類、理由、許可する代替案、見直し条件を設定してください。
```

設定は`research/planning/HYPOTHESIS_POLICY.md`に保存されます。`$plan-experiment`はこの方針を読み、違反する候補仮説を採用しません。使える候補が残らない場合は、計画を進めず、人間に方針または研究目的の見直しを求めます。

### 11.2.1 比較一式を一実験として実行する

従来の単一実行の設定はそのまま使えます。比較が必要な場合だけ、configに`comparison`を追加します。ひな型は`experiments/templates/COMPARISON.json`です。計画時に次のように依頼します。

```text
$plan-experiment を使い、コア仮説は一つに保ったまま、必要な手法比較・条件・反復をcomparisonにまとめてください。共通条件、主比較、集計方法、計算上限を固定し、独立監査へ進めてください。
```

| 設定 | 意味 |
|---|---|
| `arms` | 比較する手法。それぞれコア仮説との関係、モデル設定、必要なら損失関数を指定 |
| `conditions` | 必要なデータ条件。変更するパラメータは全手法に同じように適用 |
| `seeds` | 先に決めた学習用の乱数値。全手法・全条件で同じ一覧を使用 |
| `primary` | 主判定に使う提案手法と比較基準の組合せ。他の手法へ後から差し替えない |
| `aggregation` | 現在は`paired_mean`。同じ条件・seedで対応を取った主比較を、全条件・seedに等しい重みで平均 |
| `max_total_batches` | 動作確認・学習・検証・最終評価を合わせた実行バッチ数の上限 |

例えば3手法 × 2条件 × 2seedなら、一実験の中に12実行を持ちます。**全組合せが必須**なので、必要な比較だけを登録します。既定の上限は一実験24実行で、`STATE.json`の`max_comparison_runs`で管理します。各実行のstage上限とfull承認も引き続き必要です。実行バッチ数は「手法数 × 条件数 × seed数 × {1 + epoch数 × (学習上限 + 検証上限) + test上限}」以下に収まるよう計画します。従来の学習制御調整は実行前の処理で、このバッチ数には含みません。

データ分割・評価処理・学習制御は共有します。学習seedを変えてもデータを変えないよう、`data.seed`を固定します。省略時は親実験のseedを使います。元configのモデルと損失関数は比較基準の手法に合わせ、学習率・バッチサイズの共通調整に使用します。比較基準は実験内で実行するため、`experiment.baseline_id`は`null`にします。過去の結果の自動再利用はしません。

計画・実装の監査と承認は比較一式に対して行います。承認後は通常の`$run-experiment`で全実行を順に処理し、途中で実行ごとのAgentや承認は要求しません。結果は`artifacts/results/<ID>/runs/R001/`などに保存され、親ディレクトリの`metrics.json`に全実行と条件別の比較を集約します。人間の進行確認は`python3 scripts/monitor_experiment.py --id <ID>`です。

全結果が揃うまで結論を確定しません。平均が良くても、必要な対照比較の失敗や逆方向の条件を無視できません。同じデータでの学習反復を、独立したデータでの再現確認と数えないことも重要です。

途中の失敗は結果を残して停止し、自動再試行しません。結果が記録された比較実験を、再実装処理で消去することも拒否します。失敗・処理中の実行の再開や、コード変更後の結果の混在は自動では扱いません。全実行が完了した後の集計・状態更新の復旧では、保存済み結果を照合して学習を省略します。

### 11.3 SCOPE.json

Codexが必要とする正確なファイルを列挙します。

```json
{
  "read_paths": [
    "data/MANIFEST.json",
    "src/dl_research/models/mlp.py"
  ],
  "write_paths": [
    "src/dl_research/models/my_model.py",
    "src/dl_research/models/factory.py"
  ],
  "test_paths": [
    "tests/unit/test_my_model.py"
  ],
  "change_targets": [
    {
      "path": "src/dl_research/models/my_model.py",
      "role": "intervention",
      "action": "create",
      "symbols": ["MyModel"]
    },
    {
      "path": "src/dl_research/models/factory.py",
      "role": "support",
      "action": "modify",
      "symbols": ["build_model"]
    },
    {
      "path": "tests/unit/test_my_model.py",
      "role": "verification",
      "action": "create",
      "symbols": ["test_my_model_shape"]
    }
  ],
  "planning_reads": [
    {
      "path": "src/dl_research/models/factory.py",
      "reason": "Confirm the registration point before locking the scope."
    }
  ],
  "implementation_entry_reads": [
    {
      "path": "src/dl_research/models/factory.py",
      "reason": "Start from the required model registration change."
    }
  ]
}
```

ディレクトリ名や、複数ファイルを一括指定する`*`、`**`などのワイルドカード（glob）は使いません。必要なファイルが増えた場合、黙って範囲を広げず、計画を見直します。

`change_targets`には`write_paths`と`test_paths`の各ファイルを一回ずつ記録します。`action`は新規作成の`create`か既存変更の`modify`、`role`は仮説の本体である`intervention`、接続変更の`support`、テストの`verification`です。`symbols`には変更予定の関数・クラス名を記し、Python以外は`<file>`を使います。

DRAFTを作るだけの段階ではPython本文を読みません。計画時も、まず`TREE.txt`または`rg --files src tests`でファイル名だけを確認します。本文がないと対象を確定できない場合だけ、読む前に`planning_reads`へパスと理由を追加し、必要な関数やクラス周辺だけを確認します。そのパスは`read_paths`、`write_paths`、`test_paths`のいずれかにも必要です。

`planning_reads`の既定上限は一実験3件です。超える場合は読み進めず、設計上の未決事項を人間へ示すか、対象を分けます。上限変更は人間が理由を確認して`STATE.json`で明示的に行います。lock時と`validate.py`実行時に、件数、理由、scope内パスかどうかが検査されます。

`implementation_entry_reads`は、実装時に許可された全ファイルではなく、最初に開くPythonだけです。計画をlockする前に、既存Pythonのうち実装開始に不可欠なものを理由付きで既定最大3件へ絞ります。新規作成するファイルはまだ存在しないため、ここには入れません。実装開始後は、現在見ているコード、targeted test、またはエラーが必要性を示した場合に限り、`read_paths`、`write_paths`、`test_paths`内の別のPythonを一件ずつ追加で確認します。scope全体やtests全体を先に読み込ませません。

### 11.4 計画固定

人間が手で編集した場合は次を実行します。

```bash
python scripts/lock_plan.py --id EXP-001
```

計画固定時に次がハッシュ化されます。

- `Hypothesis`
- `Method`
- config
- `SCOPE.json`
- baseline behavior、candidate behavior、intervention point、unchanged invariants

lock時に`IMPLEMENTATION_DELTA.json`も作られ、変更対象ごとの作成・変更、役割、予定シンボル、変更前hashが固定されます。結果を見た後でこれらを変更すると確定できません。科学的変更が必要なら新しい実験IDを作ります。`mark_implemented.py`が決定的に管理するbatch sizeとlearning rateだけは、調整前に元のhashを検査したうえで共通stage条件へ置き換えます。計画監査ではこの二項目を管理値として扱い、それ以外のconfig変更は監査を失効させます。

### 11.5 指標ハックの計画監査

lock後、実装前に次を依頼します。

```text
$audit-experiment-plan を使ってEXP-001の計画を指標ハックの観点から独立監査し、監査取込み後に停止してください。
```

Plan Auditorは、9,000文字以内の閉じた資料だけから、研究目的とprimary metricの対応、metricだけを改善できる具体的な経路、validationによる選択とtest評価の分離、baseline比較、実装プロファイルを確認します。出力は250語以内です。指標ハックを検出する値が必要でも一つだけで、promotionには使いません。

- `pass`：人間レビューへ進める。
- `warn`：注意点を人間が明示的に受け入れる場合だけ承認できる。
- `fail`：承認できず、計画を`DRAFT`へ戻して修正する。

### 11.6 人間向け計画レビュー

計画監査を受理した後、実装に進む前に人間が計画を確認します。

```text
$review-experiment-plan を使ってEXP-001のlocked planを日本語で説明し、人間レビュー用の確認点を出してください。実装や学習は行わないでください。
```

Codexは、仮説、alternative explanation、minimum discriminating evidence、単一の制御変更、データ条件、seed、評価規則、Python読取り範囲に加え、計画監査の判定、指標ハック経路、補助値、実装プロファイルを日本語で説明します。問題がある場合は計画を直接書き換えず、計画修正を提案します。

レビュー後は、承認または修正要求を明示します。

```text
$approve-or-revise-plan を使ってEXP-001の計画レビュー結果を反映してください。
```

承認された場合だけ、次に行う作業は実装になります。修正が必要な場合は、スクリプトで計画を`DRAFT`へ戻し、`$revise-experiment-plan`で修正してから再度lockします。

---

## 12. 実装フェーズ

モデル、loss、データ処理、評価コードの実装方針に未定項目がある場合は、実装前に`$discuss-implementation-design`で人間と相談します。このスキルはコード編集や学習を行わず、選択肢、研究上の影響、実装リスク、変更対象ファイル、検証方法を整理します。baselineは更新せず、提案手法側の実装方針だけを扱います。

科学条件、評価指標、seed、計算上限、`SCOPE.json`を変える必要が出た場合は、実装を始めず計画を`DRAFT`へ戻して修正します。

Agentを使う計画、実装、各監査、評価では、最初に`scripts/next_agent_action.py`を実行します。状態、承認、ロック済みhash、読取り範囲、監査資料の鮮度を機械的に確認し、保存済み出力が完成していれば再度Agentへ依頼せず取り込みます。返り値の意味は、`build`が資料作成、`compress`が上限内への圧縮、`delegate`がAgentを一回起動、`accept`が完成済み出力の取込み、`blocked`が不整合による停止です。評価記録が完成済みなら`finalize`、smokeで人間または現在のCodexが記入すべき場合は`local`が返ります。

モデル配分は次で固定します。ここでいう`high`と`medium`はモデルの推論量です。

| 作業 | Agent | モデル・推論量 | 選択条件 |
|---|---|---|---|
| 計画 | `research_planner` | `gpt-6-astra`・high | 仮説、反証、評価設計の品質を優先 |
| 計画監査 | `plan_auditor` | `gpt-6-astra`・high・read-only | 指標ハックを計画者から独立確認 |
| 機械的実装 | `mechanical_implementer` | `gpt-5.6-luna`・medium | config、登録、template、testのみで科学的動作を変えない |
| 通常実装 | `experiment_implementer` | `gpt-5.6-terra`・medium | 安定した契約内、低い曖昧さ、原則三つ以内の変更先 |
| 科学的に重要な実装 | `scientific_implementer` | `gpt-6-astra`・high | loss、split、sampling、metric、checkpoint、runner、再現性、外部実装移植に触れる |

各フェーズで使うサブAgentは一つだけです。機械ゲートが`delegate`を返さない限り起動しません。並列の審査会、自動再試行、暗黙の上位モデル切替は行いません。実装中にプロファイル不足が分かった場合は停止して計画を修正し、明示的な再分類による昇格は最大一回です。これにより、計画品質には計算を配分し、定型実装での過剰消費を防ぎます。

学習率とバッチサイズは研究アイデアのコアではないため、Codexの推論では決めません。smokeまたはpilotでは`scripts/tune_training_controls.py`が決定的な候補列を試し、発散しない最大寄りの値から一段余裕を持った値を選びます。選ばれた値は`research/TRAINING_CONTROLS.json`へstageごとの共通条件として固定され、同じstageの後続実験と最終比較では再利用されます。


コード変更は、変更不要なら何もしない、既存コードを再利用する、標準機能または導入済み依存を使う、最後に必要最小限だけ実装する、の順で判断します。将来用の抽象化や依存は追加しません。ただし、データ分割、有限値、再現性、ロック済み計画と成果物hashなど、研究結果を守る検査は省略しません。
### 12.1 Codexへの指示例

```text
$implement-experiment を使ってEXP-001のlocked planだけを実装してください。最初はimplementation_entry_readsだけを開き、その後も必要性が示されたSCOPE.json内のPythonを一件ずつ確認してください。targeted testと必要ならdl-sanityまで実行し、mark-implemented後に停止してください。
```

targeted testは変更箇所だけを確認するテスト、`dl-sanity`は学習前にデータとモデルの基本契約を確認する短い検査です。

Codexは仮説や成功条件を変更できません。変更が必要と判断した場合、実装を続けず計画変更を提案させます。

実装フェーズへ進むには、人間レビュー後の承認が`STATE.json`へ記録されている必要があります。

実装後、smokeは実行へ進み、pilot/fullは先に実装監査へ進みます。失敗時は`error.json`または受理済み監査を起点にし、指摘されたscope内ファイルだけを確認します。

### 12.2 Modelの追加

基底クラスは`src/dl_research/models/base.py`です。新しいモデルは例えば次へ置きます。

```text
src/dl_research/models/my_model.py
```

`forward()`は未正規化のタスク出力を返します。追加後、`src/dl_research/models/factory.py`へ明示登録します。

### 12.3 TrainerとTester

- `Trainer`は学習し、最良epochと集約指標だけを返します
- `Tester`は固定checkpointを評価し、loss、accuracy、件数だけを返します
- バッチ履歴やエポック履歴は保持しません
- 進捗バーやログは出しません

validationデータがある場合、`Trainer`はvalidation lossを監視します。checkpointはvalidation loss最小のepochを保存し、`early_stopping_patience`の期間だけ改善しなければ学習を停止します。primary metricは最終評価用であり、過学習回避の停止基準には使いません。

タスク固有の指標へ変更する場合は、評価規則とmetricsファイルの形式を一つの実験として管理してください。

### 12.4 実装完了の記録

Codexが実行しなかった場合は次を実行します。

```bash
python scripts/mark_implemented.py --id EXP-001
```

`mark_implemented.py`は、各対象の変更後hashと実際に変わったPythonシンボルを`IMPLEMENTATION_DELTA.json`へ追記します。GitのHEADが使える場合は対象外ファイルの作業状態も比較し、未宣言変更があれば停止します。Gitが使えない場合は宣言対象だけを検査します。記録後に対象コードを変更すると学習を開始できません。

### 12.5 pilot・fullの実装監査

`mark_implemented.py`は、pilot/fullを`review_implementation`へ遷移させます。学習前に次を依頼します。

```text
$audit-experiment-implementation を使ってEXP-002の閉じたreview bundleだけを監査し、監査取込み後に停止してください。
```

読み取り専用Evaluatorは、次を確認します。

- locked planへの忠実性
- データ分割と漏洩
- lossと最適化処理
- primary metricの実装
- 再現性とcheckpoint処理
- `SCOPE.json`内の必要最小限の変更か
- 宣言したbaselineからcandidateへの差分と、実測したファイル・シンボル差分が一致するか

`pass`または、注意点を結論へ残せる`warn`なら`implemented`へ進みます。`fail`なら`FAILED`となり、指摘箇所だけを`$debug-failure`で修正します。監査後に計画、config、scope、実装を変えるとhashが一致せず、実行できません。

smokeはこの監査を省略します。

---

## 13. 研究用コードの軽量ポリシー

このテンプレートは研究用であり、常時稼働サービス向けの過剰な防御コードを目的としません。

### 13.1 残す例外検査

研究結果を無効にし得るものだけを早期停止させます。

- 設定の型や必須値が不正
- データ分割が空
- 入出力shapeが不一致
- lossまたは勾配が非有限
- primary metricとbaselineが非互換
- full実行の承認がない
- 計画固定後にconfigが変化
- 実装記録後にコードが変化
- pilot・fullで受理済み実装監査がない、または監査後に対象が変化
- 必須metricsまたはcheckpointが欠落

### 13.2 省略するもの

- 自動再試行
- 別モデル、別データ、別device、別指標への無言fallback
- 内部関数ごとの広範な`try/except`
- 深い独自例外階層
- 発生していない障害への推測的な検査
- 常設のdebug mode
- stack traceやtensor dumpの保存
- batch・epochごとのログ
- 実験に無関係な一般リファクタリング

内部クラスは例外をそのまま上位へ伝えます。CLI境界で一度だけ捕捉し、最終的な一行エラーへ変換します。

### 13.3 デバッグ方針

失敗時だけ`$debug-failure`を使用します。

- 実行失敗なら`error.json`、監査失敗なら受理済み`IMPLEMENTATION_AUDIT.md`または`INTEGRITY_AUDIT.md`を読む
- 最小のコマンドで再現する
- expensive trainingを最初に再実行しない
- 一回の最小修正を行う
- 再発しやすいコード不具合だけ回帰テストを追加する
- 一時的なprintや計測は確定前に削除する

本番配備、外部からの不正入力、分散学習の自動復旧、長時間サービスの監視は別のhardening工程で追加してください。

---

## 14. 実行フェーズ

Codexには実行フェーズだけを依頼し、実処理はPythonスクリプトへ任せます。

pilot/fullでは、受理済み実装監査があり、その後に計画、config、scope、実装が変わっていない場合だけ実行できます。

```text
$run-experiment を使ってEXP-001を一回だけ実行し、実行後に停止してください。
```

同じ処理を手動で起動する場合は次を使います。

```bash
python scripts/run_experiment.py --id EXP-001
```

この一回のコマンドで次を順に行います。

1. config、計画、実装ハッシュと、必要な実装監査を確認
2. 一バッチのsanity check
3. stage上限内の学習
4. 最良checkpointを読み込んでtest評価
5. 実験全体を要約した集約指標（metrics）と実行目録（manifest）を保存
6. ロック済み設定とmetricsのhashを確認し、`DECISION_FACTS.json`へ比較値と機械判定を保存
7. 動作確認のsmokeなら`READY_TO_FINALIZE`へ遷移
8. pilotまたはfullなら監査用パッケージ（review bundle）を作り`REVIEW_REQUIRED`へ遷移

実行と、完全性監査または結果評価は別フェーズです。`TRAINED`でreview経路の作成だけが中断した場合も`$run-experiment`を使いますが、既存のmetricsとmanifestを再利用し、学習を再実行しません。

実行中は何も表示しません。成功時の例：

```text
OK run-experiment EXP-001 phase=READY_TO_FINALIZE test_accuracy=0.750000
```

失敗時の例：

```text
ERROR run-experiment: FloatingPointError: non-finite training loss
```

### 14.1 生成結果

```text
artifacts/results/EXP-001/
├── AGENTS.md
├── best.pt
├── sanity.json
├── metrics.json
├── manifest.json
└── error.json      # 失敗時だけ
```

通常の評価で読むのは`metrics.json`と`manifest.json`だけです。checkpointはモデル再利用または特定の復旧が必要な場合だけ開きます。

結果の解釈が機械的に困難な場合は、Codexに推測させず、人間確認用ファイルを作ります。

```text
$request-human-result-interpretation を使ってEXP-001の結果確認用ファイルを作成してください。
```

人間は`human/results/EXP-001/RESULTS.md`でmetricsと機械判定を確認し、`human/results/EXP-001/INTERPRETATION.md`へ解釈を書きます。`Mechanical rule status`は表示された値をそのまま転記します。`Conclusion`と`Issues and Next Direction`の必須行は`EXPERIMENT.md`へ転記されるため英語で簡潔に書き、日本語の詳細は`Japanese Notes`へ書きます。

### 14.2 保存しないもの

- batch lossの全履歴
- epochごとの全履歴
- progress bar
- console log
- tensor dump
- 正常時のstack trace
- 会話履歴の複製

必要な曲線や詳細分析が研究目的に含まれる場合は、その出力自体を事前に仮説と方法へ記載し、別の小さなartifactとして明示的に追加します。

---

## 15. smoke実験の評価

smokeは独立Evaluatorを使いません。Codexへ次のように指示します。

```text
$evaluate-experiment を使ってEXP-001のaggregate metricsだけを評価し、Supported scopeとUnsupported or missing evidenceを含むConclusion、Issues and Next Directionを埋め、finalizeした時点で停止してください。
```

または人間が直接記入します。

### 15.1 Conclusion

- `Decision`：`support`、`reject`、`inconclusive`
- `Mechanical rule status`：`DECISION_FACTS.json`にある機械判定を変更せず記載
- `Decision-rule assessment`：固定した数値閾値または傾向条件と、実際の観測の対応
- `Primary result`：主要指標の値
- `Baseline comparison`：baselineとの差またはbaseline未設定
- `Supported scope`：実際に支持できるdataset、split、seed、stage、条件
- `Unsupported or missing evidence`：他dataset、他seed、外的妥当性、未実施比較など
- `Confidence and caveats`：smokeであること、件数、既知の制約

`support`は今回の条件内で支持、`reject`は反証条件に該当、`inconclusive`は証拠不足で保留という意味です。`trend`では、期待どおり、弱い、逆向き、混在、情報不足のどれかを`Decision-rule assessment`へ書きます。傾向は次のpilot方針や狭い方向性の主張には使えますが、測っていない効果量まで支持しません。

smokeは実装確認なので、通常は強い科学的支持とはみなしません。動作したことと仮説が支持されたことを区別してください。

### 15.2 Issues and Next Direction

- `Main issue`：最大の未解決点
- `Next action`：pilot、修正、棄却、停止など
- `Stop condition`：`Next action`で提案した次の検証または研究枝を、どの観測・回数・予算で打ち切るか

`Conclusion`と`Issues and Next Direction`の合計は400語以内にします。上限は`finalize_experiment.py`と`validate.py`の両方で検査されます。

### 15.3 確定

`$evaluate-experiment`を使った場合は、必須欄とゲートの確認後に同じ評価フェーズで確定します。人間が直接記入した場合だけ、次を実行します。

```bash
python scripts/finalize_experiment.py --id EXP-001
```

完了すると次が行われます。

- `experiments/active/EXP-001`を`completed/`へ移動
- `experiments/INDEX.json`を更新
- `experiments/DIGEST.md`へ一行要約を追加
- `research/CONTEXT.md`を再生成
- active experimentを空にする

### 15.4 結果レビュー、証拠記録、研究方針更新

確定後、人間向けに結果を確認します。

```text
$review-experiment-result を使ってEXP-001の結果を日本語で説明してください。
```

次に、支持範囲を含む証拠、研究記憶、実験台帳を更新します。

```text
$maintain-research-memory を使って、EXP-001のEVIDENCE、INSIGHTS、DEAD_ENDS、OPEN_QUESTIONS、IDEA_BANK、LEDGERを更新してください。
```

`research/EVIDENCE.jsonl`と`experiments/LEDGER.jsonl`が完了記録と一致すると、状態は`update_direction`へ進みます。その後、前の実験結果を受けて研究方針を更新します。

```text
$update-research-direction を使って、前の実験結果に基づき research/PROPOSED_METHOD.md、CLAIMS、QUEUE、DECISIONSを更新してください。
baselineは更新しないでください。
```

結果から新規仮説が導ける場合は、既存キューが残っていても、方針更新の中で候補を最大一件追加します。`research/ideas/IDEA_BANK.jsonl`へ`candidate`として保存し、元の実験・証拠ID、未検証の機構、反証条件、次の十分な比較を記録します。既存案と重複する場合は再利用し、ポリシー違反や既知の失敗案は追加しません。候補がなければ、その理由を`DECISIONS.md`へ残します。

```text
$update-research-direction を使って、EXP-001の結果から新規仮説候補があれば根拠付きで追加してください。既存候補と比較し、次に検証する案は最大一件に絞ってください。
```

候補の保存だけでは次の実験の作成・承認・実行には進みません。結果説明だけを依頼した場合は追加経路を提案し、ファイルは変更しません。自律モードの`update_direction`と明示した無介入1ループでは、この候補確認を既存の方針更新工程で行います。候補は未検証の推論として扱い、新規性・計画審査を省略しません。外部調査の許可は拡張しません。

有望な結果はbaselineへ昇格せず、`research/PROPOSED_METHOD.md`の提案手法として更新します。baselineは比較基準として維持し、新しい提案手法は次のqueue itemで検証します。

結果後は、固定済みの集約結果だけで観測、解釈、研究上の含意を分けます。修正順は、まず主張を狭めるか言い換え、重要な曖昧さが残る場合だけalternative explanationを見分ける実験を一件置き、それ以外は停止または保留です。結果を見てから別metricや都合のよいパターンを探して主張を救済しません。

次の候補が定まったら、別ターンで一件だけ実験を作ります。

```text
$select-next-experiment を使って、次の実験を一件だけDRAFTとして作成してください。
```

---

## 16. pilot・full実験の実行後監査と独立評価

pilotとfullでは、12.5の実装監査を受理して実行した後、結果の監査・評価に必要な情報だけを集めた閉じた資料（review bundle）が再構成されます。

```text
review/bundles/EXP-002/
├── GOAL.md
├── IMPLEMENTATION_AUDIT.md
├── EXPERIMENT.md
├── METRICS.json
├── BASELINE.json
├── DECISION_FACTS.json
├── MANIFEST.json
├── CONFIG.json
├── SCOPE.json
├── implementation/        # 実装監査時からhashで追跡する変更snapshot
├── REQUEST.json
├── INTEGRITY_REQUEST.json
├── INTEGRITY_AUDIT.md
└── EVALUATION.md
```

実装全体ではなく、当該実験で記録されたファイルのsnapshotだけを含みます。checkpoint、生ログ、データ本体、論文PDFは含まれません。

### 16.1 完全性監査

通常のCodexセッションから次のように指示します。監査だけで一ターンを終了します。

```text
$audit-experiment-integrity を使ってEXP-002の閉じたreview bundleだけを監査し、監査取込み後に停止してください。
```

read-only evaluatorは`INTEGRITY_AUDIT.md`へ次を記録します。

- `Verdict`：`pass`、`warn`、`fail`
- 結果出所とmanifestの整合
- locked plan、config、scopeへの準拠
- metricの意味と計算条件の妥当性
- データリークとsplitのリスク
- 実行範囲を越えた主張がないか

`python scripts/accept_integrity_audit.py --id EXP-002`で監査を取り込むと、監査本文と対象入力のhashがactive manifestへ固定されます。再開時に両方が一致していれば監査Agentを再起動せず評価へ進みます。`pass`または`warn`なら評価へ進み、`fail`なら`FAILED`へ遷移して修正が必要です。

`pass`は重大な問題なし、`warn`は結論の範囲を狭めれば利用可能、`fail`は結果を主張評価へ使えない重大な問題あり、という判定です。

### 16.2 支持可能な主張の独立評価

監査受理後の次ターンで評価します。

```text
$evaluate-experiment を使ってEXP-002のaggregate evidenceを最小の支持可能なclaimへ対応付け、確定後に停止してください。
```

Evaluatorは`.codex/agents/evaluator.toml`で読み取り専用に設定されています。独立性を保つため、実装時の会話、コード全体、checkpointを読ませません。metric名、向き、baselineとの差、閾値比較、hashは`DECISION_FACTS.json`を正とし、Evaluatorには再計算させません。Evaluatorは監査上の注意、仮説との対応、支持範囲、未解決点の判断に集中し、`EVALUATION.md`へ`Supported scope`と`Unsupported or missing evidence`を必ず記入します。

利用中のCodex環境でcustom evaluatorを起動できない場合は、別の新規セッションを閉じたbundleで開始します。実行前は`IMPLEMENTATION_AUDIT.md`、実行後は`INTEGRITY_AUDIT.md`、その受理後は`EVALUATION.md`だけを読み取り専用で完成させます。人間が同じテンプレートを記入しても構いません。

### 16.3 監査と評価の取込み

```bash
python scripts/accept_integrity_audit.py --id EXP-002
python scripts/accept_evaluation.py --id EXP-002
python scripts/finalize_experiment.py --id EXP-002
```

skillを使う場合、各取込みコマンドと`finalize_experiment.py`はskill内で実行されます。手動運用では、上記を一つずつ実行します。`accept_evaluation.py`は監査判定と監査対象hashを再確認してから、`Conclusion`と`Issues and Next Direction`をアクティブ記録へ反映します。

### 16.4 監査後と評価時に禁止すること

- 結果を見てminimum effectを下げる
- primary metricを都合のよいsecondary metricへ変更する
- baselineを差し替える
- データsplitを変更する
- checkpoint選択規則を変更する
- コードを修正する
- その場で次の実験を開始する

受理済み監査の後でmetrics、runtime manifest、config、scope、実装snapshotの元ファイルを変更すると、評価または確定は拒否されます。必要な修正は現在の実験を`FAILED`から復旧するか、確定後に別IDの実験として計画します。ただし、実行記録のある比較実験は、以下のとおり通常の修復には進めません。

新しい疑問は`Next action`へ書き、現在の実験を確定してから別IDで検証します。

---

## 17. 失敗時の復旧

`$debug-failure`は修復前に機械判定を実行します。比較実験に`comparison_state.json`がある場合は、ソースを読み込んで修正を始める前に停止します。人間が中止を選んだ場合は17.2の手順で記録を保存して閉じます。結果や進捗ファイルを消して通常の修復へ戻さないでください。実行開始前の失敗と、従来の単一実行では、以下の通常手順を使えます。

スーパーバイザ（研究全体を進行する親Agent）は、失敗の詳細やソースを読み込まず、専用の修復Agentへ渡します。修復Agentは元の実装会話を引き継がない新しい会話で、固定済みの実装プロファイルと変更範囲だけを使います。調査中の仮説、差分、テスト出力は修復Agent側に留め、親には短い状態確認だけを返します。

実行が失敗すると状態は`FAILED`になり、次が作られます。

```text
artifacts/results/<ID>/error.json
```

内容は実験ID、失敗時フェーズ、例外型、一行メッセージだけです。

実装監査または完全性監査が`fail`となった場合も状態は`FAILED`になります。この場合は`error.json`ではなく、`experiments/active/<ID>/IMPLEMENTATION_AUDIT.md`または`INTEGRITY_AUDIT.md`のblocking issueとrequired actionを修正根拠にします。

Codexへの指示例：

```text
$debug-failure を使い、EXP-001の修復を新しい専用Agentへ渡してください。科学的条件を変えず、親は詳細を読み込まずに完了状態だけ確認し、実験実行前に停止してください。
```

修正後は`mark_implemented.py`が変更箇所と修復回数を記録し、状態を`IMPLEMENTED`へ戻します。親は`python3 scripts/repair_context.py status --id EXP-001`で実装hash・固定条件・修復記録を確認し、実験ID、変更ファイル数、次の工程だけを受け取ります。pilot/fullでは再度の実装監査を経てから、次の実行を判断します。

```bash
python scripts/run_experiment.py --id EXP-001
```

修復依頼書は`review/repairs/<ID>/attempt-001/REQUEST.json`などに保存され、最大6,000文字です。内容は失敗の要点、変更可能箇所、計画・設定への参照です。親は依頼書を開かず、パスだけを新しいAgentへ渡します。修復できない場合の返答も80語以内に絞り、別Agentへの再試行や親自身によるデバッグは行いません。依頼書と元の失敗情報は、必要時に対象IDを指定して調べられます。

### 17.1 典型的な分類

| 分類 | 最初に確認するもの |
|---|---|
| configuration | configの名前、型、必須値 |
| data contract | 空split、shape、dtype、label範囲 |
| model contract | 入力shape、出力クラス数、lossとの整合 |
| numerical | 非有限loss、学習率、AMP、gradient |
| environment | device指定、PyTorch、依存関係 |
| infrastructure | 容量、権限、壊れたファイル |
| integrity audit | 結果出所、計画逸脱、metric不整合、リーク、scope超過 |

失敗のたびに大規模な例外処理を追加しないでください。原因となった契約だけを修正します。

### 17.2 失敗した比較実験を記録を残して中止する

対象は`FAILED`で実行記録のある比較実験だけです。実行中のプロセスを終了させるコマンドではありません。人間が対象IDを指定して中止を明言した場合だけ実行します。単に「Next」と言うことや無介入モードの許可は、中止の許可にはなりません。

```bash
python3 scripts/abort_comparison.py --id EXP-001 --reason "Data contract failure requires a revised plan" --confirm-abort
```

理由は英語で400文字以内に記入します。計画と監査記録は`experiments/aborted/EXP-001/`へ移り、`ABORTION.json`に理由・元の管理情報・主要ファイルのhashを保存します。config、実行結果、checkpoint、レビュー用資料は元の場所に残ります。`ABORTED`は「中止済み」であり、成功・失敗という科学的結論ではありません。比較基準や受理済み証拠への流用はしません。

直近の中止理由は`DIGEST.md`に最大5件・各160文字で表示し、全文は保存記録に残します。アクティブ枠と対象実験への承認を解除しますが、最新の評価完了実験や研究上の主張は変更しません。自動で再実行せず、次は具体的な修正方針を検討して別IDで計画・監査・承認をやり直します。同じIDは再利用できません。

中止処理自体が途中で止まった場合は、同じID・理由・確認フラグで再実行すると、記録を照合して終了処理だけを進めます。実験の学習処理は再開しません。記録が変更されている場合や別の実験が進行している場合は拒否します。

---

## 18. 状態機械

状態機械とは、実験が「計画前からいきなり確定」のような不正な順序で進まないよう、許可された作業順をスクリプトで管理する仕組みです。

主な遷移は次です。

```text
DRAFT
  ↓ lock-plan
PLANNED
  ↓ mark-implemented
IMPLEMENTED
  ↓ sanity成功
SANITY_PASSED
  ↓ 学習・test成功
TRAINED
  ├─ smoke → READY_TO_FINALIZE
  └─ pilot/full → REVIEW_REQUIRED
                    ↓ accept-integrity-audit: pass/warn
                 REVIEW_REQUIRED
                    ↓ accept-evaluation
                 READY_TO_FINALIZE
                    ↓ finalize
                 FINALIZED

IMPLEMENTED / SANITY_PASSED / TRAINED
  └─ 実行失敗 → FAILED → mark-implemented → IMPLEMENTED

REVIEW_REQUIRED
  └─ integrity audit fail → FAILED → debug-failure → IMPLEMENTED

実行記録のある比較実験のFAILED
  └─ 人間の中止指示 → abort-comparison → ABORTED → select_experiment

確定後のnext_action.mode
  maintain_memory → update_direction → select_experiment
```

自然言語で状態値を直接書き換えず、原則としてスクリプトを使います。

現在地は次で確認できます。

```bash
cat research/CONTEXT.md
```

---

## 19. トークンを抑える運用

### 19.1 一セッション一作業

計画、実装、実行、評価を一つの長い会話で連続実行しません。各フェーズ終了後にファイルへ状態を保存し、必要なら新しいCodexセッションを開始します。

`automation/ONE_CYCLE_PROMPT.md`は、ルーターが返す同じ`operation`内だけ最大三フェーズを実行する短いプロンプトです。結果確認作業では監査から評価・最終化まで、実験後整理作業では記憶更新から次のDRAFT作成までをまとめ、別の作業または人間判断の前で停止します。

### 19.2 CONTEXT.mdから始める

過去の全会話や全実験を渡さず、`research/CONTEXT.md`を入口にします。このファイルには現在地、次の行動、Goalの要点、現在の仮説と方法、限定したパス、最近のDigestだけが入ります。

生成後の上限は9,000文字です。長いactive計画が含まれる場合はDigestを省き、それでも超える場合は上限内へ切り詰めたことを末尾に表示します。

### 19.3 完了実験はDIGESTから読む

`experiments/completed/`を再帰的に読ませません。まず`experiments/DIGEST.md`を読み、必要な実験IDだけを指定して詳細を開きます。

### 19.4 SCOPE.jsonを厳密にする

「関連ファイルを探して」ではなく、計画フェーズで正確なファイルと変更予定シンボルを列挙します。ファイル数上限は`STATE.json`の`max_scope_files`で管理され、lock後は宣言外の変更を機械検査します。

### 19.5 計画時はPython本文よりパス一覧を使う

DRAFT作成ではPython本文を開きません。計画時はパス一覧から候補を絞り、本文確認が不可欠なファイルだけを`planning_reads`へ理由付きで先に記録します。既定の3件を超えて探索しません。

### 19.6 実装時は入口から一件ずつ読む

計画をlockする前に、実装開始に必要なPythonだけを`implementation_entry_reads`へ理由付きで記録します。実装ではその入口だけを先に開き、追加ファイルは現在のコード、targeted test、またはエラーが必要性を示した時にscope内から一件ずつ確認します。実行と結果評価では実装Pythonを読み直しません。

### 19.7 機械処理をPythonへ任せる

次はCodexに計算させません。

- 設定検査
- ハッシュ計算
- 状態遷移
- sanity check
- 学習
- 指標集計
- baseline差分
- review bundle生成
- 完全性監査対象のhash固定と再検証
- 証拠・実験台帳の完了検査
- Digest生成

Codexは仮説、実装差分、結果の意味、次の検証に集中します。

### 19.8 Agentと監査資料の上限

一フェーズのサブAgentは一つです。テンプレートの`.codex/config.toml`では、セッション全体のスレッド数や階層を制限しません。`max_concurrent_threads_per_session`、旧名の`max_threads`、`max_depth`は設定せず、利用環境に任せます。Codex本体やユーザー設定の上限を無制限にする変更ではありません。成果物を保存した完了済みサブAgentは、終了ツールが使える環境では閉じ、繰り返し実験で開いたスレッドを溜めません。新しい監査には独立したAgentを使います。既存チャットでは変更前の設定が残る可能性があるため、設定反映後に新しいチャットで再開してください。

計画監査の入力とひな型は合計9,000文字、出力は250語までです。自動再試行はなく、実装モデルの昇格は計画を修正して明示的に再分類した場合の最大一回だけです。これらの研究上の上限は`research/STATE.json`と`validate.py`で検査されます。

字数だけの超過では、`$compress-audit-material`が同じ工程内で圧縮し、再確認して続きを進めます。計画監査の入力は、まずJSONの空白などを減らし、値や固定済み計画は変えません。各監査の出力文書も9,000文字のコンテキスト上限へ収め、計画監査では250語の制限も維持します。圧縮に追加承認や別の監査Agentは不要です。

重複除去だけで収まらない未受理の監査文は、`review/compression/<ID>/<監査種別>/`に原文`ORIGINAL.md`と短縮案`CANDIDATE.md`を保存します。短縮案では繰り返しを減らしますが、各項目の固有の語句、判定、根拠、数値、否定や限定条件は残します。スクリプトの検査だけでは意味が同じとは証明できないため、Codexは原文と照合してから適用します。受理済みの監査文は変更しません。

```bash
python3 scripts/compress_audit_material.py --id EXP-001 --task plan-audit
```

`status=ready`なら元の監査判定を再実行します。`status=needs-edit`なら示された短縮案を直し、同じコマンドに`--apply`を付けて検証・適用します。`--task`には実装監査の`implementation-audit`、実行後監査の`integrity-audit`も指定できます。必要な根拠そのものが上限に収まらない場合や、短縮で意味が失われる場合は停止します。上限緩和や根拠の削除で通すことはありません。

primary metricは一つです。指標ハック経路を検出するdiagnostic guardrailは最大一つだけ許し、採用判定には使いません。多数の評価値を積み上げて、良かったものを後から選ぶ運用はしません。

#### 19.8.1 サブAgentの既定モデルを指定する

`$set-subagent-defaults`で、このプロジェクトの`.codex/config.toml`に既定モデルと必要に応じて推論強度を設定できます。例えば次のように依頼します。

```text
$set-subagent-defaults サブエージェントの既定モデルを gpt-6.1-sol、推論強度を medium に設定して
```

モデル名と推論強度は利用環境で対応している値を指定してください。モデル名だけなら既存の推論強度を保持し、非対応の組合せなら変更前に確認します。「現在の既定設定を確認して」「既定モデルと推論強度の指定を解除して」にも対応します。解除ではキーを削除し、上位の設定や継承に戻します。空文字を設定する操作ではありません。

変更するのは`[agents]`内の`default_subagent_model`と、依頼された場合の`default_subagent_reasoning_effort`だけです。ユーザー全体の設定を変更したい場合は、その対象を明示してください。既定モデルは、起動時の明示指定や役割別ファイルのモデル指定より優先されません。このテンプレートで固定済みの計画・監査モデル、実装プロファイル、実験計画は書き換えません。既定値を設定しても、これらの専用Agentが一律に切り替わるわけではありません。[公式のサブAgent設定](https://learn.chatgpt.com/docs/agent-configuration/subagents)を参照してください。

実行中のAgentの設定は変わりません。設定を再読込した新しいチャットで、新規サブAgentへの適用を確認してください。スキルを作成しただけではモデルを選択・変更しません。

### 19.9 重要実験だけ独立監査・評価

smokeごとにEvaluatorを起動しません。pilot、full、予想外に大きい改善、指標間の矛盾、報告に使用する結果だけ、閉じたBundleで完全性監査と独立評価を行います。

### 19.10 論文は構造化記録を優先

通常はAbstractと関連点だけを使い、本文は正確な節や図表に限定します。

### 19.11 研究記憶を短く保つ

長期研究では、すべての過去実験を読み直しません。`research/memory/`に再利用する知見、再試行しない方向、未解決問題だけを残します。候補仮説は`research/ideas/IDEA_BANK.jsonl`に置き、新規性確認は`research/novelty/NOVELTY_CHECKS.jsonl`へ短く記録します。

完了実験は`experiments/LEDGER.jsonl`へ構造化して追記し、claimへ接続する根拠は`research/EVIDENCE.jsonl`へ判定規則との対応、支持範囲、不足証拠を含めて追記します。これにより、Codexは過去会話ではなく短い台帳から次の研究枝を選べます。

### 19.12 AIとの分業

通常のCodexは一つの限定された`operation`だけを進めます。同じ判断目的の機械処理だけをまとめ、計画、実装、実行、結果確認をまたぎません。既存グラフの局所照会は`$query-paper-knowledge`、許可済み調査とグラフ更新は`$research-paper-graph`、広い探索は`$scan-research-landscape`、次の枝選択は`$select-research-branch`、新規性確認は`$audit-novelty`に分けます。長時間実験の途中確認は`$monitor-experiment`とスクリプトに任せ、LLMで途中解釈しません。

---

## 20. 比較基準（baseline）の作り方

最初の有効な実験は、通常baselineの確立です。

baselineには二種類あります。

| 種類 | 例 | 使い方 |
|---|---|---|
| 外部資料baseline | 論文、GitHub、Web記事に基づくモデル | `baselines/records/BASE-001.json`へ登録し、実験作成時に`--baseline-id`で指定する |
| 完了実験baseline | 自分の過去実験の結果 | 完了後に`research/STATE.json`の`baseline_experiment`や次実験のconfigで参照する |

外部資料baselineを作る基本手順は次です。

1. 人間が資料を用意する
2. Codexに読ませてよい節、ページ、図、表、GitHubファイルを決める
3. `scripts/register_baseline.py`で`BASE-001`のようなIDを登録する
4. `python scripts/new_experiment.py --id EXP-001 --stage smoke --baseline-id BASE-001`で実験を作る
5. `$plan-experiment`で、資料に準拠した実装方針と`SCOPE.json`を固定する
6. `$implement-experiment`で、外部コードを丸ごとコピーせず、必要な最小実装を`src/`へ統合する
7. smokeで実装を確認する
8. pilotで学習可能性を確認する
9. 必要なseedでfull評価する
10. 完了後に、その実験IDを以後の比較baselineとして使う

baselineと比較実験では、原則として次を同じにします。

- データ版とsplit
- primary metric
- test処理
- checkpoint選択
- 乱数方針
- 計算予算の比較可能性

異なる場合は`Method`と`Confidence and caveats`へ明記します。

---

## 21. 効率的な実験計画

### 21.1 研究目的から必要な証拠を決める

研究全体で示したいことから、必要な比較・条件・別の説明の検証を整理します。そのうち今回どこまで確かめるかを選びます。無関係な改良は混ぜませんが、一つの手法を成り立たせる複数の構成要素を無理に小分けにはしません。

### 21.2 十分な規模を選び、その後で費用を抑える

「動くか」だけなら`smoke`、研究上の傾向や効果を調べるなら目的に十分な`pilot`または`full`を選びます。必要なデータ量・観測数・計算量を説明し、より小さい実験では何が分からず、より大きい実験を今は行わない理由は何かを記録します。予算に収まらなければ、実験を不十分な規模に縮めず、目的や予算を相談します。`full`の明示的承認は引き続き必要です。

### 21.3 反証条件を先に書く

成功だけでなく、どの結果なら棄却または限定するかを計画時に書きます。これにより、悪い結果を見て追加実験を無制限に増やすことを防ぎます。

### 21.4 判定方式を事前に選ぶ

`threshold`の`minimum meaningful effect`は、統計的または数値的に僅かな差ではなく、採用判断を変える最小差です。計算費用や推論時間の増加も含めます。

妥当な閾値がまだない場合は`trend`を選べます。ただし「良さそう」では不十分です。例えば、固定した三つのノイズ水準で指標が同じ方向へ変わることを期待し、一点でも逆転すれば混在、全点で逆なら反証、と結果より前に書きます。

### 21.5 昇格条件を明示する

例：

```text
smokeで有限lossとcheckpoint生成を確認し、pilotでbaseline比+0.01以上ならfullへ進む。
```

### 21.6 停止条件を守る

ここで止める対象は、現在の手法案に対する追加実験です。改善が出ないたびにハイパーパラメータを追加探索すると、計算量と選択バイアスが増えます。事前に定めた試行数、費用、改善量に達したらその研究枝を打ち切り、別案へ移るか研究全体を終了します。

---

## 22. よく使うコマンド一覧

```bash
# 構造検査
python scripts/validate.py

# 単体・smokeテスト
python -m pytest -q

# 外部資料baselineを登録
python scripts/register_baseline.py \
  --id BASE-001 \
  --title "User supplied image baseline" \
  --source-type paper \
  --reference-id REF-001 \
  --scope "Abstract" \
  --scope "Method 3.1" \
  --implementation-path src/dl_research/models/baseline_model.py \
  --metric psnr \
  --dataset-assumption "Use the fixed split in data/MANIFEST.json"

# 実験作成
python scripts/new_experiment.py --id EXP-001 --stage smoke

# baseline付き実験作成
python scripts/new_experiment.py --id EXP-001 --stage smoke --baseline-id BASE-001

# 計画固定
python scripts/lock_plan.py --id EXP-001

# 計画監査bundleの作成と、記入済み監査の取込み
python scripts/build_plan_review_bundle.py --id EXP-001
python scripts/accept_plan_audit.py --id EXP-001

# 実装ハッシュ記録
python scripts/mark_implemented.py --id EXP-001

# full実験の承認
python scripts/approve_full.py --id EXP-003

# sanity・学習・test・結果集約
python scripts/run_experiment.py --id EXP-001

# review bundleを再生成する場合
python scripts/build_review_bundle.py --id EXP-002

# 完全性監査の取込み
python scripts/accept_integrity_audit.py --id EXP-002

# 独立評価の取込み
python scripts/accept_evaluation.py --id EXP-002

# 実験確定
python scripts/finalize_experiment.py --id EXP-001

# 証拠・研究記憶と実験台帳を記録した後の完了検査
python scripts/complete_memory_update.py

# 研究方針を更新した後の完了検査
python scripts/complete_direction_update.py

# 圧縮コンテキスト再生成
python scripts/build_context.py

# 完了実験Digest再生成
python scripts/build_digest.py
```

Makefileを使う場合：

```bash
make new ID=EXP-001 STAGE=smoke
make lock ID=EXP-001
make implemented ID=EXP-001
make run ID=EXP-001
make finalize ID=EXP-001
```

---

## 23. Codexへの短い指示例

### 初期設定

```text
$initial-setup を使って研究開始設定を対話で行ってください。
研究目的、データ、ベースライン資料、承認済み読取り範囲、最初のsmoke目的を確認し、
必要な設定とbaseline recordを作成してください。
論文やGitHub全体は読まないでください。
```

### 計画

```text
$plan-experimentでEXP-001を計画してください。
Goal、Digest、active record、config、scope、必要ならBASE-001のbaseline recordだけを読み、
lock-plan後に停止してください。
```

### 計画監査

```text
$audit-experiment-planでEXP-001の主評価指標をハックできる計画になっていないか独立監査し、監査取込み後に停止してください。
```

### 実装

```text
$implement-experimentでEXP-001を実装してください。locked fieldsを変更せず、SCOPE.json内だけを扱い、targeted testsとmark-implemented後に停止してください。
```

### 実装監査（pilot・full）

```text
$audit-experiment-implementationでEXP-002の閉じたreview bundleだけを監査し、監査取込み後に停止してください。
```

### 実行

```text
$run-experimentでEXP-001を一回だけ実行し、実行後に停止してください。評価や修正を同じターンで行わないでください。
```

### smoke評価

```text
$evaluate-experimentでEXP-001のmetricsとbaselineだけを評価し、支持範囲と不足証拠を含む結論と次方針を記入してfinalize後に停止してください。
```

### 完全性監査

```text
$audit-experiment-integrityでEXP-002の閉じたreview bundleだけを監査し、監査取込み後に停止してください。
```

### 独立評価

```text
$evaluate-experimentでEXP-002の受理済み監査とaggregate evidenceだけを読み、支持範囲と不足証拠を記入して確定後に停止してください。
```

### 確定後の研究記憶

```text
$maintain-research-memoryで最新の完了実験からEVIDENCE、研究記憶、IDEA_BANK、実験台帳を更新し、完了検査後に停止してください。
```

### 失敗修正

```text
$debug-failureでEXP-001のerror.json、失敗したIMPLEMENTATION_AUDIT.md、またはINTEGRITY_AUDIT.mdから原因を一つ診断し、科学的条件を変えず一つの最小修正だけ行い、mark-implemented後に停止してください。
```

### 一作業自動実行

```text
automation/ONE_CYCLE_PROMPT.mdに従い、ルーターが返す次の一作業だけ実行し、別の作業または人間判断の前で停止してください。
```

### 明示専用の無介入1ループ

```text
$run-one-unattended-loop を明示的に使用し、研究実験を1ループだけ無介入で実施してください。
```

この指示は、独立した計画監査が`pass`の対象一件だけを先に承認します。`warn`、`fail`、full実行、広い外部調査、人間にしか決められない結果解釈、失敗後の再試行は別の判断または作業です。対象と進捗は`STATE.unattended_loop`へ復帰用に残りますが、実行許可は保存されません。

---

## 24. 研究開始チェックリスト

### 環境

- [ ] `$prepare-environment`で環境とGit状態を確認した
- [ ] 仮想環境を作成した
- [ ] `pip install -e ".[dev]"`が完了した
- [ ] `validate.py`が成功した
- [ ] `pytest`が成功した
- [ ] Gitを初期化した

### データ

- [ ] `$prepare-data-manifest`でデータ事実と未解決項目を整理した
- [ ] 原データを`data/raw/`へ配置した
- [ ] ライセンスと入手元を確認した
- [ ] `data/MANIFEST.json`を作成した
- [ ] train、validation、testを固定した
- [ ] 重複またはリークを確認した
- [ ] DataLoaderをfactoryへ登録した

### 研究目的

- [ ] `$define-research-intent`で研究目標、主張、次に試す候補一覧、現在状態を初期化した
- [ ] 研究質問が比較可能な形で書かれている
- [ ] 結果により変える行動が書かれている
- [ ] 結論を適用する範囲と対象外が明示されている
- [ ] 主判定に使う一つの評価指標と、良い方向が固定されている
- [ ] `threshold`なら最小改善量、`trend`なら期待する形・最低比較点・矛盾条件がある
- [ ] 比較基準がある、または最初に確立する
- [ ] 計算予算と、研究枝または研究全体を何の条件で止めるかがある

### 参考文献

- [ ] 比較基準の資料がある場合、`$register-source-baseline`で登録した
- [ ] 必要なPDFをユーザーが配置した
- [ ] 原本と構造化記録を分けた
- [ ] Abstractと関連点を記録した
- [ ] 支持だけでなく相違と限界を記録した
- [ ] 本文読取り範囲を必要最小限にした
- [ ] GitHubやWeb記事を使う場合、読んでよいファイルやURLを限定した
- [ ] 比較基準を使う場合、`BASE-001`のようなIDで登録した
- [ ] 比較基準の出典記録に主評価指標と実装予定先を書いた

### 実験

- [ ] 一件だけactiveにした
- [ ] 必要なら`--baseline-id BASE-001`付きで実験を作った
- [ ] 仮説と反証条件を事前に書いた
- [ ] 最も有力なalternative explanationを一つ書いた
- [ ] 仮説と別の説明を見分けるminimum discriminating evidenceを固定した
- [ ] 一つの制御された変更にした
- [ ] primary metricは一つだけで、補助値をpromotionに使っていない
- [ ] `mechanical`、`balanced`、`frontier`の実装プロファイルと理由を固定した
- [ ] SCOPE.jsonへ正確なファイルを列挙した
- [ ] smokeから開始した
- [ ] 結果を見る前に計画をlockした
- [ ] 実装前に計画監査を受理し、`warn`なら注意点を人間が明示的に判断した
- [ ] 実装後にmark-implementedした
- [ ] pilot・fullでは、実行前に実装監査を受理した
- [ ] batch履歴ではなく、実験全体を要約した評価値で評価した
- [ ] pilot・fullでは、評価前に完全性監査を受理した
- [ ] 結果出所、計画遵守、評価指標、test情報の混入、結論範囲を確認した
- [ ] 支持範囲と不足証拠を明記した
- [ ] 結論、課題、次方針を記録した
- [ ] finalize後に`EVIDENCE.jsonl`、研究記憶、実験台帳を更新した
- [ ] 研究方針を更新してから次の実験を一件だけ作る

---

## 25. 最終的な運用原則

このテンプレートでは、次の五点を崩さないことが重要です。

1. **研究目的に十分な比較と規模を計画し、一まとまりの手法を一実験ずつ検証する。**
2. **計画を独立監査し、実装は科学的リスクに合う最小のAgent一つだけを使う。**
3. **学習と集計は決定的なプログラムへ任せ、Codexへログを読ませない。**
4. **研究結果を壊す異常だけを検出し、過剰な例外処理・再試行・デバッグ機構を追加しない。**
5. **詳細履歴ではなく、支持範囲付きのEvidence、Hypothesis、Method、Conclusion、Issues and Next Directionへ圧縮して次の実験を決める。**

この形にすると、実験の独立性と再現性を維持しながら、Codexのコンテキスト量、論文読取り量、Agent間の重複、学習ログの再読を抑えられます。
