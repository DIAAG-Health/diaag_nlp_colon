
### Colon Polyp

Object representing a colon polyp (or group of polyps) found during a colonoscopy procedure or 
described in a pathology report.

##### Polyp properties
| Property           | Type      | Report Type | Description                                     |
|:---                |:---       |:---         |:---                                             |
| `location`         | string    | Col, Path   | Location of polyp                               |
| `morphology`       | string    | Col         | Characteristic of polyp shape                   |
| `quantity`         | integer   | Col         | Number of polyps in observation                 |
| `quantity_approx`  | string    | Col         | Nonspecific number of polyps                    |
| `size_meas`        | float     | Col         | Measured size of polyp                          |
| `size_approx`      | string    | Col         | Nonspecific size of polyp                       |
| `cyt_dysplasia`    | string    | Path        | Whether cytologic dysplasia was observed        |
| `hg_dysplasia`     | string    | Path        | Whether high-grade dysplasia was observed       |
| `histology`        | string    | Path        | Histology of polyp                              |
| `multi`            | boolean   | Col         | True if sentence contained >1 location or size  |
| `retained`         | boolean   | Col         | True if polyp not removed during colonoscopy    |
| `sample`           | boolean   | Path        | True if sample contained polyp                  |

Currently most of the properties are not restricted or mapped onto a known set of values.
Since they come directly from the entity text, there might be inconsistent representations of one value
(e.g. location can be `ascending`, `ascending colon`, `asc colon`, etc).

Note about `multi`: affects computed total number of polyps in colonoscopy report. If a polyp has a null
`quantity` value, it will still count towards the total number of polyps, but *not* if it was in a 
sentence with more than one polyp observation.

Note about `sample`: helps distinguish between pathology samples containing polyps vs unrelated biopsied tissue

##### Example

Description of polyp observation in colonoscopy report:
````text
There were two flat 5 mm polyps in the ascending colon removed completely/retrieved with cold snare polypectomy.
````
Extracted polyp object:
```json
{
  "location": "ascending colon",
  "morphology": "flat",
  "quantity": 2,
  "quantity_approx": "",
  "size_meas": 0.5,
  "size_approx": "",
  "multi": false
}
```

Description of the same polyp in pathology report:
````text
A.  COLON, ASCENDING, POLYP X2 (POLYPECTOMY): - Tubular adenoma x2  - No high-grade dysplasia    
````
Extracted polyp object:
```json
{
  "cyt_dysplasia": "",
  "hg_dysplasia": "no",
  "histology": "tubular adenoma",
  "location": "ascending",
  "sample": true
}
```
