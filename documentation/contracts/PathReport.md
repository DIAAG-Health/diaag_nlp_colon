
### Colon Pathology Report 

Representation of a pathology report and its features with respect to the NLP pipeline.

##### Path Report properties

| Property         | Type    | Description                                       |
|:---              |:---     |:---                                               |
| `polyps`         | list    | list of extracted [Polyps](./Polyp.md)            |
| `review_flags`   | dict    | Flags for potential <1 year follow-up             |

Can also contain a property `summary_vals`, containing variables computed by the pipeline
(useful for verifying consistency of output across system, esp. after feature updates)

###### Manual Review Flags

* `malignancy` (cancerous polyp found, Final Diagnosis mentions terms like `adenocarcinoma`)

##### Example

Description of polyp observation in pathology report final diagnosis:
````text
A.  COLON, ASCENDING, POLYP X2 (POLYPECTOMY): - Tubular adenoma x2  - No high-grade dysplasia    
````
```json
{    
   "polyps": [ 
      {
        "cyt_dysplasia": "",
        "hg_dysplasia": "no",
        "histology": "tubular adenoma",
        "location": "ascending"
      }
   ],
  "review_flags": {
    "malignancy": false
  }
}
```

