import argparse

from microscopy_colocalization.commands import c2c, c2p, p2p

COMMANDS = {
    'c2c': (c2c, 'Channel-to-channel: Manders overlap coefficients between two image channels.'),
    'p2p': (p2p, 'Point-to-point: match spot coordinates between two CSVs by distance.'),
    'c2p': (c2p, 'Channel-to-point: distance of each spot in a CSV to a thresholded image.'),
}


def main():
    parser = argparse.ArgumentParser(
        prog='mcoloc',
        description='Colocalization analysis for microscopy images and spot-detection CSVs.',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    for name, (module, help_text) in COMMANDS.items():
        subparser = subparsers.add_parser(name, help=help_text)
        module.add_arguments(subparser)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
