"""
Visualization module for 3D rendering.

This module provides Mayavi-based 3D visualization components for
rendering bone surfaces with density coloring.
"""

from bone_segmentation.visualization.mayavi_widget import MayaviQWidget
from bone_segmentation.visualization.enhanced_mayavi_widget import (
    DensityColoredVisualization,
    EnhancedMayaviQWidget,
)

__all__ = [
    "MayaviQWidget",
    "DensityColoredVisualization",
    "EnhancedMayaviQWidget",
]
