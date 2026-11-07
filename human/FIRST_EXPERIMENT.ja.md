# 最初の実験を始める手順

この文書は、参照できる前回実験がない状態から、最初の実験をまだ修正可能な計画下書き（`DRAFT`）として作り、計画レビューへ進むまでを説明します。

ここでは、前回結果に基づく研究方針更新は行いません。最初の実験では、研究目的、データ事実、baseline資料、最初に検証する仮説を人間が決め、Codexに記録させます。

## 到達点

この手順の到達点は次です。

- `research/GOAL.md` が埋まっている。
- `data/MANIFEST.json` にデータ事実がある。
- 必要なら baseline record が登録されている。
- `research/QUEUE.json` に最初の候補がある。
- `research/PROPOSED_METHOD.md` に最初の提案手法がある。
- `experiments/active/<ID>/` に最初の実験が `DRAFT` として作られている。
- 次に `$plan-experiment` を使える状態になっている。

まだ実装、学習、評価は行いません。

この文書では、ファイル名、コマンド名、状態名、スキル名は英語のまま書きます。主な読み替えは次です。

| 用語 | この手順での意味 |
|---|---|
| smoke | 精度の結論ではなく、実装と保存処理が最低限動くかを見る小規模実験 |
| DRAFT | 仮説や比較条件をまだ修正できる計画下書き状態 |
| baseline | 新しい手法と同じ条件で比べる既存手法または過去実験 |
| baseline record | baselineの出典、読んでよい範囲、実装先を記録したもの |
| primary metric | 実験の成否判定に最優先で使う一つの評価値 |
| plan audit | 主指標だけが改善する抜け道を実装前に独立確認する監査 |
| implementation profile | 実装リスクに合わせて使うAgentの段階 |
| decision mode | 数値閾値で判定する`threshold`か、事前に定めた方向や形で判定する`trend`か |
| minimum meaningful effect | `threshold`で、採用判断を変えるほど意味がある最小改善量 |
| seed / split | seedは乱数の固定値、splitはデータをtrain・validation・testへ分ける規則 |
| claim | 複数の実験結果で支持、棄却、限定する研究上の主張 |
| queue | 次に実験化する仮説候補の優先一覧。ここに追加しても学習は始まらない |
| STATE | 現在の実験、作業段階、次に行う一作業をスクリプトが管理するファイル |
| scope | 研究上の対象範囲、または`SCOPE.json`に列挙したCodexのファイル操作範囲 |
| planning reads | 計画中に本文まで開いたPython。読む前にパスと理由を`SCOPE.json`へ記録する |
| implementation entry reads | 実装開始時に最初に開くPython。必要理由とともに少数へ絞り、全scopeの一括読込みを避ける |
| falsifier | 出たら現在の仮説を棄却または限定する観測 |
| stop condition | 予算超過や改善なしが続いた時など、研究全体または現在の研究枝を打ち切る条件 |
| leakage / hash | leakageはtest情報の学習側への混入、hashはデータやファイルの変更を検出する指紋値 |
| manifest | データの版や、実験の設定・生成物を記録する目録 |

## 0. 前提

最初の実験では、`experiments/DIGEST.md` に参照できる完了実験がありません。そのため、次のスキルはまだ使いません。

- `$review-experiment-result`
- `$update-research-direction`
- `$select-next-experiment`

これらは、少なくとも一つの実験が完了してから使います。

最初は、人間が研究の初期条件を与えます。

研究テーマがまだ決まっていない場合は、環境設定より先に`$discuss-research-theme`を使います。このSkillは2〜4件の候補を検証可能性、データ、計算量、新規性の不確実性、打切り条件で比較し、人間が明示的に選ぶまで研究ファイルを変更しません。

```text
$discuss-research-theme を使って、最初の研究テーマ候補を私と比較し、選択を支援してください。
```

## 1. 環境を確認する

必要なら、Codexに環境確認だけを依頼します。

```text
$prepare-environment を使って、このリポジトリで最初の研究設定を始められるか確認してください。
依存関係のインストールや学習は行わないでください。
```

ここで確認するのは、Python、検証スクリプト、Git状態、Codex hookの扱いです。

## 2. データ事実を記録する

最初の実験に使うデータについて、Codexに`data/MANIFEST.json`を準備させます。

