# Keywords to determine if a report is colon-related or not
COL_KEYWORDS = [
    'ascending polyp',
    '\\sAnal\\s',
    'Colorectal',
    'rect[au][ml]',
    'cec[au][ml]',
    'Colon',
    'Anus',
    'Transverse',
    'Sigmoid',
    'descending polyp',
    'Colonoscopy'
]

COL_FP_KEYWORDS = [
    'through the mouth',
    'into the mouth',
    'into the skin',
    'transcranial',
    'Electroencephalography',
    'Anorectal Manometry'
    'DAILY PROGRESS CONSULT NOTE',
    'INITIAL CONSULT',
    'Intubation Procedure Note',
    'Line Insertion',
    'Procedure: Optic Nerve',
    'Manometry Protocol:',
    '24-Hour Ambulatory Intraesophageal pH Study'
]

HIST_TYPES = {
    'traditional serrated': 'traditional serrated adenoma',
    'serrated': 'sessile serrated',
    'hyperplastic': 'hyperplastic',
    'tubulovillous': 'tubulovillous adenoma',
    'villous': 'villous adenoma',
    'tubular': 'tubular adenoma'
}

COL_NO_HIST = [
    'colonic mucosa',
    'lymphoid aggregate',
    'inflammatory polyp',
    'leiomyoma',
    'submucosal lipoma'
]

COL_INCOMPLETE_PROC = [
    'incomplete colonoscopy',
    'unable to complete colonoscopy'
]

COL_POOR_PREP_REGEX = [
    'quality of the preparation was poor',
    'poor\\s(\\w+\\s)?prep',
    'poor prep(aration)?',
    'prep(aration)? was poor'
]

COL_PREP_QUALITY = {
    'excellent': 0,
    'good': 1,
    'fair': 2,
    'adequate': 3,
    'inadequate': 4,
    'poor': 5
}

COL_ADEQUATE_PREP = [
    'excellent',
    'good',
    'fair',
    'adequate'
]

PATH_MALIGNANCY = [
    'neuroendocrine tumor',
    'NET',
    'carcinoma',
    'adenocarcinoma',
    'sarcoid',
    'carcinoid',
    'lymphoma',
    'cancer'
]
