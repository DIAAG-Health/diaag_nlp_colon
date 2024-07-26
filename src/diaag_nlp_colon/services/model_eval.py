from spacy.scorer import Scorer
from spacy.training import Example
from spacy import displacy
from diaag_nlp_colon.config.colon import displacy_configs
import random
import pandas as pd
from diaag_nlp_colon.services import file_proc


# TODO: move classes to separate file
# using spaCy's implementation for now
class DiaagPRFScore(object):
    """
    A precision / recall / F score
    """

    def __init__(self):
        self.tp = 0
        self.fp = 0
        self.fn = 0
        self.tn = 0
        # use to get # true negatives:
        self.fn_tokens = 0

    def score_set(self, cand, gold):
        self.tp += len(cand.intersection(gold))
        self.fp += len(cand - gold)
        self.fn += len(gold - cand)
        # get # false negative tokens
        fn_ents = gold - cand
        self.fn_tokens = sum(map(len, fn_ents))

    def token_score_set(self, cand, gold):
        for token in cand:
            pred_ent = token.ent_type_
            gold_ent = gold[token.i]
            if not pred_ent:
                if gold_ent == 'UNLABELED':
                    self.tn += 1
                else:
                    self.fn += 1
            elif pred_ent == gold_ent:
                self.tp += 1
            elif gold_ent == 'UNLABELED':
                self.fp += 1
            elif pred_ent != gold_ent:
                self.fp += 1
            else:
                print('missed a token case: pred is {}, gold is {}'.format(pred_ent, gold_ent))

    def token_label_score_set(self, cand, gold, label):
        for token in cand:
            pred_ent = token.ent_type_
            gold_ent = gold[token.i]
            if not pred_ent:
                if gold_ent == label:
                    token._.set('err_type', '{}_FN'.format(label))
                    self.fn += 1
                else:
                    self.tn += 1
            elif pred_ent == gold_ent == label:
                self.tp += 1
            elif pred_ent == label and gold_ent != label:
                token._.set('err_type', '{}_FP'.format(label))
                self.fp += 1
            elif gold_ent == label and pred_ent != label:
                token._.set('err_type', '{}_FN'.format(label))
                self.fn += 1
            elif pred_ent != label and gold_ent != label:
                self.tn += 1
            else:
                print('missed a token type case: pred is {}, gold is {}, label is {}'.format(pred_ent, gold_ent, label))


    @property
    def precision(self):
        return self.tp / (self.tp + self.fp + 1e-100)

    @property
    def recall(self):
        return self.tp / (self.tp + self.fn + 1e-100)

    @property
    def fscore(self):
        p = self.precision
        r = self.recall
        return 2 * ((p * r) / (p + r + 1e-100))

    @property
    def pr_counts(self):
        return self.tp, self.fp, self.tn, self.fn


