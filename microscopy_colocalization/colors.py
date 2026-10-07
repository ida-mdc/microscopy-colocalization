"""Per-channel color assignment, shared by every plot so the same channel always gets the
same color. Default palette favors saturated primaries/secondaries that read well as
microscopy overlays on a dark background (unlike matplotlib's chart-oriented qualitative
colormaps, e.g. tab10, whose muted tones look muddy there).
"""
import matplotlib.pyplot as plt

DEFAULT_COLORS = ['#00FF00', '#FF00FF', '#00FFFF', '#FF0000', '#FFFF00', '#0000FF',
                  '#FFFFFF', '#FFA500']


def _colormap_colors(colormap):
    cmap = plt.get_cmap(colormap)
    if hasattr(cmap, 'colors'):
        return list(cmap.colors)
    return [cmap(i / 19) for i in range(20)]


def channel_color(channel_index, colormap=None):
    """The color for a given channel index, consistent across every plot regardless of
    which other channels it's being compared to. colormap=None uses DEFAULT_COLORS;
    otherwise any matplotlib colormap name.
    """
    colors = DEFAULT_COLORS if colormap is None else _colormap_colors(colormap)
    return colors[channel_index % len(colors)]
