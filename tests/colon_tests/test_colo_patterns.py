import spacy
from spacy.pipeline import EntityRuler
from spacy.tokens import Doc
import pytest
from tests.helpers import (
    extract_section_span, get_section_header_list, extract_withdrawal_time,
    check_prep_quality, has_poor_prep, has_retained_polyp
)


header_patterns = [
    {"label": "SECTION_HEADER",
     "pattern": [{"TEXT": "INDICATIONS"}, {"TEXT": "FOR", "OP": "?"}, {"TEXT": "EXAMINATION", "OP": "?"}, {"TEXT": ":"}],
     "id": "section_IND"},
    {"label": "SECTION_HEADER", "pattern": [{"TEXT": "PROCEDURE"}, {"TEXT": "PERFORMED"}, {"TEXT": ":"}],
     "id": "section_PROC_P"},
    {"label": "SECTION_HEADER", "pattern": [{"TEXT": "Indications"}, {"TEXT": ":"}], "id": "section_IND"},
    {"label": "SECTION_HEADER", "pattern": [{"TEXT": "Consent"}, {"TEXT": ":"}], "id": "section_CONS"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "medications"}, {"TEXT": ":"}], "id": "section_MEDS"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "procedure"}, {"LOWER": "technique"}, {"TEXT": ":"}],
     "id": "section_PROC_TECH"},
    {
        "label": "SECTION_HEADER",
        "pattern": [{"LOWER": "description"}, {"LOWER": "of"}, {"LOWER": "the"}, {"LOWER": "procedure"}, {"TEXT": ":"}],
        "id": "section_DOTP"
    },
    {"label": "SECTION_HEADER",
     "pattern": [{"TEXT": "DESCRIPTION"}, {"TEXT": "OF"}, {"TEXT": "PROCEDURE"}, {"TEXT": ":"}],
     "id": "section_DOP"},
    {"label": "SECTION_HEADER", "id": "section_SED",
     "pattern": [{"LOWER": "sedation"}, {"LOWER": "start"}, {"TEXT": ":"}]},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "visualization"}, {"TEXT": ":"}], "id": "section_VIS"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "extent"}, {"LOWER": "of"}, {"LOWER": "exam"},
                                            {"TEXT": ":"}], "id": "section_EXT"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "total"}, {"LOWER": {"REGEX": "withdrawa?l"}}, {"LOWER": "time"},
                                            {"TEXT": ":"}],
     "id": "section_WITHDRAWAL_TIME"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "total"}, {"LOWER": "insertion"}, {"LOWER": "time"},
                                            {"TEXT": ":"}],
     "id": "section_INSERTION_TIME"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "instruments"}, {"TEXT": ":"}], "id": "section_INST"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "technical"}, {"LOWER": "difficulty"}, {"TEXT": ":"}],
     "id": "section_TECH"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "findings"}, {"TEXT": ":"}], "id": "section_FIN"},
]

polyp_patterns = [
    {"label": "POLYP_MORPH", "pattern": [{"LOWER": "flat"}], "id": "morph_flat"},
    {"label": "POLYP_SIZE_MEAS", "pattern": [{"LOWER": {"REGEX": "\\d+-?[cm]m"}}], "id": "size_meas"},
    {"label": "POLYP_SIZE_MEAS", "pattern": [{"IS_DIGIT": True}, {"LOWER": {"IN": ["cm", "mm"]}}]},
    # {"label": "POLYP_SIZE_MEAS", "pattern": [{"LIKE_NUM": True}, {"LOWER": {"REGEX": "((centi|milli)meters?|[cm]m)"}}]},
    {"label": "POLYP_PROC", "pattern": [{"LOWER": {"IN": ["biopsy", "biopsied"]}}, {"LOWER": "taken", "OP": "?"}],
     "id": "proc_biopsy_taken"},
]

