import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import os
import numpy as np
import copy
import datetime

import constants
import utilities


FONT_SIZE = 12
FIGURE_DIMENSIONS = (12, 6)
COLOUR_LIST = ['gold', 'darkorange', 'forestgreen', 'blue', 'black']


def create_chart_outline(x_label, y_label, set_yaxis_as_percent=False, title=None,
                         figure_dimensions=(8, 6), fontsize=14):
    """
    Setup the default figure with figure size, font size, axis labels, and title.
    """
    fig = plt.figure(1, figure_dimensions)
    ax = fig.add_subplot(1, 1, 1)
    ax.set_xlabel(x_label, fontsize=fontsize)
    ax.set_ylabel(y_label, fontsize=fontsize)
    if title is not None:
        ax.set_title(title, fontsize=fontsize, pad=20)
    ax.tick_params(axis='both', which='major', labelsize=fontsize)
    if set_yaxis_as_percent:
        ax.yaxis.set_major_formatter(PercentFormatter())  # decimals=2
    return ax


def save_figure(file_name, legend=None):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
    file_path = os.path.join(constants.SAVE_PATH, f'{file_name}_{timestamp}.png')
    if legend is not None:
        plt.savefig(file_path, dpi=400, bbox_extra_artists=(legend,), bbox_inches='tight')
    else:
        plt.savefig(file_path, dpi=400)


