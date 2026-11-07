# 最短手順

この手順は、テンプレートを展開した直後に「Codexに何を読ませ、何を読ませないか」を保ったまま、最初のsmoke実験を作るためのものです。

ここでは例として、ユーザーが用意した論文またはGitHub記事をもとに、画像モデルのベースラインを登録してから実験を始めます。画像タスクは固定しません。分類、復元、超解像、セグメンテーションなどは、ユーザーが提供した資料に従って決めます。

この手順で使う用語は次の意味です。

| 用語 | 意味 |
|---|---|
| Skill | `$initial-setup`のような、Codexに一つの作業を依頼する手順。一ターンでは一つだけ使う |
| smoke | 精度を確定する実験ではなく、データ読込み、学習、保存まで動くかを見る最小の動作確認 |
| baseline | 新しい手法と同じ条件で比べる既存手法または過去結果 |
| locked plan | 結果を見る前に固定した仮説、比較条件、評価指標、対象ファイル |
| plan audit | 主指標だけを上げて研究目的を改善しない抜け道がないか、実装前に独立確認する工程 |
| diagnostic guardrail | 指標ハックを見つける補助値。最大一つで、採用判定には使わない |
| implementation profile | 科学的リスクに応じ、実装Agentを三段階から選ぶ記録 |
| `SCOPE.json` | Codexがその実験で読んだり変更したりしてよいファイルの一覧 |
| planning reads | 計画中に例外的に本文を確認したPython。読む前にパスと理由を記録する |
| implementation entry reads | 実装開始時に最初に開くPython。全対象を一括で読まないため、必要理由とともに少数へ絞る |
| train / validation / test | モデル更新用、学習中の選択用、最後の評価用に分けたデータ |
| forward / loss | forwardは入力から予測を計算する処理、lossは予測の誤差 |
| checkpoint | 途中または最良時点で保存した学習済みモデルの重み |
| aggregate metrics | 一回ごとの履歴ではなく、実験全体を要約した評価値 |
| manifest | 実行条件、使用コード、生成ファイルを記録した目録 |
| queue | 次に実験化する仮説候補の優先一覧。ここに入れても学習は始まらない |
| alternative explanation | 提案機構がなくても同じ結果を説明できる、最も有力な別の説明 |
| minimum discriminating evidence | 仮説と別の説明を見分けるために最低限必要な観測 |
| implementation audit | pilot/fullの実行前に、計画どおりの実装かを独立確認する工程 |

---

## 1. インストールと検査

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/validate.py
python -m pytest -q
```

Windows PowerShellでは、仮想環境の有効化だけ次を使います。

```powershell
.venv\Scripts\Activate.ps1
```

`validate.py` が成功すると、次のような一行が出ます。

```text
OK validate files=... warnings=0
```

---

## 2. まずCodexに初期設定を頼む

研究テーマ自体が未確定なら、初期設定の前ターンに次を使います。このSkillは候補を比較して人間の合意を作るだけで、ファイルは更新しません。

```text
$discuss-research-theme を使って、関心、利用可能なデータ、計算制約から研究テーマ候補を比較し、私と議論してください。私が選ぶまで確定しないでください。
```

テーマを選んだ後、別ターンで初期設定へ進みます。

リポジトリのルートでCodexを開き、次のように依頼します。

```text
$initial-setup を使って、この画像深層学習研究を初期設定してください。
研究目的、データ、ベースライン資料、読んでよい範囲、最初のsmoke実験の目的を対話で確認してください。
論文やGitHub全体を勝手に読まず、承認した範囲だけ使ってください。
```

Codexから質問されたら、分かる範囲で答えます。未定なら「未定」と答えて構いません。未定項目については、Codexが必要性、保留した場合の影響、保守的な選択肢を短く提示し、確定・仮定・保留を分けて進めます。

回答例：

```text
研究目的: ユーザー提供の論文Aに準拠した画像復元モデルを、固定データ分割で再現できるか確認したい。
データ: data/raw/my_images/ に配置済み。train/val/test のリストは data/MANIFEST.json に書く。
ベースライン資料: REF-001 の論文PDFと、著者GitHubの model.py。
読んでよい範囲: 論文のAbstract、Method 3.1、Table 1、GitHubの models/baseline.py のみ。
指標: PSNRは大きいほど良い唯一の主評価指標。SSIMは崩れを検出する補助値で、採用判定には使わない。
smoke目的: forward、loss、checkpoint保存まで確認する。
```

Codexは確認後、必要な設定ファイルとベースライン記録を作ります。最後に `validate.py` が成功していることを確認します。

---

## 3. 手動でベースラインを登録する場合

Codexを使わずに登録する場合は、次のようにします。

```bash
python scripts/register_baseline.py \
  --id BASE-001 \
  --title "User supplied image baseline" \
  --source-type paper \
  --reference-id REF-001 \
  --scope "Abstract" \
  --scope "Method 3.1" \
  --scope "Table 1" \
  --implementation-path src/dl_research/models/baseline_model.py \
  --metric psnr \
  --dataset-assumption "Use the fixed split described in data/MANIFEST.json"