metrics_patterns = [
    {
        "label": "PREP_QUALITY",
        "pattern": [
            {"LOWER": {"REGEX": "prep(aration)?"}}, {"LOWER": "was"}, {"LOWER": {"NOT_IN": ["not"]}, "OP": "?"},
            {"LOWER": {"IN": ["poor", "inadequate", "adequate", "fair", "good", "excellent"]}},
        ]
    },
    {
        "label": "PREP_QUALITY",
        "pattern": [
            {"LOWER": {"IN": ["poor", "inadequate", "adequate", "fair", "good", "excellent"]}},
            {"LOWER": {"REGEX": "colon(ic)?"}, "OP": "?"}, {"LOWER": {"REGEX": "prep(aration)?"}}
        ]
    },
    {
        "label": "PREP_QUALITY",
        "pattern": [
            {"LOWER": "views"}, {"LOWER": "were"},
            {"LOWER": {"IN": ["poor", "inadequate", "adequate", "fair", "good", "excellent"]}}
        ]
    },
    {"label": "CECAL_INT",
     "pattern": [{"LOWER": "cecum"}, {"LOWER": "was", "OP": "?"}, {"LOWER": {"NOT_IN": ["not"]}, "OP": "?"},
                 {"LOWER": {"IN": ["intubated", "visualized", "examined"]}}
                 ]},
    {"label": "CECAL_INT",
     "pattern": [{"LOWER": "advanced"}, {"LOWER": "to"}, {"LOWER": "the"}, {"LOWER": "cecum"}]},
    {
        "label": "CECAL_INT",
        "pattern": [{"LOWER": "prevented"}, {"LOWER": "cecal"}, {"LOWER": "intubation"}],
        "id": "cecal_int_neg"
    },
    {
        "label": "INCOMPLETE_PROC",
        "pattern": [{"LOWER": "unable"}, {"LOWER": "to"}, {"LOWER": "complete"},
                    {"LOWER": {"IN": ["colonoscopy", "procedure"]}}]
    },
    {"label": "INCOMPLETE_PROC",
     "pattern": [{"LOWER": "incomplete"}, {"LOWER": {"IN": ["colonoscopy", "procedure"]}}]},
    {"label": "INCOMPLETE_PROC",
     "pattern": [{"LOWER": {"IN": ["colonoscopy", "procedure"]}}, {"LOWER": "was"}, {"LOWER": "incomplete"}]},
    {
        "label": "INCOMPLETE_PROC",
        "pattern": [{"LOWER": "cecum"}, {"LOWER": "could"}, {"LOWER": "not"}, {"LOWER": "be"}, {"LOWER": "reached"}]
    },
    {
        "label": "REMOVED_PIECEMEAL",
        "pattern": [{"LOWER": "piecemeal"}]
    },
    {"label": "RETAINED_POLYP",
     "pattern": [{"LOWER": "unable"}, {"LOWER": "to"}, {"LOWER": "remove"}]},
    {"label": "RETAINED_POLYP",
     "pattern": [{"LOWER": "resection"}, {"LOWER": "was", "OP": "?"}, {"LOWER": "not"}, {"LOWER": "attempted"}]},
    {"label": "RETAINED_POLYP",
     "pattern": [{"LOWER": "could"}, {"LOWER": "not"}, {"LOWER": "be", "OP": "?"}, {"LOWER": {"REGEX": "removed?"}}]},
    {"label": "RETAINED_POLYP",
     "pattern": [{"LOWER": "seen"}, {"LOWER": {"IN": ["and", "but"]}}, {"LOWER": "not"}, {"LOWER": "removed"}]},
    {
        "label": "RETAINED_POLYP",
        "pattern": [{"LOWER": "unable"}, {"LOWER": "to"}, {"LOWER": "be", "OP": "?"},
                    {"LOWER": {"IN": ["remove", "removed", "retrieve", "retrieved"]}}]
    },
    {
        "label": "WITHDRAWAL_TIME",
        "pattern": [{"LOWER": {"REGEX": "withdrawa?l"}}, {"LOWER": "time"}, {"LOWER": "was", "OP": "?"},
                    {"LIKE_NUM": True}, {"LOWER": "minutes"}]
    },
    {
        "label": "WITHDRAWAL_TIME",
        "pattern": [{"LOWER": "withdrawal"}, {"LOWER": "time"}, {"TEXT": ":", "OP": "?"},
                    {"TEXT": {"REGEX": "\\d+:\\d+"}}]
    },
]

# TODO: find a better way to do this
with open(f"./tests/reports/colo_sample.txt") as f:
    colo_report = f.read()

with open(f"./tests/reports/colo_prep_sample.txt") as fp:
    colo_prep_report = fp.read()


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
    _ruler.add_patterns(header_patterns)
    _ruler.add_patterns(polyp_patterns)
    _ruler.add_patterns(metrics_patterns)
    return _ruler


@pytest.fixture(scope='class')
def pipeline(nlp, ruler):
    yield nlp
    nlp.remove_pipe('entity_ruler')


class TestMorphologyPatterns:
    @pytest.fixture(scope='class')
    def ents(self, ruler, pipeline):
        doc = pipeline(colo_report)
        return [(ent.text, ent.label_) for ent in doc.ents]

    def test_flat(self, ents):
        assert ('flat', 'POLYP_MORPH') in ents


class TestSizePatterns:
    @pytest.fixture(scope='class')
    def ents(self, report, ruler, pipeline):
        doc = pipeline(report)
        return [(ent.text, ent.label_) for ent in doc.ents]

    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(colo_report, ('2mm', 'POLYP_SIZE_MEAS'), id="size-measurement"),
            pytest.param(colo_report, ('9mm', 'POLYP_SIZE_MEAS'), id="size-measurement")
        ],
        scope='class'
    )
    def test_size_meas(self, report, ents, expected):
        assert expected in ents


