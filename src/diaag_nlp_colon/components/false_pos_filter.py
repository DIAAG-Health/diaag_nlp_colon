import re
from spacy.language import Language

# Component to correct common NER errors using token context


# remove entity Spans that contain a Token marked as a false positive
@Language.component("remove_false_pos")
def remove_false_pos(doc):
    doc.ents = [ent for ent in doc.ents if not ent._.has_false_pos]
    return doc


# remove location/size false positives, e.g. 'COLON AT 15 cm'
@Language.component("mark_size_false_pos")
def mark_size_false_pos(doc):
    col_next_fps = ['snare', 'snares', 'number', 'quantity', 'amount',
                    'clots', 'above', 'round', 'long', 'hiatal', 'erosions',
                    'sec', 'second', 'area', 'from', 'circumference']
    col_prev_fps = ['at', 'first', 'distal']
    size_meas_regex = r'(centimeter|cm)|(mil?limeter|mm)'
    report_type = doc._.get('report_type')
    try:
        test = doc.ents
    except ValueError:
        print('Error getting doc.ents')
        doc.ents = []
        return doc
    for ent in doc.ents:
        token = doc[ent.start]
        prev_token = doc[ent.start - 1: ent.start]
        next_token = doc[ent.end: ent.end + 1]
        ent_context = doc[ent.start - 2: ent.end + 3]

        if ent.label_ == 'POLYP_SIZE_MEAS':
            next_next_token = doc[ent.end + 1:ent.end + 2]
            if prev_token and prev_token.text.lower() in col_prev_fps:
                token._.set('is_false_pos', True)
            if next_token and next_token.text.lower() in col_next_fps:
                token._.set('is_false_pos', True)
            # Checking text of the 3 tokens after ent
            following_text = doc[ent.end:ent.end + 4].text.lower()
            if following_text and any([fp in following_text for fp in ['boston', 'scientific', 'circumference']]):
                token._.set('is_false_pos', True)
            # measurement check - if the units are not cm or mm, mark as FP
            # NOTE: this filters too much out for Pathology
            if report_type == 'col':
                size_units_match = re.search(size_meas_regex, doc[ent.start: ent.end + 3].text, re.IGNORECASE)
                if not size_units_match:
                    # print('no units - found false positive size meas: {} {} {}'.format(prev_token.text, ent.text,
                    #                                                                    doc[ent.end:ent.end + 5]))
                    token._.set('is_false_pos', True)
                if next_token.text.lower() == 'biopsy' and next_next_token.text.lower() == 'forceps':
                    token._.set('is_false_pos', True)
            # ulcer check
            if mentions_ulcer(ent_context.text):
                token._.set('is_false_pos', True)

        if ent.label_ == 'POLYP_SIZE_NONSPEC':
            if prev_token and prev_token.text.lower() == 'no':
                token._.set('is_false_pos', True)
            if next_token and next_token.text.lower() in col_next_fps:
                token._.set('is_false_pos', True)
            # ulcer check
            if mentions_ulcer(ent_context.text):
                token._.set('is_false_pos', True)

    return doc


@Language.component("mentions_ulcer")
def mentions_ulcer(ent_context):
    ulcer_regex = r'ulcer'
    return re.search(ulcer_regex, ent_context, re.IGNORECASE)


# mark quantity false positives for removal
# pathology: "specimen received in two containers" ...
@Language.component("mark_quant_false_pos")
def mark_quant_false_pos(doc):
    path_prev_fps = []
    path_next_fps = ['container', 'containers', 'deeper']
    try:
        test = doc.ents
    except ValueError:
        print('Error getting doc.ents')
        doc.ents = []
        return doc
    for ent in doc.ents:
        if ent.label_ == 'POLYP_QUANT':
            prev_token = doc[ent.start - 1: ent.start]
            next_token = doc[ent.end: ent.end + 1]
            if '#' in ent.text:
                doc[ent.start]._.set('is_false_pos', True)
            if prev_token and prev_token.text.lower() in path_prev_fps:
                doc[ent.start]._.set('is_false_pos', True)
            if next_token and next_token.text.lower() in path_next_fps:
                doc[ent.start]._.set('is_false_pos', True)
    return doc


