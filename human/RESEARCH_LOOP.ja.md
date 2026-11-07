# Codexドリブン研究ループ

この文書は、研究ループの回し方だけを説明します。データ準備、環境構築、モデル実装の詳細は扱いません。

## 基本方針

Codexが計画、実装、実行、評価などの作業段階（フェーズ）を一つずつ進めます。人間は、方針を変える時、計画を承認する時、結果を解釈する時だけ介入します。

常に次を守ります。

- 一度に扱うactive experimentは一つだけ。
- 一つの実験では、一つのコア仮説だけを検証する。
- 採用判定に使うprimary metricは一つだけにし、補助値を後から昇格させない。
- 計画、実装、実行、評価、方針更新を混ぜない。
- baselineは比較基準として維持し、有望な結果は`research/PROPOSED_METHOD.md`の提案手法として更新する。
- 結果を見た後で、metric、baseline、seed、split、判定方式や判定条件を変更しない。

この文書では、ファイル名、コマンド名、状態名、スキル名は英語のまま書きます。主な読み替えは次です。

| 用語 | この手順での意味 |
|---|---|
| Skill | `$plan-experiment`のような、Codexに一つの作業を実行させる手順 |
| active experiment | 現在処理中の一件。完了前に次の実験を開始しない |
| research branch | 同じ仕組みや手法案を追う一連の方向。複数実験を含み、停止条件を満たせば打ち切る |
| baseline | 新しい手法と同じ条件で比べる既存手法または過去実験 |
| primary metric | 成否判定に最優先で使う一つの評価値 |
| plan audit | 主評価指標だけを上げて研究目的を改善しない抜け道がないか、実装前に独立確認する監査 |
| diagnostic guardrail | 指標ハックを検出するための補助値。最大一つで、採用判定には使わない |
| implementation profile | 科学的リスクに応じて実装Agentを`mechanical`・`balanced`・`frontier`から選ぶ記録 |
| decision mode | 意味のある数値差で判定する`threshold`か、事前に定めた方向や形で判定する`trend`か |
| seed / split | seedは乱数の固定値、splitはtrain・validation・testの分け方 |
| scope | 研究結果が当てはまる範囲、またはCodexが扱えるファイル範囲 |
| planning reads | 計画中に本文まで確認したPython。読む前にパスと理由をscopeへ記録する |
| queue | 次に実験化する仮説候補の優先一覧。実行待ちジョブではない |
| hypothesis / claim | hypothesisは今回試す予測、claimは複数の証拠で更新する研究上の主張 |
| alternative explanation | 提案した仕組みが正しくなくても同じ結果を説明できる、最も有力な別の説明 |
| minimum discriminating evidence | 仮説とalternative explanationを見分けるために最低限必要な観測 |
| DRAFT / locked plan | DRAFTは修正可能な下書き、locked planは結果を見る前に比較条件を固定した計画 |
| falsifier | 出たら現在の仮説を棄却または限定する観測 |
| stop condition | 現在の研究枝または研究全体を打ち切る、回数・予算・結果の条件 |
| stage / phase | stageは実験規模、phaseは計画・実装・評価など現在の作業段階 |
| smoke / pilot / full | smokeは動作確認、pilotは有望性確認、fullは承認済み予算による最終評価 |
| aggregate metrics | 処理単位ごとの履歴ではなく、実験全体を少数の値へ要約した評価結果 |
| review bundle / hash | bundleは監査用に閉じた資料、hashは監査後の内容変更を検出する指紋値 |
| implementation audit | pilot/fullの実行前に、実装が計画どおりでデータ漏洩や指標実装の欠陥がないか確認する監査 |
| integrity audit | 結果出所、計画遵守、指標、データ漏洩、結論範囲を評価前に確認する監査 |
| evidence | 実験結果をclaimへ結ぶ、支持範囲と不足証拠を含む確定済み根拠 |

## ループ全体

