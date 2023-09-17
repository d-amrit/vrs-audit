import numpy as np
import random

import constants


class CustomError(Exception):
    pass


def draw_from_multinomial_distribution(discrete_dist, n=1):
    """
    discrete_dist: List of tuples (subgroup, Pr[subgroup]). Example: [('Male', 0.5), ('Female', 0.5)]
    """
    pvals = [i[1] for i in discrete_dist]
    assert sum(pvals) == 1, 'Please provide a valid distribution.'

    assert n == 1, 'Write code to handle multiple draws!'
    _result = np.random.multinomial(n=n, pvals=pvals)

    _subgroup_idx = _result.argmax()
    selected_subgroup = discrete_dist[_result.argmax()][0]
    return selected_subgroup


def initialize_random_state(random_state):
    """
    Seed the generator for different libraries to get consistent results.
    """
    if random_state is not None:
        np.random.seed(random_state)
        random.seed(random_state)
    return random_state


def convert_count_dict_to_list_of_perc(count_dict, decimals=10, multiply_by=100.0, return_dict=False):
    total = sum(count_dict.values())
    _perc = {key: round((i * multiply_by) / total, decimals) for key, i in count_dict.items()}
    if return_dict:
        return _perc
    return list(_perc.values())


def calc_total_variation_distance(dist_1, dist_2, normalize=True, multiply_by=1.0, decimals=5, return_dist=False):
    if normalize:
        dist_1 = convert_count_dict_to_list_of_perc(dist_1, multiply_by=multiply_by)
        dist_2 = convert_count_dict_to_list_of_perc(dist_2, multiply_by=multiply_by)
    frac_diff = [abs(t - dist_2[i]) for i, t in enumerate(dist_1)]
    tvd = round(0.5 * sum(frac_diff), decimals)

    if return_dist:
        return tvd, dist_1, dist_2
    else:
        return tvd


def find_max_discrepancy_for_one_demographic_over_another(value_dict, first_demographic, second_demographic,
                                                          demo_format):
    _discrepancy = []
    _no_of_subgroups = len(second_demographic)
    for g in first_demographic:
        for i in range(_no_of_subgroups):
            for j in range(_no_of_subgroups):
                if i != j and i < j:
                    if demo_format == '1-2':
                        d1 = f'{g}-{second_demographic[i]}'
                        d2 = f'{g}-{second_demographic[j]}'
                    else:
                        d1 = f'{second_demographic[i]}-{g}'
                        d2 = f'{second_demographic[j]}-{g}'
                    _discrepancy.append(abs(value_dict[d1] - value_dict[d2]))
    return _discrepancy


def find_max_discrepancy(value_dict):
    d1 = find_max_discrepancy_for_one_demographic_over_another(
        value_dict,
        first_demographic=constants.GENDER_NAMES,
        second_demographic=constants.RACE_NAMES,
        demo_format='1-2'
    )
    d2 = find_max_discrepancy_for_one_demographic_over_another(
        value_dict,
        first_demographic=constants.RACE_NAMES,
        second_demographic=constants.GENDER_NAMES,
        demo_format='2-1'
    )
    return max(d1 + d2)
