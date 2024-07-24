import re
from nlp_pipeline.config.colon import vocab
from spacy.language import Language


# Component to filter out non colon-related reports

@Language.component("col_keyword_filter")
def col_keyword_filter(doc):
    col_tp_regex = r'(' + ')|('.join(vocab.COL_KEYWORDS) + r')'
    col_fp_regex = r'(' + ')|('.join(vocab.COL_FP_KEYWORDS) + r')'
    tp_match = re.search(col_tp_regex, doc.text, re.IGNORECASE)
    fp_match = re.search(col_fp_regex, doc.text, re.IGNORECASE)
    if fp_match:
        doc._.set('col_related', False)
        print('\nfound non colon-related doc with FP term {}: \n{}'.format(fp_match, doc.text))
    elif tp_match:
        doc._.set('col_related', True)
    else:
        doc._.set('col_related', False)
    return doc
