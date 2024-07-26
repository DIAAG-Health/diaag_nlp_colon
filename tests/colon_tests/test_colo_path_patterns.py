import spacy
from spacy.pipeline import EntityRuler
from spacy.tokens import Token, Span
import pytest
from tests.helpers import remove_false_pos, mark_malignancy_false_pos, has_false_positive

with open(f"./tests/reports/colo_path_sample.txt") as f:
    report = f.read()

test_patterns = [
    {"label": "MALIGNANCY",
     "pattern": [{"LOWER": {"IN": ["sarcoid", "malignant", "malignancy", "carcinoid", "lymphoma"]}},
                 {"LOWER": "tumor", "OP": "?"}
                 ]},
    {"label": "MALIGNANCY", "pattern": [{"LOWER": "invasive", "OP": "?"}, {"LOWER": {"REGEX": "(adeno)?carcinoma"}}]},
    {"label": "MALIGNANCY", "pattern": [{"LOWER": "neuroendocrine"}, {"LOWER": "tumor"}]},
    {"label": "MALIGNANCY", "pattern": [{"TEXT": "NET"}]},
    {"label": "POLYP_HIST", "pattern": [{"LOWER": "sessile"}, {"LOWER": "serrated"},
                                        {"LOWER": {"REGEX": "(polyp\\(?s?\\)?)|(lesion\\(?s?\\)?)|(adenoma\\(?s?\\)?)"}}]},
    {"label": "POLYP_HIST", "pattern": [{"LOWER": "tubulovillous"}, {"LOWER": {"REGEX": "adenoma\\(?s?\\)?-?"}}]},
]

# Four steps of a test:
# 1. Arrange
# 2. Act
# 3. Assert
# 4. Cleanup


@pytest.fixture(scope='class')
def nlp():
    return spacy.blank('en')


@pytest.fixture(scope="class")
def ruler(nlp):
    _ruler = nlp.add_pipe("entity_ruler", config={"overwrite_ents": True})
    _ruler.add_patterns(test_patterns)
    return _ruler


@pytest.fixture(scope='class')
def pipeline(nlp, ruler):
    yield nlp
    nlp.remove_pipe('entity_ruler')


class TestHistology:
    @pytest.fixture(scope='class')
    def ents(self, report, ruler, pipeline):
        doc = pipeline(report)
        return [(ent.text, ent.label_) for ent in doc.ents]

    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(report, ('Sessile serrated polyp', 'POLYP_HIST'), id="hist-SSP-singular"),
            pytest.param(report, ('Sessile serrated polyp(s', 'POLYP_HIST'), id="hist-SSP-paren"),
            pytest.param(report, ('Sessile serrated polyps', 'POLYP_HIST'), id="hist-SSP-plural"),
            pytest.param(report, ('Tubulovillous adenoma', 'POLYP_HIST'), id="hist-TVA"),
        ],
        scope='class'
    )
    def test_histology(self, report, ents, expected):
        assert expected in ents


class TestPosMalignancy:
    @pytest.fixture(scope='class')
    def ents(self, report, ruler, pipeline):
        Token.set_extension('is_false_pos', default=False, force=True)
        Span.set_extension('has_false_pos', getter=has_false_positive, force=True)
        pipeline.add_pipe('mark_malignancy_false_pos_helper')
        pipeline.add_pipe('remove_false_pos_helper')

        doc = pipeline(report)
        return [(ent.text, ent.label_) for ent in doc.ents]

    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(report, ('adenocarcinoma', 'MALIGNANCY'), id='mal-adeno'),
            pytest.param(report, ('sarcoid tumor', 'MALIGNANCY'), id='mal-sarcoid'),
            pytest.param(report, ('neuroendocrine tumor', 'MALIGNANCY'), id='mal-neuro'),
            pytest.param(report, ('Invasive adenocarcinoma', 'MALIGNANCY'), id='mal-invasive'),
            pytest.param(report, ('NET', 'MALIGNANCY'), id='mal-NET')
        ],
        scope='class'
    )
    def test_pos_malignancy(self, report, ents, expected):
        assert expected in ents


class TestNegMalignancy:
    @pytest.fixture(scope='class')
    def ents(self, report, ruler, pipeline):
        Token.set_extension('is_false_pos', default=False, force=True)
        Span.set_extension('has_false_pos', getter=has_false_positive, force=True)
        pipeline.add_pipe('mark_malignancy_false_pos_helper')
        pipeline.add_pipe('remove_false_pos_helper')

        doc = pipeline(report)
        return [(ent.text, ent.label_) for ent in doc.ents]

    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(report, ('malignant', 'MALIGNANCY'), id='mal-neg-1'),
            pytest.param(report, ('invasive carcinoma', 'MALIGNANCY'), id='mal-neg-2'),
            pytest.param(report, ('carcinoid tumor', 'MALIGNANCY'), id='mal-neg-3'),
            pytest.param(report, ('malignancy', 'MALIGNANCY'), id='mal-neg-4'),
        ],
        scope='class'
    )
    def test_neg_malignancy(self, report, ents, expected):
        assert expected not in ents
