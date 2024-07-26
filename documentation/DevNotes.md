## Developer Notes

### Recommended Tooling

* Recommended IDEs are:
    1. Pycharm - Community Edition is free (Highly recommended)
    2. Visual Studio Code

### Dependencies 

To install dependencies in a pipenv virtual environment:
```commandline
pipenv install --dev
```

### Adding Test Reports

We aren't going to add reports with PHI to gitlab, so the current test reports are small toy examples.
If you want to test out the script with real data, reports can be added to the `test_reports` directory.
They can be added directly from an unzipped Brat download.

Example: for testing out a Pathology report, add two files per report (`<filename>.txt` and `<filename>.ann`)
to the `test_reports/path/` directory.

### brat data format

brat standoff annotation format outlined here: https://brat.nlplab.org/standoff.html

### Working with spaCy

#### These are a few convenient way to check inner workings of spaCy pipeline in python console:

Using blank English-language spaCy pipeline:
```python
import spacy
nlp = spacy.blank('en')
```
Or using English pre-trained model:
```python
from spacy.lang.en import English
nlp = English()
```
Can also check spaCy's built-in Sentencizer component:
```python
from spacy.pipeline import Sentencizer
sentencizer = nlp.create_pipe('sentencizer')
nlp.add_pipe(sentencizer)
```
Then pass some text to the pipeline `nlp` and examine results
```python
report = 'Some interesting text. Yay!!'
doc = nlp(report)
```
Finally you can inspect the resulting spaCy `Doc` object by iterating through its tokens
```shell
>>> [token.text for token in doc]
['Some', 'interesting', 'text', '.', 'Yay', '!', '!']

>>> [sentence.text for sentence in doc.sents]
['Some interesting text.', 'Yay!!']
```
If `ner` or `entity_ruler` components were added to pipeline, can check entity text and labels
```shell
>>> [(ent.text, ent.label_) for ent in doc.ents]
[('SOME_ENT_LABEL', 'matching text')]
```

### Adding Entity Patterns

spaCy docs found here: https://spacy.io/usage/rule-based-matching#entityruler

Entity patterns are dictionaries with two keys: `label`, specifying the label to assign 
to the entity if the pattern is matched, and `pattern`, the match pattern. 
The entity ruler accepts two types of patterns:

**String**: Phrase patterns for exact string matches.
```python
{"label": "ORG", "pattern": "Apple"}
```
**List**: Token patterns, specified as lists with one dict describing one token.
```python
{"label": "GPE", "pattern": [{"LOWER": "san"}, {"LOWER": "francisco"}]}
```

### Automated Testing

The current tests are basic unit tests written using the python package `pytest`

Running tests from root directory: 
```commandline
python -m pytest (add -v for verbose)
```

Pytest looks for a `tests/` module, then collects and runs all available tests.

example verbose output:

```commandline
============================= test session starts =============================
platform win32 -- Python 3.7.5, pytest-6.2.2, py-1.10.0, pluggy-0.13.1
cachedir: .pytest_cache
rootdir: C:\Users\EDPeterson\DIAAG\DIAAG_report_nlp\tests
collecting ... collected 6 items

sample_test.py::TestHistologyPatterns::test_hyperplastic PASSED          [ 16%]
sample_test.py::TestDysplasiaPatterns::test_dysplasia[high-grade dysplasia] PASSED [ 33%]
sample_test.py::TestDysplasiaPatterns::test_dysplasia[cytologic dysplasia] PASSED [ 50%]
test_colo_patterns.py::TestMorphologyPatterns::test_flat PASSED          [ 66%]
test_colo_patterns.py::TestSizePatterns::test_size_meas[size-measurement] PASSED [ 83%]
test_colo_patterns.py::TestPrepQuality::test_prep_quality[prep-was-x] PASSED [100%]

============================== 6 passed in 1.37s ==============================
```

To show collected tests:
```commandline
pytest --co
```

Examples of ways to only run colonoscopy tests:
```commandline
python -m pytest test_colo_patterns.py
python -m pytest -k "colo" -v
```

Tests can be marked as expected to fail, e.g. with `marks=pytest.mark.xfail`


### Saving/Loading Models

Loading trained model:
```python
import en_trained_sections_col
nlp = en_trained_sections_col.load()
```
Then add or modify any existing pipes or components.

### Working with a trained statistical model

Interaction of statistical (custom `en_trained`) vs. rule-based (`EntityRuler`) NER models:
The entity ruler comes after the statistical NER but if `overwrite_ents` is set to `True`,
then the ruler can add entities even if they overlap/overwrite what the model predicted.

```python
# add colonoscopy entity ruler for rule-based entities
ruler = EntityRuler(nlp, overwrite_ents=True)
```

Pipeline component order can be checked by inspecting `nlp.pipe_names`

More info here: https://spacy.io/usage/rule-based-matching#entityruler-usage
