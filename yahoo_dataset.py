import pandas
import numpy as np
from scipy.stats import norm, lognorm
import matplotlib.pyplot as plt

import create_figures


def fit_lognormal_data(data, plot_fit=True):
    # Step 1: Transform the data
    transformed_data = np.log(data)

    # Step 2: Fit the transformed data to a normal distribution
    mu, sigma = norm.fit(transformed_data)

    # Step 3: Use the parameters for the lognormal distribution
    shape = sigma
    scale = np.exp(mu)

    if plot_fit:
        # Plot the histogram and fitted PDF
        plt.hist(data, bins=50, density=True, alpha=0.6, color='b', label="Observed Data")
        x_min, x_max = plt.xlim()
        x = np.linspace(x_min, x_max, 100)
        pdf = lognorm.pdf(x, shape, scale=scale)
        plt.plot(x, pdf, 'k', linewidth=2, label="Fitted PDF")
        plt.legend()
        plt.title("Fit data to Lognormal distribution")
        plt.show()

    return round(np.log(scale), 2), round(shape, 2)


class FitLogNormal:
    def __init__(self):
        self.df = self.read()
        self.remove_missing_prices()
        mean_list, sigma_list = self.fit_lognormal_for_each_phrase()
        self.gen_boxplot(metric='Mean', list_of_values=mean_list)
        self.gen_boxplot(metric='Standard deviation', list_of_values=sigma_list)

    @staticmethod
    def read():
        file_path = '/Users/amrit/Downloads/dataset/ydata-ysm-advertiser-bids-v1_0.txt'
        _columns = ['Timestamp', 'Phrase_ID', 'Account_ID', 'Price', 'Auto']
        df = pandas.read_csv(file_path, delimiter='\t', names=_columns)
        return df

    def remove_missing_prices(self):
        _mask = (self.df['Price'].isnull()) | (self.df['Price'] < 0)
        self.df = self.df.loc[self.df[~_mask].index, ].reset_index(drop=True)

    def fit_lognormal_for_each_phrase(self):
        mean_list, sigma_list = [], []
        phrase_list = self.df['Phrase_ID'].unique()
        for phrase in phrase_list:
            bid_list = self.df.loc[self.df[self.df['Phrase_ID'] == phrase].index, 'Price'].tolist()
            mu, sigma = fit_lognormal_data(bid_list, plot_fit=False)
            mean_list.append(mu)
            sigma_list.append(sigma)
        return mean_list, sigma_list

    @staticmethod
    def gen_boxplot(metric, list_of_values):
        create_figures.create_chart_outline(
            x_label='',
            y_label=f'{metric} of fitted lognormal distribution for each keyword',
            set_yaxis_as_percent=False,
            title=f"How much does {metric.lower()} vary across different keywords in Yahoo dataset?",
            fontsize=create_figures.FONT_SIZE,
            figure_dimensions=(8, 6)
        )
        plt.boxplot(list_of_values)
        _file_name = f'{metric} of fitted lognormal distribution for each keyword in Yahoo dataset.png'
        create_figures.save_figure(_file_name)
        plt.show()


if __name__ == '__main__':
    _ = FitLogNormal()
