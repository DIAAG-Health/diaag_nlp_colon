from diaag_nlp_colon.components import false_pos_filter
from spacy.language import Language

# Component to process Docs according to section headers in report text


# Only keep ents in Final Diagnosis section
@Language.component("filter_outside_ents_path")
def filter_outside_ents_path(doc):
    if not doc._.col_related:
        doc.ents = []
        return doc

    section_headers = doc._.get('section_header_list')
    section_start = 0
    section_end = len(doc)

    # if no headers were found, just process entire doc
    if len(section_headers) > 0:
        for idx, header_ent in enumerate(section_headers):
            if header_ent.ent_id_ in ['section_FD']:
                section_start = header_ent.start
                if idx < len(section_headers) - 1:
                    section_end = section_headers[idx + 1].start
                else:
                    section_end = len(doc)
        new_ents = []
        for ent in doc.ents:
            if ent.label_ == 'SECTION_HEADER':
                new_ents.append(ent)
                continue
            if section_start < ent.start < section_end:
                new_ents.append(ent)
        doc.ents = new_ents
    return doc


# helper function to get the next section after final diagnosis and gross description
@Language.component("get_following_sections")
def get_following_sections(doc):
    section_headers = doc._.get('section_headers')
    final_diag, fd_order = section_headers['section_FD']
    gross_desc, gd_order = section_headers['section_GD']
    after_fd = None
    after_gd = None
    for _, tup in section_headers.items():
        ent, pos = tup
        if pos == fd_order + 1:
            after_fd = ent
        if pos == gd_order + 1:
            after_gd = ent
    return after_fd, after_gd


# make new doc with only relevant report sections for pathology
@Language.component("extract_relevant_sections_path")
def extract_relevant_sections_path(doc):
    if not doc._.col_related:
        doc.ents = []
        # doc.user_data['full_report_text'] = doc.text
        return doc

    section_headers = doc._.get('section_header_list')
    section_start = 0
    section_end = len(doc)

    # if no headers were found, just process entire doc
    if len(section_headers) == 0:
        # doc.user_data['full_report_text'] = doc.text
        return doc

    # TODO: review decision to only use first FD section
    if len(section_headers) > 0:
        for idx, header_ent in enumerate(section_headers):
            if header_ent.ent_id_ in ['section_FD']:
                section_start = header_ent.end
                if idx < len(section_headers) - 1:
                    section_end = section_headers[idx + 1].start
                else:
                    section_end = len(doc)
                # Some revised reports have multiple FD sections, only take first
                break

    # turn section into its own doc
    section_span = doc[section_start+1:section_end]
    section_doc = section_span.as_doc()
    section_doc._.set('col_related', True)
    # section_doc.user_data['full_report_text'] = doc.text

    return section_doc


# Only keep ents in Findings or Description of the Procedure sections
@Language.component("filter_outside_ents_col")
def filter_outside_ents_col(doc):
    if not doc._.col_related:
        doc.ents = []
        return doc
    section_headers = doc._.get('section_header_list')
    section_start = 0
    section_end = len(doc)

    # if no headers were found, just process entire doc
    if len(section_headers) > 0:
        for idx, header_ent in enumerate(section_headers):
            if header_ent.ent_id_ in ['section_FIN', 'section_DOTP']:
                section_start = header_ent.start
                if idx < len(section_headers) - 1:
                    section_end = section_headers[idx + 1].start
                else:
                    section_end = len(doc)
        new_ents = []
        for ent in doc.ents:
            if ent.label_ == 'SECTION_HEADER':
                new_ents.append(ent)
                continue
            if section_start < ent.start < section_end:
                new_ents.append(ent)
        doc.ents = new_ents
    return doc


