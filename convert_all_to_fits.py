import os
import sys
import platform
import datetime
from pathlib import Path
import skimage.color
import imageio
import sunpy.io.fits


BITFACTOR = 255


def get_created_time(path_to_file):
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return datetime.datetime.fromtimestamp(
                stat.st_birthtime or stat.st_ctime
            )
        except AttributeError:
            return datetime.datetime.fromtimestamp(stat.st_mtime)


def convert_png_to_fits(read_path, write_path):
    if isinstance(read_path, str):
        read_path = Path(read_path)
    if isinstance(write_path, str):
        write_path = Path(write_path)
        write_path.mkdir(exist_ok=True)

    all_files = read_path.glob('**/*')

    png_files = [
        x for x in all_files if x.is_file() and
        x.name.endswith('.png')
    ]

    for png_file in png_files:
        try:
            im = skimage.color.rgb2gray(
                imageio.imread(
                    png_file
                )
            ) * BITFACTOR
        except Exception:
            sys.stdout.write(
                'Invalid Image file: {}\n'.format(
                    png_file.absolute()
                )
            )
            continue

        png_filename = png_file.name + '.fits'

        write_path_fits = write_path / png_filename

        header = dict()

        header['obstime'] = get_created_time(png_file).isoformat()

        sunpy.io.fits.write(write_path_fits, im, header, overwrite=True)
