# Custom component to extract values from polyp entities and add to doc data
import re
from spacy.language import Language
from components import false_pos_filter
from config.num_words import num_words
from config.colon import vocab
from config.prostate import prostate_vocab, prostate_path_vocab
from config.breast import breast_vocab

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


# region prostate lesion extractors


@Language.component("prostate_lesion_extractor")
def prostate_lesion_extractor(doc):
    doc_lesions = []
    lesion = {
        k: v for k, v in prostate_vocab.LESION_PROPS.items()
    }

    for sent in doc.sents:
        # exclude newline at end of sentence
        sent = sent[:-1]
        for ent in sent.ents:
            field = doc[ent.end: sent.end]
            field_text = doc[ent.end: sent.end].text.lower()
            if ent.label_ == 'TARGET':
                lesion = {
                    k: v for k, v in prostate_vocab.LESION_PROPS.items()
                }
                doc_lesions.append(lesion)
                lesion['target_num'] = __extract_number(ent.text)
            elif ent.label_ == 'ROI_NUM':
                lesion['roi_num'] = __extract_number(ent.text)
            elif ent.label_ == 'SLICE_NUM':
                lesion['slice_num'] = __extract_number(ent.text)
            elif ent.label_ == 'VOLUME':
                doc.user_data['prostate_vol'] = __extract_meas(ent)
            elif ent.label_ == 'SUSP_SEM':
                lesion['seminal_ves_susp'] = __extract_first_number(field_text)
            elif ent.label_ == 'SUSP_NEURO':
                lesion['neuro_bund_susp'] = __extract_first_number(field_text)
            elif ent.label_ == 'LOCATION':
                if not lesion['target_num']:
                    # If there is no "Target" then use "Location" as start of next lesion finding
                    lesion = {
                        k: v for k, v in prostate_vocab.LESION_PROPS.items()
                    }
                    doc_lesions.append(lesion)
                # Remove occasional newline characters from quadrant (text field)
                lesion['quadrant'] = field_text.replace('\n', ' ')
                lesion['side'] = __get_vocab_list(field_text, prostate_vocab.LESION_SIDE)
                lesion['location'] = __get_vocab_list(field_text, prostate_vocab.LESION_LOCATION)
                lesion['zone'] = __get_vocab_list(field_text, prostate_vocab.LESION_ZONE)
                lesion['level'] = __get_vocab_list(field_text, prostate_vocab.LESION_LEVEL)
                # additional lesion level rule
                if any([token.lower_ == 'entire' for token in field]):
                    lesion['level'] = ['apex', 'midgland', 'base']
            elif ent.label_ == 'CLOCK_FACE':
                lesion['clock_loc'] = __extract_clock_face_loc(ent)
            elif ent.label_ == 'LOC_CRANIO':
                lesion['apex_loc'] = __extract_number(sent.text)
            elif ent.label_ == 'DIAMETER':
                lesion['size_diam'] = __extract_number(sent.text)
            elif ent.label_ == 'CAPSULAR_INV':
                lesion['capsule_rel'] = __get_vocab_val(field_text, prostate_vocab.LESION_RELATION_TO_CAPSULE)
            elif ent.label_ == 'T2_SIGNAL':
                if lesion['overall_score']:
                    break
                lesion['T2_signal'] = __get_vocab_val(field_text, prostate_vocab.T2_SIGNAL)
                # additional T2 signal rules
                if any([token.lower_ == 'low' or token.lower_ == 'dark' for token in field]):
                    lesion['T2_signal'] = prostate_vocab.T2_SIGNAL['hypointense']
                if any([token.lower_ == 'high' for token in field]):
                    lesion['T2_signal'] = prostate_vocab.T2_SIGNAL['hyperintense']
                lesion['T2_shape'] = __get_vocab_val(field_text, prostate_vocab.T2_SHAPE)
                lesion['T2_margin'] = __get_vocab_val(field_text, prostate_vocab.T2_MARGIN)
                # distinguish between overall UCLA score (default) vs. overall PI-RADS score (if specified)
                t2_scores = __extract_scores(sent)
                if len(t2_scores) > 0:
                    lesion['T2_score'] = t2_scores[0]
                    lesion['T2_score_PIRADS'] = t2_scores[-1] if 'pi-rads' in field_text else ''
            elif ent.label_ == 'DWI_ADC':
                if lesion['overall_score']:
                    break
                lesion['DWI_focal_yn'] = True if any([token.lower_ == 'focal' for token in field]) else None
                signals = __get_vocab_list(field_text, prostate_vocab.DWI_SIGNAL)
                # *very* rough heuristic for assigning DWI and ADC signals
                lesion['DWI_signal'] = signals[0] if signals else ''
                lesion['ADC_signal'] = signals[-1] if signals else ''
                # additional DWI/ADC signal rules
                if ent.text == "DWI/ADC:" and not lesion['DWI_signal']:
                    dwi, _ = __get_alt_signals(field)
                    lesion['DWI_signal'] = dwi
                if ent.text == "DWI/ADC:" and not lesion['ADC_signal']:
                    _, adc = __get_alt_signals(field)
                    lesion['ADC_signal'] = adc
                lesion['ADC_avg'] = __extract_ADC_avg(sent)
                # distinguish between overall UCLA score (default) vs. overall PI-RADS score (if specified)
                dwi_scores = __extract_scores(sent)
                if len(dwi_scores) > 0:
                    lesion['DWI_score'] = dwi_scores[0]
                    lesion['DWI_score_PIRADS'] = dwi_scores[-1] if 'pi-rads' in field_text else ''
            elif ent.label_ == 'DCE_PERF':
                if lesion['overall_score']:
                    break
                lesion['DCE_focal_yn'] = any([token.lower_ == 'focal' for token in field])
                lesion['DCE_intense_yn'] = any([token.lower_ == 'intense' for token in field])
                lesion['DCE_early_yn'] = any([token.lower_ == 'early' for token in field])
                lesion['DCE_washout_yn'] = any([token.lower_ == 'washout' for token in field])
                lesion['DCE_imm_washout_yn'] = any([token.lower_ == 'immediate' for token in field])
                lesion['DCE_score'] = __extract_score(sent)
                lesion['DCE_score_PIRADS_yn'] = __get_DCE_score_pirads(field_text)
                __check_DCE_negations(lesion, field)
            elif ent.label_ == 'EN_KIN':
                if lesion['overall_score']:
                    break
            elif ent.label_ == 'KTRANS':
                lesion['ktrans'] = __extract_number(ent.text)
            elif ent.label_ == 'KEP':
                lesion['kep'] = __extract_number(ent.text)
            elif ent.label_ == 'IAUC':
                lesion['iauc'] = __extract_number(ent.text)
            elif ent.label_ == 'SUSP_ECE':
                lesion['extracap_susp'] = __extract_first_number(field_text)
            elif ent.label_ == 'PIRADS_SCORE':
                lesion['overall_score_PIRADS'] = __extract_first_number(field_text)
            elif ent.label_ == 'UCLA_SCORE':
                lesion['overall_score'] = __extract_first_number(field_text)
                break
            elif ent.label_ == 'SUSP_OVERALL':
                overall_scores = __extract_scores(sent)
                # distinguish between overall UCLA score (default) vs. overall PI-RADS score (if specified)
                if len(overall_scores) > 0:
                    lesion['overall_score'] = overall_scores[0]
                    lesion['overall_score_PIRADS'] = overall_scores[-1] if 'pi-rads' in field_text else ''
                else:
                    lesion['overall_score'] = __extract_min(doc[ent.end].text)
                    lesion['overall_score_PIRADS'] = __extract_min(doc[ent.end].text) if 'pi-rads' in field_text else ''
                break

    doc.user_data['lesions'] = doc_lesions[:]

    return doc