def plot_figure_for_experiment(results_dict, x_axis, x_label, y_lim_dict=None):
    """
    TODO: Refactor code. This is awful.
    """
    if y_lim_dict is None:
        y_lim_dict = {}

    red_in_rev_list = []
    dist_target_actual_list = []
    dist_target_vrs_list = []
    ad_slots_won_list = []
    auction_count_list = []
    housing_avg_cost_list = []
    non_housing_avg_cost_list = []
    vrs_housing_avg_cost_list = []
    vrs_non_housing_avg_cost_list = []

    for x in x_axis:
        list_of_results = results_dict[x]
        target_count = {i[0]: 0 for i in constants.GENDER}
        actual_count_without_vrs = {i[0]: 0 for i in constants.GENDER}
        actual_count_with_vrs = {i[0]: 0 for i in constants.GENDER}
        revenue_without_vrs = 0
        revenue_with_vrs = 0
        auction_count = 0

        housing_ad_slots = 0
        housing_spend = 0
        vrs_housing_ad_slots = 0
        vrs_housing_spend = 0

        non_housing_ad_slots = 0
        non_housing_spend = 0
        vrs_non_housing_ad_slots = 0
        vrs_non_housing_spend = 0

        for result in list_of_results:
            target_count[result['gender']] += 1

            # Regular auction.
            if housing_spend < constants.HOUSING_BUDGET:
                if result['winner']['idx'] == 0:
                    actual_count_without_vrs[result['gender']] += 1
                    housing_spend += result['winner']['price_paid']
                    housing_ad_slots += 1
                else:
                    non_housing_ad_slots += 1
                    non_housing_spend += result['winner']['price_paid']
            else:
                break

            # Auction with VRS
            if vrs_housing_spend < constants.HOUSING_BUDGET:
                if result['vrs_winner']['idx'] == 0:
                    actual_count_with_vrs[result['gender']] += 1
                    vrs_housing_spend += result['vrs_winner']['price_paid']
                    vrs_housing_ad_slots += 1
                else:
                    vrs_non_housing_ad_slots += 1
                    vrs_non_housing_spend += result['vrs_winner']['price_paid']

                revenue_without_vrs += result['winner']['price_paid']
                revenue_with_vrs += result['vrs_winner']['price_paid']
                auction_count += 1

        # % reduction in revenue if we use VRS.
        red_in_rev = round(((revenue_without_vrs - revenue_with_vrs) * 100) / revenue_without_vrs, 2)

        # Distance from target audience
        dist_target_actual = utilities.calc_total_variation_distance(target_count, actual_count_without_vrs)
        dist_target_vrs = utilities.calc_total_variation_distance(target_count, actual_count_with_vrs)

        # Calculate cost / impression
        housing_avg_cost = housing_spend / housing_ad_slots
        non_housing_avg_cost = non_housing_spend / non_housing_ad_slots
        vrs_housing_avg_cost = vrs_housing_spend / vrs_housing_ad_slots
        vrs_non_housing_avg_cost = vrs_non_housing_spend / vrs_non_housing_ad_slots

        # Save results
        red_in_rev_list.append(red_in_rev)
        dist_target_actual_list.append(dist_target_actual)
        dist_target_vrs_list.append(dist_target_vrs)
        ad_slots_won_list.append(vrs_housing_ad_slots)
        auction_count_list.append(auction_count)
        housing_avg_cost_list.append(housing_avg_cost)
        non_housing_avg_cost_list.append(non_housing_avg_cost)
        vrs_housing_avg_cost_list.append(vrs_housing_avg_cost)
        vrs_non_housing_avg_cost_list.append(vrs_non_housing_avg_cost)

    y_label = '% reduction in revenue'
    ax = create_chart_outline(
        x_label=x_label,
        y_label=y_label,
        set_yaxis_as_percent=True,
        title="How does the VRS system impact the ad platform's total revenue?",
        fontsize=FONT_SIZE,
        figure_dimensions=FIGURE_DIMENSIONS
    )
    ax.set_xticks(x_axis, fontsize=FONT_SIZE)
    plt.plot(x_axis, red_in_rev_list)
    if 'fig_1' in y_lim_dict:
        ax.set_ylim(y_lim_dict['fig_1'])

    plt.savefig(os.path.join(constants.SAVE_PATH, f'{x_label}_vs_{y_label}.png'), dpi=400)
    plt.show()

    y_label = 'Total variation distance from target audience'
    ax = create_chart_outline(
        x_label=x_label,
        y_label=y_label,
        title="Does VRS reduce the distance between the target and actual audience?",
        fontsize=FONT_SIZE,
        figure_dimensions=FIGURE_DIMENSIONS
    )
    plt.plot(x_axis, dist_target_actual_list, label='Without VRS')
    plt.plot(x_axis, dist_target_vrs_list, label='With VRS')
    ax.set_xticks(x_axis, fontsize=FONT_SIZE)
    legend = ax.legend(fontsize=FONT_SIZE, bbox_to_anchor=(1.04, 1), loc="upper left")
    if 'fig_2' in y_lim_dict:
        ax.set_ylim(y_lim_dict['fig_2'])

    plt.savefig(os.path.join(constants.SAVE_PATH, f'{x_label}_vs_{y_label}.png'), dpi=400,
                bbox_extra_artists=(legend, ), bbox_inches='tight')
    plt.show()

    y_label = '#Ad auctions the housing advertiser competes in'
    ax1 = create_chart_outline(
        x_label=x_label,
        y_label=y_label,
        title="What is the impact on #ad-auctions needed to spend budget and #ad slots won?",
        fontsize=FONT_SIZE,
        figure_dimensions=FIGURE_DIMENSIONS
    )
    ax1.plot(x_axis, auction_count_list, color='green', label='#Ad Auctions')
    if 'fig_3_1' in y_lim_dict:
        ax1.set_ylim(y_lim_dict['fig_3_1'])

    ax2 = ax1.twinx()
    ax2.plot(x_axis, ad_slots_won_list, label='#Ad slots won')
    ax2.set_ylabel('#Ad slots won by the housing advertiser', fontsize=FONT_SIZE)
    if 'fig_3_2' in y_lim_dict:
        ax2.set_ylim(y_lim_dict['fig_3_2'])

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    legend = ax2.legend(lines + lines2, labels + labels2, fontsize=FONT_SIZE,
                        bbox_to_anchor=(1.04, 1), loc="upper left")
    ax2.set_xticks(x_axis, fontsize=FONT_SIZE)

    plt.savefig(os.path.join(constants.SAVE_PATH, f'{x_label}_vs_{y_label}.png'), dpi=400,
                bbox_extra_artists=(legend, ), bbox_inches='tight')
    plt.show()

    y_label = 'Avg cost per impression'
    ax = create_chart_outline(
        x_label=x_label,
        y_label=y_label,
        title="How does VRS affect the cost per impression?",
        fontsize=FONT_SIZE,
        figure_dimensions=FIGURE_DIMENSIONS
    )

    plt.plot(x_axis, housing_avg_cost_list, label='Housing adv. w/o VRS', color='blue')
    plt.plot(x_axis, non_housing_avg_cost_list, label='Non-housing adv. w/o VRS', color='blue', linestyle='--')
    plt.plot(x_axis, vrs_housing_avg_cost_list, label='Housing adv. with VRS', color='black')
    plt.plot(x_axis, vrs_non_housing_avg_cost_list, label='Non-housing adv. with VRS', color='black', linestyle='--')

    ax.set_xticks(x_axis, fontsize=FONT_SIZE)
    legend = ax.legend(fontsize=FONT_SIZE, bbox_to_anchor=(1.04, 1), loc="upper left")
    if 'fig_4' in y_lim_dict:
        ax.set_ylim(y_lim_dict['fig_4'])

    plt.savefig(os.path.join(constants.SAVE_PATH, f'{x_label}_vs_{y_label}.png'), dpi=400,
                bbox_extra_artists=(legend, ), bbox_inches='tight')
    plt.show()


