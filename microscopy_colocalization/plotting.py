"""Result plot: Manders boxplot, one per channel pair, from channel_colocalization.

Rewritten from the original's two overlapping sns.boxplot calls (which drew M1 and M2 at the
same x positions on top of each other) to one hue-dodged call, so M1/M2 are actually
side-by-side and the channel colors are real box colors, not just legend swatches.
"""
import os

import matplotlib.pyplot as plt
import seaborn as sns


def plot_and_save_manders(df, result_dir, c1_color, c2_color, pair_tag, is_show=False):
    long_df = df.melt(id_vars=['condition'], value_vars=['M1', 'M2'],
                       var_name='metric', value_name='value')

    ax = sns.boxplot(x='condition', y='value', hue='metric', data=long_df,
                      palette={'M1': c1_color, 'M2': c2_color})
    ax.set_ylabel("Mander's Coefficient")
    ax.get_legend().set_title(None)

    plt.savefig(os.path.join(result_dir, f'manders_boxplot_{pair_tag}.png'))
    if is_show:
        plt.show()
    plt.close()
