from spacy.tokens import Doc, Span, Token
from spacy import displacy
import re

from services import prop_getters
from classes.report import ColReport, PathReport
from config.colon import displacy_configs, col_patterns, path_patterns
from nlp_models import en_trained_sections_col, en_trained_sections_path

# SET SPACY EXTENSIONS
# Doc extensions
Doc.set_extension('col_related', default=True)
Doc.set_extension('has_large_polyp', default=False)
Doc.set_extension('has_poor_prep', default=False)
Doc.set_extension('has_incomplete_proc', default=False)
Doc.set_extension('has_retained_polyp', default=False)
Doc.set_extension('section_headers', getter=prop_getters.get_section_headers)
Doc.set_extension('section_header_list', getter=prop_getters.get_section_header_list)
Doc.set_extension('has_props', getter=prop_getters.has_props)
Doc.set_extension('has_malignancy', getter=prop_getters.has_malignancy)

# Span extensions
# indicator, True if Span contains a Token marked as a false positive
Span.set_extension('has_false_pos', getter=prop_getters.has_false_positive)
Span.set_extension('has_sample', getter=prop_getters.has_sample)
Span.set_extension('sample_count', getter=prop_getters.sample_count)
Span.set_extension('loc_count', getter=prop_getters.loc_count)
Span.set_extension('size_meas_count', getter=prop_getters.size_meas_count)
Span.set_extension('size_nonspec_count', getter=prop_getters.size_nonspec_count)
Span.set_extension('has_props', getter=prop_getters.has_props)

# Token extensions
Token.set_extension('is_false_pos', default=False)


# Runs the colonoscopy report text through the spaCy pipeline
# required param: report text
# returns: ColReport object
def col_pipeline(report_text, to_html=False):
    # Some reports have newlines that cause problems
    if to_html:
        report_text = re.sub(r'[\r\n]+', r' \r\n ', report_text)
    else:
        report_text = re.sub(r'[\r\n]+', ' ', report_text)

    Doc.set_extension('report_type', default='col', force=True)

    # IMPORT MODEL
    nlp = en_trained_sections_col.load()

    # BUILD PIPELINE

    # add col keyword filter to pipeline
    nlp.add_pipe("col_keyword_filter", first=True)

    # add colonoscopy entity ruler for rule-based entities
    col_ruler = nlp.add_pipe("entity_ruler", config={"overwrite_ents": True})
    col_ruler.add_patterns(col_patterns.header_patterns)
    col_ruler.add_patterns(col_patterns.polyp_patterns)
    col_ruler.add_patterns(col_patterns.metrics_patterns)

    # Scan entire report text for review flags
    # mark and remove entities that are in or before Indication section, likely false pos
    nlp.add_pipe("filter_outside_properties_col")

    # Extract procedure-level properties, add to user_data, set review flags
    # including indications, exam extent, withdrawal time, and visualization section text
    nlp.add_pipe("extract_col_props")

    # filter doc, only grab relevant report section(s)
    nlp.add_pipe("extract_relevant_sections_col")

    # flag location / size false positives
    nlp.add_pipe("mark_size_false_pos")

    # flag sample false positives
    nlp.add_pipe("mark_sample_false_pos")

    # flag quantity false positives
    nlp.add_pipe("mark_quant_false_pos_col")

    # flag procedure false positives
    nlp.add_pipe("mark_proc_false_pos_col")

    # remove false positive entities
    nlp.add_pipe("remove_false_pos")

    # get doc's sentences to distinguish polyps
    nlp.add_pipe("sentencizer")

    # add component to extract polyp data from entities
    # group them into polyp objects and add to doc.user_data
    nlp.add_pipe("polyp_property_extractor_col")

    # RUN PIPELINE
    doc = nlp(report_text)

    # SET REPORT PROPERTIES
    extracted_props = doc.user_data.get('extracted_props', {})
    report = ColReport(doc.text, **extracted_props)

    # Computed properties
    total_indiv_polyps = 0
    doc_polyps = doc.user_data.get('polyps', [])
    if len(doc_polyps) > 0:
        # Estimate total number of individual polyps
        quant_sum = sum([p['quantity'] for p in doc_polyps if p['quantity']])
        if quant_sum == 0:
            quant_less_obs = len([p for p in doc_polyps if not p['quantity']])
        else:
            quant_less_obs = len([p for p in doc_polyps if (not p['quantity'] and not p['multi'])])
        total_indiv_polyps = quant_less_obs + quant_sum

    report.polyps = doc_polyps
    report.total_polyps = total_indiv_polyps
    report.large_polyp = doc._.has_large_polyp
    report.col_related = doc._.col_related

    # Manual review flags, potential <1 year follow-up
    report.review_flags['incomplete_proc'] = doc._.has_incomplete_proc
    report.review_flags['poor_prep'] = doc._.has_poor_prep
    report.review_flags['retained_polyp'] = prop_getters.has_retained_polyp(doc)
    if total_indiv_polyps > 10:
        report.review_flags['many_polyps'] = True

    if to_html:
        doc.user_data['title'] = 'Colonoscopy Report Findings:'
        options = displacy_configs.DISPLACY_RENDER_OPTIONS['col']
        return displacy.render(doc, style='ent', page=True, minify=True, options=options)
    else:
        return report


# Runs the pathology report text through the spaCy pipeline
# required param: report text
# returns: PathReport object
def path_pipeline(report_text, to_html=False):
    # Some reports have newlines that cause problems
    if to_html:
        report_text = re.sub(r'[\r\n]+', r' \r\n ', report_text)
    else:
        report_text = re.sub(r'[\r\n]+', ' ', report_text)

    Doc.set_extension('report_type', default='path', force=True)

    # IMPORT MODEL
    nlp = en_trained_sections_path.load()

    # BUILD PIPELINE

    # add col keyword filter to pipeline
    # NOTE: When filtered by sections, many gross descriptions do not contain col-related keywords
    nlp.add_pipe("col_keyword_filter", first=True)

    # add entity ruler
    path_ruler = nlp.add_pipe("entity_ruler", config={"overwrite_ents": True})
    path_ruler.add_patterns(path_patterns.header_patterns)
    path_ruler.add_patterns(path_patterns.polyp_patterns)

    # filter doc, only grab relevant report section(s)
    nlp.add_pipe("extract_relevant_sections_path")

    # filter out location / size false positives
    nlp.add_pipe("mark_size_false_pos")

    # filter out quantity false positives
    nlp.add_pipe("mark_quant_false_pos")

    # filter out location false positives
    nlp.add_pipe("mark_loc_false_pos")

    # filter out malignant histology false positives
    nlp.add_pipe("mark_malignancy_false_pos")

    # remove false positive entities
    nlp.add_pipe("remove_false_pos")

    # add component to extract polyp data from entities
    # group them into polyp objects and add to doc.user_data
    nlp.add_pipe("polyp_property_extractor_path")

    # RUN PIPELINE
    doc = nlp(report_text)

    # determine report properties
    report = PathReport(doc.text)
    doc_polyps = doc.user_data.get('polyps', [])

    report.polyps = doc_polyps

    if doc._.has_malignancy:
        report.review_flags['malignancy'] = True

    if to_html:
        doc.user_data['title'] = 'Pathology Report Entities:'
        options = displacy_configs.DISPLACY_RENDER_OPTIONS['path']
        return displacy.render(doc, style='ent', page=True, minify=True, options=options)
    else:
        return report
