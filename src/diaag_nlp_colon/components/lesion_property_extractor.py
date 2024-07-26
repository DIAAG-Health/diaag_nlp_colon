# Custom component to extract values from polyp entities and add to doc data
import re
from spacy.language import Language
from diaag_nlp_colon.components import false_pos_filter
from diaag_nlp_colon.config.num_words import num_words
from diaag_nlp_colon.config.colon import vocab

# region colon polyp extractors


@Language.component("polyp_property_extractor_path")
def polyp_property_extractor_path(doc):
    if not doc._.col_related:
        doc.ents = []
        doc.user_data['polyps'] = []
        return doc
    if not doc._.has_props:
        doc.user_data['polyps'] = []
        return doc

    doc_polyps = []
    polyp = {
        'cyt_dysplasia': '',
        'hg_dysplasia': '',
        'histology': '',
        'location': '',
        'sample': False
    }

    # handle case where there is no regex sample but there's still a sample
    has_sample_regex = any([t.ent_type_ == 'POLYP_SAMPLE_REGEX' for t in doc])
    if not has_sample_regex:
        hist_regex = r'(' + ')|('.join(vocab.HIST_TYPES) + r')'
        hist_match = re.search(hist_regex, doc.text, re.IGNORECASE)
        if hist_match:
            polyp['sample'] = True
            doc_polyps.append(polyp)

    # example for alternate report format: POLYP_SAMPLE_REGEX_ALT
    # e.g. (BIOPSY A): or (SNARE POLYPECTOMY A): or (SNARE POLYPECTOMY AND BIOPSY A):
    # if any of those ents: add new polyp on LOCATION (rather than regex sample) or HIST (same)

    for ent in doc.ents:
        if ent.label_ == 'POLYP_SAMPLE_REGEX':
            # check for H. Pylori false positive
            token = doc[ent.start]
            next_token = doc[ent.end: ent.end + 1]
            if next_token and 'pylori' in next_token.text.lower():
                token._.set('is_false_pos', True)
                continue
            # Move on to new polyp
            polyp = {
                'cyt_dysplasia': '',
                'hg_dysplasia': '',
                'histology': '',
                'location': '',
                'sample': False
            }
            doc_polyps.append(polyp)
        elif ent.label_ == 'POLYP_SAMPLE':
            polyp['sample'] = True
        elif ent.label_ == 'POLYP_LOC':
            polyp['location'] = ent.text.lower()
        elif ent.label_ == 'POLYP_HIST':
            hist = ent.text.lower()
            # treating multiple hist types in one sample as multiple observations
            # Move on to new polyp
            if polyp['histology']:
                polyp = polyp.copy()
                doc_polyps.append(polyp)
            polyp['histology'] = get_hist(hist)
        elif ent.label_ == 'POLYP_HG_DYSPLASIA':
            hist = polyp['histology']
            # TODO fix dysplasia entity labels/ids
            neg = re.search(r'(no)|(negative)', ent.text, re.IGNORECASE)
            # sessile serrated polyps can only have cytologic dysplasia
            # (correcting NER error)
            if not hist:
                # probably normal, colonic mucosa
                polyp['hg_dysplasia'] = 'no' if neg else 'yes'
            elif hist and hist.lower() == 'sessile serrated':
                cyt = 'no' if neg else 'yes'
                polyp['cyt_dysplasia'] = cyt
                polyp['hg_dysplasia'] = ''
            else:
                hgd = 'no' if neg else 'yes'
                polyp['hg_dysplasia'] = hgd
                polyp['cyt_dysplasia'] = ''
        elif ent.label_ == 'POLYP_CYT_DYSPLASIA':
            if 'cytologic' not in ent.text.lower():
                token = doc[ent.start]
                token._.set('is_false_pos', True)
                continue
            hist = polyp['histology']
            neg = re.search(r'(no)|(negative)', ent.text, re.IGNORECASE)
            # (correcting NER error)
            if not hist:
                polyp['hg_dysplasia'] = 'no' if neg else 'yes'
            elif 'sessile serrated' not in hist.lower():
                hgd = 'no' if neg else 'yes'
                polyp['hg_dysplasia'] = hgd
                polyp['cyt_dysplasia'] = ''
            else:
                cyt = 'no' if neg else 'yes'
                polyp['cyt_dysplasia'] = cyt
                polyp['hg_dysplasia'] = ''

    # filter out empty polyp objects
    # also filters non-polyp biopsy/tissue samples included in pathology report
    doc_polyps = [p for p in doc_polyps if p['sample'] or p['histology']]
    # TODO: If there are a lot of empty polyp obs in the db, we should try adding this 'location' condition
    # doc_polyps = [p for p in doc_polyps if (p['sample'] and p['location']) or p['histology']]

    # add to user_data storage of doc
    doc.user_data['polyps'] = doc_polyps[:]

    return false_pos_filter.remove_false_pos(doc)