```text
$prepare-data-manifest を使って、最初の実験で使うデータ事実を data/MANIFEST.json に整理してください。
data/raw/を再帰的に読まず、私が指定したメタデータまたは少数サンプルだけを使ってください。
```

人間が伝える主な情報は次です。

- データの場所
- 入手元（source）と利用条件（license）
- 分類、復元などの課題種別（task）
- 入力と正解データの次元（input shape、target shape）
- 学習用、選択用、最終評価用への分け方（train/validation/test split）
- test情報や同一サンプルが学習側へ混ざっていないか（leakage check）
- データ変更を検出する指紋値（hash）または固定版の識別方法

未定項目は「未定」と答えて構いません。ただし、split、metric、taskなど、計画を固定できない項目は後で解決する必要があります。

## 3. baseline資料を登録する

最初の比較対象として論文、GitHub、Web記事などを使う場合だけ登録します。

```text
$register-source-baseline を使って、ユーザー提供のbaseline資料を登録してください。
読んでよい範囲は、私が指定した節、ページ、図表、URL、またはリポジトリ内ファイルだけです。
```

ここでは、資料全体を読ませません。登録するのは、baselineの出典、読んでよい範囲、実装予定先、metric、データ仮定です。

baselineがない場合は、最初の実験で「最小baselineを確立する」か、「baselineなしのsmoke実装確認」として始めます。その場合も、baselineを発明しません。

## 4. 初期研究目的を定義する

前回実験がないため、研究方針は結果から更新できません。人間が最初の研究目的と判断基準を与えます。

```text
$define-research-intent を使って、研究目的、最初のclaim、QUEUE、STATEを初期化してください。
前回実験はないため、実験結果からの方針更新は行わないでください。
```

人間が伝える主な情報は次です。

- 研究質問
- 何を採用、棄却、または限定するための研究か
- 対象データ、課題種別、比較するモデルの系統、運用条件
- 主判定に使う一つの評価指標と、値が大きい方・小さい方のどちらが良いか
- 判定方式。`threshold`なら最小有用効果、`trend`なら期待する方向・最低比較点・矛盾条件
- baselineの有無
- seed、split、特定属性のデータ群などを変えても結論が保たれるかの条件
- 使用できるGPU時間、epoch、実験数などの計算上限
- falsifier（どの結果なら最初の仮説を棄却または限定するか）
- stop condition（何回、どの予算、どの結果で研究枝または研究全体を止めるか）
- 最初のsmoke目的

ここで`research/QUEUE.json`に最初の仮説候補が入ります。これは候補登録であり、実験作成や学習開始ではありません。

## 5. 最初の提案手法を記録する

最初の実験で検証したい新規手法の現在形を、`research/PROPOSED_METHOD.md`に記録します。

人間がCodexに依頼する例です。

```text
research/PROPOSED_METHOD.md に、最初に検証する提案手法、コア仮説、まだ未支持であることを記録してください。
baselineは更新しないでください。
```

baselineは比較基準です。最初から提案手法をbaselineとして扱いません。

## 6. 禁止する仮説があれば設定する

計画前に、避けたい仮説方向がある場合だけ設定します。

```text
$configure-hypothesis-policy を使って、禁止したい仮説の種類、理由、許可する代替案、見直し条件を設定してください。
```

例:

- 既存論文の単純な再現だけを目的にする仮説は禁止。
- seed探索で良い結果を探す仮説は禁止。
- データsplit変更をモデル改善として扱う仮説は禁止。
- コア仮説が未支持の段階でアブレーションだけを行う仮説は禁止。

## 7. 最初の実験を作る

初期設定が`ready`になり、active experimentがないことを確認してから、最初の実験を一件だけ作ります。

baselineを使う場合:

```bash
python scripts/new_experiment.py --id EXP-001 --stage smoke --baseline-id BASE-001
```

baselineなしの場合:

```bash
python scripts/new_experiment.py --id EXP-001 --stage smoke
```

作成される主なファイルは次です。

```text
experiments/active/EXP-001/EXPERIMENT.md
experiments/active/EXP-001/SCOPE.json
experiments/active/EXP-001/MANIFEST.json
configs/experiments/EXP-001.json
```

この時点の作業段階（phase）は`DRAFT`です。まだ計画は固定されていないため、人間レビューに応じて修正できます。