class TestPrepQuality:
    @pytest.fixture(scope='class')
    def doc(self, report, ruler, pipeline):
        Doc.set_extension('section_header_list', getter=get_section_header_list, force=True)
        doc = pipeline(report)
        return doc

    @pytest.fixture(scope='class')
    def ents(self, doc):
        return [(ent.text, ent.label_) for ent in doc.ents]

    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(colo_report, ('prep was fair', 'PREP_QUALITY'), id="prep-fair"),
            pytest.param(colo_report, ('preparation was only fair', 'PREP_QUALITY'), id="prep-fair-wildcard"),
            pytest.param(colo_prep_report, ('preparation was poor', 'PREP_QUALITY'), id="prep-poor-1"),
            pytest.param(colo_prep_report, ('Poor colon prep', 'PREP_QUALITY'), id="prep-poor-2"),
        ],
        scope='class'
    )
    def test_prep_quality_ent(self, report, doc, ents, expected):
        assert expected in ents


    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(colo_report, True, id="prep-adeq-excellent"),
            pytest.param(colo_report, True, id="prep-adeq-fair"),
            pytest.param(colo_prep_report, False, id="prep-adeq-poor")
        ],
        scope='class'
    )
    def test_adequate_prep(self, report, doc, ents, expected):
        section_span = extract_section_span(doc, 'PREP_QUALITY')
        assert expected == check_prep_quality(section_span)


    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(colo_prep_report, ('preparation was poor', 'PREP_QUALITY'), id="poor-prep"),
            pytest.param(colo_prep_report, ('Poor colon prep', 'PREP_QUALITY'), id="poor-colon-prep"),
            pytest.param(colo_prep_report, ('Inadequate prep', 'PREP_QUALITY'), id="inadequate-prep")
        ],
        scope='class'
    )
    def test_poor_prep(self, report, doc, ents, expected):
        assert expected in ents
        assert has_poor_prep(doc) == True


class TestCecalIntubation:
    @pytest.fixture(scope='class')
    def doc(self, report, ruler, pipeline):
        Doc.set_extension('section_header_list', getter=get_section_header_list, force=True)
        doc = pipeline(report)
        return doc

    @pytest.fixture(scope='class')
    def ents(self, doc):
        return [(ent.text, ent.label_) for ent in doc.ents]

    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(colo_report, ('advanced to the cecum', 'CECAL_INT'), id="cecal-int-1"),
            pytest.param(colo_report, ('Cecum was intubated', 'CECAL_INT'), id="cecal-int-2"),
            pytest.param(colo_report, ('Cecum was not visualized', 'CECAL_INT'), marks=pytest.mark.xfail, id="not-cecal-int"),
            pytest.param(colo_prep_report, ('prevented cecal intubation', 'CECAL_INT'), id="cecal-int-neg")
        ],
        scope='class'
    )
    def test_cecal_intubation(self, report, doc, ents, expected):
        assert expected in ents

    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(colo_report, 'cecum', id="extent-cecum"),
            pytest.param(colo_prep_report, 'terminal ileum', id="extent-other"),
        ],
        scope='class'
    )
    def test_exam_extent(self, report, doc, expected):
        section_span = extract_section_span(doc, 'section_EXT')
        section_text = section_span.text.lower().strip()
        assert expected == section_text

    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(colo_report, ('Unable to complete colonoscopy', 'INCOMPLETE_PROC'), id="incomp-1"),
            pytest.param(colo_report, ('Incomplete colonoscopy', 'INCOMPLETE_PROC'), id="incomp-2"),
            pytest.param(colo_report, ('Incomplete procedure', 'INCOMPLETE_PROC'), id="incomp-3"),
            pytest.param(colo_report, ('Colonoscopy was incomplete', 'INCOMPLETE_PROC'), id="incomp-4"),
            pytest.param(colo_report, ('cecum could not be reached', 'INCOMPLETE_PROC'), id="incomp-5")
        ],
        scope='class'
    )
    # A colonoscopy is considered incomplete if the cecum was not reached
    def test_incomplete_proc(self, report, ents, expected):
        assert expected in ents


