import re
from diaag_nlp_colon.classes.representations import AsDictMixin
from diaag_nlp_colon.config.colon import vocab


class Report:

    def __init__(self, text='', mrn=None):
        self.text = text
        self.pat_mrn = mrn


class ColReport(Report, AsDictMixin):
    """
    Structured representation of a colonoscopy report
    """

    def __init__(self, text='', pat_mrn=None, polyps=None, total_polyps=0, large_polyp=False, candidate_buckets=None,
                 adj_polyps=None, full_report_text=None, indications_text=None, extent_text=None, ad_prep_quality=None,
                 vis_text=None, withdrawal_text=None, withdrawal_time_min=None, withdrawal_time_sec=None,
                 cecal_int=None, col_related=False, prep_quality_worst=None, prep_quality_best=None):
        super().__init__(text, pat_mrn)
        self.polyps = polyps or []
        self.total_polyps = total_polyps
        self.large_polyp = large_polyp
        self.candidate_buckets = candidate_buckets or {}
        self.adj_polyps = adj_polyps
        self.full_report_text = full_report_text
        self._sample_sents = []
        self.review_flags = {
            'poor_prep': False,
            'incomplete_proc': False,
            'many_polyps': False,
            'retained_polyp': False,
            'polyp_removed_piecemeal': False,
        }
        self.col_related = col_related
        self.indications_text = indications_text
        self.extent_text = extent_text
        self.ad_prep_quality = ad_prep_quality
        self.prep_quality_worst = prep_quality_worst
        self.prep_quality_best = prep_quality_best
        self.vis_text = vis_text
        self.withdrawal_text = withdrawal_text
        self.withdrawal_time_min = withdrawal_time_min
        self.withdrawal_time_sec = withdrawal_time_sec
        self.cecal_int = cecal_int

    @property
    def candidate_bucket_list(self):
        return [b for b in self.candidate_buckets if self.candidate_buckets[b]]

    @property
    def report_props(self):
        return {
            'indications': self.indications_text,
            'extent': self.extent_text,
            'visualization': self.vis_text,
            'withdrawal_text': self.withdrawal_text,
            'prep_worst': self.prep_quality_worst,
            'prep_best': self.prep_quality_best
        }

    @property
    def quality_metrics(self):
        # Prep quality documented T/F
        # Prep quality adequate T/F
        # Cecal intubation documented T/F
        # Cecal intubation successful T/F
        # Withdrawal time documented T/F
        # Withdrawal time (min, sec)
        return {
            'doc_prep_tf': True if self.ad_prep_quality is not None else False,
            'adequate_prep_tf': True if self.ad_prep_quality else False,
            'doc_cecal_int_tf': True if self.cecal_int is not None else False,
            'cecal_int_tf': True if self.cecal_int else False,
            'doc_withdrawal_time_tf': True if self.withdrawal_time_min is not None else False,
            'withdrawal_time_min': self.withdrawal_time_min,
            'withdrawal_time_sec': self.withdrawal_time_sec
        }

    def regex_poor_prep(self):
        prep_regex = r'(' + ')|('.join(vocab.COL_POOR_PREP_REGEX) + r')'
        match = re.search(prep_regex, self.text, re.IGNORECASE)
        return True if match else False

    def regex_incomplete_proc(self):
        incomp_regex = r'(' + ')|('.join(vocab.COL_INCOMPLETE_PROC) + r')'
        match = re.search(incomp_regex, self.text, re.IGNORECASE)
        return True if match else False


class PathReport(Report, AsDictMixin):
    """
    Structured representation of a colon pathology report
    """

    hists = ['tubular adenoma', 'sessile serrated']
    bucket_4_hists = ['tubulovillous adenoma', 'villous adenoma', 'traditional serrated adenoma']
    hra_hists = ['tubulovillous adenoma', 'villous adenoma']

    def __init__(self, text='', pat_mrn=None, polyps=None, candidate_buckets=None, full_report_text=None,
                 mentions_hist=False):
        super().__init__(text, pat_mrn)
        self.polyps = polyps or []
        self.candidate_buckets = candidate_buckets or {}
        self.full_report_text = full_report_text
        self.review_flags = {
            'malignancy': False
        }
        self.mentions_hist = mentions_hist

    @property
    def candidate_bucket_list(self):
        return [b for b in self.candidate_buckets if self.candidate_buckets[b]]

    @property
    def hist_counts(self):
        hist_counts = {
            hist: 0
            for _, hist in vocab.HIST_TYPES.items()
        }
        for polyp in self.polyps:
            if polyp['histology'] and polyp['histology'] in hist_counts:
                hist_counts[polyp['histology']] += 1
        return hist_counts

    # all hyperplastic (or normal)
    def all_hp(self):
        all_hp = False
        if any('hyperplastic' in p['histology'] for p in self.polyps):
            all_hp = True
        for p in self.polyps:
            if p['histology'] in ['sessile serrated', 'tubular adenoma'] + self.bucket_4_hists:
                all_hp = False
        return all_hp

    # no polyps have a histology type that we recognize
    def all_normal(self):
        no_polyp_hists = not any([p['histology'] for p in self.polyps])
        # check report text for hists in case extraction missed any
        if self.mentions_hist or (self.text and self.text_has_hist()):
            no_polyp_hists = False
        return no_polyp_hists

    def has_adenoma(self):
        return any([p['histology'] and p['histology'] in 'tubular adenoma' for p in self.polyps])

    def has_ssp(self):
        return any([p['histology'] and p['histology'] in 'sessile serrated' for p in self.polyps])

    def has_hp(self):
        return any([p['histology'] and p['histology'] in 'hyperplastic' for p in self.polyps])

    def has_bucket_4_hist(self):
        return any([p['histology'] and p['histology'] in self.bucket_4_hists for p in self.polyps])

    def has_hra_hist(self):
        return any([p['histology'] and p['histology'] in self.hra_hists for p in self.polyps])

    def has_dysp(self):
        return any([p['hg_dysplasia'] == 'yes' or p['cyt_dysplasia'] == 'yes' for p in self.polyps])

    def has_hg_dysp(self):
        return any([p['hg_dysplasia'] == 'yes' for p in self.polyps])

    # trying to account for polyps that turned out to just be normal tissue
    def normal_sample_count(self):
        return len([p for p in self.polyps if not p['histology']])

    def text_has_hist(self):
        hist_regex = r'(' + ')|('.join(list(vocab.HIST_TYPES.keys())) + r')'
        hist_match = re.search(hist_regex, self.text, re.IGNORECASE)
        return True if hist_match else False

    def text_has_bucket_4_hist(self):
        hist_regex = r'(' + ')|('.join(self.bucket_4_hists) + r')'
        hist_match = re.search(hist_regex, self.text, re.IGNORECASE)
        return True if hist_match else False

    def regex_malignancy(self):
        mal_regex = r'(' + ')|('.join(vocab.PATH_MALIGNANCY) + r')'
        match = re.search(mal_regex, self.text, re.IGNORECASE)
        return True if match else False