@Language.component("prostate_path_lesion_extractor")
def prostate_path_lesion_extractor(doc):
    doc_lesions = []
    lesion_props = prostate_path_vocab.SAMPLE_PROPS
    lesion = {
        p: None for p in lesion_props
    }
    current_biopsy_method = None
    current_sample_id = None
    biopsy_table = False

    for sent in doc.sents:
        # exclude newline at end of sentence
        sent = sent[:-1]
        for ent in sent.ents:
            if ent.label_ == 'CORE_TABLE':
                current_biopsy_method = "targeted" if "target" in ent.text.lower() else "systematic"
                biopsy_table = True
            elif ent.label_ == 'SAMPLE_ID':
                current_sample_id = ent.text
                # In biopsy reports, cores usually separated by sample
                if doc._.report_type == 'biopsy':
                    lesion = {
                        p: None for p in lesion_props
                    }
                    doc_lesions.append(lesion)
                    lesion['biopsy_method'] = current_biopsy_method or "systematic"
                lesion['sample_id'] = ent.text
            elif ent.label_ == 'SAMPLE':
                # If resection, distinct lesions can be described in a single sample
                if doc._.report_type == 'resection':
                    lesion = {
                        p: None for p in lesion_props
                    }
                    doc_lesions.append(lesion)
                    lesion['sample_id'] = current_sample_id
                lesion['sample'] = ent.text
            elif ent.label_ == 'REPORT_TYPE':
                if 'prostatectomy' in ent.text.lower() and lesion['sample'] is None:
                    lesion['sample'] = 'prostate'
            elif ent.label_ == 'BIOPSY_METHOD':
                lesion['biopsy_method'] = ent.text
            elif ent.label_ == 'GLEASON':
                gleason_scores = __extract_gleason_scores(ent)
                lesion['gleason'] = ent.text
                if len(gleason_scores) > 0:
                    lesion['gleason_1'] = gleason_scores[0]
                    lesion['gleason_2'] = gleason_scores[-1]
            elif ent.label_ == 'GLEASON_3':
                lesion['gleason_3'] = __extract_number(ent.text)
            elif ent.label_ == 'GRADE_GROUP':
                lesion['grade_group'] = __extract_number(ent.text)
                if doc._.report_type == 'biopsy' and biopsy_table:
                    row_vals = __extract_row_numbers(doc[ent.end:sent.end].text)
                    if len(row_vals) > 0:
                        lesion['core_perc'] = row_vals[0]
                    if len(row_vals) > 1:
                        lesion['core_len'] = row_vals[1]
                    if len(row_vals) > 2:
                        lesion['g4_perc'] = row_vals[2]
            elif ent.label_ == 'HIST':
                lesion['hist'] = ent.text
            elif ent.label_ == 'G4_PERC':
                lesion['g4_perc'] = __extract_number(ent.text)
            elif ent.label_ == 'G5_PERC':
                lesion['g5_perc'] = __extract_number(ent.text)
            elif ent.label_ == 'POS_CORES':
                lesion['pos_cores'] = __extract_first_number(ent.text)
            elif ent.label_ == 'CORE_LEN':
                lesion['core_len'] = __extract_meas(ent)
            elif ent.label_ == 'CORE_PERC':
                lesion['core_perc'] = __extract_meas(ent)
            elif ent.label_ == 'SITE':
                lesion['site'] = __get_vocab_val(ent.text, prostate_path_vocab.SAMPLE_SITE)
                if ent.text == 'TARGET':
                    current_biopsy_method = "targeted"
            elif ent.label_ == 'SIDE':
                if not lesion['side']:
                    lesion['side'] = []
                lesion['side'].append(__get_vocab_val(ent.text.lower(), prostate_path_vocab.LESION_SIDE))
            elif ent.label_ == 'LOC':
                if not lesion['location']:
                    lesion['location'] = []
                lesion['location'].append(__get_vocab_val(ent.text.lower(), prostate_path_vocab.LESION_LOCATION))
            elif ent.label_ == 'ZONE':
                if not lesion['zone']:
                    lesion['zone'] = []
                lesion['zone'].append(__get_vocab_val(ent.text.lower(), prostate_path_vocab.LESION_ZONE))
            elif ent.label_ == 'LEVEL':
                if not lesion['level']:
                    lesion['level'] = []
                lesion['level'].append(__get_vocab_val(ent.text.lower(), prostate_path_vocab.LESION_LEVEL))
            elif ent.label_ == 'QUAD':
                if not lesion['quadrant']:
                    lesion['quadrant'] = []
                lesion['quadrant'].append(ent.text.lower())
            elif ent.label_ == 'CLOCK_LOC':
                lesion['clock_loc'] = __extract_clock_face_loc(ent)
            elif ent.label_ == 'LES_SIZE':
                lesion['les_size'] = __extract_meas(ent)
            elif ent.label_ == 'LES_VOL':
                lesion['les_vol'] = __extract_meas(ent)
            elif ent.label_ == 'EXTRA_EXT':
                lesion['extra_ext'] = True
                if 'focal' in ent.text.lower():
                    lesion['p_ece'] = 'focal'
                if 'established' in ent.text.lower():
                    lesion['p_ece'] = 'established'
            elif ent.label_ == 'APEX_INV':
                lesion['apex_inv'] = True
            elif ent.label_ == 'LYMPH_INV':
                lesion['lymph_inv'] = True
            elif ent.label_ == 'PERI_INV':
                lesion['peri_inv'] = True
            elif ent.label_ == 'SEM_VESC':
                lesion['sem_vesc'] = True
            elif ent.label_ == 'IDC':
                lesion['idc'] = 'present'
            elif ent.label_ == 'CRIB':
                lesion['crib'] = 'present'
            elif ent.label_ == 'SURG_MARGINS':
                lesion['surg_margins'] = True
            elif ent.label_ == 'STAGING':
                stage = __get_vocab_val(ent.text.lower(), prostate_path_vocab.LESION_STAGING)
                lesion['staging'] = stage
                doc.user_data['staging'] = stage
            elif ent.label_ == 'MOLD':
                doc.user_data['mold_yn'] = True
            elif ent.label_ == 'WEIGHT':
                doc.user_data['prostate_weight'] = __extract_meas(ent)
            elif ent.ent_id_ == 'section_SA':
                break
            elif ent.ent_id_ == 'biopsy_note':
                if current_biopsy_method == 'targeted':
                    break

    # Filter out entity noise
    if doc._.report_type == 'resection':
        doc_lesions = [l for l in doc_lesions if l['gleason'] or l['sample']]
    elif doc._.report_type == 'biopsy':
        doc_lesions = [l for l in doc_lesions if l['hist'] or l['gleason']]

    if len(doc_lesions) == 0 and lesion['sample'] is not None:
        doc_lesions.append(lesion)

    # Making sure to catch resection staging and prostate weight ents
    for ent in doc.ents:
        if ent.label_ == 'STAGING':
            stage = __get_vocab_val(ent.text.lower(), prostate_path_vocab.LESION_STAGING)
            doc.user_data['staging'] = stage
        if ent.label_ == 'WEIGHT':
            doc.user_data['prostate_weight'] = __extract_meas(ent)

    doc.user_data['lesions'] = doc_lesions[:]

    return doc