@Language.component("polyp_property_extractor_col")
def polyp_property_extractor_col(doc):
    if not doc._.col_related:
        doc.ents = []
        doc.user_data['polyps'] = []
        return doc

    doc_polyps = []
    doc_prop_vals = {'doc_quant': 0, 'max_size': 0}
    for sent in doc.sents:
        if not sent._.has_sample or not sent._.has_props:
            continue
        polyp = {
            'location': '',
            'morphology': '',
            'quantity': None,
            'quantity_approx': '',
            'size_meas': None,
            'size_approx': '',
            'multi': False,
            'retained': False
        }
        # if there are multiple polyp sizes or locations in the sentence, we should have multiple polyps/obs
        multi_loc = False
        multi_size = False
        if sent._.loc_count > 1:
            multi_loc = True
            polyp['multi'] = True
        elif sent._.size_meas_count > 1:
            multi_size = True
            polyp['multi'] = True
        for ent in sent.ents:
            if ent.label_ == 'POLYP_LOC':
                polyp['location'] = ent.text
                if multi_loc:
                    # if we see a **location** then we're done with current polyp
                    doc_polyps.append(polyp)
                    # should create a **copy without quantity**
                    polyp = polyp.copy()
                    polyp['quantity'] = None
                    polyp['quantity_approx'] = None
                    polyp['retained'] = False
                    # **backpropagate location** to prev polyps (if None)
                    for prev_polyp in doc_polyps:
                        if not prev_polyp['location']:
                            prev_polyp['location'] = ent.text
            elif ent.label_ == 'POLYP_MORPH':
                polyp['morphology'] = ent.text
            elif ent.label_ == 'POLYP_QUANT':
                quant = extract_quantity(ent)
                if not quant:
                    print('In property extraction: could not extract quantity from ent:', ent)
                elif type(quant) is str:
                    polyp['quantity_approx'] = quant
                else:
                    polyp['quantity'] = quant
                    # add to total quantity
                    doc_prop_vals['doc_quant'] += quant
            elif ent.label_ == 'POLYP_SIZE_MEAS':
                size = extract_size_meas(ent)
                max_size = doc_prop_vals['max_size']
                if size:
                    # large sizes are probably false positives
                    if size > 8:
                        token = doc[ent.start]
                        token._.set('is_false_pos', True)
                        continue
                    if size >= 1.0:
                        doc._.set('has_large_polyp', True)
                    polyp['size_meas'] = size
                    # track max size
                    if not max_size or size > max_size:
                        doc_prop_vals['max_size'] = size
                    if multi_size:
                        # if we see a **measured size** then we're done with current polyp
                        doc_polyps.append(polyp)
                        # should create a **copy without quantity**
                        polyp = polyp.copy()
                        polyp['quantity'] = None
                        polyp['quantity_approx'] = None
                        # **backpropagate location** to prev polyps (if None)
                        for prev_polyp in doc_polyps:
                            if not prev_polyp['location'] and polyp['location']:
                                prev_polyp['location'] = polyp['location']
            elif ent.label_ == 'POLYP_SIZE_NONSPEC':
                polyp['size_approx'] = ent.text.lower()
                if ent.text.lower() in ['large', 'giant', 'huge']:
                    doc._.set('has_large_polyp', True)
            elif ent.label_ == 'POLYP_PROC' and ent.ent_id_ == 'proc_biopsy_taken':
                polyp['retained'] = True
                doc._.set('has_retained_polyp', True)
            elif ent.label_ == 'RETAINED_POLYP':
                polyp['retained'] = True
                doc._.set('has_retained_polyp', True)

        if not multi_loc and not multi_size:
            doc_polyps.append(polyp)

    # add to user_data storage of doc
    doc.user_data['polyps'] = doc_polyps[:]
    doc.user_data['prop_vals'] = doc_prop_vals

    return false_pos_filter.remove_false_pos(doc)


