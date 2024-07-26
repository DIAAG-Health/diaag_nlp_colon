| Feature | Description                             |
| --- |-----------------------------------------|
| **Name** | `en_trained_sections_path`              |
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

<summary>View label scheme (7 labels for 1 components)</summary>

| Component | Labels |
| --- | --- |
| **`ner`** | `POLYP_CYT_DYSPLASIA`, `POLYP_HG_DYSPLASIA`, `POLYP_HIST`, `POLYP_LOC`, `POLYP_QUANT`, `POLYP_SAMPLE`, `POLYP_SIZE_MEAS` |

</details>

### Accuracy

| Type | Score |
| --- | --- |
| `ENTS_F` | 88.30 |
| `ENTS_P` | 87.07 |
| `ENTS_R` | 89.57 |
| `TOK2VEC_LOSS` | 48114.82 |
| `NER_LOSS` | 99386.16 |