# extract number
def __extract_number(ent_text):
    match = re.search(r'\d+(.\d+)?', ent_text)
    if match:
        return match.group()
    return None


# extract first number
def __extract_first_number(ent_text):
    match = re.search(r'^\d+', ent_text)
    if match:
        return match.group()
    return None


def __extract_row_numbers(ent_text):
    matches = re.findall(r'\d[.]?\d?', ent_text)
    return matches


def __extract_min(ent_text):
    matches = re.findall(r'\d[.]?\d?', ent_text)
    if matches and len(matches) > 0:
        return sorted(matches)[0]
    return None


def __extract_clock_face_loc(ent):
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


def __extract_meas(ent):
    for token in ent:
        if token.like_num:
            return token.text
    return None


def __extract_score(sent):
    for ent in sent.ents:
        if ent.label_ == 'SUSP':
            return __extract_min(ent.text)
    return ''


def __extract_ADC_avg(sent):
    for ent in sent.ents:
        if ent.label_ == 'ADC_AVG':
            return __extract_number(ent.text)
    return ''


def __extract_scores(sent):
    scores = []
    for ent in sent.ents:
        if ent.label_ == 'SUSP':
            scores.append(__extract_min(ent.text))
    return scores


def __get_DCE_score_pirads(ent_text):
    if 'positive' in ent_text:
        return True
    elif 'negative' in ent_text:
        return False
    else:
        return None


