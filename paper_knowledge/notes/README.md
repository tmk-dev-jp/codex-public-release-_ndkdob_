# Notes

Put scoped literature notes here when you want deterministic ingestion into the
paper knowledge graph.

Example:

```markdown
---
id: paper:smith2024
kind: paper
title: Example Robustness Paper
year: 2024
authors: Ada Smith; Taro Yamada
tags: robustness, contrastive-learning
doi: 10.0000/example
---

This note links to [[method:contrastive-learning]] and [[dataset:cifar10]].

uses_method:: method:contrastive-learning
uses_dataset:: dataset:cifar10
reports_metric:: metric:accuracy
supports:: claim:augmentation-improves-robustness
```