# modifying spaCy's implementation for now
class DiaagScorer(object):
    """Compute evaluation scores."""

    def __init__(self):
        """Initialize the Scorer.
        eval_punct (bool): Evaluate the dependency attachments to and from
            punctuation.
        RETURNS (Scorer): The newly created object.
        DOCS: https://spacy.io/api/scorer#init
        """
        self.ner = DiaagPRFScore()
        self.ner_per_ents = dict()
        self.token_ner = DiaagPRFScore()
        self.token_ner_per_ents = dict()

    @property
    def ents_p(self):
        """RETURNS (float): Named entity accuracy (precision)."""
        return self.ner.precision * 100

    @property
    def ents_r(self):
        """RETURNS (float): Named entity accuracy (recall)."""
        return self.ner.recall * 100

    @property
    def ents_f(self):
        """RETURNS (float): Named entity accuracy (F-score)."""
        return self.ner.fscore * 100

    @property
    def ents_per_type(self):
        """RETURNS (dict): Scores per entity label.
        """
        return {
            k: {"p": v.precision * 100, "r": v.recall * 100, "f": v.fscore * 100}
            for k, v in self.ner_per_ents.items()
        }

    @property
    def token_ents_p(self):
        """RETURNS (float): Named entity accuracy (precision)."""
        return self.token_ner.precision * 100

    @property
    def token_ents_r(self):
        """RETURNS (float): Named entity accuracy (recall)."""
        return self.token_ner.recall * 100

    @property
    def token_ents_f(self):
        """RETURNS (float): Named entity accuracy (F-score)."""
        return self.token_ner.fscore * 100

    @property
    def token_ents_per_type(self):
        """RETURNS (dict): Scores per entity label.
        """
        return {
            k: {"p": v.precision * 100, "r": v.recall * 100, "f": v.fscore * 100}
            for k, v in self.token_ner_per_ents.items()
        }

    # TODO: clean up
    def score(self, pred, gold, ent_labels):
        """Update the evaluation scores from a single Doc / GoldParse pair.
        doc (Doc): The predicted annotations.
        gold (GoldParse): The correct annotations.
        DOCS: https://spacy.io/api/scorer#score
        """
        # get superset of all NER labels in gold and doc
        gold_ents = gold.ents
        # ent_labels = set([x[0] for x in gold_ents] + [k.label_ for k in pred.ents])
        # Set up all labels for per type scoring and prepare gold per type
        gold_per_ents = {ent_label: set() for ent_label in ent_labels}
        for ent_label in ent_labels:
            if ent_label not in self.ner_per_ents:
                self.ner_per_ents[ent_label] = DiaagPRFScore()
            gold_per_ents[ent_label].update(
                [x for x in gold_ents if x[0] == ent_label]
            )
        # Find all candidate labels, overall and per type
        cand_ents = set()
        cand_per_ents = {ent_label: set() for ent_label in ent_labels}
        for ent in pred.ents:
            if ent.label_ not in ent_labels:
                continue
            # getting labelled entities from gold by position in cand
            first = gold.cand_to_gold[ent.start]
            last = gold.cand_to_gold[ent.end - 1]
            if first is None or last is None:
                print('ent tokens not found in gold std doc:', ent)
                self.ner.fp += 1
                self.ner_per_ents[ent.label_].fp += 1
            else:
                cand_ents.add((ent.label_, first, last))
                cand_per_ents[ent.label_].add((ent.label_, first, last))
        # Score for all ents
        self.ner.score_set(cand_ents, gold_ents)
        # set true neg (total unlabelled tokens - false neg tokens)
        total_unlab_tokens = len(pred) - sum(map(len, pred.ents))
        self.ner.tn += total_unlab_tokens - self.ner.fn_tokens
        # Scores per ent
        for label, prf in self.ner_per_ents.items():
            prf.score_set(cand_per_ents[label], gold_per_ents[label])
            neg_ent_tokens = sum(map(len, [ent for ent in pred.ents if ent.label_ != label]))
            # set true neg (total unlabelled tokens - false neg + tokens with other labels)
            prf.tn += total_unlab_tokens - prf.fn_tokens + neg_ent_tokens
        return

    def score_tokens(self, pred, gold, ent_labels):
        gold_token_labels = ['UNLABELED'] * len(gold)
        gold_tokens = []
        # get token position and labels from goldparse's weird default ents
        for annot in gold.orig_annot:
            idx = annot[0]
            label = annot[-1].split('-')[-1]
            if label in ent_labels:
                gold_tokens.append((label, idx))
        for ent in gold_tokens:
            label, idx = ent
            gold_token_labels[idx] = label
        # overall token score
        self.token_ner.token_score_set(pred, gold_token_labels)
        # by entity type
        for ent_label in ent_labels:
            if ent_label not in self.token_ner_per_ents:
                self.token_ner_per_ents[ent_label] = DiaagPRFScore()
        for label, prf in self.token_ner_per_ents.items():
            prf.token_label_score_set(pred, gold_token_labels, label)

    # LOOK AT ACTUAL TEXT VALUES OF ENTS
    # MAYBE PASS IF THEY'RE WITHIN 2-3 TOKENS OF EACH OTHER?
    # OR JUST CHECK CHAR OR TOKEN OVERLAP
    def check_errors(self, cand, gold):
        pass

    def draw_conf_matrices(self, cat=None):
        if not cat or cat == 'ent':
            print('\nOverall Entity Confusion Matrix: ------------------')
            self._draw_conf_matrix(self.ner.pr_counts)
            for label, prf in self.ner_per_ents.items():
                print('Entity Confusion Matrix for label {}'.format(label))
                self._draw_conf_matrix(prf.pr_counts)
        if not cat or cat == 'token':
            print('\nOverall Token Confusion Matrix: -------------------')
            self._draw_conf_matrix(self.token_ner.pr_counts)
            for label, prf in self.token_ner_per_ents.items():
                print('Token Confusion matrix for label {}'.format(label))
                self._draw_conf_matrix(prf.pr_counts)

    def print_scorer_results(self, cat=None, spreadsheet=True):
        if not cat or cat == 'ent':
            total_metrics = [self.ents_p, self.ents_r, self.ents_f]
            if spreadsheet:
                print('\nOverall Entity NER Performance:')
            else:
                print('\nOverall Entity NER Performance: ------------------')
            self._print_scorer_results(total_metrics, self.ents_per_type, 'entity', spreadsheet)
        if not cat or cat == 'token':
            total_metrics = [self.token_ents_p, self.token_ents_r, self.token_ents_f]
            if spreadsheet:
                print('\nOverall Token NER Performance:')
            else:
                print('\nOverall Token NER Performance: -------------------')
            self._print_scorer_results(total_metrics, self.token_ents_per_type, 'token', spreadsheet)

    @staticmethod
    def _draw_conf_matrix(metrics):
        tp, fp, tn, fn = metrics
        print('--------')
        print('tp:', tp)
        print('fp:', fp)
        print('tn:', tn)
        print('fn:', fn)
        print('--------\n')

    @staticmethod
    def _print_scorer_results(total_metrics, ent_type_metrics, cat, spreadsheet):
        p, r, f = total_metrics
        print('{}{:0.2f}'.format('\tprecision: ' if not spreadsheet else '', p))
        print('{}{:0.2f}'.format('\trecall: ' if not spreadsheet else '', r))
        print('{}{:0.2f}'.format('\tf score: ' if not spreadsheet else '', f))
        for ent_type in sorted(list(ent_type_metrics.keys())):
            print('')
            if spreadsheet:
                print(ent_type)
                print('{:0.2f}'.format(ent_type_metrics[ent_type]['p']))
                print('{:0.2f}'.format(ent_type_metrics[ent_type]['r']))
                print('{:0.2f}'.format(ent_type_metrics[ent_type]['f']))
            else:
                print('\n{} Metrics for Label: {}'.format(cat.capitalize(), ent_type))
                print('\tprecision: {:0.2f}'.format(ent_type_metrics[ent_type]['p']))
                print('\trecall: {:0.2f}'.format(ent_type_metrics[ent_type]['r']))
                print('\tf score: {:0.2f}'.format(ent_type_metrics[ent_type]['f']))


