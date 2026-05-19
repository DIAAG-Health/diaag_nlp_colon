from diaag_nlp_colon.config.colon import vocab
from diaag_nlp_colon.components import report_section_filter
from diaag_nlp_colon.services import prop_getters
from spacy.language import Language
import re
# import logging
# logging.basicConfig(level=logging.INFO)

# mypkg/pipelines/colon_pipelines.py
# import logging
# logger = logging.getLogger(__name__)  # e.g., 'mypkg.pipelines.colon_pipelines'


# (Optional, good practice for libraries)
# Avoid "No handler found" warnings for users who didn't configure logging:
# logging.getLogger(__name__).addHandler(logging.NullHandler())
# 
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
    ## initialize both variables as false such that the default assumption is prep is good, 
    # following code will check if there are any conditions that would say the prep is bad and change these variables
    text_prep_bad = False
    bbps_bad = False
   
    extracted_props = doc.user_data.get('extracted_props', {})
    bbps_left = extracted_props.get('bbps_left')
    bbps_right = extracted_props.get('bbps_right')
    bbps_transverse = extracted_props.get('bbps_transverse')

    # Check for recorded quality of preparation or views
    for ent in doc.ents:
        if ent.label_ == 'PREP_QUALITY':
            for token in ent:
                if token.lower_ in vocab.COL_PREP_QUALITY:
                    prep_quality_list.append(token.lower_)
                    worst_prep, best_prep = check_prep_quality(token.lower_, worst_prep, best_prep)
    text_prep_bad = (
    (best_prep is not None and best_prep not in vocab.COL_ADEQUATE_PREP) or
    (worst_prep is not None and worst_prep not in vocab.COL_ADEQUATE_PREP)
)
    bbps_complete = (
                bbps_left is not None and
                bbps_right is not None and
                bbps_transverse is not None
            )
    

    bbps_bad = (
        bbps_complete and
        (
            bbps_left < 2 or
            bbps_right < 2 or
            bbps_transverse < 2
        )
    )
    if text_prep_bad or bbps_bad:
        adequate_prep = False
    else:
        adequate_prep = True
    ## Previous logic
    # print("adequate_prep", adequate_prep)
    # print("worst_prep:", worst_prep)
    # print("best prep:", best_prep)
    # REMOVED because the VISUALIZATION section in report is never changed and will always be true.
    # Only use "visualization" report section if there are no other options 
    # if len(prep_quality_list) == 0:
    #     print("Prep list empty")
    #     extracted_props = doc.user_data.get('extracted_props', {})
    #     print("extracted:", extracted_props)
    #     vis_text = extracted_props.get('vis_text')
    #     print("vis_text:", vis_text)
    #     print("check", vis_text in vocab.COL_PREP_QUALITY)
    #     if vis_text and vis_text in vocab.COL_PREP_QUALITY:
    #         print("Entering here??")
    #         prep_quality_list.append(vis_text.lower())
    #         worst_prep, best_prep = check_prep_quality(vis_text.lower(), worst_prep, best_prep)
    #         print("1. worst, best", worst_prep, best_prep)

    # REMOVED : as logic is changed from assuming the prep is inadequate unless proof that it's adequate to assumption that prep is good unless specified otherwise
    # Adequate if the BEST documented prep quality is adequate
    # adequate_prep = True if best_prep in vocab.COL_ADEQUATE_PREP else False
    # adequate_prep = False if (worst_prep in  or bbps_left<2 or bbps_right<2 or bbps_transverse<2) else True

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
       
        text = withdrawal_span.text.lower().strip()
         # NEW: Format 2b: "TOTAL WITHDRAWL TIME: 17 minutes"
        minute_match = re.search(r'(\d+(?:\.\d+)?)\s*minute', text)
        
        if minute_match:

            withdrawal_time_min = float(minute_match.group(1))
            withdrawal_time_sec = None
            # return (withdrawal_time_min, withdrawal_time_sec)
        # Format 2: "TOTAL WITHDRAWL TIME: 00:19:55"
        else: 
            matches = re.findall(r'\d+', text)
            if matches and len(matches) > 2:
                time_vals = [float(i) for i in matches]
                withdrawal_time_min = time_vals[1]
                withdrawal_time_sec = time_vals[2]
            # if 10:00 instead of 00:10:00
            elif matches and len(matches) == 2:
                time_vals = [float(i) for i in matches]
                withdrawal_time_min = time_vals[1]
                withdrawal_time_sec = time_vals[0]
            else:
                withdrawal_time_min = None
                withdrawal_time_sec = None



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

