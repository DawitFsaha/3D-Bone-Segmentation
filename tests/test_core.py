"""
Sample test file for bone segmentation core module.
"""
import pytest


class TestImageProcessing:
    """Tests for image processing functions."""
    
    def test_import_core_module(self):
        """Test that core module can be imported."""
        from bone_segmentation.core import image_processing
        assert image_processing is not None
    
    def test_load_image_function_exists(self):
        """Test that load_image function is available."""
        from bone_segmentation.core.image_processing import load_image
        assert callable(load_image)
    
    def test_get_slice_function_exists(self):
        """Test that get_slice function is available."""
        from bone_segmentation.core.image_processing import get_slice
        assert callable(get_slice)


class TestUIModule:
    """Tests for UI module imports."""
    
    def test_import_ui_module(self):
        """Test that UI module can be imported."""
        from bone_segmentation import ui
        assert ui is not None


class TestVisualizationModule:
    """Tests for visualization module imports."""
    
    def test_import_visualization_module(self):
        """Test that visualization module can be imported."""
        from bone_segmentation import visualization
        assert visualization is not None
