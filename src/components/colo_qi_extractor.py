from config.colon import vocab
from components import report_section_filter
from services import prop_getters
from spacy.language import Language
import re

# Component to extract colonoscopy quality indicator variables


# Check quality of colon preparation or views
# Returns worst and best recorded prep qualities
# Returns adequate prep quality T/F/N:
#   True if at least one quality counts as "adequate"
#   False if only inadequate recorded
#   None if no quality recorded
@Language.component("extract_prep_quality")
def extract_prep_quality(doc):
    prep_quality_list = []
    worst_prep = None
    best_prep = None
    # Check for recorded quality of preparation or views
    for ent in doc.ents:
        if ent.label_ == 'PREP_QUALITY':
            for token in ent:
                if token.lower_ in vocab.COL_PREP_QUALITY:
                    prep_quality_list.append(token.lower_)
                    worst_prep, best_prep = check_prep_quality(token.lower_, worst_prep, best_prep)

    # Only use "visualization" report section if there are no other options
    if len(prep_quality_list) == 0:
        extracted_props = doc.user_data.get('extracted_props', {})
        vis_text = extracted_props.get('vis_text')
        if vis_text and vis_text in vocab.COL_PREP_QUALITY:
            prep_quality_list.append(vis_text.lower())
            worst_prep, best_prep = check_prep_quality(vis_text.lower(), worst_prep, best_prep)

    # Adequate if the BEST documented prep quality is adequate
    adequate_prep = True if best_prep in vocab.COL_ADEQUATE_PREP else False

    return (worst_prep, best_prep, adequate_prep)


# Compare current preparation quality to recorded best and worst qualities
@Language.component("check_prep_quality")
def check_prep_quality(prep, worst, best):
    worst = prep if worst is None else worst
    best = prep if best is None else best
    prep_pos = vocab.COL_PREP_QUALITY[prep]
    worst_pos = vocab.COL_PREP_QUALITY[worst]
    best_pos = vocab.COL_PREP_QUALITY[best]
    if prep_pos < best_pos:
        best = prep
    elif prep_pos > worst_pos:
        worst = prep
    return (worst, best)


# Extract withdrawal time from WITHDRAWAL_TIME entity
# Only handles 2 time formats
#   returns withdrawal time in minutes as a Float
#   returns None if no numbers are found in entity
@Language.component("extract_withdrawal_time")
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
    withdrawal_span = report_section_filter.extract_section_span(doc, 'section_WITH_TIME')
    if withdrawal_span and len(withdrawal_span) > 0:
        # Format 2: "TOTAL WITHDRAWL TIME: 00:19:55"
        matches = re.findall(r'\d+', withdrawal_span.text.strip())
        if matches and len(matches) > 2:
            time_vals = [float(i) for i in matches]
            withdrawal_time_min = time_vals[1]
            withdrawal_time_sec = time_vals[2]
    return (withdrawal_time_min, withdrawal_time_sec)


# Check cecal intubation entities
#   returns True if any CECAL_INT entities are positive, or if exam extent = cecum
#   returns False if there's a negative ent and no positive ones, or if exam extent != cecum
#   returns None if there were no CECAL_INT entities
@Language.component("extract_cecal_intubation")
def extract_cecal_intubation(doc):
    # Initialize cecal_int by checking EXTENT_OF_EXAM
    cecal_int = check_exam_extent(doc)
    # Overwrite extent section with any CECAL_INT ents
    for ent in doc.ents:
        if ent.label_ == 'CECAL_INT' and ent.ent_id_ == 'cecal_int_pos':
            cecal_int = True
        elif ent.label_ == 'CECAL_INT' and ent.ent_id_ == 'cecal_int_neg':
            # only set to False if we haven't already seen positive ent
            cecal_int = False if cecal_int is None else cecal_int
        elif ent.label_ == 'INCOMPLETE_PROC' and ent.ent_id_ == 'incomplete_proc_cecum':
            cecal_int = False if cecal_int is None else cecal_int

    return cecal_int


# Extract values for procedure-level properties
# Exam indications, Withdrawal time, Extent of exam, Visualization, Quality of Preparation
@Language.component("extract_col_props")
def extract_col_props(doc):
    # extract report section text
    indications_span = report_section_filter.extract_section_span(doc, 'section_IND')
    withdrawal_span = report_section_filter.extract_section_span(doc, 'section_WITH_TIME')
    extent_span = report_section_filter.extract_section_span(doc, 'section_EXTENT')
    vis_span = report_section_filter.extract_section_span(doc, 'section_VIS')

    # Keys should match ColReport properties
    doc.user_data['extracted_props'] = {
        'indications_text': indications_span.text.strip() if indications_span else None,
        'withdrawal_text': withdrawal_span.text.lower().strip() if withdrawal_span else None,
        'extent_text': extent_span.text.lower().strip() if extent_span else None,
        'vis_text': vis_span.text.lower().strip() if vis_span else None,
        'withdrawal_time_min': None,
        'withdrawal_time_sec': None,
        'prep_quality_worst': None,
        'prep_quality_best': None,
        'ad_prep_quality': None,
        'cecal_int': None
    }

    worst_prep, best_prep, adequate_prep = extract_prep_quality(doc)
    withdrawal_min, withdrawal_sec = extract_withdrawal_time(doc)

    # derive properties from entity text
    doc.user_data['extracted_props']['prep_quality_worst'] = worst_prep
    doc.user_data['extracted_props']['prep_quality_best'] = best_prep
    doc.user_data['extracted_props']['ad_prep_quality'] = adequate_prep
    doc.user_data['extracted_props']['withdrawal_time_min'] = withdrawal_min
    doc.user_data['extracted_props']['withdrawal_time_sec'] = withdrawal_sec
    doc.user_data['extracted_props']['cecal_int'] = extract_cecal_intubation(doc)
    set_review_flags(doc)

    return doc


# Flag reports for manual review, likely <1 year followup
#   Poor preparation quality, Incomplete colonoscopy, Retained polyp
def set_review_flags(doc):
    doc._.set('has_poor_prep', prop_getters.has_poor_prep(doc))
    doc._.set('has_retained_polyp', prop_getters.has_retained_polyp_ent(doc))

    # Flag incomplete procedure if negative pattern match
    incomplete_proc = prop_getters.has_incomplete_proc(doc)
    doc._.set('has_incomplete_proc', incomplete_proc)

    return doc


# Returns True if extent satisfies criteria for "complete" colonoscopy (i.e. cecum reached)
def check_exam_extent(doc):
    extent_text = doc.user_data['extracted_props'].get('extent_text')
    if not extent_text:
        return None
    elif 'cecum' in extent_text.lower():
        return True
    else:
        return False