# mark quantity false positives for removal
# sometimes size is mistaken for quantity, e.g. 14-mm or 10-15mm polyp
@Language.component("mark_quant_false_pos_col")
def mark_quant_false_pos_col(doc):
    col_next_fps = ['mm', 'cm', 'millimeter', 'centimeter']
    try:
        test = doc.ents
    except ValueError:
        print('Error getting doc.ents')
        doc.ents = []
        return doc
    for ent in doc.ents:
        if ent.label_ == 'POLYP_QUANT':
            context = doc[ent.start: ent.end + 1].text.lower()
            # TODO: test changing the following condition from AND --> OR
            if any([fp in context for fp in col_next_fps]) and not doc[ent.start].like_num:
                print('found false positive quant ent: {}'.format(context))
                doc[ent.start]._.set('is_false_pos', True)
    return doc


# mark location false positives for removal
@Language.component("mark_loc_false_pos")
def mark_loc_false_pos(doc):
    path_prev_fps = ['labelled "', 'designated as']
    try:
        test = doc.ents
    except ValueError:
        print('Error getting doc.ents')
        doc.ents = []
        return doc
    for ent in doc.ents:
        if ent.label_ == 'POLYP_LOC':
            prev_tokens = doc[ent.start - 2: ent.start]
            if any([fp in prev_tokens.text for fp in path_prev_fps]):
                print('found false positive loc ent: {} {}'.format(prev_tokens.text, ent.text))
                doc[ent.start]._.set('is_false_pos', True)
    return doc


# mark polyp sample false positives for removal
@Language.component("mark_sample_false_pos")
def mark_sample_false_pos(doc):
    try:
        test = doc.ents
    except ValueError:
        print('Error getting doc.ents')
        doc.ents = []
        return doc
    for ent in doc.ents:
        if ent.label_ == 'POLYP_SAMPLE':
            prev_token = doc[ent.start - 1:ent.start]
            prev_tokens = doc[ent.start - 3: ent.start]
            if prev_tokens.text.lower() == 'no evidence of':
                doc[ent.start]._.set('is_false_pos', True)
            if prev_token.text.lower() == 'no':
                doc[ent.start]._.set('is_false_pos', True)
        if ent.label_ == 'SAMPLE':
            if ent[0].lower_ == 'diagnosis':
                doc[ent.start]._.set('is_false_pos', True)

    return doc


# mark malignant histology false positives for removal
@Language.component("mark_malignancy_false_pos")
def mark_malignancy_false_pos(doc):
    for ent in doc.ents:
        if ent.label_ == 'MALIGNANCY':
            prev_tokens = doc[ent.start - 8: ent.start]
            if any(token.lower_ in ['negative', 'no'] for token in prev_tokens):
                doc[ent.start]._.set('is_false_pos', True)
    return doc


@Language.component("mark_proc_false_pos_col")
def mark_proc_false_pos_col(doc):
    for ent in doc.ents:
        next_tokens = doc[ent.end: ent.end + 3]
        prev_tokens = doc[ent.start - 3: ent.start]
        if ent.label_ == 'POLYP_PROC' and ent.ent_id_ == 'proc_biopsy_taken':
            if any(token.lower_ in ['forcep', 'forceps'] for token in next_tokens):
                doc[ent.start]._.set('is_false_pos', True)
            if any(token.lower_ in ['random', 'removed', 'cold'] for token in prev_tokens):
                doc[ent.start]._.set('is_false_pos', True)
    return doc


# Check if lesion described in report is actually from a previous procedure + ignore those entities
@Language.component("filter_previous_breast_lesions")
def filter_previous_breast_lesions(doc):
    previous_les = ['previously seen', 'not visualized', 'not persist', 'additional evaluation', 'follow-up']
    for sent in doc.sents:
        if len(sent.ents) > 0:
            # Skip mentions of lesions seen during previous procedures
            if any([pr in sent.text.lower() for pr in previous_les]):
                doc[sent.start]._.set('prev_lesion', True)
    doc.ents = [ent for ent in doc.ents if not ent.sent._.has_prev_lesion]
    return doc