```text
研究記憶と証拠を更新
  -> 研究方針を更新
  -> 次の研究枝を選択
  -> 論文知識グラフを照会
  -> 新規性を確認
  -> 次の実験をDRAFTで作成
  -> 実験計画
  -> 計画監査
  -> 人間レビュー
  -> 承認またはDRAFTへ戻す
  -> 実装
  -> pilot/fullなら実装監査
  -> 決定的スクリプトで実行
  -> pilot/fullなら完全性監査
  -> 支持可能な主張を評価して確定
  -> 結果レビュー
  -> 研究記憶と証拠を更新
```

Codexに自律実行させる場合は、`automation/ONE_CYCLE_PROMPT.md`に従い、ルーターが返す同じ`operation`内だけ最大三フェーズまで進めます。別の作業または人間判断へ移る前に停止します。

## 1. ループの開始地点を確認する

最初の実験では`FIRST_EXPERIMENT.ja.md`に従い、研究目的と最初の仮説候補一覧（queue）を人間が定義します。完了実験がある場合は、先にこの文書の「11. 記憶と研究方針を更新して次へ進む」を完了します。

現在地は`research/CONTEXT.md`と`research/STATE.json`で確認します。`next_action.mode`は「次の一ターンで使うSkill」を表す値です。人間が直接書き換えず、対応するSkillと終端スクリプトに遷移を任せます。

## 2. 次の研究枝を選択する

`research/memory/`と`research/ideas/IDEA_BANK.jsonl`から、情報量と意思決定への影響が大きく、コストと実装リスクが小さい候補を一つ選びます。

```text
$select-research-branch を使って、次に検証する研究枝を一つ選んでください。まだ実験は作成しないでください。
```

必要なら、候補の背景だけを限定的に調べます。

既存の論文知識グラフがある場合は、広い再検索の前に局所的な計画資料を作ります。

```text
$query-paper-knowledge を使って、候補仮説に関係する論文、手法、データセット、未解決点を計画用query packにしてください。
```

query packは、知識グラフ全体ではなく、今回の計画に関係する項目、関係、元資料だけを抜き出した短い資料です。

グラフに必要な情報がなく、人間が調査範囲を明示的に許可した場合だけ、`$research-paper-graph`で調査とグラフ更新を別ターンに行います。人間向けの詳細は`PAPER_KNOWLEDGE_MANUAL.ja.md`を参照してください。

```text
$scan-research-landscape を使って、承認済み資料の範囲だけで研究ギャップを整理してください。
```

選んだ研究枝は、実験にする前に新規性を確認します。

```text
$audit-novelty を使って、選んだコア仮説が既存研究の単純な再現でないか確認してください。
```

この確認では、名前や表現が違うだけでは新規とは扱いません。機構、条件、データ状況、目的関数、実装変更のどこが既存研究と違うのかを確認します。新規性リスクが高い場合、または人間判断が必要な場合は、実装へ進まず仮説を修正します。

実験を作る段階では、従来どおり次を使います。

```text
$select-next-experiment を使って、次の実験を一件だけDRAFTとして作成してください。
```

## 3. 必要なら仮説禁止方針を更新する

特定の仮説、比較、データ条件、モデル方向を禁止したい場合だけ、人間が方針を設定します。

```text
$configure-hypothesis-policy を使って、禁止したい仮説の種類、理由、許可する代替案、見直し条件を設定してください。
```

設定は`research/planning/HYPOTHESIS_POLICY.md`に残ります。以後の計画では、この方針に違反する仮説を採用しません。

## 4. 実験計画を作る

Codexが、仮説、最も有力な別の説明、両者を見分ける最低限の観測、反証条件、一つの主評価指標、判定方式と条件、既存研究との差分、禁止方針への適合、seed、対象範囲を固定します。`threshold`では採用判断を変える最小改善量、`trend`では期待する方向や形、最低比較点、弱い・逆向き・混在・観測不足の扱いを結果より前に決めます。

この計画フェーズに限り、容易に想像できる単語で簡易な先行研究検索をして構いません。確認するのはタイトル、abstract、検索スニペット程度で、類似度の高い2、3件までにします。全文読解、ダウンロード、リポジトリ全体の調査は行いません。

