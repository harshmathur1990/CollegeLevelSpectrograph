import sys
from pathlib import Path
import numpy as np
import imageio
import skimage.color
import sunpy.io.fits


BITFACTOR = 255


def corshft(array1, array2):

    sz1 = (np.shape(array1))[0]
    sz2 = (np.shape(array2))[0]

    xx1 = np.arange(sz1)
    coef = np.polyfit(xx1, array1, 1)
    LinfitArray1 = coef[1] + coef[0] * xx1
    Array1 = array1 - LinfitArray1

    xx2 = np.arange(sz2)
    coef = np.polyfit(xx2, array2, 1)
    LinfitArray2 = coef[1] + coef[0] * xx2
    Array2 = array2 - LinfitArray2
    corvec = np.zeros(9)
    for i in range(-4, 4 + 1):
        Difarray = Array1[4: sz1 - 5 + 1] - Array2[i + 4: sz2 - 5 + i + 1]
        corvec[i + 4] = np.sum(Difarray * Difarray)

    xmax = np.argmin(corvec[1:7 + 1]) + 2

    x = np.arange(9)
    coeff = np.polyfit(
        x[xmax - 1 - 1:xmax + 2 + 1], corvec[xmax - 1 - 1:xmax + 2 + 1], 2)
    sx = (-coeff[1] / 2. / coeff[0]) - 4
    return sx


def fshft(input_array, shft):
    nx = input_array.shape[0]
    Nx = np.fft.fftfreq(nx)
    fft_inputarray = np.fft.fft(input_array)
    fourier_shift = np.exp(1j * 2 * np.pi * shft * Nx)
    output_array = np.fft.ifft(fft_inputarray * fourier_shift)
    return np.real(output_array)


def remove_spectral_line(
    master_flat,
    reference_row=None,
    reference_columns=None
):

    if not reference_row:
        reference_row = master_flat.shape[0] / 2

    if not reference_columns:
        reference_columns = (500, 1100)

    x1, x2 = reference_columns
    reference_profile = master_flat[
        reference_row, x1:x2
    ]

    shift_vertical = np.zeros(master_flat.shape[0])

    for j in range(master_flat.shape[0]):
        _slit = master_flat[j, x1:x2]
        shift_vertical[j] = corshft(reference_profile, _slit)

    xvalues = np.arange(master_flat.shape[0])

    coef = np.polyfit(xvalues, shift_vertical, 1)




def create_dark_master(dark_files):
    dark_data_list = list()

    for dark_file in dark_files:
        dark_data_list.append(
            skimage.color.rgb2gray(
                imageio.imread(
                    dark_file
                )
            )
        )

    dark_average = np.mean(dark_data_list, axis=0)

    return dark_average * BITFACTOR


def create_flat_master(flat_files, master_dark_path):

    dark_master, _ = sunpy.io.fits.read(master_dark_path)[0]

    flat_data_list = list()

    for flat_file in flat_files:
        flat_data_list.append(
            skimage.color.rgb2gray(
                imageio.imread(
                    flat_file
                )
            ) * BITFACTOR - dark_master
        )

    return np.mean(flat_data_list, axis=0)


def generate_master_dark(
    path_to_raw_directory,
    path_to_write_directory,
    search_string='Dark',
    master_dark_filename='MasterDark.fits'
):
    all_files = path_to_raw_directory.glob('**/*')
    dark_files = [
        x for x in all_files if x.is_file() and
        x.name.endswith('.png') and search_string.lower()
        in x.name.lower()
    ]

    dark_master = create_dark_master(dark_files)

    write_path = path_to_write_directory / master_dark_filename

    sunpy.io.fits.write(
        write_path,
        dark_master,
        dict()
    )


def generate_master_flat(
    path_to_raw_directory,
    path_to_write_directory,
    search_string='NaD',
    master_dark_filename='MasterDark.fits',
    master_flat_filename='MasterFlat.fits'
):

    master_dark_path = path_to_write_directory / master_dark_filename

    if not master_dark_path.exist():
        sys.stdout.write(
            'Master Dark not found at path: {}\n'.format(
                master_dark_path.absolute()
            )
        )
        sys.stdout.write(
            'Please Create Master Dark First\n'
        )
        sys.exit(1)

    all_files = path_to_raw_directory.glob('**/*')

    flat_files = [
        x for x in all_files if x.is_file() and
        x.name.endswith('.png') and search_string.lower()
        in x.name.lower()
    ]

    master_flat = create_flat_master(flat_files, master_dark_path)

    shift_corrected_flat, shifts = remove_spectral_line(master_flat)

    write_path = path_to_write_directory / master_flat_filename

    sunpy.io.fits.write(
        write_path,
        shift_corrected_flat,
        dict()
    )


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.stdout.write(
            'Usage: python generate_master_dark.py ' +
            '<path_to_raw_directory> <path_to_write_directory>\n'
        )
        sys.stdout.write(
            'Example:\npython generate_master_dark.py ' +
            '. ./Level1\n'
        )
        sys.exit(1)
    path_to_raw_directory = Path(sys.argv[1])
    path_to_write_directory = Path(sys.argv[2])
    path_to_write_directory.mkdir(exist_ok=True)
    generate_master_dark(
        path_to_raw_directory,
        path_to_write_directory,
        search_string='Dark',
        master_dark_filename='MasterDark.fits'
    )
    generate_master_flat(
        path_to_raw_directory,
        path_to_write_directory,
        search_string='NaD',
        master_dark_filename='MasterDark.fits',
        master_flat_filename='MasterFlat.fits'
    )