# Functions to help evaluate model results

ent_to_excl = ['SECTION_HEADER', 'POLYP_SAMPLE_REGEX']

# compare model output to labelled Brat data
# Format of processed Brat data for one entity:
#     (
#        "Two large polypoid fragments, 1 x 0.3 x 0.2 cm and 0.9 x 0.7 x 0.4 cm",
#        {"entities": [(31, 47, LABEL), (52, 60, LABEL)]},
#    )
def evaluate_model(nlp, test_set):
    print('\nEvaluating NER model...')
    scorer = DiaagScorer()
    pred_docs = []
    for input_, annot in test_set:
        # get predicted ents for test report
        pred_doc = nlp(input_)
        gold_doc_text = nlp.make_doc(input_)
        # remove annotations from outside relevant sections before testing
        # gold_annot = remove_outside_annot(annot['entities'], pred_doc)
        example = Example.from_dict(nlp.make_doc(gold_doc_text), annot['entities'])
        # gold_doc = GoldParse(gold_doc_text, entities=gold_annot)
        # for rule-based
        # pipe_labels = nlp.pipe_labels['entity_ruler']
        # for pre-trained:
        pipe_labels = nlp.pipe_labels['ner']
        labels = [label for label in pipe_labels if label not in ent_to_excl]
        # get prf score
        scorer.score(pred_doc, example, labels)
        scorer.score_tokens(pred_doc, example, labels)
        pred_docs.append(pred_doc)
    scorer.print_scorer_results()
    # scorer.draw_conf_matrices()
    return pred_docs


