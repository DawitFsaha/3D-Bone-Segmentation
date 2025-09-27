# image_processing.py
import SimpleITK as sitk
from PyQt5.QtGui import QImage, qRgb
import numpy as np
import scipy.ndimage as ndimage


def load_image(filename):
    try:
        image = sitk.ReadImage(filename)
        return image
    except Exception as e:
        print(f"Failed to load image: {str(e)}")
        return None


def load_image_series(folder):
    try:
        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(folder)
        reader.SetFileNames(dicom_names)
        image = reader.Execute()
        return image
    except Exception as e:
        print(f"Failed to load image series: {str(e)}")
        return None


def get_slice(image, index, orientation='axial'):
    try:
        array = sitk.GetArrayFromImage(image)
        if orientation == 'axial':
            slice = array[index, :, :]
        elif orientation == 'coronal':
            slice = array[:, index, :]
        elif orientation == 'sagittal':
            slice = array[:, :, index]
        return slice
    except Exception as e:
        print(f"Failed to get slice: {str(e)}")
        return None


def normalize_slice_safe(slice_data):
    """Safely normalize a slice to 0-255 range, handling edge cases"""
    try:
        slice_min = slice_data.min()
        slice_max = slice_data.max()

        # Handle case where min == max (uniform slice)
        if slice_max == slice_min:
            # Return a uniform array with middle gray value
            return np.full(slice_data.shape, 128, dtype=np.uint8)

        # Normal normalization
        slice_normalized = ((slice_data - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)
        return slice_normalized

    except Exception as e:
        print(f"Warning: Error in slice normalization: {e}")
        # Fallback: clip to 0-255 range
        return np.clip(slice_data, 0, 255).astype(np.uint8)


def create_qimage_from_slice(slice, target_size=(400, 400)):
    try:
        height, width = slice.shape
        bytes_per_line = width
        slice_normalized = normalize_slice_safe(slice)
        qimage = QImage(slice_normalized.data, width, height, bytes_per_line, QImage.Format_Indexed8)

        # Set color table (grayscale)
        gray_color_table = [qRgb(i, i, i) for i in range(256)]
        qimage.setColorTable(gray_color_table)

        return qimage
    except Exception as e:
        print(f"Failed to create QImage from slice: {str(e)}")
        return None


def apply_threshold(slice, threshold_value):
    try:
        thresholded_slice = (slice > threshold_value) * slice
        return thresholded_slice
    except Exception as e:
        print(f"Failed to apply threshold: {str(e)}")
        return None


def adjust_contrast(slice, contrast_value):
    try:
        factor = (259 * (contrast_value + 255)) / (255 * (259 - contrast_value))
        adjusted_slice = np.clip(128 + factor * (slice - 128), 0, 255)
        return adjusted_slice.astype(np.uint8)
    except Exception as e:
        print(f"Failed to adjust contrast: {str(e)}")
        return None


def apply_windowing(image, min_val, max_val):
    try:
        if isinstance(image, sitk.Image):
            array = sitk.GetArrayFromImage(image)
        else:
            array = image.copy()

        print(f"Applying windowing: min_val={min_val}, max_val={max_val}")
        print(f"Original array range: {array.min()} to {array.max()}")

        # Ensure we're working with float for precise calculations
        array = array.astype(np.float64)

        # Apply windowing: clamp values to the window range
        windowed_array = np.clip(array, min_val, max_val)

        # Scale to 0-255 range for display
        if max_val > min_val:
            # Normalize to 0-1 range first
            windowed_array = (windowed_array - min_val) / (max_val - min_val)
            # Scale to 0-255
            windowed_array = windowed_array * 255.0
        else:
            # If min_val == max_val, set everything to middle gray
            windowed_array = np.full_like(windowed_array, 127.0)

        # Convert to uint8
        windowed_array = np.clip(windowed_array, 0, 255).astype(np.uint8)

        print(f"Windowed array range: {windowed_array.min()} to {windowed_array.max()}")

        if isinstance(image, sitk.Image):
            windowed_image = sitk.GetImageFromArray(windowed_array)
            windowed_image.CopyInformation(image)
            return windowed_image
        else:
            return windowed_array

    except Exception as e:
        print(f"Failed to apply windowing: {str(e)}")
        return image


def apply_gaussian_filter(image, sigma=1):
    try:
        array = sitk.GetArrayFromImage(image)
        filtered_array = ndimage.gaussian_filter(array, sigma=sigma)
        filtered_image = sitk.GetImageFromArray(filtered_array)
        filtered_image.CopyInformation(image)
        print("Gaussian filter applied with sigma =", sigma)
        return filtered_image
    except Exception as e:
        print(f"Failed to apply Gaussian filter: {str(e)}")
        return None


def apply_median_filter(image, size=3):
    try:
        array = sitk.GetArrayFromImage(image)
        filtered_array = ndimage.median_filter(array, size=size)
        filtered_image = sitk.GetImageFromArray(filtered_array)
        filtered_image.CopyInformation(image)
        print("Median filter applied with size =", size)
        return filtered_image
    except Exception as e:
        print(f"Failed to apply Median filter: {str(e)}")
        return None