DRAFT作成時はPython本文を読みません。次の計画でも、まず`TREE.txt`または`rg --files src tests`のパス一覧で対象を絞ります。本文が不可欠な場合だけ、`SCOPE.json`の`planning_reads`へ理由付きで先に記録した最大3件の必要箇所を確認します。lock前には、実装開始時に最初に開く既存Pythonも`implementation_entry_reads`へ理由付きで最大3件だけ記録します。

## 8. 最初の実験計画を作る

Codexに、最初の実験計画だけを作らせます。

計画フェーズに限り、容易に想像できる単語で簡易な先行研究検索をして構いません。確認するのはタイトル、abstract、検索スニペット程度で、類似度の高い2、3件までにします。全文読解、ダウンロード、リポジトリ全体の調査は行いません。

```text
$plan-experiment を使ってEXP-001を計画し、lock-plan後に停止してください。
前回実験はないため、experiments/DIGEST.mdに完了結果がない前提で計画してください。
baseline資料がある場合は、登録済みrecordと承認済み読取範囲だけを使ってください。
```

計画では次を固定します。

- Research objective：研究全体のどの判断に役立つ実験か
- Study role：動作確認の`feasibility`、主効果の`core`、仕組みの`mechanism`、条件変化への強さの`robustness`
- Claim：この実験が関係する研究上の主張
- Rationale：その仮説を試す理由
- Alternative explanation：提案機構がなくても同じ結果を説明できる最も有力な別の説明
- Minimum discriminating evidence：仮説と別の説明を見分けるのに十分な観測。単に一番安いテストを選ぶ意味ではありません
- Falsifier：仮説を棄却または限定する観測
- Primary metric：主判定に使う評価値
- Diagnostic guardrail：`none`、または指標ハック検出専用で昇格判定には使わない一つの補助値
- Baseline：比較対象
- Decision mode：数値閾値の`threshold`または傾向の`trend`
- Minimum meaningful effect：`threshold`の最小改善量。`trend`では`not_applicable`
- Expected trend：`trend`で結果より前に決める方向や形
- Trend evidence rule：傾向判定に最低限必要な比較点と、逆向き・混在・観測不足の扱い
- Novelty check：既存研究の単純な繰返しでないかの確認
- Hypothesis policy check：禁止した仮説方向に違反しないかの確認
- Promotion rule：smokeからpilotなど、次の規模へ進む条件
- Evidence coverage：今回調べる比較・条件と、後続実験で調べる範囲・着手条件
- Scale justification：データ量・観測数・学習量・予算が今回の役割に十分で、過剰でもない理由
- Implementation：比較する一まとまりの手法。不可欠な複数の構成要素は一緒に扱えます
- Baseline behavior：変更箇所で現在行われている処理
- Candidate behavior：この実験で置き換える処理
- Intervention point：変更するファイル内の関数・クラス・設定位置
- Unchanged invariants：データ、指標など変えてはいけない条件
- Implementation profile：配線のみの`mechanical`、通常実装の`balanced`、科学的妥当性へ触れる`frontier`
- Profile rationale：その段階で研究品質を保てる理由
- Data control：固定するデータ版、split、前処理
- Training：学習予算と停止方法
- Evaluation：test方法と結論の判定規則
- `SCOPE.json.change_targets`：各変更ファイルの作成・変更、仮説本体・接続・テストの役割、変更予定の関数またはクラス

`Hypothesis`と`Method`は合計700語以内です。評価後に書く`Conclusion`と`Issues and Next Direction`は合計400語以内で、`EXPERIMENT.md`全体に対する別の500語制限はありません。生成される`research/CONTEXT.md`は9,000文字以内です。

最初の実験でも、seed探索や細かい条件探索は行いません。原則として、最初に決めた一つのseedでsmokeを通します。

ただし、研究計画全体をこの小さな実行に合わせて縮めません。`GOAL.md`の`Evidence Strategy`で、必要な比較・条件・検証順序を整理します。`smoke`は動作確認の`feasibility`だけで、効果の証明ではありません。本検証は十分な`pilot`または`full`で行います。同じコア仮説の比較・反復はconfigの`comparison`にまとめ、新しい仮説だけ別IDにします。