計画には、新規性の軸、想定する機構、alternative explanation、minimum discriminating evidence、既存研究との差分、失敗したと判断する観測を含めます。アブレーション、seed探索、細かな条件探索は、コア仮説の有望性が確認されるまで行いません。

```text
$plan-experiment を使ってEXP-001を計画し、lock-plan後に停止してください。
```

計画がlockされると、`Hypothesis`、`Method`、config、`SCOPE.json`がハッシュ化されます。結果を見た後でこれらを変えることはできません。

`Hypothesis`と`Method`は合計700語以内です。評価後の`Conclusion`と`Issues and Next Direction`は合計400語以内とし、`EXPERIMENT.md`全体への別の500語制限は設けません。生成コンテキストの上限は9,000文字を維持します。

DRAFT作成ではPython本文を読みません。計画では`TREE.txt`または`rg --files src tests`のパス一覧からscope候補を選び、本文確認が不可欠な場合だけ、先に`SCOPE.json.planning_reads`へ理由を記録した最大3件の必要箇所を読みます。さらにlock前に、実装開始時に最初に開く既存Pythonを`implementation_entry_reads`へ理由付きで最大3件だけ記録します。上限を超える場合は探索を止め、人間へ未決事項を返します。

計画には実装プロファイルも固定します。設定・登録・テストだけで科学的動作が変わらない場合は`mechanical`、安定した契約内の通常実装は`balanced`、loss、split、sampling、metric、checkpoint、runner、再現性、外部baseline移植、または解消していない曖昧さへ触れる場合は`frontier`です。

さらに、現在の処理であるbaseline behavior、提案後のcandidate behavior、変更する正確なintervention point、変えてはいけないunchanged invariantsを記録します。`SCOPE.json.change_targets`には各変更ファイルの作成・変更、仮説本体・接続・テストの役割、予定する関数またはクラスを固定します。

### 4.1 計画監査

lock後、独立Agent一つが9,000文字以内の閉じた資料だけを読み、主指標を改善しても研究上のclaimが改善しない経路を確認します。

```text
$audit-experiment-plan を使ってEXP-001の計画を指標ハックの観点から監査し、取込み後に停止してください。
```

監査出力は250語以内です。`pass`は人間レビューへ進め、`warn`は注意点を人間が明示的に受け入れた場合だけ承認でき、`fail`は計画修正が必要です。補助値が必要でも、具体的な抜け道を検出する一つだけにし、promotionには使いません。

## 5. 人間が計画をレビューする

計画監査の受理後、人間が計画の意味とリスクを確認します。

```text
$review-experiment-plan を使ってEXP-001のlocked planを日本語で説明し、人間レビュー用の確認点を出してください。
```

確認する点は次です。

- コア仮説が明確か。
- 既存研究の単純ななぞりではないか。
- 禁止された仮説に該当しないか。
- 一つの制御変更だけになっているか。
- seed探索や細かすぎる条件探索になっていないか。
- metric、baseline、split、判定方式と判定条件が固定されているか。
- plan auditの抜け道、補助値、実装プロファイルが妥当か。
- 実装開始時に読むPythonが少数で、各ファイルの必要理由が明確か。
- 仮説とは別の説明が一つ明示されているか。
- どの最小観測で仮説と別の説明を見分けるかが固定されているか。

## 6. 承認またはDRAFTへ戻す

問題がなければ承認します。

```text
$approve-or-revise-plan を使ってEXP-001の計画を承認してください。
```

修正が必要なら、同じスキルで計画を`DRAFT`へ戻します。その後、次で修正します。

```text
$revise-experiment-plan を使って、人間レビューの指摘に基づきEXP-001の計画を修正してください。
```

承認されるまで実装へ進みません。

## 7. 実装する

モデル構造、loss、データ処理、評価コードの実装方針が未定なら、実装前に次で相談します。

```text
$discuss-implementation-design を使ってEXP-001の実装方針を人間と相談してください。コード編集や学習は行わないでください。
```

この相談で科学条件や`SCOPE.json`を変える必要が出た場合は、計画を`DRAFT`へ戻して修正します。baselineは更新せず、提案手法側の実装方針だけを扱います。

