from classes.report import ColReport, PathReport
from pipelines import colon_pipelines


# returns ColReport with updated candidate buckets
def filter_buckets_col(report):
    possible_buckets = {"0": True, "1": True, "2": True, "3": True, "4": True, "5": True}
    total_indiv_polyps = 0
    polyps = report.polyps

    if polyps and len(polyps) > 0:
        # Estimate total number of individual polyps
        # include the polyp observations that didn't have quantity
        # (unless they were in a multi-sentence - probably double counting)
        quant_sum = sum([p['quantity'] for p in polyps if p['quantity']])
        if quant_sum == 0:
            quant_less_obs = len([p for p in polyps if not p['quantity']])
        else:
            quant_less_obs = len([p for p in polyps if (not p['quantity'] and not p['multi'])])
        total_indiv_polyps = quant_less_obs + quant_sum
    else:
        for b in possible_buckets.keys():
            possible_buckets[b] = False
        possible_buckets['0'] = True

    meas_large_polyp = any([p['size_meas'] and p['size_meas'] >= 1 for p in polyps])
    gen_large_polyp = any(p['size_approx'] and p['size_approx'] in ['large', 'giant', 'huge'] for p in polyps)

    report.total_polyps = total_indiv_polyps
    report.large_polyp = report.large_polyp or meas_large_polyp or gen_large_polyp

    # rule out buckets
    if total_indiv_polyps > 20:
        possible_buckets['0'] = False
    if total_indiv_polyps < 3 and not report.large_polyp:
        possible_buckets['3'] = False
    if total_indiv_polyps <= 10:
        possible_buckets['5'] = False
    if report.large_polyp:
        possible_buckets['0'] = False
        possible_buckets['1'] = False
        possible_buckets['2'] = False
        possible_buckets['3'] = True
        possible_buckets['4'] = True

    report.candidate_buckets = possible_buckets

    return report


# returns PathReport with updated candidate buckets
def filter_buckets_path(report):
    possible_buckets = {'0': True, '1': True, '2': True, '3': True, '4': True, '5': True}
    polyps = report.polyps

    if polyps and len(polyps) > 0:
        report.polyps = polyps
    elif report.mentions_hist:
        possible_buckets['0'] = False
    else:
        for b in possible_buckets.keys():
            possible_buckets[b] = False
        possible_buckets['0'] = True

    # rule out buckets
    if report.has_ssp():
        possible_buckets['0'] = False
        possible_buckets['1'] = False
    else:
        possible_buckets['2'] = False
    if report.has_adenoma():
        possible_buckets['0'] = False
    else:
        possible_buckets['1'] = False
    if report.all_hp():
        possible_buckets['4'] = False
        possible_buckets['5'] = False
    if report.has_bucket_4_hist() or report.has_dysp():
        for b in ['0', '1', '2', '3']:
            possible_buckets[b] = False
        possible_buckets['4'] = True
    if report.all_normal():
        for b in possible_buckets.keys():
            possible_buckets[b] = False
        possible_buckets['0'] = True

    report.candidate_buckets = possible_buckets

    return report


