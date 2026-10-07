# microscopy-colocalization

Colocalization analysis for microscopy images and spot-detection CSVs (e.g. RS-FISH).  

Run `mcoloc` with three subcommands:

- `c2c` (channel-to-channel): Manders' overlap coefficients between two or more channels of
  the same multi-channel image; with more than two channels, every unique pair is compared.
- `p2p` (point-to-point): matches spot coordinates between two or more CSVs (e.g. RS-FISH
  output per channel) by nearest-neighbor distance; with more than two, every unique pair is
  compared.
- `p2c` (point-to-channel): distance of each spot in a CSV to the nearest thresholded object
  in an image.

Supports tif/tiff, HDF5/.ims (including Imaris), and anything else `bioio` reads (czi, nd2, lif,
png/jpg, etc.) via one shared multi-format reader.

## Installation

Uses [uv](https://docs.astral.sh/uv/) for environment and package management. Install uv first if
you don't have it:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Clone the repo, then create a virtual environment and install the package into it:

```
git clone https://github.com/ida-mdc/microscopy-colocalization
cd microscopy-colocalization
uv venv
source .venv/bin/activate
uv pip install .
```

## Usage

```
mcoloc c2c -p /path/to/images -ext tif -c 0 -c 1
mcoloc p2p -p /path/to/csvs --pattern 'C1-*.csv' --pattern 'C2-*.csv'
mcoloc p2c -p /path/to/data -p1 '*.csv' -p2 '*.tif'
```

Run `mcoloc <command> --help` any time for the full, up-to-date argument list, including
defaults and which arguments are required for each command.

### `c2c`: channel-to-channel

| Flag | Meaning |
|---|---|
| `-p`, `--path` (required) | Root folder of images, laid out as `condition/file` or `condition/run/file`. |
| `-ext`, `--extension` | Image file extension to look for, e.g. `tif`, `czi`, `ims` (no dot). If omitted, scans for every supported format. |
| `-c`, `--channels` (required, give 2+) | Index of a channel to compare, repeat the flag for each one, e.g. `-c 0 -c 1`. With more than 2, every unique pair is compared. |
| `--colormap` | Matplotlib colormap name; each channel index gets one color from it, used consistently in every plot. Default: a small built-in palette of microscopy-overlay-style colors. |
| `-tm`, `--threshold_method` | `otsu`, `li`, `triangle`, or `yen`. Default: `otsu`. |

Output: `stats.csv` (one row per image per channel pair: thresholds and M1/M2), one
`manders_boxplot_c<i>_c<j>.png` per channel pair, and per-image-per-pair thresholded/overlap
mask tif files.

### `p2p`: point-to-point

| Flag | Meaning |
|---|---|
| `-p`, `--path` (required) | Folder containing the CSV files (also searched one level deep). |
| `--pattern` (required, give 2+) | Filename wildcard for one group of CSVs, repeat the flag for each one, e.g. `--pattern 'C1-*.csv' --pattern 'C2-*.csv'`. With more than 2, every unique pair is compared. |
| `-d`, `--max_dist` | Maximum distance (pixels) between two points for them to count as a match. Default: `2`. |

Output: `summary.csv` (one row per image per pattern pair: point counts, match count, mean
distance) and one `<tag1><tag2><index>.csv` per image per pair (e.g. `C1-C2-0.csv`) listing
the matched points and their distances.

### `p2c`: point-to-channel

| Flag | Meaning |
|---|---|
| `-p`, `--path` (required) | Folder containing the images and CSVs (also searched one level deep). |
| `-p1`, `--pattern1` (required) | Filename wildcard for the point CSV files, e.g. `'*.csv'`. |
| `-p2`, `--pattern2` | Filename wildcard for the image files, e.g. `'*.tif'`. If omitted, scans for every supported image format. |
| `-c`, `--channel` | Index of the channel to use from each image (0 is the first channel). Required if the images are multi-channel; leave at the default `-1` for plain 2D images with no channel axis. |
| `-tm`, `--threshold_method` | `otsu`, `li`, `triangle`, or `yen`. Default: `otsu`. |

Output: `distances.csv`, the distance of every point to its nearest thresholded object.

## Testing

```
uv pip install -e ".[test]"
pytest
```

## License

MIT