# make new doc with only relevant report sections
@Language.component("extract_relevant_sections_col")
def extract_relevant_sections_col(doc):
    if not doc._.col_related:
        doc.ents = []
        return doc

    section_headers = doc._.get('section_header_list')
    section_start = 0
    section_end = len(doc)

    findings = False
    # if no headers were found, just process entire doc
    if len(section_headers) > 0:
        for idx, header_ent in enumerate(section_headers):
            if header_ent.ent_id_ in ['section_FIN', 'section_DOTP']:
                findings = True
                section_start = header_ent.end
                if idx < len(section_headers) - 1:
                    section_end = section_headers[idx + 1].start
                else:
                    section_end = len(doc)
                # I think the ADDENDUM findings get cut off, should use first findings section
                break

        # use DESCRIPTION OF PROCEDURE section (only if there is no FINDINGS or DOTP section)
        if not findings:
            for idx, header_ent in enumerate(section_headers):
                if header_ent.ent_id == 'section_DOP':
                    section_start = header_ent.end
                    if idx < len(section_headers) - 1:
                        section_end = section_headers[idx + 1].start
                    else:
                        section_end = len(doc)

    try:
        # turn section into its own doc
        section_span = doc[section_start:section_end]
        section_doc = section_span.as_doc()
        # section_doc.user_data['full_report_text'] = doc.text

        # copy over extracted props and flags from original doc
        section_doc._.set('col_related', doc._.col_related)
        section_doc.user_data['extracted_props'] = doc.user_data['extracted_props'].copy()
        section_doc._.set('has_poor_prep', doc._.has_poor_prep)
        section_doc._.set('has_incomplete_proc', doc._.has_incomplete_proc)
        section_doc._.set('has_retained_polyp', doc._.has_retained_polyp)
        section_doc._.set('has_removed_piecemeal', doc._.has_removed_piecemeal)

    except ZeroDivisionError:
        print('Could not make section doc')
        # doc.user_data['full_report_text'] = doc.text
        return doc

    return section_doc


# extract span contents of report section (starting after header ent, ending at next section header)
#   for example, the indications section:
#   INDICATIONS FOR EXAMINATION:      Screening Colonoscopy.
#   function returns span with tokenized string for "Screening Colonoscopy."
@Language.component("extract_section_span")
def extract_section_span(doc, section_id):
    section_headers = doc._.get('section_header_list')
    section_start = 0
    section_end = len(doc)

    # If there are no headers of that type, return empty list
    if not any([ent.ent_id_ == section_id for ent in doc.ents]):
        return None

    if len(section_headers) > 0:
        for idx, header_ent in enumerate(section_headers):
            if header_ent.ent_id_ == section_id:
                section_start = header_ent.end
                if idx < len(section_headers) - 1:
                    section_end = section_headers[idx + 1].start
                else:
                    section_end = len(doc)

    return doc[section_start: section_end]


# remove section labels at end of pipeline
@Language.component("remove_section_ents")
def remove_section_ents(doc):
    doc.ents = [ent for ent in doc.ents if not ent.label_ == 'SECTION_HEADER']
    return doc


# for testing: remove SAMPLE entity labels
@Language.component("remove_sample_ents")
def remove_sample_ents(doc):
    doc.ents = [ent for ent in doc.ents if not ent.label_ == 'POLYP_SAMPLE_REGEX']
    return doc


# Filter out any entities like PREP_QUALITY, INCOMP_PROC, RETAINED_POLYP, that show up before end of Indications section
@Language.component("filter_outside_properties_col")
def filter_outside_properties_col(doc):
    ind_span = extract_section_span(doc, 'section_IND')
    boundary_pos = ind_span.end if ind_span and len(ind_span) > 0 else 0

    for ent in doc.ents:
        if ent.start <= boundary_pos and ent.label_ != 'SECTION_HEADER':
            doc[ent.start]._.set('is_false_pos', True)

    return false_pos_filter.remove_false_pos(doc)


# make new doc with only relevant report sections for prostate MRI
@Language.component("prostate_extract_relevant_sections")
def prostate_extract_relevant_sections(doc):
    section_headers = doc._.get('section_header_list')
    section_start = 0
    section_end = len(doc)

    # if no headers were found, just process entire doc
    if len(section_headers) == 0:
        return doc

    if len(section_headers) > 0:
        for idx, header_ent in enumerate(section_headers):
            if header_ent.ent_id_ in ['section_FIN']:
                section_start = header_ent.end
                if idx < len(section_headers) - 1:
                    section_end = section_headers[idx + 1].start
                else:
                    section_end = len(doc)

    # turn section into its own doc
    section_span = doc[section_start+1:section_end]
    section_doc = section_span.as_doc()

    return section_doc