# standardize vocabulary
def __get_vocab_list(field_text, vocab_dict):
    lesion_vals = []
    for key in vocab_dict.keys():
        if key in field_text:
            lesion_vals.append(vocab_dict[key])
    return lesion_vals


# standardize vocabulary
def __get_vocab_val(field_text, vocab_dict):
    for key in vocab_dict.keys():
        if key in field_text:
            return vocab_dict[key]
    return field_text


# extend vocabulary
def __get_alt_signals(field):
    alt_signals = {
        'high': 'hyperintense',
        'low': 'hypointense',
        'iso': 'isointense'
    }
    dwi_signal = ''
    adc_signal = ''
    for token in field:
        if token.lower_ in alt_signals.keys():
            if not dwi_signal:
                dwi_signal = alt_signals[token.lower_]
            elif not adc_signal:
                adc_signal = alt_signals[token.lower_]
                break

    return dwi_signal, adc_signal


# Check preceding tokens for negation words for some DCE fields
def __check_DCE_negations(lesion, field):
    for idx, token in enumerate(field):
        # intensity
        if token.lower_ == 'intense':
            context = field[idx - 2: idx].text.lower()
            if 'non' in context:
                lesion['DCE_intense_yn'] = False
        # washout
        if token.lower_ == 'washout':
            context = field[idx - 2: idx].text.lower()
            if any([neg in context for neg in ['without', 'with out', 'no']]):
                lesion['DCE_washout_yn'] = False


