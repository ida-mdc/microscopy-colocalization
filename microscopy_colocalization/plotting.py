"""Result plot: Manders boxplot, from channel_colocalization, unchanged."""
import os

import matplotlib.pyplot as plt
import seaborn as sns


def plot_and_save_manders(df, result_dir, c1_color, c2_color, is_show=False):
    ax = sns.boxplot(x='condition', y='M1', data=df, color='green')
    ax = sns.boxplot(x='condition', y='M2', data=df, color='yellow')
    ax.set_ylabel("Mander's Coefficient")

    legend_labels = ['M1', 'M2']
    legend_colors = [c1_color, c2_color]
    patches = [plt.Line2D([0], [0], marker='o', color='w', label=label,
                          markerfacecolor=color, markersize=10)
               for label, color in zip(legend_labels, legend_colors)]
    ax.legend(handles=patches)

    plt.savefig(os.path.join(result_dir, 'manders_boxplot.png'))
    if is_show:
        plt.show()
    plt.close()