def code_we_used_to_demonstrate_that_vrs_creates_diff(list_of_results, batch_size):
    """
    This is here for posterity. Graphs are in meeting notes for 2023-09-05 under the 'Improving VRS' subsection.
    """
    actual_count_with_vrs = {i[0]: 0 for i in constants.GENDER}
    ad_slots_won = 0
    amount_spent_with_vrs = 0
    diff_bw_genders = []
    sx, sy = [], []
    same_x, same_y = [], []
    diff_x, diff_y = [], []

    for idx, result in list_of_results:
        # Housing advertiser won with VRS.
        if amount_spent_with_vrs < constants.HOUSING_BUDGET:
            if result['vrs_winner']['idx'] == 0:
                actual_count_with_vrs[result['gender']] += 1
                amount_spent_with_vrs += result['vrs_winner']['price_paid']
                ad_slots_won += 1

                if ad_slots_won % batch_size == 0:
                    male_slots = actual_count_with_vrs['Male']
                    female_slots = actual_count_with_vrs['Female']
                    true_diff = actual_count_with_vrs['Male'] - actual_count_with_vrs['Female']
                    exp_diff = ((result['target_gender_count']['Male'] - result['target_gender_count']['Female']) /
                                result['total_no_of_users']) * result['vrs_ad_reach']
                    if female_slots > male_slots and result['gender_var_sign']['Female'] == -1:
                        sx.append(int(ad_slots_won / 10))
                        sy.append(true_diff)

                    if np.sign(true_diff) == np.sign(exp_diff):
                        same_x.append(true_diff)
                        same_y.append(exp_diff)
                    else:
                        diff_x.append(true_diff)
                        diff_y.append(exp_diff)
                    diff_bw_genders.append(true_diff)

    x_axis = list(range(1, len(diff_bw_genders) + 1))
    x_label = 'Batch'
    y_label = 'Diff between ad slots delivered to male and female users'
    _ = create_chart_outline(
        x_label=x_label,
        y_label=y_label,
        fontsize=FONT_SIZE,
        figure_dimensions=(16, 8)
    )

    plt.plot(x_axis, diff_bw_genders)
    plt.scatter(sx, sy, s=50, color='red')
    plt.axhline(y=0, color='black', linestyle='--')
    plt.savefig(os.path.join(constants.SAVE_PATH, f'{x_label}_vs_{y_label}.png'), dpi=400)
    plt.show()

    x_label = 'Actual diff between male and female slots'
    y_label = 'Exp diff between male and female slots'
    _ = create_chart_outline(
        x_label=x_label,
        y_label=y_label,
        fontsize=FONT_SIZE,
        figure_dimensions=(8, 8)
    )

    plt.scatter(same_x, same_y)
    plt.scatter(diff_x, diff_y, color='red')
    plt.axhline(y=0, color='black', linestyle='--')
    plt.axvline(x=0, color='black', linestyle='--')
    plt.xlim((-35, 35))
    plt.ylim((-35, 35))
    plt.savefig(os.path.join(constants.SAVE_PATH, f'Actual vs exp diff between male and female slots.png'), dpi=400)
    plt.show()


