# 論文知識グラフ 手順書

この手順書は、`paper_knowledge/` に作成した論文知識グラフを人間が利用するためのものです。目的は、関連研究・手法・データセット・評価指標・主張の関係をグラフとして整理し、研究計画時に全体像を把握しやすくすることです。

| 用語 | この手順での意味 |
|---|---|
| graph | 論文などの項目と、その関係をつないだ全体 |
| node | 論文、手法、dataset、metric、claimなど、一つの項目 |
| edge | `uses_method`や`supports`など、二つのnode間の関係 |
| source | nodeやedgeの根拠となる論文URL、リポジトリ、手元資料 |
| planning brief | 検索語に近いnodeと関係だけを抜き出した、実験計画前の短い資料 |
| CSL JSON / BibTeX | 文献管理ソフトから出力できる書誌情報のファイル形式 |

## できること

- Codex に関連研究の調査と知識グラフ作成を依頼する
- ローカルの論文メモ、CSL JSON、BibTeX からグラフを更新する
- グラフを人間向けビューワーで確認する
- 検索、ノード種別フィルタ、エッジ種別フィルタで関係を調べる
- 研究計画用の短いブリーフを生成する

## 主要ファイル

| ファイル | 用途 |
|---|---|
| `paper_knowledge/HUMAN_ENTRYPOINT.md` | 人間向けビューワーの明確な入口 |
| `.agents/skills/research-paper-graph/SKILL.md` | 許可された調査とグラフ更新を依頼するskill |
| `.agents/skills/query-paper-knowledge/SKILL.md` | 既存グラフから計画用query packを作るskill |
| `paper_knowledge/skills/systematize-paper-knowledge/SKILL.md` | 既存メモやメタデータを整理するための skill |
| `paper_knowledge/notes/` | 論文・手法・主張などのメモ置き場 |
| `paper_knowledge/graph/graph.json` | 知識グラフ本体 |
| `paper_knowledge/viewer/index.html` | 人間向けグラフビューワー |
| `paper_knowledge/viewer/graph-data.js` | ビューワーが読む表示用データ |
| `paper_knowledge/out/planning_brief.md` | 研究計画用ブリーフ |

## 1. Codex に調査とグラフ作成を依頼する

外部検索を使って関連研究を調査し、グラフを作る場合は、調査範囲と件数を明示的に許可してCodexへ次のように依頼します。

```text
$research-paper-graph を使って、<調査したいテーマ> について関連研究を調べ、
paper_knowledge の知識グラフを更新してください。
外部検索は許可します。読む範囲は abstract、README、公式メタデータに限定してください。
最大 5 件まででよいです。
```

例:

```text
$research-paper-graph を使って、画像分類における contrastive learning と robustness の関連研究を調べ、
paper_knowledge の知識グラフを更新してください。
外部検索は許可します。読む範囲は abstract と公式 README まで、最大 5 件にしてください。
```

Codex は原則として次を行います。

1. 調査範囲を確認する
2. 関連する論文・GitHub・Web記事を少数だけ確認する
3. `paper_knowledge/notes/` に短いメモを作る
4. `paper_knowledge/graph/graph.json` を更新する
5. `paper_knowledge/viewer/graph-data.js` を更新する
6. 必要なら `paper_knowledge/out/planning_brief.md` を生成する

## 2. 手元のメモからグラフを更新する

自分でメモを作る場合は、`paper_knowledge/notes/` に Markdown ファイルを置きます。

最小例:

```markdown
---
id: paper:smith2024
kind: paper
title: Example Robustness Paper
year: 2024
authors: Ada Smith; Taro Yamada
tags: robustness, contrastive-learning
url: https://example.com/paper
---

小さな要約を1段落で書く。

uses_method:: method:contrastive-learning
uses_dataset:: dataset:cifar10
reports_metric:: metric:accuracy
addresses_task:: task:image-classification
supports:: claim:contrastive-features-improve-robustness
```

メモを追加した後、次を実行します。

```bash
python3 paper_knowledge/bin/pk.py systematize --notes paper_knowledge/notes
python3 paper_knowledge/bin/pk.py viewer-data
python3 paper_knowledge/bin/pk.py validate
```

## 3. ビューワーを開く

人間向けの入口は次です。