承認済みのlocked planだけを実装します。

```text
$implement-experiment を使ってEXP-001のlocked planだけを実装してください。
```

Codexは固定した実装プロファイルに対応するAgentを一つだけ使い、最初に`implementation_entry_reads`だけを開きます。その後は、現在のコード、targeted test、またはエラーから必要性が示された場合だけ、scope内の別のPythonを一件ずつ確認します。scope全体やtests全体を先に読みません。

実装は、変更不要なら何もしない、既存コードを再利用する、標準機能または導入済み依存を使う、最後に必要最小限だけ書く、の順で判断します。ただし、データ分割、有限値、再現性、計画と成果物のhashなど、科学的妥当性と安全性の検査は削りません。

プロファイル不足が判明した場合は、自動再試行や上位Agentへの暗黙切替をせず、計画修正で停止します。一フェーズのサブAgentは一つ、モデルの明示的な再分類による昇格は最大一回です。

学習率とバッチサイズはCodexが推論で選びません。`mark_implemented`時に`scripts/tune_training_controls.py`がsmokeまたはpilotで決定的に調整し、`research/TRAINING_CONTROLS.json`へstageごとの共通条件として固定します。以後の同じstageの実験と最終比較では、その固定値を再利用します。

validationデータがある場合、学習中はvalidation lossを監視します。学習済み重みの保存点（checkpoint）はvalidation lossが最小のepochを保存し、事前に決めた待機回数（patience）だけ改善しなければ学習処理を停止します。これは研究枝の停止条件ではありません。最終評価のprimary metricは別に維持します。

Codexは`SCOPE.json`に書かれたファイルとシンボルだけを変更します。lock時に変更前、`mark_implemented`時に変更後を`IMPLEMENTATION_DELTA.json`へ機械記録し、対象外の変更があれば停止します。仮説、metric、baseline、seed、成功条件は変更しません。

## 8. 実験を実行する

入出力、loss、勾配、保存処理の最小動作確認（sanity check）、制限内の学習、test、実験全体を要約した評価値の保存は決定的スクリプトが担当します。

pilotまたはfullでは、学習を始める前に独立した実装監査を行います。

```text
$audit-experiment-implementation を使ってEXP-002の閉じたreview bundleだけを監査し、監査取込み後に停止してください。
```

この監査は、locked planへの忠実性、データ分割と漏洩、lossと最適化、metric実装、再現性、変更範囲を確認します。`pass`または`warn`なら実行へ進めます。`fail`なら状態は`FAILED`となり、`$debug-failure`で指摘箇所だけを修正します。監査後に計画、config、scope、実装を変えると監査は失効します。

smokeはこの実装監査を省略し、直接、決定的実行へ進みます。

```text
$run-experiment を使ってEXP-001を一回だけ実行し、実行後に停止してください。
```

手動で同じ処理を起動する場合は次を使います。

```bash
python scripts/run_experiment.py --id EXP-001
```

プログラムは途中ログを出さず、最後に`OK ...`または`ERROR ...`を一行だけ返します。phaseが`TRAINED`で中断していた場合も同じskillを使いますが、既存の集約結果からreview経路だけを復旧し、再学習しません。

実行中にCodexは実装Pythonやtestを読み直しません。実装監査は実行前の計画と変更snapshot、完全性監査は実行後の記録と集約指標を使います。結果評価は受理済み監査と集約指標を使い、snapshotを再読しません。

失敗した場合は次を使います。

```text
$debug-failure を使って、失敗原因を一つだけ診断し、最小修正してください。
```

## 9. 監査し、評価して確定する

smokeでは、Codexが実験全体を要約した評価値（aggregate metrics）と固定済み計画を対応付け、結論を書きます。

```text
$evaluate-experiment を使ってEXP-001のaggregate metricsだけを評価し、Supported scopeとUnsupported or missing evidenceを含む結論を書き、finalize後に停止してください。
```

pilotまたはfullでは、評価前に独立した完全性監査を一ターンで行います。