def update_counts(g_count, r_count, gr_count, result):
    g_count[result['gender']] += 1
    r_count[result['race']] += 1
    r_g = f"{result['gender']}-{result['race']}"
    gr_count[r_g] += 1
    return g_count, r_count, gr_count


def calc_tvd_for_demographic_groups(target_gender, actual_gender, target_race, actual_race, target_race_gender,
                                    actual_race_gender):
    tvd_gender = utilities.calc_total_variation_distance(target_gender, actual_gender)
    tvd_race = utilities.calc_total_variation_distance(target_race, actual_race)
    tvd_gender_race = utilities.calc_total_variation_distance(target_race_gender, actual_race_gender)
    return tvd_gender, tvd_race, tvd_gender_race


def figures_for_race_gender_experiments(results_dict, x_axis, user_vrs_prob_list, x_label, y_lim_dict=None):
    if y_lim_dict is None:
        y_lim_dict = {
            'tvd': (0, 0.25),
            '50_audience': (28, 72),
            '25_audience': (10, 36)
        }

    chart_dict = {}
    for p in user_vrs_prob_list:
        chart_dict[p] = {}

        for x in x_axis:
            list_of_results = results_dict[x][p]

            target_gender = {i[0]: 0 for i in constants.GENDER}
            target_race = {i[0]: 0 for i in constants.RACE}
            target_race_gender = {f'{g[0]}-{r[0]}': 0 for g in constants.GENDER for r in constants.RACE}

            actual_gender = {i[0]: 0 for i in constants.GENDER}
            actual_race = {i[0]: 0 for i in constants.RACE}
            actual_race_gender = copy.deepcopy(target_race_gender)

            vrs_gender = {i[0]: 0 for i in constants.GENDER}
            vrs_race = {i[0]: 0 for i in constants.RACE}
            vrs_race_gender = copy.deepcopy(target_race_gender)

            housing_spend = 0
            vrs_housing_spend = 0

            for result in list_of_results:
                # Update target audience
                target_gender, target_race, target_race_gender = update_counts(target_gender, target_race,
                                                                               target_race_gender, result)

                # Regular auction.
                if housing_spend < constants.HOUSING_BUDGET:
                    if result['winner']['idx'] == 0:
                        actual_gender, actual_race, actual_race_gender = update_counts(actual_gender, actual_race,
                                                                                       actual_race_gender, result)
                        housing_spend += result['winner']['price_paid']
                else:
                    break

                # Auction with VRS
                if vrs_housing_spend < constants.HOUSING_BUDGET:
                    if result['vrs_winner']['idx'] == 0:
                        vrs_gender, vrs_race, vrs_race_gender = update_counts(vrs_gender, vrs_race,
                                                                              vrs_race_gender, result)
                        vrs_housing_spend += result['vrs_winner']['price_paid']

            tvd_gender, tvd_race, tvd_gender_race = calc_tvd_for_demographic_groups(
                target_gender, actual_gender, target_race, actual_race, target_race_gender, actual_race_gender)

            tvd_vrs_gender, tvd_vrs_race, tvd_vrs_gender_race = calc_tvd_for_demographic_groups(
                target_gender, vrs_gender, target_race, vrs_race, target_race_gender, vrs_race_gender)

            chart_dict[p][x] = {
                'target_race_gender': target_race_gender,
                'vrs_race_gender': vrs_race_gender,
                'target_race': target_race,
                'vrs_race': vrs_race,
                'target_gender': target_gender,
                'vrs_gender': vrs_gender,

                'tvd_gender': tvd_gender,
                'tvd_race': tvd_race,
                'tvd_gender_race': tvd_gender_race,
                'tvd_vrs_gender': tvd_vrs_gender,
                'tvd_vrs_race': tvd_vrs_race,
                'tvd_vrs_gender_race': tvd_vrs_gender_race,
            }

    for suffix in ['gender', 'race', 'gender_race']:
        y_label = 'Total variation distance from target audience'
        ax = create_chart_outline(
            x_label=x_label,
            y_label=y_label,
            title=f"Does VRS reduce the distance between the target and actual audience in "
                  f"terms of \n{suffix.upper().replace('_', ' and ')}?",
            fontsize=FONT_SIZE,
            figure_dimensions=FIGURE_DIMENSIONS
        )
        wo_vrs = [chart_dict[user_vrs_prob_list[0]][x][f'tvd_{suffix}'] for x in x_axis]
        plt.plot(x_axis, wo_vrs, label=f'Without VRS', color='red')
        for idx, p in enumerate(user_vrs_prob_list):
            vrs = [chart_dict[p][x][f'tvd_vrs_{suffix}'] for x in x_axis]
            plt.plot(x_axis, vrs, label=f'p = {p} (VRS)', color=COLOUR_LIST[idx])

        ax.set_xticks(x_axis, fontsize=FONT_SIZE)
        legend = ax.legend(fontsize=FONT_SIZE, bbox_to_anchor=(1.04, 1), loc="upper left")
        plt.savefig(os.path.join(constants.SAVE_PATH, f'{suffix}_{x_label}_vs_{y_label}.png'), dpi=400,
                    bbox_extra_artists=(legend,), bbox_inches='tight')
        if 'tvd' in y_lim_dict:
            ax.set_ylim(y_lim_dict['tvd'])
        plt.show()

    gender_names = [i[0] for i in constants.GENDER]
    race_names = [i[0] for i in constants.RACE]
    gender_race_names = [f'{g[0]}-{r[0]}' for g in constants.GENDER for r in constants.RACE]
    config = [
        ('vrs_gender', 50, gender_names),
        ('vrs_race', 50, race_names),
        ('vrs_race_gender', 25, gender_race_names)
    ]
    y_label = '% of actual audience'
    for key, threshold, list_of_names in config:
        for gr_idx, gr in enumerate(list_of_names):
            ax = create_chart_outline(
                x_label=x_label,
                y_label=y_label,
                title=f"Does VRS reduce the distance between the target and actual audience for \n{gr.upper()}?",
                fontsize=FONT_SIZE,
                set_yaxis_as_percent=True,
                figure_dimensions=FIGURE_DIMENSIONS
            )
            for idx, p in enumerate(user_vrs_prob_list):
                vrs = [utilities.convert_count_dict_to_list_of_perc(chart_dict[p][x][key], decimals=2)[gr_idx] for x in
                       x_axis]
                plt.plot(x_axis, vrs, label=f'p = {p} (VRS)', color=COLOUR_LIST[idx])

            ax.set_xticks(x_axis, fontsize=FONT_SIZE)
            plt.axhline(y=threshold, color='red', linestyle='--', label='% of target audience')
            legend = ax.legend(fontsize=FONT_SIZE, bbox_to_anchor=(1.04, 1), loc="upper left")

            plt.savefig(os.path.join(constants.SAVE_PATH, f'{key}_{gr}_{x_label}_vs_{y_label}.png'), dpi=400,
                        bbox_extra_artists=(legend,), bbox_inches='tight')
            _y_lim_key = f'{threshold}_audience'
            if _y_lim_key in y_lim_dict:
                ax.set_ylim(y_lim_dict[_y_lim_key])
            plt.show()