def __extract_gleason_scores(ent):
    scores = []
    matches = re.findall(r'\d[.]?\d?', ent.text)
    if matches:
        scores = [int(i) for i in matches]
    return scores[:2]

# endregion

# region breast property extractors


@Language.component("breast_img_lesion_extractor")
def breast_img_lesion_extractor(doc):
    lesions = []
    lesion = {
        k: v for k, v in breast_vocab.LESION_PROPS.items()
    }
    # Keep track of multi-sentence lateral location ents
    current_loc = ""
    current_exam_type = ""

    # Loop through sentences and group properties into lesion objects
    for sent in doc.sents:
        # Check for existing lesion obj (from previous sentences)
        if lesion['les_type']:
            # If current sentence mentions lesion or new exam type, assume it's a new lesion obs
            # (otherwise, continue adding properties to existing lesion - unless it is an empty object)
            if any([ent.label_ in ['LESION', 'EXAM_TYPE', 'CALC', 'ASYM'] for ent in sent.ents]) or not has_lesion_props(lesion):
                lesions.append(lesion)
                lesion = {
                    k: v for k, v in breast_vocab.LESION_PROPS.items()
                }
            lesion['exam_type'] = current_exam_type
        for ent in sent.ents:
            if ent.label_ == 'LESION':
                if not lesion['les_type'] or lesion['les_type'] in ['calc', 'asym']:
                    lesion['les_type'] = ent.text
                if 'cluster' in ent.text:
                    lesion['distrib'] = 'cluster'
                    lesion['les_type'] = 'cyst' if 'cyst' in ent.text else ent.text
                    lesion['les_type'] = 'microcyst' if 'microcyst' in ent.text else ent.text
            elif ent.label_ == 'COMP_MM':
                doc.user_data['tissue_comp_mm'] = ent.text
            elif ent.label_ == 'COMP_US':
                doc.user_data['tissue_comp_us'] = ent.text
            elif ent.label_ == 'ASYM':
                # Asymmetry can also be a lesion type
                if not lesion['les_type']:
                    lesion['les_type'] = 'asym'
                if not lesion['asym'] or lesion['asym'] == 'asymmetry':
                    lesion['asym'] = ent.text
            elif ent.label_ == 'CALC':
                # Calcification can also be a lesion type
                if not lesion['les_type']:
                    lesion['les_type'] = 'calc'
                if not lesion['calc'] or lesion['calc'] in ['calcification', 'calcifications']:
                    lesion['calc'] = ent.text
                if 'benign' in sent.text.lower():
                    lesion['benign_app'] = True
            elif ent.label_ == 'SHAPE':
                lesion['shape'] = ent.text
            elif ent.label_ == 'MARGINS':
                lesion['margins'] = ent.text
            elif ent.label_ == 'LES_MEAS':
                lesion['les_meas'] = 'measure' if 'meas' in ent.text else ent.text
            elif ent.label_ == 'LES_SIZE':
                lesion['diam_x'], lesion['diam_y'], lesion['diam_z'] = extract_dimensions(ent)
            elif ent.label_ == 'LATERAL_LOC':
                # Wait to set lesion location until end of sentence
                current_loc = get_lateral_loc(ent)
            elif ent.label_ == 'QUADRANT':
                lesion['loc_quad'] = check_breast_vocab(ent.text, breast_vocab.LESION_QUAD)
            elif ent.label_ == 'DIST_FN':
                lesion['dist_fn'] = __extract_first_number(ent.text)
            elif ent.label_ == 'CLOCK_LOC':
                lesion['loc_clock'] = get_breast_clock_loc(ent)
            elif ent.label_ == 'DEPTH':
                lesion['loc_depth'] = check_breast_vocab(ent.text, breast_vocab.LESION_DEPTH)
            elif ent.label_ == 'DENSITY':
                lesion['density'] = ent.text
            elif ent.label_ == 'ORIENTATION':
                lesion['orientation'] = ent.text
            elif ent.label_ == 'ECHO_PAT':
                lesion['echo_pat'] = ent.text
            elif ent.label_ == 'POST_FEATS':
                lesion['post_feats'] = ent.text
            elif ent.label_ == 'DISTRIB':
                lesion['distrib'] = ent[0].text
            elif ent.label_ == 'EXAM_TYPE':
                sent_exam_type = get_breast_exam_type(ent.sent)
                if sent_exam_type:
                    current_exam_type = sent_exam_type
                lesion['exam_type'] = current_exam_type
        # If sentence with lesion ends and lateral loc still unset, use last seen loc
        if lesion['les_type'] and not lesion['loc_lat']:
            lesion['loc_lat'] = current_loc

    # Add last existing lesion
    lesions.append(lesion)

    doc_lesions = []
    # Filter out empty/unrelated lesion objects
    for lesion in lesions:
        # Skip objects with no lesion type
        if not lesion['les_type']:
            continue
        # keep "benign appearing calcifications"
        elif 'benign_app' in lesion and lesion['benign_app'] is True:
            doc_lesions.append(lesion)
        # Skip objects with lesion (type, asym, or calc) as only property
        elif not has_lesion_props(lesion):
            continue
        else:
            doc_lesions.append(lesion)

    doc.user_data['lesions'] = doc_lesions[:]

    return doc


