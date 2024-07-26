header_patterns = [
    {"label": "SECTION_HEADER",
     "pattern": [{"LOWER": "indications"}, {"TEXT": "FOR", "OP": "?"}, {"TEXT": "EXAMINATION", "OP": "?"}, {"TEXT": ":"}],
     "id": "section_IND"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "procedure"}, {"LOWER": "orders", "OP": "?"}, {"TEXT": ":"}],
     "id": "section_PROC_O"},
    {"label": "SECTION_HEADER", "pattern": [{"TEXT": "PROCEDURE"}, {"TEXT": "PERFORMED"}, {"TEXT": ":"}],
     "id": "section_PROC_P"},
    {"label": "SECTION_HEADER", "pattern": [{"TEXT": "TYPE"}, {"TEXT": "OF"}, {"TEXT": "PROCEDURE"}],
     "id": "section_PROC_T"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "medications"}, {"TEXT": ":"}], "id": "section_MEDS"},
    {"label": "SECTION_HEADER", "pattern": [{"TEXT": "PROCEDURE"}, {"TEXT": "TECHNIQUE"}, {"TEXT": ":"}],
     "id": "section_PROC_TECH"},
    {"label": "SECTION_HEADER", "pattern": [{"TEXT": "Consent"}, {"TEXT": ":"}], "id": "section_CONS"},
    {"label": "SECTION_HEADER",
     "pattern": [{"LOWER": "description"}, {"LOWER": "of"}, {"LOWER": "the"}, {"LOWER": "procedure"}, {"TEXT": ":"}],
     "id": "section_DOTP"},
    {"label": "SECTION_HEADER",
     "pattern": [{"LOWER": "description"}, {"LOWER": "of"}, {"LOWER": "procedure"}, {"TEXT": ":"}], "id": "section_DOP"},
    {"label": "SECTION_HEADER", "pattern": [{"TEXT": "Performed"}, {"TEXT": "By"}, {"TEXT": ":"}], "id": "section_PERF_BY"},
    {"label": "SECTION_HEADER", "pattern": [{"TEXT": "COMPLICATIONS"}, {"TEXT": ":"}], "id": "section_COMP"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "findings"}, {"TEXT": ":"}], "id": "section_FIN"},
    {"label": "SECTION_HEADER", "pattern": [{"TEXT": "DIAGNOSIS"}, {"TEXT": ":"}], "id": "section_DIAG"},
    {"label": "SECTION_HEADER", "pattern": [{"TEXT": "ESTIMATED"}, {"TEXT": "BLOOD"}, {"TEXT": "LOSS"}],
     "id": "section_EBL"},
    {"label": "SECTION_HEADER",
     "pattern": [{"LOWER": "endoscopic", "OP": "?"}, {"LOWER": "impressions"}, {"TEXT": ":"}], "id": "section_IMP"},
    {"label": "SECTION_HEADER",
     "pattern": [{"LOWER": {"IN": ["procedure", "postprocedure"]}}, {"LOWER": "findings"}, {"TEXT": ":"}],
     "id": "section_P_FIN"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "summary"}, {"TEXT": ":"}], "id": "section_SUM"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": {"REGEX": "recommendations?"}}, {"TEXT": ":"}],
     "id": "section_REC"},
    {"label": "SECTION_HEADER", "pattern": [{"TEXT": "BRIEF"}, {"TEXT": "PROCEDURE"}, {"TEXT": "NOTE"}],
     "id": "section_BPN"},
    {"label": "SECTION_HEADER", "pattern": [{"TEXT": "ASSESSMENT"}, {"TEXT": ":"}], "id": "section_ASSESS"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "visualization"}, {"TEXT": ":"}], "id": "section_VIS"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "extent"}, {"LOWER": "of"}, {"LOWER": "exam"},
                                            {"TEXT": ":"}], "id": "section_EXTENT"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "total"}, {"LOWER": {"REGEX": "withdrawa?l"}}, {"LOWER": "time"},
                                            {"TEXT": ":"}], "id": "section_WITH_TIME"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "total"}, {"LOWER": "insertion"}, {"LOWER": "time"},
                                            {"TEXT": ":"}], "id": "section_INS_TIME"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "instruments"}, {"TEXT": ":"}], "id": "section_INST"},
    {"label": "SECTION_HEADER", "pattern": [{"LOWER": "technical"}, {"LOWER": "difficulty"}, {"TEXT": ":"}],
     "id": "section_TECH"},
    {"label": "SECTION_HEADER", "id": "section_SED",
     "pattern": [{"LOWER": "sedation"}, {"LOWER": "start"}, {"TEXT": ":"}]},
]