def create_housing_advertiser_mu_discrepancy_figure(results_dict, x_axis, h_mu, m_mu):
    x_label = "Non-housing advertiser's mean of lognormal distribution for female users"
    y_label = '% of actual audience'
    threshold = 25

    ax = create_chart_outline(
        x_label=x_label,
        y_label=y_label,
        set_yaxis_as_percent=True,
        title="How does difference in non-housing advertisers bid across gender affect housing advertiser's audience?",
        figure_dimensions=(12, 8)
    )

    for key, value in results_dict.items():
        if 'Male' in key:
            _style = 'dashed'
        else:
            _style = 'solid'

        _key = tuple(key.split('-'))
        if _key in constants.USE_VRS_FOR_THESE_GROUPS:
            _colour = 'pink'
            suffix = '(VRS applied)'
        else:
            _colour = 'red'
            suffix = '(No VRS)'

        plt.plot(x_axis, value, label=f"{key} {suffix}", linewidth=3, linestyle=_style, color=_colour)

    plt.axvline(x=h_mu, color='#808080', linestyle='dotted', label='Housing advertiser mu - all users', linewidth=2)
    plt.text(h_mu + 0.025, 45, 'Housing \n mu  - ALL', fontsize=FONT_SIZE)
    plt.axvline(x=m_mu, color='#808080', linestyle='dotted', label='Non-housing mu - male users', linewidth=2)
    plt.text(m_mu + 0.025, 45, 'Non-housing \n mu - MALE', fontsize=FONT_SIZE)
    plt.axhline(y=threshold, color='#808080', linestyle='dotted', label='% of target audience', linewidth=2)
    plt.text(h_mu + 0.025, 26, '% of target \n audience', fontsize=FONT_SIZE)

    ax.set_xticks(x_axis, fontsize=FONT_SIZE)
    legend = ax.legend(fontsize=FONT_SIZE, bbox_to_anchor=(1.04, 1), loc="upper left")
    ax.set_ylim((0, 50))
    plt.savefig(os.path.join(constants.SAVE_PATH, f'{x_label}_vs_{y_label}.png'), dpi=400,
                bbox_extra_artists=(legend,), bbox_inches='tight')
    plt.show()


