# 実験結果確認用: {{EXPERIMENT_ID}}

このファイルは、人間が結果を確認するための読み取り専用メモです。解釈は同じディレクトリの`INTERPRETATION.md`に書いてください。

## 確認すること

- 固定済みの判定方式は数値閾値か傾向か。数値閾値なら最小改善量を満たすか。
- 傾向方式なら、期待した方向や形が最低限必要な観測条件で現れたか。弱い、逆向き、混在、観測不足のどれか。
- 同じ条件で比較する既存手法または過去実験（baseline）との差は、研究上意味があるか。
- 動作確認（smoke）、有望性確認（pilot）、最終評価（full）の規模に対して、結論が強すぎないか。
- 注意点、学習側へのtest情報混入、指標の不一致、実行予算の制限がないか。
- 次に支持、棄却、限定、保留、停止のどれを選ぶべきか。

## 実験記録

```markdown
{{EXPERIMENT_TEXT}}
```

## 集約評価値（Metrics）

```json
{{METRICS_JSON}}
```

## 実行条件と生成物の目録（Runtime Manifest）

```json
{{MANIFEST_JSON}}
```

## 比較基準（Baseline）

```json
{{BASELINE_JSON}}
```

## 機械判定された評価事実（Decision Facts）

```json
{{DECISION_FACTS_JSON}}
```

## 実装前の計画・評価指標監査（Plan Audit）

```markdown
{{PLAN_AUDIT}}
```

## 実行前の実装監査（Implementation Audit）

```markdown
{{IMPLEMENTATION_AUDIT}}
```

## 結果出所・計画遵守・漏洩リスクの監査（Integrity Audit）

```markdown
{{INTEGRITY_AUDIT}}
```