比較形式は`experiments/templates/COMPARISON.json`を元に、手法・条件・seedの全組合せを事前登録します。一つの計画として監査・承認し、通常の`$run-experiment`で順次実行します。全結果をまとめて評価し、失敗した実行だけを隠したり、良い条件だけ選んだりしません。設定と制限は[マニュアル11.2.1](MANUAL.ja.md#1121-比較一式を一実験として実行する)を参照してください。

研究初期で妥当な数値閾値がない場合は`trend`を選べます。ただし、結果を見てから「傾向がある」と判断せず、増加・減少・U字・頭打ちなどの期待形、比較条件の順序、最低比較点、反対または混在時の扱いを先に固定します。

## 9. 計画監査と人間レビュー

計画がlockされたら、実装前に独立した計画監査を一回行います。

```text
$audit-experiment-plan を使ってEXP-001の主評価指標をハックできる計画になっていないか確認し、監査取込み後に停止してください。
```

監査は主指標と研究目的のずれ、評価データの使い回し、比較条件の不一致、実装プロファイル不足に加え、目的に対して実験が小さすぎないか・不要に大きくないかを確認します。規模の確認は`Research scale adequacy`に記録し、追加エージェントは使いません。主指標は一つに固定し、抜け道を検出する補助値が必要でも最大一つ、採用判定には使いません。

監査が`pass`または`warn`なら、人間が計画を確認します。`fail`は承認できません。

```text
$review-experiment-plan を使ってEXP-001のlocked planを日本語で説明し、人間レビュー用の確認点を出してください。
```

問題なければ承認します。

```text
$approve-or-revise-plan を使ってEXP-001の計画を承認してください。
```

修正が必要なら`DRAFT`へ戻します。

```text
$approve-or-revise-plan を使ってEXP-001の計画をDRAFTへ戻してください。
```

その後、次で修正します。

```text
$revise-experiment-plan を使って、人間レビューの指摘に基づきEXP-001の計画を修正してください。
```

承認されるまで実装へ進みません。

## 10. ここから通常ループへ入る

計画が承認されたら、通常の研究ループに入ります。

モデル、loss、データ処理、評価コードの実装方針に未定項目がある場合は、実装前に次で相談します。

```text
$discuss-implementation-design を使ってEXP-001の実装方針を人間と相談してください。コード編集や学習は行わないでください。
```

科学条件や対象ファイルを変える必要がある場合は、計画を`DRAFT`へ戻してから修正します。

```text
$implement-experiment を使ってEXP-001のlocked planだけを実装してください。
```

Codexは計画で固定したプロファイルの実装Agentを一つだけ使います。`implementation_entry_reads`だけを最初に開き、追加のPythonは現在のコードやtargeted testから必要性が判明したscope内ファイルを一件ずつ確認します。プロファイル不足なら自動切替や再試行をせず、計画修正で止まります。

最初のsmokeまたはpilotでは、学習率とバッチサイズを決定的なスクリプトで調整します。最大ぎりぎりの値ではなく、少し余裕を持った値を`research/TRAINING_CONTROLS.json`に固定します。以後の比較実験では、この固定条件を使い、実験ごとに都合よく調整しません。

実装は、変更不要なら何もしない、既存コードを再利用する、標準機能または導入済み依存を使う、最後に必要最小限だけ書く、の順で判断します。科学的妥当性と安全性の検査は省略しません。

validationデータがある場合、checkpoint保存と早期終了はvalidation loss基準にします。accuracyなどのprimary metricは最終評価の判断に使い、過学習前に止める基準とは分けます。

以降は、`RESEARCH_LOOP.ja.md`の流れに従います。

```text
実装
  -> pilot/fullなら $audit-experiment-implementation
  -> $run-experiment
  -> pilot/fullなら $audit-experiment-integrity
  -> $evaluate-experiment
  -> $review-experiment-result
  -> $maintain-research-memory
  -> $update-research-direction
  -> $select-next-experiment
```

各矢印は別ターンです。`$evaluate-experiment`は支持できる範囲と不足証拠を明記して実験を確定し、`$maintain-research-memory`はその内容を`research/EVIDENCE.jsonl`と研究記憶へ移します。

## 最初の実験でしてはいけないこと

- 前回実験がある前提で方針を更新する。
- 完了実験がないのに`$select-next-experiment`を使う。
- baselineを提案手法として更新する。
- 既存研究の単純ななぞりを新規仮説として扱う。
- コア仮説の前にアブレーションを始める。
- seed探索や細かな条件探索を行う。
- 計画レビュー前に実装へ進む。
- 実装、学習、評価を初期設定と同じターンで行う。
