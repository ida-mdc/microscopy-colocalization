# microscopy-colocalization

Colocalization analysis for microscopy images and spot-detection CSVs (e.g. RS-FISH).  

Run `mcoloc`with three subcommands:

- `c2c` (channel-to-channel): Manders' overlap coefficients between two channels of the same
  multi-channel image, or across all channel pairs with `--all-channel-pairs`.
- `p2p` (point-to-point): matches spot coordinates between two CSVs (e.g. RS-FISH output) by
  nearest-neighbor distance.
- `c2p` (channel-to-point): distance of each spot in a CSV to the nearest thresholded object
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
mcoloc c2c -p /path/to/images -ext tif -c1i 0 -c2i 1
mcoloc p2p -i /path/to/csvs -p1 '*.csv' -p2 'C1-*.csv'
mcoloc c2p -i /path/to/data -p1 '*.tif' -p2 '*.csv'
```

Run `mcoloc <command> --help` any time for the full, up-to-date argument list, including
defaults and which arguments are required for each command.

### `c2c`: channel-to-channel

| Flag | Meaning |
|---|---|
| `-p`, `--path` (required) | Root folder of images, laid out as `condition/file` or `condition/run/file`. |
| `-ext`, `--extension` (required) | Image file extension to look for, e.g. `tif`, `czi`, `ims` (no dot). |
| `-c1i`, `--channel1` | Index of the first channel to compare (0 is the first channel). Required unless `--all-channel-pairs` is set. |
| `-c2i`, `--channel2` | Index of the second channel to compare. Required unless `--all-channel-pairs` is set. |
| `--all-channel-pairs` | Run every unique pair of channels found in each image instead of one fixed pair. Cannot be combined with `--channel1`/`--channel2`. |
| `-c1c`, `--color1` | Display color for channel 1 in the output plot. Default: `green`. |
| `-c2c`, `--color2` | Display color for channel 2 in the output plot. Default: `yellow`. |
| `-tm`, `--threshold_method` | `otsu`, `li`, `triangle`, or `yen`. Default: `otsu`. |

### `p2p`: point-to-point

| Flag | Meaning |
|---|---|
| `-i`, `--input_path` (required) | Folder containing the CSV files (also searched one level deep). |
| `-p1`, `--pattern1` (required) | Filename wildcard for the first group of CSVs, e.g. `'C1-*.csv'`. |
| `-p2`, `--pattern2` (required) | Filename wildcard for the second group of CSVs, e.g. `'C2-*.csv'`. |
| `-d`, `--min_dist` | Maximum distance (pixels) between two points for them to count as a match. Default: `2`. |

### `c2p`: channel-to-point

| Flag | Meaning |
|---|---|
| `-i`, `--input_path` (required) | Folder containing the images and CSVs (also searched one level deep). |
| `-p1`, `--pattern1` (required) | Filename wildcard for the image files, e.g. `'*.tif'`. |
| `-p2`, `--pattern2` (required) | Filename wildcard for the point CSV files, e.g. `'*.csv'`. |
| `-c`, `--image_channel` | Channel index to use from each image. Required if the images are multi-channel; leave at the default `-1` for plain 2D images with no channel axis. |
| `-t`, `--threshold_method` | `otsu`, `li`, `triangle`, or `yen`. Default: `otsu`. |

## License

MIT