# endregion


# region colon helper functions

# extract 'A' from 'A.' or 'Part A'
def extract_path_sample(ent, doc):
    path_sample_regex = r'[A-Z](\.|,|-)?'
    sample_str = ent.text
    sample = None
    if doc[ent.start].text == 'Part':
        sample_str = doc[ent.start + 1:ent.end].text
    match = re.search(path_sample_regex, sample_str)
    if match:
        match = match.group()
        sample = re.search(r'\w', match).group()
    return sample


# standardize histology vocabulary
# (or just return ent text if no matches)
def get_hist(hist):
    for keyword in vocab.HIST_TYPES.keys():
        if keyword in hist:
            return vocab.HIST_TYPES[keyword]
    return hist


def get_cyt_dysplasia(ent):
    if ent.ent_id_ == 'cyt_dys_no':
        return 'no'
    elif ent.ent_id_ == 'cyt_dys_low':
        return 'low'
    elif ent.ent_id_ == 'cyt_dys_high':
        return 'high'


# endregion

# region general helper functions


# get largest size in cm
def extract_size_meas(ent):
    sizes = []
    matches = re.findall(r'\d[.]?\d?', ent.text)
    if matches:
        sizes = [float(i) for i in matches]
    if 'mm' in ent.text.lower() or 'millimeters' in ent.text.lower():
        sizes = [size / 10 for size in sizes]
    if len(sizes) == 0:
        print('In property extraction: no measurement found in str:', ent)
        return None
    return sorted(sizes, reverse=True)[0]


# extract up to 3 measurements from lesion size entity
def extract_dimensions(ent):
    sizes = []
    matches = re.findall(r'\d[.]?\d?', ent.text)
    if matches:
        sizes = [int(float(i)) for i in matches]
    if len(sizes) == 0:
        print('In property extraction: no measurement found in str:', ent)
    if len(sizes) < 3:
        sizes.extend([None for i in range(3 - len(sizes))])
    return sizes[:3]


# get value from quantity label
# "One" or "x1" --> 1
# "multiple", "a", etc
def extract_quantity(ent):
    quant = None
    # number ("1")
    matches = re.findall(r'\d+', ent.text)
    if matches:
        num_matches = sorted([int(i) for i in matches], reverse=True)
        quant = num_matches[0]
    # word for number ("one", "twenty two")
    elif any(t.like_num for t in ent):
        num_words_dict = {}
        for idx, word in enumerate(num_words):
            num_words_dict[word] = idx
        num_str = ' '.join([t.lower_ for t in ent if t.like_num])
        if num_str not in num_words_dict:
            print('In property extraction: no matching number for', num_str)
        else:
            quant = num_words_dict[num_str]
    # specific word for number ("single", "a")
    elif ent.text.lower() in ['single', 'a']:
        quant = 1
    # nonspecific number ("multiple", "many") <- Do not currently translate into integer quantity
    else:
        print('In property extraction: suspicious quantity ent:', ent.text)
        quant = ent.text
    return quant


def str_is_digit(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

# endregion