class TestWithdrawalTime:
    @pytest.fixture(scope='class')
    def doc(self, report, ruler, pipeline):
        Doc.set_extension('section_header_list', getter=get_section_header_list, force=True)
        doc = pipeline(report)
        print(doc._.section_header_list)
        return doc

    @pytest.fixture(scope='class')
    def ents(self, doc):
        return [(ent.text, ent.label_) for ent in doc.ents]
        # return doc.ents

    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(colo_report, '00:19:55', id="withdrawal-time-section"),
            # pytest.param(colo_prep_report, '', id="withdrawal-time-empty"),
        ],
        scope='class'
    )
    def test_withdrawal_time_section(self, report, doc, ents, expected):
        section_span = extract_section_span(doc, 'section_WITHDRAWAL_TIME')
        section_text = section_span.text.lower().strip()
        assert expected == section_text
        time_min, time_sec = extract_withdrawal_time(doc)
        # assert 19.0 == extract_withdrawal_time(doc)[0]
        assert 19.0 == time_min
        assert 55.0 == time_sec

    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(colo_prep_report,
                         ('withdrawal time was 6 minutes', 'WITHDRAWAL_TIME'),
                         id="withdrawal-time-sentence"),
        ],
        scope='class'
    )
    def test_withdrawal_time_sentence(self, report, doc, ents, expected):
        assert 6.0 == extract_withdrawal_time(doc)[0]
        assert expected in ents

    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(colo_prep_report, ('Withdrawal time: 15:21', 'WITHDRAWAL_TIME'), id="withdrawal-time"),
        ],
        scope='class'
    )
    def test_withdrawal_time(self, report, ents, expected):
        assert expected in ents


class TestSectionHeaders:
    @pytest.fixture(scope='class')
    def ents(self, report, ruler, pipeline):
        doc = pipeline(report)
        return [(ent.text, ent.label_) for ent in doc.ents]

    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(colo_report, ('VISUALIZATION:', 'SECTION_HEADER'), id="section-vis"),
            pytest.param(colo_report, ('EXTENT OF EXAM:', 'SECTION_HEADER'), id="section-extent"),
            pytest.param(colo_report, ('TOTAL WITHDRAWL TIME:', 'SECTION_HEADER'), id="section-with-time"),
            pytest.param(colo_report, ('INDICATIONS FOR EXAMINATION:', 'SECTION_HEADER'), id="section-ind"),
            pytest.param(colo_report, ('PROCEDURE PERFORMED:', 'SECTION_HEADER'), id="section-proc"),
            pytest.param(colo_report, ('SEDATION START:', 'SECTION_HEADER'), id="section-sedation"),
        ],
        scope='class'
    )
    def test_section_headers(self, report, ents, expected):
        assert expected in ents


class TestSectionExtraction:
    @pytest.fixture(scope='class')
    def doc(self, ruler, pipeline):
        Doc.set_extension('section_header_list', getter=get_section_header_list, force=True)
        doc = pipeline(colo_report)
        return doc

    @pytest.mark.parametrize(
        'report,section_id,expected',
        [
            pytest.param(colo_report, 'section_IND', 'Screening Colonoscopy.', id="section-indications"),
            pytest.param(colo_report, 'section_WITHDRAWAL_TIME', '00:19:55', id="section-withdrawal"),
            pytest.param(colo_report, 'section_EXT', 'cecum', id="section-extent")
        ],
        scope='class'
    )
    def test_section_extraction(self, report, section_id, doc, expected):
        section_span = extract_section_span(doc, section_id)
        section_text = section_span.text.strip()
        assert section_text == expected


class TestRetainedPolyp:
    @pytest.fixture(scope='class')
    def doc(self, report, ruler, pipeline):
        doc = pipeline(report)
        return doc

    @pytest.fixture(scope='class')
    def ents(self, doc):
        return [(ent.text, ent.label_) for ent in doc.ents]

    @pytest.mark.parametrize(
        'report,expected',
        [
            pytest.param(colo_report, ('unable to remove', 'RETAINED_POLYP'), id="retained-polyp-1"),
            pytest.param(colo_report, ('Resection not attempted', 'RETAINED_POLYP'), id="retained-polyp-2"),
            pytest.param(colo_report, ('could not be removed', 'RETAINED_POLYP'), id="retained-polyp-3")
        ],
        scope='class'
    )
    def test_retained_polyp(self, report, doc, ents, expected):
        assert expected in ents
        assert has_retained_polyp(doc) == True


class TestRemovedPiecemeal:
    pass


class TestProcedureType:
    @pytest.fixture(scope='class')
    def ents(self, ruler, pipeline):
        doc = pipeline(colo_report)
        return [(ent.text, ent.label_, ent.ent_id_) for ent in doc.ents]

    @pytest.mark.parametrize(
        'expected',
        [
            pytest.param(('biopsied', 'POLYP_PROC', 'proc_biopsy_taken'), id="proc-biopsy-taken")
        ],
        scope='class'
    )
    def test_biopsy(self, ents, expected):
        assert expected in ents


class TestVisualization:
    @pytest.fixture(scope='class')
    def doc(self, ruler, pipeline):
        Doc.set_extension('section_header_list', getter=get_section_header_list, force=True)
        doc = pipeline(colo_report)
        return doc

    def test_visualization_section(self, doc):
        section_span = extract_section_span(doc, 'section_VIS')
        section_text = section_span.text.lower().strip()
        assert section_text == 'good'
