| Feature | Description                             |
| --- |-----------------------------------------|
| **Name** | `en_trained_sections_col`               |
| **Version** | `2.0.0`                                 |
| **spaCy** | `>=3.3.1,<3.5.0`                        |
| **Default Pipeline** | `tok2vec`, `ner`                        |
| **Components** | `tok2vec`, `ner`                        |
| **Vectors** | 0 keys, 0 unique vectors (0 dimensions) |
| **Sources** | n/a                                     |
| **License** | n/a                                     |
| **Author** | [edpeterson]()                          |

### Label Scheme

<details>

<summary>View label scheme (6 labels for 1 components)</summary>

| Component | Labels |
| --- | --- |
| **`ner`** | `POLYP_LOC`, `POLYP_MORPH`, `POLYP_QUANT`, `POLYP_SAMPLE`, `POLYP_SIZE_MEAS`, `POLYP_SIZE_NONSPEC` |

</details>

### Accuracy

| Type | Score |
| --- | --- |
| `ENTS_F` | 89.38 |
| `ENTS_P` | 89.90 |
| `ENTS_R` | 88.87 |
| `TOK2VEC_LOSS` | 49312.71 |
| `NER_LOSS` | 52753.72 |