```text
$audit-experiment-integrity を使ってEXP-002の閉じたreview bundleだけを監査し、監査取込み後に停止してください。
```

監査では結果出所、計画遵守、metric妥当性、データリークとsplitのリスク、scopeを確認します。`pass`または`warn`なら次のターンで`$evaluate-experiment`へ進み、`fail`なら状態は`FAILED`となるため`$debug-failure`で最小修正します。監査と評価を同じターンで連続実行しません。

結果の解釈が機械的に難しい場合は、人間が確認するファイルを作ります。

```text
$request-human-result-interpretation を使って、EXP-001の結果確認用ファイルと人間解釈ファイルを作成してください。
```

人間は`human/results/EXP-001/RESULTS.md`を読み、`human/results/EXP-001/INTERPRETATION.md`へ解釈を書きます。その後、同じスキルで解釈を取り込みます。傾向方式でも、見えてから新しい形を作らず、固定済みの期待形と最低比較点に照らして、期待どおり、逆向き、混在、情報不足を判断します。

pilotまたはfullの監査と評価では、read-only evaluatorが`review/bundles/<ID>/`だけを読みます。受理時に監査対象のhashが固定されるため、後からmetrics、config、scope、実装snapshotを変更すると評価または確定が拒否されます。

## 10. 結果を人間がレビューする

確定後、人間向けに結果を確認します。

```text
$review-experiment-result を使ってEXP-001の結果を日本語で説明してください。
```

確認する点は次です。

- 結果は固定したminimum effect、または事前登録した傾向規則にどう対応したか。
- コア仮説を支持、棄却、限定、保留のどれにするか。
- caveatは何か。
- 次にpilot、full、別仮説、停止のどれへ進むか。

## 11. 記憶と研究方針を更新して次へ進む

結果レビュー後、まず再利用できる証拠と研究記憶を固定します。

```text
$maintain-research-memory を使って、最新結果からEVIDENCE、INSIGHTS、DEAD_ENDS、OPEN_QUESTIONS、IDEA_BANK、LEDGERを更新してください。
```

このフェーズは`research/EVIDENCE.jsonl`へ、decision、固定した判定規則との対応、primary result、支持範囲、不足証拠、完全性監査の判定、完了記録とmetricsへの参照を残します。記憶と台帳が検証された後に、研究方針を更新します。

```text
$update-research-direction を使って、前の実験結果を受けて研究方針を更新してください。
baselineは更新せず、提案手法を更新してください。
```

更新先は主に次です。

- `research/PROPOSED_METHOD.md`
- `research/CLAIMS.jsonl`
- `research/QUEUE.json`
- `research/DECISIONS.md`

結果後の修正は、固定済みの集約結果だけを使い、まず主張を狭めるか言い換えます。それでも重要な曖昧さが残る場合だけ、alternative explanationを見分ける実験を一件追加し、それ以外は停止または保留にします。結果を見てから別metricや都合のよいパターンを探して主張を救済しません。

次の実験候補ができたら、別ターンで`$select-next-experiment`へ戻ります。順序は`maintain_memory -> update_direction -> select_experiment`であり、確定直後に次実験を作りません。

## 人間が介入する場面

人間が介入するのは主に次の時です。

- 研究方針を変える。
- 禁止する仮説を設定する。
- 計画を承認または修正要求する。
- 結果の意味を確認する。
- 完全性監査が`warn`または`fail`となった時に、限定付き採用、修正、停止を判断する。
- 研究を止める、狭める、または次の方向を選ぶ。

それ以外の通常フェーズは、Codexが`next_action.mode`に従って一つずつ進めます。

## してはいけないこと

- 実装監査が`warn`または`fail`となり、実行可否や修正範囲に人間判断が必要な時。
- 計画と実装を同じターンで進める。
- 結果を見た後で計画条件を変える。
- baselineを提案手法として更新する。
- seed探索や細かな条件探索を先に行う。
- active experimentを複数作る。
- scope外のファイルを暗黙に読む。
- raw data、checkpoint、completed experimentsを再帰的に読む。