@Language.component("mark_breast_lesion_false_pos")
def mark_breast_lesion_false_pos(doc):
    fp_vocab = ['benign', 'dense']
    pre_fp = ['likely', 'versus', 'correlate', 'mammographic']
    post_fp = ['correlate', 'mammographic']
    for ent in doc.ents:
        if ent.label_ in ['LESION', 'ASYM', 'CALC']:
            # Check if negation comes before lesion in sentence
            sent = ent.sent
            prec = doc[sent.start: ent.start]
            if any([token.lower_ in ['no'] for token in prec]):
                doc[ent.start]._.set('is_false_pos', True)
            # another negation: "non-mass" (enhancement, etc)
            if doc[ent.start - 2: ent.start].text.lower() == 'non-':
                doc[ent.start]._.set('is_false_pos', True)
            # Filter out known false pos matches
            if any([token.lower_ in fp_vocab for token in ent]):
                doc[ent.start]._.set('is_false_pos', True)
            # Check if notes are referring to a lesion seen on another exam, or estimated lesion type
            if any([token.lower_ in pre_fp for token in doc[ent.start - 5: ent.start]]):
                doc[ent.start]._.set('is_false_pos', True)
            if any([token.lower_ in post_fp for token in doc[ent.end: ent.end + 3]]):
                doc[ent.start]._.set('is_false_pos', True)
    return doc


@Language.component("mark_breast_lesion_size_false_pos")
def mark_breast_lesion_size_false_pos(doc):
    size_ents = [ent for ent in doc.ents if ent.label_ == 'LES_MEAS']
    for ent in size_ents:
        next_tokens = doc[ent.end: ent.end + 3]
        if any([token.lower_ in ["deep", "marker"] for token in next_tokens]):
            doc[ent.start]._.set('is_false_pos', True)
    return doc


# Mark false positive pathology entities for removal
@Language.component("mark_breast_path_false_pos")
def mark_breast_path_false_pos(doc):
    # Ignore entities in comment sections
    for sent in doc.sents:
        if doc[sent.start].ent_id_ == 'section_CM':
            for ent in sent.ents[1:]:
                doc[ent.start]._.set('is_false_pos', True)
    for ent in doc.ents:
        # Ignore entities labelled in "surgical margins" description
        if ent.label_ == 'SURG_MARGINS':
            for ent in doc[ent.end: ent.sent.end].ents:
                doc[ent.start]._.set('is_false_pos', True)
        # Filter out unrelated measurement (sometimes noted with mitotic score)
        if ent.label_ == 'SIZE':
           if doc[ent.end].lower_ in ['field', 'diameter']:
               doc[ent.start]._.set('is_false_pos', True)
           if any(['margin' in token.lower_ for token in ent.sent]):
               doc[ent.start]._.set('is_false_pos', True)
        if ent.label_ == 'HIST':
            if any(token.lower_ in ['negative', 'no', 'not'] for token in ent.sent):
                doc[ent.start]._.set('is_false_pos', True)
        if ent.label_ == 'CLOCK':
            if any(['margin' in token.text for token in ent.sent]):
                doc[ent.start]._.set('is_false_pos', True)
            next_tokens = doc[ent.end: ent.end + 3]
            if any([token.lower_ in ["am", "pm"] for token in next_tokens]):
                doc[ent.start]._.set('is_false_pos', True)
    return doc


@Language.component("mark_prostate_path_false_pos")
def mark_prostate_path_false_pos(doc):
    summary = False
    if doc._.report_type != 'resection':
        return doc
    for ent in doc.ents:
        if ent.ent_id_ == 'section_SR':
            summary = True
        if summary and ent.label_ not in ['WEIGHT', 'STAGING']:
            doc[ent.start]._.set('is_false_pos', True)
    return doc