@Language.component("breast_path_lesion_extractor")
def breast_path_lesion_extractor(doc):
    lesions = []
    lesion_props = breast_vocab.SAMPLE_PROPS
    lesion = {
        p: None for p in lesion_props
    }
    biomarkers = {
        k: [] for k in ['er', 'er_perc', 'pgr', 'pgr_perc', 'her_imm', 'her_imm_score', 'her_situ', 'ki']
    }
    # Keep track of multi-sentence lateral location ents
    current_hist = ""
    current_loc = ""

    # Loop through entities and group properties into lesion objects
    for sent in doc.sents:
        for ent in sent.ents:
            if ent.label_ == 'SAMPLE_ID':
                # New sample ID => new lesion obs
                lesion = {
                    p: None for p in lesion_props
                }
                lesions.append(lesion)
                lesion['sample_id'] = ent.text
            elif ent.label_ == 'CALC':
                lesion['calc'] = sent[1:].text.strip()
            elif ent.label_ == 'MICROCALC':
                lesion['microcalc'] = sent[1:].text.strip()
            elif ent.label_ == 'SIDE':
                # In case sample ID is missing, add lesion on lateral location
                if lesion['sample_id'] is None:
                    lesions.append(lesion)
                current_loc = get_lateral_loc(ent)
                lesion['side'] = current_loc
            elif ent.label_ == 'SIZE':
                size = extract_size_meas(ent)
                if 'DCIS' in sent.text:
                    lesion['dcis'] = size
                    lesion['size'] = size if lesion['size'] is None else lesion['size']
                else:
                    lesion['size'] = size
            elif ent.label_ == 'QUADRANT':
                lesion['quadrant'] = check_breast_vocab(ent.text.lower(), breast_vocab.LESION_QUAD)
            elif ent.label_ == 'DIST_FN':
                lesion['dist_fn'] = __extract_first_number(ent.text)
            elif ent.label_ == 'CLOCK':
                lesion['clock'] = __extract_clock_face_loc(ent)
            elif ent.label_ == 'DEPTH':
                lesion['depth'] = check_breast_vocab(ent.text.lower(), breast_vocab.LESION_DEPTH)
            elif ent.label_ == 'GRADE':
                lesion['grade'] = __extract_number(ent.text)
            elif ent.label_ == 'GRADE_N':
                lesion['grade_n'] = __extract_number(ent.text)
            elif ent.label_ == 'GRADE_M':
                lesion['grade_m'] = __extract_number(ent.text)
            elif ent.label_ == 'GRADE_T':
                lesion['grade_t'] = __extract_number(ent.text)
            elif ent.label_ == 'BR_SCORE':
                lesion['br_score'] = __extract_br_score(ent)
            elif ent.label_ == 'FOCALITY':
                # pattern matches mention of multiple foci
                lesion['focality'] = 'multiple'
            elif ent.label_ == 'EIC':
                if any(token.lower_ in ['no', 'none', 'not', 'negative', 'absent'] for token in sent):
                    lesion['eic'] = False
                elif any(token.lower_ in ['positive', 'seen', 'identified', 'present'] for token in sent):
                    lesion['eic'] = True
                else:
                    lesion['eic_other'] = sent[1:].text.strip()
            elif ent.label_ == 'PERC_TUMOR':
                # Only keep first recorded % tumor value
                if lesion['perc_tumor'] is None:
                    lesion['perc_tumor'] = __extract_number(ent.text)
            elif ent.label_ == 'ARCH':
                if lesion['arch'] is None:
                    lesion['arch'] = []
                arch_patterns = check_breast_vocab_list(ent, breast_vocab.ARCH_PATTERNS)
                lesion['arch'].extend(arch_patterns)
            elif ent.label_ == 'NUCLEAR':
                lesion['nuclear'] = ent.text
            elif ent.label_ == 'NECROSIS':
                if any([token.lower_ == 'with' for token in ent]):
                    lesion['necrosis'] = True
                elif any([token.lower_ == 'without' for token in ent]):
                    lesion['necrosis'] = False
                else:
                    lesion['necrosis_other'] = ent.text
            elif ent.label_ == 'SURG_MARGINS':
                # Assign entire sentence to surgical margins free text variable
                lesion['surg_margins'] = sent[1:].text.strip()
            elif ent.label_ == 'HIST':
                if lesion['hist'] is None:
                    lesion['hist'] = [ent.text]
                else:
                    lesion['hist'].append(ent.text)
                current_hist = ent.text
            elif ent.label_ == 'HIST_DET':
                lesion['hist_det'] = ent.text
            elif ent.label_ == 'HIST_GRADE':
                lesion['hist_grade'] = ent.text
            elif ent.label_ == 'LYMPH_INV':
                if any(token.lower_ in ['no', 'none', 'not', 'negative', 'absent'] for token in sent):
                    lesion['lymph_inv'] = False
                elif any(token.lower_ in ['positive', 'seen', 'identified', 'present'] for token in sent):
                    lesion['lymph_inv'] = True
                else:
                    lesion['lymph_inv_other'] = sent[1:].text.strip()
            elif ent.label_ == 'DERMAL_INV':
                if any(token.lower_ in ['no', 'none', 'not', 'negative', 'absent'] for token in sent):
                    lesion['dermal_inv'] = False
                elif any(token.lower_ in ['positive', 'seen', 'identified'] for token in sent):
                    lesion['dermal_inv'] = True
                else:
                    lesion['dermal_inv_other'] = sent[1:].text.strip()
            elif ent.label_ == 'P_T':
                lesion['p_t'] = ent.text
            elif ent.label_ == 'P_N':
                lesion['p_n'] = ent.text
            elif ent.label_ == 'P_M':
                lesion['p_m'] = ent.text
            elif ent.label_ == 'HER_IMM':
                biomarkers['her_imm'].append(ent.text)
            elif ent.label_ == 'HER_IMM_SCORE':
                biomarkers['her_imm_score'].append(ent.text)
            elif ent.label_ == 'HER_SITU':
                biomarkers['her_situ'].append(ent.text)
            elif ent.label_ == 'KI':
                biomarkers['ki'].append(__extract_number(ent.text))

    # Catch lesion with histology but no sample ID or lateral location
    if len(lesions) == 0 and lesion['hist'] is not None:
        lesions.append(lesion)

    doc.user_data['lesions'] = lesions[:]
    doc.user_data['biomarkers'] = biomarkers

    return doc