def remove_outside_annot(gold_ents, pred_doc):
    filtered_gold_ents = []
    section_headers = pred_doc._.get('section_headers')
    earliest = len(pred_doc.text)
    for header_type, header_tup in section_headers.items():
        if header_type in ['section_IMP', 'section_EBL', 'section_EM', 'section_ADD', 'section_INT']:
            header, _ = header_tup
            if header.start_char < earliest:
                earliest = header.start_char
    for gold in gold_ents:
        # check if ent comes after final relevant section
        if gold[0] < earliest:
            filtered_gold_ents.append(gold)
    return filtered_gold_ents


def view_ent_labels(nlp, test_set):
    for index, file in enumerate(test_set):
        prob = random.uniform(0, 1)
        test_text, ent_obj = file
        if prob < 0.03:
            print("\n%d Labelled entities:\n" % len(ent_obj['entities']))
            for ent in file[1]['entities']:
                start = ent[0]
                end = ent[1]
                print(ent[2], test_text[start:end])
        doc = nlp(test_text)
        if prob < 0.03:
            print("\n%d Predicted entities:\n" % len(doc.ents))
            for ent in doc.ents:
                # print([(ent.label_, ent.text, ent.ent_id_) for ent in doc.ents])
                print(ent.label_, ent.text)
        # set difference
        label_diff = set(doc.ents) - set(ent_obj['entities'])
        # print('extras:', label_diff)
        # print('-----')


# spacy's default method for evaluating models
def spacy_evaluate_ner(nlp, test_set):
    print('\nEvaluating NER model...')
    scorer = Scorer()
    for input_, annot in test_set:
        gold_doc_text = nlp.make_doc(input_)
        example = Example.from_dict(nlp.make_doc(gold_doc_text), annot['entities'])
        pred_value = nlp(input_)
        scorer.score(pred_value, example)
    # scorer.print_scorer_results()
    print('\nOverall NER Performance:')
    print('\tprecision: {:0.2f}'.format(scorer.ents_p))
    print('\trecall: {:0.2f}'.format(scorer.ents_r))
    print('\tf score: {:0.2f}'.format(scorer.ents_f))
    for ent_type in scorer.ents_per_type.keys():
        print('\nLabel: {}'.format(ent_type))
        print('\tprecision: {:0.2f}'.format(scorer.ents_per_type[ent_type]['p']))
        print('\trecall: {:0.2f}'.format(scorer.ents_per_type[ent_type]['r']))
        print('\tf score: {:0.2f}'.format(scorer.ents_per_type[ent_type]['f']))


def render_results(proc_reports, report_type):
    options = displacy_configs.DISPLACY_RENDER_OPTIONS[report_type]
    # pick random sample of documentation to display
    # displacy_sample = random.sample(proc_reports, 20)
    displacy.serve(proc_reports, style='ent', host='localhost', port=5000, options=options)