```text
paper_knowledge/HUMAN_ENTRYPOINT.md
```

ビューワーを開く前に、表示用データを更新します。

```bash
python3 paper_knowledge/bin/pk.py viewer-data
```

その後、ブラウザで次のファイルを開きます。

```text
paper_knowledge/viewer/index.html
```

ビューワーでは次ができます。

- ノードをドラッグして配置を調整する
- マウスホイールでズームする
- 背景をドラッグしてパンする
- `Search` で論文名、手法、データセット、タグなどを検索する
- `Node Types` で paper、claim、method などを絞り込む
- `Edge Type` で supports、uses_method、reports_metric などを絞り込む
- ノードをクリックして詳細と接続を見る
- `Fit` で表示範囲に収める
- `Reset` で検索・フィルタ・表示を初期化する

## 4. 研究計画用ブリーフを作る

研究計画時は、外部を再検索する前に既存グラフを局所照会します。Codexへ依頼する場合は次を使います。

```text
$query-paper-knowledge を使って、<候補仮説>に関係する論文、手法、データセット、metric、支持・反証、未解決点を計画用query packにしてください。
```

CLIを直接使う場合は次を実行します。

```bash
python3 paper_knowledge/bin/pk.py brief --query "<調べたい語句>"
```

例:

```bash
python3 paper_knowledge/bin/pk.py brief --query "contrastive robustness cifar10"
```

出力先:

```text
paper_knowledge/out/planning_brief.md
```

このブリーフは、実験結果や`research/EVIDENCE.jsonl`の根拠ではなく「事前知識の整理」として扱います。計画では元資料（source）、読んだ範囲、未確認点を保持し、支持範囲を広げる根拠にはしません。

## 5. 関係タイプの使い分け

| 関係 | 意味 |
|---|---|
| `uses_method` | 論文やメモが特定の手法を使う |
| `uses_dataset` | 特定のデータセットを使う |
| `reports_metric` | 特定の評価指標を報告する |
| `addresses_task` | 特定のタスクを扱う |
| `supports` | 主張を支持する |
| `contradicts` | 主張と矛盾する、または否定的結果を示す |
| `extends` | 既存研究や手法を拡張する |
| `cites` | 明示的な引用関係がある |
| `links_to` | 弱い関連がある |
| `related_by_tag` | 共通タグから自動的に作られた関連 |

`supports` や `contradicts` は強い意味を持つため、読んだ範囲で明確に言える場合だけ使います。

## 6. 安全な運用ルール

- フルペーパーや大きなリポジトリを丸ごと読ませない
- 調査件数を少数に制限する
- メモには長い引用を入れず、短い要約と URL を残す
- グラフを研究証拠として扱わない
- 実験計画に使う場合は、必ず元の source URL と読んだ範囲を確認する
- 更新後は `pk.py validate` を実行する

## 7. よく使うコマンド

```bash
# グラフを検証する
python3 paper_knowledge/bin/pk.py validate

# Markdown メモからグラフを更新する
python3 paper_knowledge/bin/pk.py systematize --notes paper_knowledge/notes

# ビューワー用データを更新する
python3 paper_knowledge/bin/pk.py viewer-data

# 研究計画用ブリーフを作る
python3 paper_knowledge/bin/pk.py brief --query "<query>"

# CSL JSON を取り込む
python3 paper_knowledge/bin/pk.py ingest-csl <path-to-csl.json>

# BibTeX を取り込む
python3 paper_knowledge/bin/pk.py ingest-bibtex <path-to-refs.bib>
```

## 8. 困ったとき

グラフが空に見える場合:

1. `paper_knowledge/notes/` にメモがあるか確認する
2. `python3 paper_knowledge/bin/pk.py systematize --notes paper_knowledge/notes` を実行する
3. `python3 paper_knowledge/bin/pk.py viewer-data` を実行する
4. ブラウザで `paper_knowledge/viewer/index.html` を再読み込みする

検索しても出ない場合:

- 検索語を短くする
- `Node Types` のチェックを戻す
- `Edge Type` を `all` に戻す
- `Reset` を押す

研究計画に使ってよいか迷う場合:

- `paper_knowledge/out/planning_brief.md` を作る
- source URL と読んだ範囲を確認する
- 未確認の関係は仮説や事前知識として扱う
