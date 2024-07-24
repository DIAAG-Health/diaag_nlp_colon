# Getters for custom property extensions


# returns True if span has any token marked as a false pos
def has_false_positive(tokens):
    return any([t._.get('is_false_pos') for t in tokens])


# returns True if span has a sample entity
def has_sample(tokens):
    return any([t.ent_type_ == 'POLYP_SAMPLE' and not t._.is_false_pos for t in tokens])


# returns True if span has any entity marked as related to a previously seen lesion
def has_prev_lesion(tokens):
    return any([t._.get('prev_lesion') for t in tokens])


# returns number of sample entities (tokens) in span
def sample_count(tokens):
    return len([t for t in tokens if t.ent_type_ == 'POLYP_SAMPLE' and not t._.is_false_pos])


# returns number of location entities in span
def loc_count(span):
    return len([e for e in span.ents if e.label_ == 'POLYP_LOC'])


# returns number of measured size entities in span
def size_meas_count(span):
    return len([e for e in span.ents if e.label_ == 'POLYP_SIZE_MEAS'])


# returns number of nonspecific size entities in span
def size_nonspec_count(span):
    return len([e for e in span.ents if e.label_ == 'POLYP_SIZE_NONSPEC'])


# returns True if span has sample properties
def has_props(tokens):
    return any([t.ent_type_ and t.ent_type_ != 'POLYP_SAMPLE' and not t._.is_false_pos for t in tokens])


# returns True if span has any entities marking malignant pathology samples
def has_malignancy(tokens):
    return any([t.ent_type_ and t.ent_type_ == 'MALIGNANCY' and not t._.is_false_pos for t in tokens])


# returns True if report mentions incomplete procedure
def has_incomplete_proc(doc):
    return any([ent.label_  == 'INCOMPLETE_PROC' for ent in doc.ents])


# returns True if any PREP_QUALITY entity indicates poor or inadequate preparation for exam
def has_poor_prep(doc):
    for ent in doc.ents:
        if ent.label_ == 'PREP_QUALITY':
            if any(token.lower_ in ['poor', 'inadequate'] for token in ent):
                return True
    return False


# True if polyp finding is marked as retained or if the description appears outside of Findings section
def has_retained_polyp_ent(doc):
    return any([ent.label_ == 'RETAINED_POLYP' for ent in doc.ents])


# True if polyp finding is marked as retained or if the description appears outside of Findings section
def has_retained_polyp(doc):
    retained_ent = doc._.has_retained_polyp
    retained_polyp = False
    if 'polyps' in doc.user_data:
        retained_polyp = any([polyp['retained'] for polyp in doc.user_data['polyps']])
    return retained_ent or retained_polyp


# Doc extension getter
# returns list of section header entities
def get_section_headers(doc):
    header_ents = {}
    order = 0
    for ent in doc.ents:
        if ent.label_ == 'SECTION_HEADER':
            header_ents[ent.ent_id_] = (ent, order)
            order += 1
    return header_ents


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


def get_score_PIRADS(doc):
    return max([les.dce_score_PIRADS for les in doc.user_data.get('lesions', [])])


def get_score_UCLA(doc):
    return max([les.dce_score_UCLA for les in doc.user_data.get('lesions', [])])
