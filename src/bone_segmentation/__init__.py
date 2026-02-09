"""
Bone Segmentation 3D - Medical Imaging Application

A comprehensive medical imaging application for patient-specific 3D bone model
generation from CT scans, designed for preoperative planning.

Modules:
    core: Image processing and data handling
    ui: User interface components
    visualization: 3D rendering and visualization

Author: Dawit
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Dawit"
__email__ = "your.email@example.com"

from bone_segmentation.core.image_processing import (
    load_image,
    load_image_series,
    get_slice,
    apply_threshold,
    adjust_contrast,
    apply_windowing,
    apply_gaussian_filter,
    apply_median_filter,
    create_qimage_from_slice,
)

__all__ = [
    "load_image",
    "load_image_series", 
    "get_slice",
    "apply_threshold",
    "adjust_contrast",
    "apply_windowing",
    "apply_gaussian_filter",
    "apply_median_filter",
    "create_qimage_from_slice",
    "__version__",
]