def extract_bbps(text):

    if not text:
        return {
            'bbps_left': None,
            'bbps_right': None,
            'bbps_transverse': None,
            'bbps_total': None,
            'bbps_manual_review': False
        }

    def get_num(pattern, text):
        m = re.search(pattern, text, flags=re.IGNORECASE)
       
        return int(m.group(1)) if m else None
    bbps_left = get_num(r'left\s*:\s*(\d+)', text)
    bbps_right = get_num(r'right\s*:\s*(\d+)', text)
    bbps_transverse = get_num(r'transverse\s*:\s*(\d+)', text)
    bbps_total = get_num(r'total\s*score\s*:\s*(\d+)', text)

    bbps_values = [bbps_left, bbps_right, bbps_transverse]

    # flag: partial presence → manual review
    bbps_manual_review = (
        any(v is not None for v in bbps_values) and
        any(v is None for v in bbps_values)
    )

    out = {
        'bbps_left': bbps_left,
        'bbps_right': bbps_right,
        'bbps_transverse': bbps_transverse,
        'bbps_total': bbps_total,
        'bbps_manual_review': bbps_manual_review
    }

   
    return out
# Extract values for procedure-level properties
# Exam indications, Withdrawal time, Extent of exam, Visualization, Quality of Preparation
@Language.component("extract_col_props")
def extract_col_props(doc):
    # extract report section text
    indications_span = report_section_filter.extract_section_span(doc, 'section_IND')
    withdrawal_span = report_section_filter.extract_section_span(doc, 'section_WITH_TIME')
    extent_span = report_section_filter.extract_section_span(doc, 'section_EXTENT')
    vis_span = report_section_filter.extract_section_span(doc, 'section_VIS')

    vis_text = vis_span.text.lower().strip() if vis_span else None

    # try BBPS from visualization section first, then whole doc
    bbps_data = extract_bbps(doc.text)

    # Keys should match ColReport properties
    doc.user_data['extracted_props'] = {
        'indications_text': indications_span.text.strip() if indications_span else None,
        'withdrawal_text': withdrawal_span.text.lower().strip() if withdrawal_span else None,
        'extent_text': extent_span.text.lower().strip() if extent_span else None,
        'vis_text': vis_text,
        'withdrawal_time_min': None,
        'withdrawal_time_sec': None,
        'prep_quality_worst': None,
        'prep_quality_best': None,
        'ad_prep_quality': None,
        'cecal_int': None,
        'bbps_left': bbps_data['bbps_left'],
        'bbps_right': bbps_data['bbps_right'],
        'bbps_transverse': bbps_data['bbps_transverse'],
        'bbps_total': bbps_data['bbps_total'],
        'bbps_manual_review': bbps_data['bbps_manual_review'],
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
    doc._.set('has_removed_piecemeal', prop_getters.has_removed_piecemeal(doc))
    return doc


# Returns True if extent satisfies criteria for "complete" colonoscopy (i.e. cecum reached)
def check_exam_extent(doc):
    extent_text = doc.user_data['extracted_props'].get('extent_text')
    keywords = ['cecum', 'ileum' , 'terminal ileum']

    if not extent_text:
        return None
    # elif 'cecum' in extent_text.lower():
    elif any(k in extent_text.lower() for k in keywords):
        return True
    else:
        return False
