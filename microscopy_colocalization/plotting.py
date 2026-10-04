"""Result plots: Manders boxplot (from channel_colocalization) and distance histogram
(from fish_colocalization), unchanged.
"""
import os

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib import ticker


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


def plot_and_save_histogram(pixel_distances, plot_path, conversion_factor=4.615):
    bin_size = 0.1

    mm_distances = [dist / conversion_factor for dist in pixel_distances]

    counts, bin_edges = np.histogram(
        mm_distances,
        bins=np.arange(min(mm_distances), max(mm_distances) + bin_size, bin_size))
    counts_percentage = counts / sum(counts)

    plt.bar(bin_edges[:-1], counts_percentage, align='center', width=bin_size)
    plt.xticks(bin_edges[:-1], rotation=45)
    plt.gca().yaxis.set_major_formatter(ticker.PercentFormatter(1.0))
    plt.xlabel('Distance (μm)')
    plt.ylabel('Percentage')
    plt.title('Distance of spots from object')

    plt.savefig(plot_path, bbox_inches='tight')
    plt.clf()