@Language.component("breast_extract_birads")
def breast_extract_birads(doc):
    les_birads = []
    overall_birads = None
    for ent in doc.ents:
        if ent.label_ == 'LES_BIRADS':
            les_birads.append(ent[-1].text)
        if ent.label_ == 'OVERALL_BIRADS':
            overall_birads = ent[-1].text
    doc.user_data['lesion_birads'] = les_birads
    doc.user_data['overall_birads'] = overall_birads
    return doc


def check_breast_vocab(field_text, vocab_dict):
    for key in vocab_dict.keys():
        if key in field_text:
            return vocab_dict[key]
    return field_text

def check_breast_vocab_list(ent, vocab_dict):
    vocab_list = []
    for token in ent:
        if token.lower_ in vocab_dict:
            vocab_list.append(vocab_dict[token.lower_])
    return vocab_list

def get_breast_exam_type(sent):
    for ent in sent.ents:
        if ent.label_ == 'EXAM_TYPE':
            if 'mammo' in ent.text.lower():
                return 'mammogram'
            elif 'ultrasound' in ent.text.lower():
                return 'ultrasound'
            else:
                return None


def get_lateral_loc(ent):
    if 'left' in ent.text.lower():
        return 'left'
    elif 'right' in ent.text.lower():
        return 'right'
    elif any([term in ent.text.lower() for term in ['bilateral', 'both']]):
        return 'bilateral'
    else:
        return ent.text


def get_breast_clock_loc(ent):
    clock_val = ''
    for token in ent:
        # 11 o'clock --> 11:00
        if token.is_digit:
            clock_val = token.text + ':00'
            if len(token) == 1:
                clock_val = '0' + clock_val
    return clock_val


def has_lesion_props(lesion):
    general_lesion_props = ['les_type', 'asym', 'calc', 'loc_lat', 'exam_type']
    return any([lesion[prop] for prop in [key for key in lesion.keys() if key not in general_lesion_props]])


def __extract_br_score(ent):
    match = re.search(r'\d', ent.text)
    if match:
        return match.group()
    return None

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