# takes ColReport, PathReport
# updates patient buckets + returns
def merge_patient_buckets(col, path):
    col_buckets = set(col.candidate_bucket_list)
    if not path:
        # if they did find polyps but we don't have path report yet
        if col.total_polyps > 0:
            return {'col_buckets': ', '.join(sorted([str(b) for b in list(col_buckets)]))}
        # otherwise it's probably a normal colonoscopy (so the final bucket depends only on colo)
        return {
            'col_buckets': ', '.join(sorted([str(b) for b in list(col_buckets)])),
            'final_bucket': min(col_buckets)
        }
    path_buckets = set(path.candidate_bucket_list)
    final_buckets = set.intersection(col_buckets, path_buckets)

    # Accounting for normal tissue samples:
    # Number of samples in path report is a LOWER BOUND on # polyps with that hist
    ta = path.hist_counts['tubular adenoma']
    ss = path.hist_counts['sessile serrated']
    hp = path.hist_counts['hyperplastic']
    # subtract normal samples (unless it goes below ta + ssp + hp)
    # adjust polyp quantity to account for normal tissue
    normal_samples = path.normal_sample_count()
    if col.total_polyps - normal_samples < ta + ss + hp:
        normal_samples = 0
    total_polyps = col.total_polyps - normal_samples
    col.adj_polyps = total_polyps

    # merged logic
    if not col.large_polyp and not path.has_bucket_4_hist() and not path.has_dysp():
        if total_polyps < 5:
            final_buckets = final_buckets - {'4'}
        if total_polyps == 5 and path.has_hp():
            final_buckets = final_buckets - {'4'}
    # Large hyperplastic polyp
    if col.large_polyp and path.all_hp() and not path.all_normal():
        final_buckets = {'3'}
    # Large polyp with other histology (TA, SSP, etc)
    if col.large_polyp and not path.has_hp() and not path.all_normal():
        if total_polyps <= 10:
            final_buckets = {'4'}
        else:
            final_buckets = {'5'}
    if not col.large_polyp and path.all_hp():
        final_buckets = final_buckets - {'3'}
    if total_polyps == 3 and not col.large_polyp and path.has_hp():
        final_buckets = final_buckets - {'3'}
    if total_polyps < 3 and not col.large_polyp:
        final_buckets = final_buckets - {'3'}

    # Rough lower bound on # polyps w/ hist: Count of polyp obs
    if ta + ss > 2:
        final_buckets = final_buckets - {'0', '1', '2'}
    if ta + ss > 4:
        final_buckets = final_buckets - {'3'}
    if ta + ss > 10:
        final_buckets = final_buckets - {'4'}
    # more than 20 hp --> bucket 5
    if hp > 20:
        final_buckets = {'5'}

    # If all buckets were ruled out, leave empty to represent "undecided"
    if len(final_buckets) == 0:
        final_bucket = None
    else:
        final_bucket = max(final_buckets)

    return {
        'col_buckets': ', '.join(sorted([str(b) for b in list(col_buckets)])),
        'path_buckets': ', '.join(sorted([str(b) for b in list(path_buckets)])),
        'final_bucket': final_bucket
    }


# given col + path polyps, get recs and merge buckets
def make_rec(col_polyps, path_polyps, large_polyp=None, mentions_hist=None, **kwargs):
    _ = kwargs
    col_report = ColReport(polyps=col_polyps, large_polyp=large_polyp)
    col = filter_buckets_col(col_report)

    # Handle case where path report was normal -> Initialize even if path_polyps is an empty list
    # the arg mentions_hist will only be None if there is truly no path report
    if path_polyps is not None and mentions_hist is not None:
        path_report = PathReport(polyps=path_polyps, mentions_hist=mentions_hist)
        path = filter_buckets_path(path_report)
    else:
        path = None

    all_buckets = merge_patient_buckets(col, path)

    computed = {
        'indiv_polyp_count': col.total_polyps,
        'adj_polyp_count': col.adj_polyps
    }

    return all_buckets, computed


# given col + path text, run through pipeline and merge buckets
def make_rec_from_text(col_text, path_text, **kwargs):
    _ = kwargs

    # Run colo report through pipeline to get polyps
    col_report = colon_pipelines.col_pipeline(col_text)

    # Filter buckets using colo polyps
    col = filter_buckets_col(col_report)

    # If there's a path report, run through pipeline to get polyps
    if not path_text:
        path = None
    else:
        path_report = colon_pipelines.path_pipeline(path_text)
        # Filter buckets using path polyps
        path = filter_buckets_path(path_report)

    # Merge candidate buckets to get final rec if possible
    all_buckets = merge_patient_buckets(col, path)

    computed = {
        'indiv_polyp_count': col.total_polyps,
        'adj_polyp_count': col.adj_polyps,
        'large_polyp': col.large_polyp
    }

    flags = {
        'poor_prep' : col.review_flags['poor_prep'],
        'incomplete_proc': col.review_flags['incomplete_proc'],
        'retained_polyp': col.review_flags['retained_polyp'],
        'malignancy': path.review_flags['malignancy'] if path else False,
        'many_polyps': True if computed['adj_polyp_count'] and computed['adj_polyp_count'] > 10 else False
    }

    return all_buckets, flags, col_report.report_props, col_report.quality_metrics, computed