```

登録される内容は `baselines/records/BASE-001.json` に保存されます。ここには、Codexが読んでよい資料範囲と、後で `src/` に統合する予定の実装ファイルだけを書きます。

重要な点：

- 論文PDF全体を登録するのではなく、「読んでよい節・図・表」を書きます。
- GitHub全体を登録するのではなく、「読んでよいファイル」を書きます。
- 外部コードを丸ごとコピーせず、実験で必要な最小実装だけを `src/` に統合します。

---

## 4. smoke実験を作る

ベースラインIDを指定して、最初の実験を作ります。

```bash
python scripts/new_experiment.py --id EXP-001 --stage smoke --baseline-id BASE-001
```

作成される主なファイルは次です。

```text
experiments/active/EXP-001/EXPERIMENT.md
experiments/active/EXP-001/SCOPE.json
configs/experiments/EXP-001.json
```

次はCodexに計画を頼みます。

特定の仮説立案を禁止したい場合は、計画前に方針を設定します。

```text
$configure-hypothesis-policy を使って、禁止したい仮説の種類と理由を research/planning/HYPOTHESIS_POLICY.md に設定してください。
```

```text
$plan-experiment を使って EXP-001 を計画し、lock-plan後に停止してください。
BASE-001の記録と、承認済みの資料範囲だけを使ってください。
実装や学習はまだ行わないでください。
```

計画がlockされたら、まず計画専用の独立監査を一回行います。

```text
$audit-experiment-plan を使って EXP-001 の主評価指標をハックできる計画になっていないか確認し、監査取込み後に停止してください。
```

監査は、研究目的と主指標の対応、主指標だけを上げる抜け道、validationによる選択とtest評価の分離、baseline比較、実装プロファイルを確認します。`pass`または`warn`なら人間向けレビューへ進み、`fail`なら計画を修正します。`warn`は人間が注意点を受け入れた場合だけ承認できます。

次に人間向けレビューを受けます。

```text
$review-experiment-plan を使って EXP-001 のlocked planを日本語で説明し、人間レビュー用の確認点を出してください。
実装や学習はまだ行わないでください。
```

レビュー後、承認または修正を記録します。

```text
$approve-or-revise-plan を使って、EXP-001 の計画レビュー結果を反映してください。
```

修正が必要な場合は、計画を`DRAFT`へ戻してから`$revise-experiment-plan`で直します。

DRAFT作成ではPython本文を読みません。計画時もパス一覧を先に使い、本文が不可欠な場合だけ`SCOPE.json`の`planning_reads`へ理由を記録して、既定で最大3件の必要箇所を確認します。lock前には、実装開始時に最初に開く既存Pythonも`implementation_entry_reads`へ理由付きで最大3件だけ記録します。計画には、配線だけの`mechanical`、通常実装の`balanced`、loss・split・metricなど科学的妥当性へ触れる`frontier`のいずれかも固定します。

同時に、現在の処理、提案後の処理、変更点、変えない条件を明記し、`change_targets`へ各変更ファイルの作成・変更、仮説本体・接続・テストの役割、予定する関数またはクラスを記録します。

計画本文である`Hypothesis`と`Method`は合計700語以内です。ここでalternative explanationとminimum discriminating evidenceも結果を見る前に固定します。後で記入する`Conclusion`と`Issues and Next Direction`は合計400語以内で、ファイル全体に対する別の500語制限はありません。`research/CONTEXT.md`は9,000文字以内のままです。

---

## 5. 実装する

人間が計画を承認したら、Codexに実装だけを頼みます。

```text
$implement-experiment を使って EXP-001 のlocked planだけを実装してください。
最初はSCOPE.jsonのimplementation_entry_readsだけを開き、追加のPythonは必要性が判明したscope内ファイルを一件ずつ確認してください。
変更箇所だけを確認するtargeted testを追加してください。
mark-implemented後に停止してください。
```

Codexが完了したら、状態は `IMPLEMENTED` になります。`IMPLEMENTATION_DELTA.json`には、計画時の変更前hashと、実装後hash・実際に変わったPythonシンボルが保存されます。宣言外変更はここで拒否されます。

コード変更は、固定した実装プロファイルのAgent一つだけが担当します。変更不要なら何もしない、既存コードを再利用する、標準機能または導入済み依存を使う、最後に必要最小限だけ書く、の順で判断します。プロファイル不足なら自動で高性能モデルへ切り替えず、計画修正で止まります。

この例のsmokeは直接実行へ進みます。pilot/fullでは、6章へ進む前に実装監査を受理します。

```text
$audit-experiment-implementation を使って EXP-002 の閉じたreview bundleだけを監査し、監査取込み後に停止してください。
```

---

## 6. 実験を一回だけ実行する

Codexには実行フェーズだけを依頼します。

```text
$run-experiment を使って EXP-001 を一回だけ実行し、実行後に停止してください。
```

同じ処理を手動で起動する場合は次を使います。

```bash
python scripts/run_experiment.py --id EXP-001
```

この段階ではCodexに実装Pythonやtestを読み直させません。失敗時は`error.json`から原因候補を絞り、必要なscope内ファイルだけを一件ずつ確認します。

この作業段階では、入出力やlossが最低限動くかのsanity check、制限内の学習、test、集約結果の保存までを行います。結果の解釈と確定は次の別段階です。中断後に現在段階（phase）が`TRAINED`で残っている場合も`$run-experiment`を使います。この場合は既存の集約結果から評価へ進む経路だけを復旧し、再学習しません。

成功例：

```text
OK run-experiment EXP-001 phase=READY_TO_FINALIZE test_accuracy=0.750000
```

画像復元など別タスクでは、表示される指標名は `psnr` など実験設定に従います。

結果は主に次へ保存されます。

```text
artifacts/results/EXP-001/
├── AGENTS.md
├── best.pt
├── sanity.json
├── metrics.json
└── manifest.json
```

---

## 7. 結論を書いて確定する

smoke実験では、集約済みの`metrics.json`と固定済みの計画を対応付けて結論を書きます。数値閾値を固定した場合はその比較を、研究初期の傾向判定を選んだ場合は事前登録した方向・最低比較点・矛盾条件との対応を使います。Codexに頼む場合は次のようにします。

```text
$evaluate-experiment を使って EXP-001 のaggregate metricsだけを評価し、
Supported scope と Unsupported or missing evidence を含むConclusion、
Issues and Next Directionを埋め、
finalize後に停止してください。
```

pilotまたはfullでは、評価の前ターンに次を実行します。

```text
$audit-experiment-integrity を使って EXP-002 の結果出所、計画遵守、metric妥当性、
データリーク、主張範囲を独立監査し、監査取込み後に停止してください。
```

監査が`pass`または`warn`なら、次のターンで`$evaluate-experiment`を使います。`fail`なら評価せず`$debug-failure`へ進みます。

手動で書く場合は、`EXPERIMENT.md` の次だけを埋めます。

- `Conclusion`
- `Issues and Next Direction`

この二節は合計400語以内にします。

Codexに評価を依頼した場合は、同じ評価フェーズ内で確定まで行われます。手動で記入した場合だけ、最後に次を実行します。

```bash
python scripts/finalize_experiment.py --id EXP-001
```

その後、構造を検査します。

```bash
python scripts/validate.py
```

完了した実験は `experiments/completed/EXP-001/` へ移動し、要点が `experiments/DIGEST.md` に追加されます。

結果を人間向けに確認したら、記憶、研究方針、次の実験を一ターンずつ順に更新します。

```text
$review-experiment-result を使って EXP-001 の結果を日本語で説明してください。
```

次のターン:

```text
$maintain-research-memory を使って EXP-001 の証拠、知見、未解決問題、台帳を更新してください。
```

その次のターン:

```text
$update-research-direction を使って、前の実験結果を受けて research/PROPOSED_METHOD.md と QUEUE を更新してください。
baselineは更新しないでください。
```

`$maintain-research-memory`は、主張の支持範囲と不足証拠を`research/EVIDENCE.jsonl`へ記録します。

結果後は、固定済み集約結果だけで、まず主張を狭めるか言い換えます。重要な曖昧さが残る場合だけalternative explanationを見分ける実験を一件置き、それ以外は停止または保留します。次の候補が決まったら、一件だけ作成します。

```text
$select-next-experiment を使って、次の実験を一件だけDRAFTとして作成してください。
```

---

## よくある失敗

- `next action is not select_experiment` が出る
  初回は初期設定を完了してください。結果確定後は記憶更新、方向更新の順に完了してから次の実験を作成します。エラーを消すためにSTATEを直接書き換えず、`scripts/next_autonomous_step.py` で現在の工程を確認してください。

- `unknown baseline ID` が出る  
  先に `scripts/register_baseline.py` で `BASE-001` を登録してください。

- Codexが「資料全体を読んでよいか」と聞く  
  全体ではなく、節・ページ・図・表・GitHubファイルを指定してください。

- 実装中にSCOPE外のファイルが必要になった  
  勝手に広げず、計画フェーズへ戻って `SCOPE.json` を見直します。

- smokeで結果が悪い  
  smokeは科学的結論ではなく、実装が最低限動くかの確認です。有限loss、checkpoint、metrics保存をまず確認します。
