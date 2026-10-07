from microscopy_colocalization.colors import DEFAULT_COLORS, channel_color


def test_default_colors_differ_per_channel():
    assert channel_color(0) != channel_color(1)


def test_default_colors_cycle():
    assert channel_color(0) == channel_color(len(DEFAULT_COLORS))


def test_custom_colormap_is_deterministic_and_differs_from_default():
    assert channel_color(0, 'tab10') == channel_color(0, 'tab10')
    assert channel_color(0, 'tab10') != channel_color(0)