# Update Scorers
#       Compare candidate buckets to Brat buckets
#       Update total PRF and Confidence
#       Update bucket-specific PRF and Confidence
def evaluate_buckets(patient_reports, bucket_labels, metrics_filename=None, sheet_name=None):
    buckets = ['0', '1', '2', '3', '4', '5']
    total_scorer = DiaagPRFScore()
    # total_conf_list = []
    bucket_metrics = {}

    for b in buckets:
        bucket_metrics[b] = {
            'scorer': DiaagPRFScore(),
            'conf': []
        }

    for mrn, report_obj in patient_reports.items():
        if not report_obj['col'] or not report_obj['path']:
            print('missing report for patient', mrn)
            continue
        all_buckets = {'0', '1', '2', '3', '4', '5'}
        cand_buckets = set([str(b) for b in report_obj['final_buckets']])
        gold_buckets = {bucket_labels[mrn]}

        # testing max bucket
        cand_buckets = report_obj['max_bucket']

        # confidence = 1 / len(cand_buckets)
        # if int(bucket_labels[mrn]) == 34:
        #     gold_buckets = {'3', '4'}
        #     confidence = 1.0

        # update total score and confidence
        total_scorer.score_set(cand_buckets, gold_buckets)
        # total_conf_list.append(confidence)

        # update bucket scores and confidence
        TP = cand_buckets.intersection(gold_buckets)
        FP = cand_buckets - gold_buckets
        FN = gold_buckets - cand_buckets
        TN = all_buckets - cand_buckets - gold_buckets

        for b in TP:
            bucket_metrics[b]['scorer'].tp += 1
            # bucket_metrics[b]['conf'].append(confidence)
        for b in FP:
            bucket_metrics[b]['scorer'].fp += 1
        for b in FN:
            bucket_metrics[b]['scorer'].fn += 1
        for b in TN:
            bucket_metrics[b]['scorer'].tn += 1

    all_metrics = [
        {
            'Bucket': 'Overall',
            'Precision': total_scorer.precision,
            'Recall': total_scorer.recall,
            'F-Score': total_scorer.fscore,
            'False Pos': total_scorer.fp,
            'False Neg': total_scorer.fn,
            'True Pos': total_scorer.tp,
            'True Neg': 0
        }]

    # Print metrics
    print('-----')
    print('\nTOTAL METRICS:')
    # print('\tOverall Decision Confidence:', sum(total_conf_list) / len(total_conf_list))
    # print('\tPrecision: ', total_scorer.precision)
    # print('\tRecall: ', total_scorer.recall)
    # print('\tF-Score: ', total_scorer.fscore)
    # print('\nOverall Confidence:\n', sum(total_conf_list) / len(total_conf_list))
    print('Precision, Recall, Fscore')
    # print(sum(total_conf_list) / len(total_conf_list))
    print(total_scorer.precision)
    print(total_scorer.recall)
    print(total_scorer.fscore)
    print('\nconf matrix:')
    print('FP:', total_scorer.fp)
    print('FN:', total_scorer.fn)
    print('TP:', total_scorer.tp)
    # print(total_scorer.precision)
    # print(total_scorer.recall)
    # print(total_scorer.fscore)
    print('---')

    print('\nBUCKET METRICS:')
    for bucket, obj in bucket_metrics.items():
        scorer = obj['scorer']
        print('\nBucket {} Metrics:'.format(bucket))
        # print('\nConfidence:\n{}'.format(sum(obj['conf']) / len(obj['conf'])))
        print('PRF:')
        print(scorer.precision)
        print(scorer.recall)
        print(scorer.fscore)
        print('\nconf matrix:')
        print('FP:', scorer.fp)
        print('FN:', scorer.fn)
        print('TP:', scorer.tp)
        print('TN:', scorer.tn)
        all_metrics.append({
            'Bucket': bucket,
            'Precision': scorer.precision,
            'Recall': scorer.recall,
            'F-Score': scorer.fscore,
            'False Pos': scorer.fp,
            'False Neg': scorer.fn,
            'True Pos': scorer.tp,
            'True Neg': scorer.tn
        })

    print('\n---')

    metrics_df = pd.DataFrame.from_records(all_metrics)

    file_proc.append_df_to_excel(metrics_filename, metrics_df, sheet_name=sheet_name, index=False)
