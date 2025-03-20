from spacy.language import Language
import time
import re

# Pipeline components and functions for tests

COL_PREP_QUALITY = [
    'excellent',
    'good',
    'fair',
    'adequate',
    'inadequate',
    'poor'
]


# remove entity Spans that contain a Token marked as a false positive
@Language.component("remove_false_pos_helper")
def remove_false_pos(doc):
    doc.ents = [ent for ent in doc.ents if not ent._.has_false_pos]
    return doc


# mark malignant histology false positives for removal
@Language.component("mark_malignancy_false_pos_helper")
def mark_malignancy_false_pos(doc):
    try:
        test = doc.ents
    except ValueError:
        print('Error getting doc.ents')
        doc.ents = []
        return doc
    for ent in doc.ents:
        if ent.label_ == 'MALIGNANCY':
            prev_tokens = doc[ent.start - 8: ent.start]
            if any(token.lower_ in ['negative', 'no'] for token in prev_tokens):
                doc[ent.start]._.set('is_false_pos', True)
    return doc


# extract stripped text contents of report section
#   for example, the indications section:
#   INDICATIONS FOR EXAMINATION:      Screening Colonoscopy.
#   function returns "Screening Colonoscopy."
def extract_section_span(doc, section_id):
    section_headers = doc._.get('section_header_list')
    section_start = 0
    section_end = len(doc)

    if len(section_headers) > 0:
        for idx, header_ent in enumerate(section_headers):
            if header_ent.ent_id_ == section_id:
                # section_start = header_ent.start
                section_start = header_ent.end
                if idx < len(section_headers) - 1:
                    section_end = section_headers[idx + 1].start
                else:
                    section_end = len(doc)

    print('Section span:', doc[section_start:section_end])
    return doc[section_start: section_end]


# EXTENSION GETTERS


def has_false_positive(tokens):
    return any([t._.get('is_false_pos') for t in tokens])


# Doc extension getter
# return ordered list of section header ents
def get_section_header_list(doc):
    header_ent_dict = {}
    header_ents = []
    for ent in doc.ents:
        if ent.label_ == 'SECTION_HEADER':
            header_ent_dict[ent.start] = ent
    for start in sorted(header_ent_dict.keys()):
        ent = header_ent_dict[start]
        header_ents.append(ent)
    return header_ents


# returns True if any prep quality entity indicates poor preparation for exam
def has_poor_prep(doc):
    for ent in doc.ents:
        if ent.label_ == 'PREP_QUALITY':
            if any(token.lower_ in ['poor', 'inadequate'] for token in ent):
                return True
    return False


def has_retained_polyp(doc):
    retained_ent = any([ent.label_  == 'RETAINED_POLYP' for ent in doc.ents])
    retained_polyp = False
    if 'polyps' in doc.user_data:
        retained_polyp = any([polyp['retained'] for polyp in doc.user_data['polyps']])
    return retained_ent or retained_polyp


def has_removed_piecemeal(doc):
    has_piecemeal = any([ent.label_ == "REMOVED_PIECEMEAL" for ent in doc.ents])
    return has_piecemeal


# Get preparation quality from entity
def check_prep_quality(prep_span):
    # quality of the preparation was ___
    prep_quality = None
    prep_adequate = None

    for token in prep_span:
        if token.lower_ in COL_PREP_QUALITY:
            prep_quality = token.lower_
    # TODO: can store best and worst documented quality
    if prep_quality in ['excellent', 'good', 'fair', 'adequate']:
        prep_adequate = True
    if prep_quality in ['inadequate', 'poor']:
        prep_adequate = False

    return prep_adequate


def extract_withdrawal_time(doc):
    withdrawal_time_min = None
    withdrawal_time_sec = None
    for ent in doc.ents:
        # Format 1: "Withdrawal time was 6 minutes"
        if ent.label_ == 'WITHDRAWAL_TIME':
            for token in ent:
                if token.is_digit:
                    try:
                        withdrawal_time_min = float(token.lower_)
                    except ValueError:
                        withdrawal_time_min = None
                    break
    withdrawal_span = extract_section_span(doc, 'section_WITHDRAWAL_TIME')[:1]
    print('withdrawal_span:', withdrawal_span)
    if len(withdrawal_span) > 0:
        # Format 2: "TOTAL WITHDRAWL TIME: 00:19:55"
        matches = re.findall(r'\d+', withdrawal_span.text.strip())
        if matches and len(matches) > 1:
            time_vals = [float(i) for i in matches]
            # withdrawal_time = time.strptime(':'.join(times), "%H:%M:%S")
            withdrawal_time_min = time_vals[1]
            withdrawal_time_sec = time_vals[2]
    return (withdrawal_time_min, withdrawal_time_sec)


def extract_pirads_version(doc):
    # pirads_regex = r'pi-rads\s?v\d(\.\d)?'
    version = None
    match = re.search(r'pi-rads\s?v\d(\.\d)?', doc.text, re.IGNORECASE)
    if match:
        match = match.group()
        version = re.search(r'\d(\.\d)?', match).group()
    return version


# find token in volume ent with number and grab text
def extract_volume(ent):
    for token in ent:
        if token.like_num:
            return token.text
    return None


def extract_clock_face_loc(ent):
    clock_vals = []
    for token in ent:
        # 9:00-12:30
        if ':' in token.text:
            clock_vals.append(token.text.replace(':', ''))
        # 1130-130
        elif token.is_digit and len(token) > 2:
            clock_vals.append(token.text)
        # 10 to 11 o'clock
        elif token.is_digit:
            clock_vals.append(token.text + '00')
    return '-'.join(clock_vals)


def mark_breast_lesion_false_pos(doc):
    previous_les = ['previously seen', 'seen on', 'not visualized', 'not persist']
    for ent in doc.ents:
        if ent.label_ in ['LESION', 'ASYM', 'CALC']:
            # Check if negation comes before lesion in sentence
            sent = ent.sent
            prec = doc[sent.start: ent.start]
            if any([token.lower_ in ['no'] for token in prec]):
                doc[ent.start]._.set('is_false_pos', True)
            # Skip mentions of lesions seen during previous procedures
            elif any([pr in sent.text.lower() for pr in previous_les]):
                doc[ent.start]._.set('is_false_pos', True)
    return doc


# Filter out empty/unrelated lesion objects
def filter_breast_lesions(lesions):
    doc_lesions = []
    for lesion in lesions:
        # Skip objects with no lesion type
        if not lesion['les_type']:
            continue
        # Skip objects with lesion (type, asym, or calc) as only property
        elif not any([lesion[prop] for prop in [key for key in lesion.keys() if key not in ['les_type', 'asym', 'calc']]]):
            continue
        else:
            doc_lesions.append(lesion)
    return doc_lesions


# extract up to 3 measurements from lesion size entity
def extract_dimensions(ent):
    sizes = []
    matches = re.findall(r'\d[.]?\d?', ent.text)
    if matches:
        sizes = [float(i) for i in matches]
    if 'mm' in ent.text.lower() or 'millimeters' in ent.text.lower():
        sizes = [size / 10 for size in sizes]
    if len(sizes) == 0:
        print('In property extraction: no measurement found in str:', ent)
    if len(sizes) < 3:
        sizes.extend([None for i in range(3 - len(sizes))])
    return sizes[:3]


def extract_gleason_scores(ent):
    scores = []
    matches = re.findall(r'\d[.]?\d?', ent.text)
    if matches:
        scores = [float(i) for i in matches]
    return scores[:2]