# make new doc with only relevant report sections for prostate pathology
@Language.component("prostate_path_extract_relevant_sections")
def prostate_path_extract_relevant_sections(doc):
    section_headers = doc._.get('section_header_list')
    section_start = 0
    section_end = len(doc)

    # if no headers were found, just process entire doc
    if len(section_headers) == 0:
        return doc

    if len(section_headers) > 0:
        for idx, header_ent in enumerate(section_headers):
            # Final Diagnosis (Biopsy + Resection) and Synoptic Review/Checklist (Resection)
            if header_ent.ent_id_ in ['section_FD', 'section_SR']:
                if section_start == 0:
                    section_start = header_ent.end
                if idx < len(section_headers) - 1:
                    section_end = section_headers[idx + 1].start
                else:
                    section_end = len(doc)
            if header_ent.ent_id_ == 'section_SA':  # Site Acronyms (Biopsy)
                break

    # turn section into its own doc
    section_span = doc[section_start+1:section_end]
    section_doc = section_span.as_doc()
    section_doc._.set('report_type', doc._.report_type)

    return section_doc


# Use relevant sub-section labels to form "sentences" for easier processing
@Language.component("prostate_assign_sentences")
def prostate_assign_sentences(doc):
    sub_sections = ['TARGET', 'LOCATION', 'LOC_CLOCK', 'LOC_CRANIO', 'DIAMETER', 'CAPSULAR_INV', 'T2_SIGNAL',
                    'DWI_ADC', 'DCE_PERF', 'EN_KIN', 'SUSP_ECE', 'SUSP_NEURO', 'SUSP_SEM', 'SUSP_OVERALL',
                    'PIRADS_SCORE', 'UCLA_SCORE']
    # Add arbitrary sentence boundary to initialize doc.sents
    if len(doc) > 0:
        doc[-1].is_sent_start = True

    # Mark each lesion field as the start of a sentence
    for ent in doc.ents:
        if ent.label_ in sub_sections:
            doc[ent.start].is_sent_start = True

    return doc


# Use relevant sub-section labels to form "sentences" for easier processing
@Language.component("prostate_path_assign_sentences")
def prostate_path_assign_sentences(doc):
    sub_sections = ['SAMPLE_ID', 'SECTION_HEADER', 'CORE_TABLE']
    # Add arbitrary sentence boundary to initialize doc.sents
    if len(doc) > 0:
        doc[-1].is_sent_start = True

    # Mark each lesion field as the start of a sentence
    for ent in doc.ents:
        if ent.label_ in sub_sections and ent.ent_id_ != 'section_FD':
            doc[ent.start].is_sent_start = True

    return doc


# Classify prostate pathology report by checking contents
@Language.component("prostate_classify_path_report")
def prostate_classify_path_report(doc):
    for ent in doc.ents:
        if ent.ent_id_ in ['biopsy_header', 'biopsy_table', 'biopsy_sample']:
            doc._.set('report_type', 'biopsy')
        if ent.ent_id_ in ['resection_sample', 'section_SR']:
            doc._.set('report_type', 'resection')
            break
    return doc


# make new doc with only relevant report sections for breast imaging reports
@Language.component("breast_extract_relevant_sections")
def breast_extract_relevant_sections(doc):
    section_headers = doc._.get('section_header_list')
    section_start = None
    section_end = len(doc)

    # if no headers were found, just process entire doc
    if len(section_headers) == 0:
        return doc

    if len(section_headers) > 0:
        for idx, header_ent in enumerate(section_headers):
            # May need to capture multiple Findings sections (e.g. MM and US)
            if header_ent.ent_id_ in ['section_FIN']:
                section_start = header_ent.start if section_start is None else section_start
                if idx < len(section_headers) - 1:
                    section_end = section_headers[idx + 1].start
                else:
                    pass
            # Stop after first Impression section
            if header_ent.ent_id_ in ['section_IMP']:
                if idx < len(section_headers) - 1:
                    section_end = section_headers[idx + 1].start
                else:
                    section_end = len(doc)
                break

    # turn relevant report sections into a new doc
    section_start = 0 if section_start is None else section_start
    section_span = doc[section_start: section_end]
    section_doc = section_span.as_doc(copy_user_data=True)

    return section_doc


