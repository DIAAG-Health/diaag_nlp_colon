DISPLACY_RENDER_OPTIONS = {
    "col": {
        "ents": [
            "POLYP_SAMPLE",
            "POLYP_SIZE_MEAS",
            "POLYP_SIZE_NONSPEC",
            "POLYP_LOC",
            "POLYP_MORPH",
            "POLYP_QUANT",
            "POLYP_PROC",
            # "COMPLICATION",
            "SECTION_HEADER",
            "PREP_QUALITY",
            "INCOMPLETE_PROC",
            "RETAINED_POLYP",
            "CECAL_INT",
            "WITHDRAWAL_TIME"
        ],
        "colors": {
            "POLYP_SAMPLE": "#f6316094",
            "POLYP_SIZE_MEAS": "#ff5722c4",
            "POLYP_SIZE_NONSPEC": "#43c6fc",
            "POLYP_LOC": "#a06cd5",
            "POLYP_QUANT": "#4D8DE0",
            "POLYP_MORPH": "#5ae22d",
            "POLYP_PROC": "#ffcc00",
            # "COMPLICATION": "#fe4238",
            "SECTION_HEADER": "lightgrey",
            "PREP_QUALITY": "yellow",
            "INCOMPLETE_PROC": "yellow",
            "RETAINED_POLYP": "yellow",
            "CECAL_INT": "gold",
            "WITHDRAWAL_TIME": "gold"
        }
    },
    "col_err": {
        "ents": [
            # "POLYP_QUANT",
            # "POLYP_LOC",
            "POLYP_LOC_FP",
            "POLYP_LOC_FN",
            "POLYP_QUANT_FP",
            "POLYP_QUANT_FN",
            "POLYP_SIZE_MEAS_FP",
            "POLYP_SIZE_NONSPEC_FP",
            "POLYP_MORPH_FP",
        ],
        "colors": {
            # "POLYP_QUANT": "lightgreen",
            # "POLYP_LOC": "lightgreen",
            "POLYP_LOC_FP": "gold",
            "POLYP_LOC_FN": "darkorange",
            "POLYP_QUANT_FP": "gold",
            "POLYP_QUANT_FN": "darkorange",
            "POLYP_SIZE_MEAS_FP": "gold",
            "POLYP_SIZE_NONSPEC_FP": "gold",
            "POLYP_MORPH_FP": "gold"
        }
    },
    "path": {
        "ents": [
            "POLYP_SAMPLE",
            "POLYP_SAMPLE_REGEX",
            "POLYP_SIZE_MEAS",
            "POLYP_QUANT",
            "POLYP_LOC",
            "POLYP_HIST",
            "POLYP_HG_DYSPLASIA",
            "POLYP_CYT_DYSPLASIA",
            "SECTION_HEADER"
        ],
        "colors": {
            "POLYP_SAMPLE": "#f6316094",
            "POLYP_SAMPLE_REGEX": "lightgrey",
            "POLYP_SIZE_MEAS": "#ff5722c4",
            "POLYP_QUANT": "#fe4238",
            "POLYP_LOC": "#a06cd5",
            "POLYP_HIST": "#43c6fc",
            "POLYP_HG_DYSPLASIA": "#5ae22d",
            "POLYP_CYT_DYSPLASIA": "#ffcc00",
            "SECTION_HEADER": "lightgrey"
        }
    },
    "path_err": {
        "ents": [
            # "POLYP_QUANT",
            # "POLYP_LOC",
            "POLYP_LOC_FP",
            "POLYP_LOC_FN",
            "POLYP_QUANT_FP",
            "POLYP_QUANT_FN",
            "POLYP_SIZE_MEAS_FP",
            "POLYP_HIST_FP",
            "POLYP_HG_DYSPLASIA_FP",
            "POLYP_CYT_DYSPLASIA_FP"
        ],
        "colors": {
            # "POLYP_QUANT": "#fe4238",
            # "POLYP_LOC": "#a06cd5",
            "POLYP_LOC_FP": "cornflowerblue",
            "POLYP_LOC_FN": "lightblue",
            "POLYP_QUANT_FP": "deeppink",
            "POLYP_QUANT_FN": "lightpink",
            "POLYP_SIZE_MEAS_FP": "lightgrey",
            "POLYP_HIST_FP": "lightgrey",
            "POLYP_HG_DYSPLASIA_FP": "lightgrey",
            "POLYP_CYT_DYSPLASIA_FP": "lightgrey",
        }
    }
}