polyp_patterns = [
    {"label": "POLYP_MORPH", "pattern": [{"LOWER": "pedunculated"}], "id": "morph_pen"},
    {"label": "POLYP_MORPH", "pattern": [{"LOWER": "raised"}], "id": "morph_raised"},
    {"label": "POLYP_MORPH", "pattern": [{"LOWER": "polypoid"}], "id": "morph_pol"},
    {"label": "POLYP_MORPH", "pattern": [{"LOWER": "mushroom"}, {"TEXT": "-", "OP": "?"}, {"LOWER": "like"}],
     "id": "morph_mush"},
    {"label": "POLYP_MORPH", "pattern": [{"LOWER": "broad"}, {"TEXT": "-", "OP": "?"}, {"LOWER": "based"}],
     "id": "morph_broad"},
    {"label": "POLYP_MORPH", "pattern": [{"LOWER": "flat"}], "id": "morph_flat"},
    {"label": "POLYP_MORPH", "pattern": [{"LOWER": "sessile"}], "id": "morph_sessile"},
    {"label": "POLYP_SIZE_MEAS", "pattern": [{"LOWER": {"REGEX": "\\d+-?[cm]m"}}], "id": "size_meas"},
    {"label": "POLYP_SIZE_MEAS", "pattern": [{"IS_DIGIT": True}, {"LOWER": {"IN": ["cm", "mm"]}}]},
    {"label": "POLYP_PROC", "pattern": [{"LOWER": {"IN": ["biopsy", "biopsied"]}}, {"LOWER": "taken", "OP": "?"}],
     "id": "proc_biopsy_taken"}
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
            {"LOWER": {"IN": ["colon", "colonic", "bowel"]}, "OP": "?"}, {"LOWER": {"REGEX": "prep(aration)?"}}
        ]
    },
    {
        "label": "PREP_QUALITY",
        "pattern": [
            {"LOWER": "views"}, {"LOWER": "were"},
            {"LOWER": {"IN": ["poor", "inadequate", "adequate", "fair", "good", "excellent"]}}
        ],
        "id": "views_quality"
    },
    {
        "label": "CECAL_INT",
        "pattern": [
            {"LOWER": "cecum"}, {"LOWER": "was", "OP": "?"}, {"LOWER": {"NOT_IN": ["not"]}, "OP": "?"},
            {"LOWER": {"IN": ["intubated", "visualized", "examined", "confirmed"]}}
        ],
        "id": "cecal_int_pos"
    },
    {
        "label": "CECAL_INT",
        "pattern": [{"LOWER": {"IN": ["advanced", "extended"]}}, {"LOWER": {"IN": ["to", "into"]}},
                    {"LOWER": "the"}, {"LOWER": "cecum"}],
        "id": "cecal_int_pos"
    },
    {
        "label": "CECAL_INT",
        "pattern": [{"LOWER": "cecal", "OP": "?"}, {"LOWER": "intubation"}, {"LOWER": "was"}, {"LOWER": "successful"}],
        "id": "cecal_int_pos"
    },
    {
        "label": "CECAL_INT",
        "pattern": [{"LOWER": "prevented"}, {"LOWER": "cecal"}, {"LOWER": "intubation"}],
        "id": "cecal_int_neg"
    },
    {
        "label": "INCOMPLETE_PROC",
        "pattern": [{"LOWER": "unable"}, {"LOWER": "to"}, {"LOWER": "complete"},
                    {"LOWER": {"IN": ["colonoscopy", "procedure", "exam", "examination"]}}]
    },
    {
        "label": "INCOMPLETE_PROC",
        "pattern": [{"LOWER": "incomplete"}, {"LOWER": {"IN": ["colonoscopy", "procedure", "exam", "examination"]}}]
    },
    {
        "label": "INCOMPLETE_PROC",
        "pattern": [
            {"LOWER": {"IN": ["colonoscopy", "procedure", "exam", "examination"]}}, {"LOWER": "was"},
            {"LOWER": {"IN": ["incomplete", "aborted"]}}
        ]
    },
    {
        "label": "INCOMPLETE_PROC",
        "pattern": [{"LOWER": "cecum"}, {"LOWER": "could"}, {"LOWER": "not"}, {"LOWER": "be"}, {"LOWER": "reached"}],
        "id": "incomplete_proc_cecum"
    },
    {
        "label": "RETAINED_POLYP",
        "pattern": [{"LOWER": "not"}, {"LOWER": {"IN": ["removed", "retrieved"]}}],
        "id": "retained_polyp_prop"
    },
    {
        "label": "RETAINED_POLYP",
        "pattern": [{"LOWER": "unable"}, {"LOWER": "to"}, {"LOWER": "be", "OP": "?"},
                    {"LOWER": {"IN": ["remove", "removed", "retrieve", "retrieved"]}}]
    },
    {
        "label": "RETAINED_POLYP",
        "pattern": [{"LOWER": "resection"}, {"LOWER": "was", "OP": "?"}, {"LOWER": "not"}, {"LOWER": "attempted"}]
    },
    {
        "label": "RETAINED_POLYP",
        "pattern": [{"LOWER": "could"}, {"LOWER": "not"}, {"LOWER": "be", "OP": "?"}, {"LOWER": {"REGEX": "removed?"}}]
    },
    {
        "label": "RETAINED_POLYP",
        "pattern": [{"LOWER": "seen"}, {"LOWER": {"IN": ["and", "but"]}}, {"LOWER": "not"}, {"LOWER": "removed"}]
    },
    {
        "label": "RETAINED_POLYP",
        "pattern": [{"LOWER": "not"}, {"LOWER": "removed"}, {"LOWER": "due"}, {"LOWER": "to"}]
    },
    {
        "label": "WITHDRAWAL_TIME",
        "pattern": [{"LOWER": {"REGEX": "withdrawa?l"}}, {"LOWER": "time"}, {"LOWER": "was", "OP": "?"},
                    {"LIKE_NUM": True}, {"LOWER": "minutes"}]
    },
]