def get_counts_by_gender_and_race(results_dict):
    target_g = {g: 0 for g in constants.GENDER_NAMES}
    target_r = {g: 0 for g in constants.RACE_NAMES}
    target_gr = {f'{g}-{r}': 0 for g in constants.GENDER_NAMES for r in constants.RACE_NAMES}
    housing_g = {g: 0 for g in constants.GENDER_NAMES}
    housing_r = {g: 0 for g in constants.RACE_NAMES}
    housing_gr = {f'{g}-{r}': 0 for g in constants.GENDER_NAMES for r in constants.RACE_NAMES}
    slots_won_due_to_vrs = {f'{g}-{r}': 0 for g in constants.GENDER_NAMES for r in constants.RACE_NAMES}
    amount_spent = 0
    for r in results_dict:
        if amount_spent < constants.HOUSING_BUDGET:
            target_g, target_r, target_gr = update_counts(target_g, target_r, target_gr, r)
            if r['vrs_winner']['idx'] == 0:
                housing_g, housing_r, housing_gr = update_counts(housing_g, housing_r, housing_gr, r)
                amount_spent += r['vrs_winner']['price_paid']
                if r['vrs_winner']['idx'] != r['winner']['idx']:
                    slots_won_due_to_vrs[f"{r['gender']}-{r['race']}"] += 1
        else:
            break
    return target_g, target_r, target_gr, housing_g, housing_r, housing_gr, slots_won_due_to_vrs
