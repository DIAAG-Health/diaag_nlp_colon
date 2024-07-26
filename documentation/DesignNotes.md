## Design Notes

### Colon Polyp Observation Extraction

#### Colonoscopy example:

##### Report text (**Findings** Section):
````text
There was a 2 mm polyp in the cecum removed completely/retrieved with cold forceps polypectomy.
There were two 5 mm polyps in the ascending colon removed completely/retrieved with cold snare polypectomy.
There was a 1.5 cm flat polyp (Paris classification IIb) in the transverse colon. 
````
##### Polyp observations objects:
````json
[
    {
        "location": "cecum",
        "morphology": "",
        "quantity": "",
        "quantity_approx": "",
        "size_meas": 0.2,
        "size_approx": ""
    },
    {
        "location": "ascending colon",
        "morphology": "",
        "quantity": 2,
        "quantity_approx": "",
        "size_meas": 0.5,
        "size_approx": ""
    },
    {
        "location": "transverse colon",
        "morphology": "flat",
        "quantity": "",
        "quantity_approx": "",
        "size_meas": 1.5,
        "size_approx": ""
    }
]
````

#### Pathology example:

##### Report text (**Final Diagnosis** Section):
````text
A.  CECUM, POLYP (BIOPSY): - Colonic mucosa with no histopathologic abnormality  - No dysplasia 
B.  COLON, ASCENDING, POLYP X2 (POLYPECTOMY): - Tubular adenoma x2  - No high-grade dysplasia    
C.  COLON, TRANSVERSE, POLYP (POLYPECTOMY): - Colonic mucosa with focal mild surface hyperplastic change  - No dysplasia
````
##### Polyp observations objects:
````json
[
    {
        "cyt_dysplasia": "",
        "hg_dysplasia": "no",
        "histology": "",
        "location": "cecum"
    },
    {
        "cyt_dysplasia": "",
        "hg_dysplasia": "no",
        "histology": "tubular adenoma",
        "location": "ascending"
    },
    {
        "cyt_dysplasia": "",
        "hg_dysplasia": "no",
        "histology": "hyperplastic",
        "location": "transverse"
    }
]
````
We don't look at the `Gross Description` section of the pathology reports because the data can be misleading.
We are trying to get an accurate picture of a patient's polyps as they were observed during the colonoscopy procedure.
If the polyps are removed in multiple pieces then the sizes and quantities recorded in the `Gross Description` section
will not be useful. 
