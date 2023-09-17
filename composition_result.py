import numpy as np
import matplotlib.pyplot as plt

import experiment
import create_figures
import utilities
import constants


class CompositionResult:
    def __init__(self, experiment_params, 
                 x_var_name,  x_axis, x_label,
                 series_var_name, series_list, series_label,
                 exp_id=None):
        self.experiment_params = experiment_params
        
        self.series_var_name = series_var_name
        self.series_list = series_list
        self.series_label = series_label
        self.x_var_name = x_var_name
        self.x_axis = x_axis
        self.x_label = x_label
        
        self.exp_id = exp_id

        # Variables used to generate figures.
        self.gender_race_list = [f'{g}-{r}' for g in constants.GENDER_NAMES for r in constants.RACE_NAMES]
        self.housing_audience = {series: {i: [] for i in self.gender_race_list} for series in series_list}
        self.housing_audience_p = {series: {i: [] for i in self.gender_race_list} for series in series_list}
        self.slots_won_due_to_vrs_p = {series: {i: [] for i in self.gender_race_list} for series in series_list}
        self.tvd_dict = {series: {'Gender': [], 'Race': [], 'Gender-Race': []} for series in series_list}
        self.max_discrepancy_dict = {series: [] for series in series_list}

    def simulate_single_experiment(self, x, series):
        self.experiment_params[self.x_var_name] = x
        self.experiment_params[self.series_var_name] = series
        e = experiment.Experiment(**self.experiment_params)
        e.simulate()
        return e

    def calc_tvd_for_demographic_groups(self, e, series):
        # Get counts by gender and race for target and actual audience.
        _r = create_figures.get_counts_by_gender_and_race(e.results)
        target_g, target_r, target_gr, housing_g, housing_r, housing_gr, slots_won_due_to_vrs = _r

        # Calculate TVD by gender and race.
        self.tvd_dict[series]['Gender'].append(utilities.calc_total_variation_distance(target_g, housing_g))
        self.tvd_dict[series]['Race'].append(utilities.calc_total_variation_distance(target_r, housing_r))
        self.tvd_dict[series]['Gender-Race'].append(utilities.calc_total_variation_distance(target_gr, housing_gr))

        return housing_gr, slots_won_due_to_vrs

    def calc_perc_housing_audience_by_demographic(self, housing_gr, series):
        housing_gr_p = utilities.convert_count_dict_to_list_of_perc(housing_gr, return_dict=True)
        for key in self.gender_race_list:
            # % of audience by gender-race
            self.housing_audience[series][key].append(housing_gr[key])
            self.housing_audience_p[series][key].append(housing_gr_p[key])
        self.max_discrepancy_dict[series].append(utilities.find_max_discrepancy(housing_gr_p))

    def calc_perc_housing_slots_won_due_to_vrs(self, housing_gr, slots_won_due_to_vrs, series):
        for key in self.gender_race_list:
            if housing_gr[key] != 0:
                _p = (slots_won_due_to_vrs[key] / housing_gr[key]) * 100.0
            else:
                _p = np.nan
            self.slots_won_due_to_vrs_p[series][key].append(_p)

    def run_experiment(self):
        for series in self.series_list:
            for x in self.x_axis:
                e = self.simulate_single_experiment(x, series)

                housing_audience_by_gender_and_race, slots_won_due_to_vrs = \
                    self.calc_tvd_for_demographic_groups(e, series)
                self.calc_perc_housing_audience_by_demographic(housing_audience_by_gender_and_race, series)
                self.calc_perc_housing_slots_won_due_to_vrs(housing_audience_by_gender_and_race,
                                                            slots_won_due_to_vrs, series)

    def create_figures(self):
        # Weirdly, if we set custom_color_and_style to False/True instead of 0/1, it flips it.
        config_list = [
            {
                'y_label': "TVD between housing advertiser's target and actual audience",
                'set_yaxis_as_percent': False,
                'data_dict': self.tvd_dict,
                'custom_color_and_style': len(self.series_list),
                'file_name': 'TVD by gender and race vs Diff between mu',
                'y_lim': None,
                'skip': False,
                'grid': False
            },
            {
                'y_label': "% of housing advertiser's actual audience",
                'set_yaxis_as_percent': True,
                'data_dict': self.housing_audience_p,
                'custom_color_and_style': 2,
                'file_name': 'Housing audience breakdown by race-gender subgroups',
                'y_lim': (-5, 55),
                'skip': False,
                'grid': False
            },
            # {
            #     'y_label': "% of ad slots won due to VRS",
            #     'set_yaxis_as_percent': True,
            #     'data_dict': self.slots_won_due_to_vrs_p,
            #     'custom_color_and_style': 2,
            #     'file_name': 'VRS prevents us from creating a 0-50 counterexample',
            #     'y_lim': (-5, 55),
            #     'skip': self.exp_id is not None,
            #     'grid': False
            # },
            # {
            #     'y_label': "Max discrepancy between same gender (resp. race) \n across different race (resp. gender)",
            #     'set_yaxis_as_percent': True,
            #     'data_dict': self.max_discrepancy_dict,
            #     'custom_color_and_style': 1,
            #     'file_name': 'Max discrepancy between subgroups',
            #     'y_lim': (-5, 55),
            #     'skip': self.series_var_name not in ['user_vrs_prob', 'no_of_non_housing_advertisers'],
            #     'grid': True
            # },
            # {
            #     'y_label': "Number of housing ads shown",
            #     'set_yaxis_as_percent': False,
            #     'data_dict': self.housing_audience,
            #     'custom_color_and_style': 2,
            #     'file_name': 'Number of housing ads shown',
            #     'y_lim': None,
            #     'skip': self.series_var_name not in ['no_of_non_housing_advertisers'],
            #     'grid': False,
            #     'exclude_key': 'Male'
            # }
        ]

        # TODO: Don't hard code this!
        if self.exp_id == 'vary_only_along_gender_lines':
            config_list[0]['exclude_key'] = 'Gender-Race'
            config_list[1]['key_filter'] = 'White'

        for config in config_list:
            if not config['skip']:
                self.create_figure_from_config(config)

    def create_figure_from_config(self, config):
        ax = create_figures.create_chart_outline(
            x_label=self.x_label,
            y_label=config['y_label'],
            set_yaxis_as_percent=config['set_yaxis_as_percent'],
            figure_dimensions=(12, 8)
        )

        for series in self.series_list:
            _series_data = config['data_dict'][series]
            if type(_series_data) == dict:
                for key, value in _series_data.items():
                    if 'exclude_key' not in config or config['exclude_key'] not in key:
                        if 'key_filter' not in config or config['key_filter'] in key:
                            self._plot_series(series, key, value, config)
            else:
                self._plot_series(series, series, _series_data, config)

        # TODO: Remove hard-coding of plot lines.
        self._add_plot_lines(config['file_name'])

        if config['y_lim'] is not None:
            ax.set_ylim(config['y_lim'])

        ax.set_xticks(self.x_axis, fontsize=create_figures.FONT_SIZE)
        legend = ax.legend(fontsize=create_figures.FONT_SIZE, bbox_to_anchor=(1.04, 1), loc="upper left")
        create_figures.save_figure(file_name=self._gen_file_name(config['file_name']), legend=legend)

        if config['grid']:
            plt.grid()

        plt.show()

    def run(self):
        self.run_experiment()
        self.create_figures()

    # --------------------------------------------------------------------------------------------------------------
    # Helper functions.
    # --------------------------------------------------------------------------------------------------------------
    def _add_color_and_style(self, series, key, _style='solid'):
        if len(self.series_list) > 1:
            _idx = self.series_list.index(series)
            _color = constants.COLOR_LIST[_idx]
        else:
            if 'Male' in key:
                _color = 'blue'
            else:
                _color = 'green'

        if 'African American' in key or 'Race' in key:
            _style = 'dashed'

        return _color, _style

    def _gen_file_name(self, file_name):
        if self.exp_id is not None:
            file_name = f'{self.exp_id}_{file_name}'
        return file_name

    def _plot_series(self, series, key, value, config):
        _label = self._get_series_label(series, key)
        if config['custom_color_and_style'] == 1:
            plt.plot(self.x_axis, value, label=_label, linewidth=2)
        else:
            _color, _style = self._add_color_and_style(series, key)
            plt.plot(self.x_axis, value, label=_label, linewidth=2,
                     color=_color, linestyle=_style)

    def _get_series_label(self, series, key):
        if len(self.series_list) == 1:
            return key
        elif series == key:
            return f'{self.series_label} = {series}'
        else:
            return f'{key} ({self.series_label} = {series})'

    def _add_plot_lines(self, file_name):
        if file_name == 'TVD by gender and race vs Diff between mu':
            for c in constants.COMPLIANCE_REQUIREMENTS:
                _label = f'{int(c * 100)}% compliance'
                plt.axhline(y=c, color='red', linestyle='dotted', label='_' + _label, linewidth=2)
                plt.text(self.x_axis[0], c + 0.002, _label, fontsize=create_figures.FONT_SIZE)

        elif file_name == 'Housing audience breakdown by race-gender subgroups':
            plt.axhline(y=25, color='red', linestyle='dotted', label='_% of target audience', linewidth=2)
            plt.text(self.x_axis[-3] + 0.25, 26, '% of target audience', fontsize=create_figures.FONT_SIZE)

            # TODO: Better flag?
            if 'user_vrs_prob' not in self.experiment_params:
                plt.axhline(y=4, color='#36454F', linestyle='dotted', label='_no_progress', linewidth=2)
                plt.text(3.1, 2, 'Stagnates at ~5% after difference >= 3', fontsize=create_figures.FONT_SIZE)
            elif self.exp_id != 'vary_only_along_gender_lines':
                plt.axhline(y=0, color='#36454F', linestyle='dotted', label='_0%', linewidth=2)
                plt.text(-2.25, 1, "~0% of housing advertiser's actual audience", fontsize=create_figures.FONT_SIZE)

                plt.axhline(y=50, color='#36454F', linestyle='dotted', label='_50%', linewidth=2)
                plt.text(-2.25, 51, "~50% of housing advertiser's actual audience", fontsize=create_figures.FONT_SIZE)

        elif file_name == 'VRS prevents us from creating a 0-50 counterexample':
            plt.text(4, 39, 'Male-Black and Female-White \nusers receive all their ad slots \ndue to VRS.',
                     fontsize=create_figures.FONT_SIZE)

        if self.exp_id == 'vary_only_along_gender_lines':
            if self.experiment_params['housing_value_mu'] != self.experiment_params['non_housing_value_male_mu']:
                plt.axvline(x=self.experiment_params['housing_value_mu'],
                            color='#808080', linestyle='dotted', label='_Housing mu - All', linewidth=2)
                plt.text(self.experiment_params['housing_value_mu'] + 0.025, 0.15, 'Housing mu - All',
                         fontsize=create_figures.FONT_SIZE)

                plt.axvline(x=self.experiment_params['non_housing_value_male_mu'],
                            color='#808080', linestyle='dotted', label='_Non-housing mu - Male', linewidth=2)
                plt.text(self.experiment_params['non_housing_value_male_mu'] + 0.025, 0.15, 'Non-housing mu - Male',
                         fontsize=create_figures.FONT_SIZE)
            else:
                plt.axvline(x=self.experiment_params['housing_value_mu'],
                            color='#808080', linestyle='dotted', label='_Housing mu - All = \nNon-housing mu - Male',
                            linewidth=2)
                plt.text(self.experiment_params['housing_value_mu'] + 0.025, 0.15,
                         'Housing mu - All = \n Non-housing mu - Male',
                         fontsize=create_figures.FONT_SIZE)
