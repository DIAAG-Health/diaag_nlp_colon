
### Colonoscopy Report 

Representation of a colonoscopy report and its features with respect to the NLP pipeline.

##### Col Report properties

| Property          | Type    | Description                                      |
|:---               |:---     |:---                                              |
| `polyps`          | list    | list of extracted [Polyps](./Polyp.md)           |
| `review_flags`    | dict    | Flags for potential <1 year follow-up            |
| `report_props`    | dict    | Additional properties extracted from colo report |
| `quality_metrics` | dict    | Colonoscopy procedure quality metrics            |

Can also contain a property `summary_vals`, containing variables computed by the pipeline
(useful for verifying consistency of output across system, esp. after feature updates)

###### Manual Review Flags

- `many_polyps` (> 10 individual polyp observations)
- `poor_prep` (the quality of the colonic preparation was poor)
- `incomplete_proc` (cecum not reached)
- `retained_polyp` (polyp not removed during procedure)

###### Extracted Report Properties

- `prep_worst` (worst recorded quality of the colonic preparation)
- `prep_best` (best recorded quality of the colonic preparation)
- `extent`(extent of colonoscopy)
- `visualization` (quality of colon visualization)
- `indications` (clinical indications extracted from report section)
- `withdrawal_text` (text contents of `TOTAL WITHDRAWAL TIME` section, if present)

###### Quality Metrics

- `doc_prep_tf` (True if quality of the colonic preparation is documented in report)
- `adequate_prep_tf` (True if quality of prep is adequate)
- `doc_cecal_int_tf`(True if cecal intubation is documented (successful or not))
- `cecal_int_tf`(True if cecal intubation is documented as successful)
- `doc_withdrawal_time_tf` (True if endoscope withdrawal time is documented)
- `withdrawal_time_min` (Withdrawal time minutes component, if documented)
- `withdrawal_time_sec` (Withdrawal time seconds component, if documented)

##### Example

Description of polyp observations in colonoscopy report findings:
````text
There were two flat 5mm polyps in the ascending colon removed with cold snare polypectomy.
A single broad-based polyp in the cecum measuring 1.2cm was seen but not removed.
````
```json
{    
   "polyps": [ 
      {
        "location": "ascending colon",
        "morphology": "flat",
        "quantity": 2,
        "quantity_approx": "",
        "size_meas": 0.5,
        "size_approx": "",
        "retained": false
      },
      {
        "location": "cecum",
        "morphology": "broadbased",
        "quantity": 1,
        "quantity_approx": "",
        "size_meas": 1.2,
        "size_approx": "",
        "retained": true
      }
   ],
  "review_flags": {
    "many_polyps": false,
    "poor_prep": false,
    "incomplete_proc": false,
    ...
  },
  "report_props": {
    "prep_quality": "fair",
    "indications_text": "Screening Colonoscopy",
    ...
  },
  "quality_metrics": {
    "doc_prep_tf": true,
    "adequate_prep_tf": true,
    ...
  }
}
```