# Classify breast pathology report by checking contents
@Language.component("breast_classify_path_report")
def breast_classify_path_report(doc):
    for ent in doc.ents:
        if ent.ent_id_ in ['biopsy_sample']:
            doc._.set('report_type', 'biopsy')
        if ent.ent_id_ in ['resection_sample']:
            doc._.set('report_type', 'resection')
            break
    return doc


# make new doc with only relevant report sections for breast pathology
@Language.component("breast_path_extract_relevant_sections")
def breast_path_extract_relevant_sections(doc):
    section_headers = doc._.get('section_header_list')
    section_start = 0
    section_end = len(doc)

    # if no headers were found, just process entire doc
    if len(section_headers) == 0:
        return doc

    if len(section_headers) > 0:
        for idx, header_ent in enumerate(section_headers):
            # Final Diagnosis Immunohistochemistry Report
            if header_ent.ent_id_ in ['section_FD', 'section_IHC']:
                if section_start == 0:
                    section_start = header_ent.end
                if idx < len(section_headers) - 1:
                    section_end = section_headers[idx + 1].start
                else:
                    section_end = len(doc)

    # turn section into its own doc
    section_span = doc[section_start+1:section_end]
    section_doc = section_span.as_doc()
    section_doc._.set('report_type', doc._.report_type)

    return section_doc


# Use anchors in text to form "sentences" for easier processing
@Language.component("breast_path_assign_sentences")
def breast_path_assign_sentences(doc):
    # Add arbitrary sentence boundary to initialize doc.sents
    if len(doc) > 0:
        doc[-1].is_sent_start = True

    # Use section headers for general sentence start
    for ent in doc.ents:
        if ent.label_ == 'SECTION_HEADER' or ent.label_ == 'SUB_HEADER':
            doc[ent.start].is_sent_start = True

    # Assign dashes "-" and sample IDs in final diagnosis to sentence starts
    for token in doc:
        # If past final diagnosis section, do not use custom sentence boundaries
        if token.ent_id_ in ['section_CM', 'section_MD', 'section_IHC']:
            break
        if not token.ent_type_ and token.text in ['-', '\\-'] and 'parts' not in [t.lower_ for t in doc[token.i-2:token.i]]:
            doc[token.i].is_sent_start = True
        # Only assign first token of SAMPLE_ID entity as sentence start
        if token.ent_type_ == 'SAMPLE_ID' and token.ent_iob_ == 'B':
            doc[token.i].is_sent_start = True

    return doc


# remove any entities after Findings sections
# (also remove section header ents)
@Language.component("breast_filter_outside_ents")
def breast_filter_outside_ents(doc):
    imp_start = len(doc)
    for ent in doc.ents:
        if ent.ent_id_ == 'section_IMP':
            imp_start = ent.end
    doc.ents = [ent for ent in doc.ents if ent.end <= imp_start and ent.label_ != 'SECTION_HEADER']
    return doc


# Filter out most ents labelled outside of final diagnosis
@Language.component("breast_path_filter_outside_ents")
def breast_path_filter_outside_ents(doc):
    outside_start = len(doc)
    inside_start = 0
    ihc_ents = ['SECTION_HEADER', 'SUB_HEADER', 'ER', 'ER_PERC', 'PGR', 'PGR_PERC', 'HER_IMM', 'HER_IMM_SCORE', 'HER_SITU', 'KI']
    inside_ents = ['SAMPLE_ID', 'SAMPLE', 'PERC_TUMOR', 'SIZE', 'CLOCK', 'DIST_FN']
    for ent in doc.ents:
        if ent.ent_id_ == 'section_FD':
            inside_start = ent.end if inside_start == 0 else inside_start
        # start filtering at microscopic description section
        if ent.ent_id_ == 'section_MD':
            outside_start = ent.end
            break
    doc.ents = [ent for ent in doc.ents if ent.end <= outside_start or ent.label_ not in inside_ents]
    return doc
