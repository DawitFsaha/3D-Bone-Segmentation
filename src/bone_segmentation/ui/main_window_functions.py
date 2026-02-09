# main_window_functions.py

from bone_segmentation.core.image_processing import (
    load_image, load_image_series, get_slice, apply_threshold, adjust_contrast,
    create_qimage_from_slice, apply_windowing, apply_gaussian_filter, apply_median_filter
)
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QVBoxLayout, QMainWindow, QApplication
from PyQt5.QtCore import QRectF, QTimer
import SimpleITK as sitk
import numpy as np
from bone_segmentation.visualization.mayavi_widget import MayaviQWidget
import traceback
import vtk
from stl import mesh
from skimage import measure


def get_image_metadata(image):
    spacing = image.GetSpacing()  # (x, y, z) spacing in mm
    print(f"Image Spacing: {spacing}")  # Debugging line
    return spacing


class MainWindowFunctions:
    def __init__(self, main_window):
        self.main_window = main_window
        self.cached_processed_array = None
        self.cached_downsampled_array = None
        self.cached_3d_vertices = None
        self.cached_3d_faces = None
        self.mayavi_widget = None
        self.mayavi_window = None
        self.roi_rect_3d = None
        self.roi_update_in_progress = False

        # Set up direct references for immediate updates
        self.setup_direct_references()

    def setup_direct_references(self):
        """Set up direct references between views and functions"""
        try:
            # This will be called after UI initialization
            pass
        except Exception as e:
            print(f"Error setting up references: {e}")

    def fix_mayavi_colorbar(self, widget):
        """Fix colorbar display issues in Mayavi widget"""
        try:
            from mayavi import mlab

            # Method 1: Direct mlab colorbar creation
            def create_colorbar():
                try:
                    # Clear any existing problematic colorbars
                    fig = mlab.gcf()
                    if fig:
                        # Force scene render first
                        fig.scene.render()

                        # Create colorbar with error handling
                        cb = mlab.colorbar(
                            title="Density (HU)",
                            orientation='vertical',
                            nb_labels=5,
                            label_fmt='%.0f'
                        )

                        if cb:
                            cb.scalar_bar.width = 0.1
                            cb.scalar_bar.height = 0.8
                            cb.scalar_bar.position = (0.9, 0.1)
                            cb.scalar_bar.title_text_property.font_size = 12
                            cb.scalar_bar.label_text_property.font_size = 10

                            # Final render
                            fig.scene.render()
                            print("Colorbar created successfully")
                            return True

                except Exception as e:
                    print(f"Direct colorbar creation failed: {e}")
                    return False

                return False

            # Try immediate creation
            if create_colorbar():
                return True

            # If immediate fails, try with delay
            QTimer.singleShot(500, create_colorbar)
            return True

        except Exception as e:
            print(f"Colorbar fix failed: {e}")
            return False

    def apply_colorbar_fix_to_widget(self, widget):
        """Apply colorbar fix to MayaviQWidget"""
        try:
            if widget and hasattr(widget, 'visualization'):
                # Add colorbar fix method to the widget if it doesn't exist
                if not hasattr(widget, 'fix_colorbar_display'):
                    widget.fix_colorbar_display = lambda: self.fix_mayavi_colorbar(widget)

                # Apply the fix
                QTimer.singleShot(1000, widget.fix_colorbar_display)

        except Exception as e:
            print(f"Failed to apply colorbar fix to widget: {e}")

    def on_roi_changed_immediate(self, rect, source_orientation):
        """Immediate ROI change handler for real-time updates"""
        try:
            if self.roi_update_in_progress:
                return

            self.roi_update_in_progress = True

            print(f"IMMEDIATE ROI update from {source_orientation}: {rect}")

            # Convert to 3D and immediately propagate
            self.roi_rect_3d = self.convert_roi_to_3d_preserving_dimensions(rect, source_orientation)
            if self.roi_rect_3d:
                # Navigate other views to show ROI if needed
                self.navigate_views_to_show_roi()
                # Immediately propagate ROI
                self.propagate_roi_immediate(source_orientation)

            self.roi_update_in_progress = False
        except Exception as e:
            print(f"Error in immediate ROI update: {e}")
            self.roi_update_in_progress = False

    def propagate_roi_immediate(self, source_orientation):
        """Immediate ROI propagation for real-time updates"""
        try:
            if not self.roi_rect_3d:
                return

            size = self.main_window.image.GetSize()
            display_width = 400
            display_height = 400

            print(f"Propagating ROI immediately from {source_orientation}")
            print(f"ROI 3D bounds: x={self.roi_rect_3d['x_min']}-{self.roi_rect_3d['x_max']}, "
                  f"y={self.roi_rect_3d['y_min']}-{self.roi_rect_3d['y_max']}, "
                  f"z={self.roi_rect_3d['z_min']}-{self.roi_rect_3d['z_max']}")

            # Update all other views immediately with error handling
            views_to_update = []

            if source_orientation != 'axial':
                scale_x = display_width / size[0]
                scale_y = display_height / size[1]

                axial_rect = QRectF(
                    self.roi_rect_3d['x_min'] * scale_x,
                    self.roi_rect_3d['y_min'] * scale_y,
                    (self.roi_rect_3d['x_max'] - self.roi_rect_3d['x_min']) * scale_x,
                    (self.roi_rect_3d['y_max'] - self.roi_rect_3d['y_min']) * scale_y
                )

                print(f"Axial ROI rect: {axial_rect}")
                if axial_rect.width() > 1 and axial_rect.height() > 1:
                    views_to_update.append((self.main_window.axial_view, axial_rect))

            if source_orientation != 'coronal':
                scale_x = display_width / size[0]
                scale_z = display_height / size[2]

                coronal_rect = QRectF(
                    self.roi_rect_3d['x_min'] * scale_x,
                    self.roi_rect_3d['z_min'] * scale_z,
                    (self.roi_rect_3d['x_max'] - self.roi_rect_3d['x_min']) * scale_x,
                    (self.roi_rect_3d['z_max'] - self.roi_rect_3d['z_min']) * scale_z
                )

                print(f"Coronal ROI rect: {coronal_rect}")
                if coronal_rect.width() > 1 and coronal_rect.height() > 1:
                    views_to_update.append((self.main_window.coronal_view, coronal_rect))

            if source_orientation != 'sagittal':
                scale_y = display_width / size[1]
                scale_z = display_height / size[2]

                sagittal_rect = QRectF(
                    self.roi_rect_3d['y_min'] * scale_y,
                    self.roi_rect_3d['z_min'] * scale_z,
                    (self.roi_rect_3d['y_max'] - self.roi_rect_3d['y_min']) * scale_y,
                    (self.roi_rect_3d['z_max'] - self.roi_rect_3d['z_min']) * scale_z
                )

                print(f"Sagittal ROI rect: {sagittal_rect}")
                if sagittal_rect.width() > 1 and sagittal_rect.height() > 1:
                    views_to_update.append((self.main_window.sagittal_view, sagittal_rect))

            # Apply updates to all views with individual error handling
            for view, rect in views_to_update:
                try:
                    print(f"Setting ROI in {view.orientation} view: {rect}")
                    view.set_roi_from_external(rect)
                    # Force additional visual updates
                    view.scene.update()
                    view.update()
                    view.viewport().update()
                except Exception as view_error:
                    print(f"Error updating {view.orientation} view: {view_error}")

        except Exception as e:
            print(f"Error in immediate propagation: {e}")

    def navigate_views_to_show_roi(self):
        """Navigate all views to slices where ROI is visible"""
        try:
            if not self.roi_rect_3d:
                return

            # Calculate center coordinates of ROI
            x_center = (self.roi_rect_3d['x_min'] + self.roi_rect_3d['x_max']) // 2
            y_center = (self.roi_rect_3d['y_min'] + self.roi_rect_3d['y_max']) // 2
            z_center = (self.roi_rect_3d['z_min'] + self.roi_rect_3d['z_max']) // 2

            print(f"Navigating views to ROI center: x={x_center}, y={y_center}, z={z_center}")

            # Navigate each view to show the ROI
            # Axial view shows Z slices, navigate to Z center
            if z_center != self.main_window.axial_scrollbar.value():
                self.main_window.axial_scrollbar.setValue(z_center)

            # Coronal view shows Y slices, navigate to Y center
            if y_center != self.main_window.coronal_scrollbar.value():
                self.main_window.coronal_scrollbar.setValue(y_center)

            # Sagittal view shows X slices, navigate to X center
            if x_center != self.main_window.sagittal_scrollbar.value():
                self.main_window.sagittal_scrollbar.setValue(x_center)

        except Exception as e:
            print(f"Error navigating views to ROI: {e}")

    def showFileDialog(self):
        try:
            fname, _ = QFileDialog.getOpenFileName(self.main_window, 'Open file', '',
                                                   "DICOM files (*.dcm);;NIfTI files (*.nii *.nii.gz)")
            if fname:
                self.processImage(fname)
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to open file dialog: {str(e)}")

    def showFolderDialog(self):
        try:
            folder = QFileDialog.getExistingDirectory(self.main_window, 'Select CT Volume Folder')
            if folder:
                self.processFolder(folder)
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to open folder dialog: {str(e)}")

    def select_series(self, series_names):
        try:
            item, ok = QInputDialog.getItem(self.main_window, "Select Series", "Series:", series_names, 0, False)
            if ok and item:
                return item
            else:
                return None
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to select series: {str(e)}")
            return None

    def processImage(self, filename):
        try:
            self.main_window.image = load_image(filename)
            self.main_window.threshold_applied = False  # Reset threshold applied flag
            self.main_window.contrast_applied = False
            self.main_window.windowing_applied = False
            self.update_scrollbars()
            self.update_views()

            # Enable buttons after dataset is loaded
            self.main_window.apply_threshold_button.setEnabled(True)
            self.main_window.apply_contrast_button.setEnabled(True)
            self.main_window.apply_windowing_button.setEnabled(True)
            self.main_window.build_3d_button.setEnabled(True)
            self.main_window.apply_filter_button.setEnabled(True)
            self.main_window.export_3d_button.setEnabled(True)
            self.main_window.clear_roi_button.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to load image: {str(e)}")

    def processFolder(self, folder):
        try:
            reader = sitk.ImageSeriesReader()
            series_ids = reader.GetGDCMSeriesIDs(folder)
            if len(series_ids) > 1:
                series_names = [f"Series {i + 1}" for i in range(len(series_ids))]
                selected_series_name = self.select_series(series_names)
                if selected_series_name:
                    selected_series_index = series_names.index(selected_series_name)
                    dicom_names = reader.GetGDCMSeriesFileNames(folder, series_ids[selected_series_index])
                else:
                    return
            else:
                dicom_names = reader.GetGDCMSeriesFileNames(folder, series_ids[0])

            reader.SetFileNames(dicom_names)
            self.main_window.image = reader.Execute()
            self.main_window.threshold_applied = False
            self.main_window.contrast_applied = False
            self.main_window.windowing_applied = False
            self.update_scrollbars()
            self.update_views()

            # Enable buttons after dataset is loaded
            self.main_window.apply_threshold_button.setEnabled(True)
            self.main_window.apply_contrast_button.setEnabled(True)
            self.main_window.apply_windowing_button.setEnabled(True)
            self.main_window.build_3d_button.setEnabled(True)
            self.main_window.apply_filter_button.setEnabled(True)
            self.main_window.clear_roi_button.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to load image series: {str(e)}")

    def on_roi_changed(self, rect, source_orientation):
        """Handle ROI changes from any view and propagate to others"""
        try:
            # Prevent recursive updates
            if self.roi_update_in_progress:
                return

            self.roi_update_in_progress = True

            print(f"ROI changed in {source_orientation}: {rect}")

            if rect is None or rect.isEmpty():
                # Clear ROI in all views
                print("Clearing ROI in all views")
                self.roi_rect_3d = None
                views = [self.main_window.coronal_view, self.main_window.sagittal_view, self.main_window.axial_view]
                for view in views:
                    if view.orientation != source_orientation:
                        view.set_roi_from_external(None)
            else:
                # Convert 2D ROI to 3D coordinates and propagate to other views
                self.roi_rect_3d = self.convert_roi_to_3d_preserving_dimensions(rect, source_orientation)
                if self.roi_rect_3d:
                    print(f"Propagating ROI from {source_orientation} to other views")
                    # Navigate other views to show ROI
                    self.navigate_views_to_show_roi()
                    # Propagate to other views
                    self.propagate_roi_to_views(source_orientation)
                else:
                    print("Failed to convert ROI to 3D coordinates")

            self.roi_update_in_progress = False
        except Exception as e:
            print(f"Failed to handle ROI change: {str(e)}")
            self.roi_update_in_progress = False

    def convert_roi_to_3d_preserving_dimensions(self, rect, orientation):
        """Convert 2D ROI rectangle to 3D coordinates while preserving existing dimensions"""
        try:
            if not self.main_window.image:
                return None

            # Get image dimensions
            size = self.main_window.image.GetSize()  # (width, height, depth)

            # Get current slice indices
            axial_index = self.main_window.axial_scrollbar.value()
            coronal_index = self.main_window.coronal_scrollbar.value()
            sagittal_index = self.main_window.sagittal_scrollbar.value()

            # Get the actual display size of the image in the viewer
            display_width = 400
            display_height = 400

            print(f"Converting ROI from {orientation}: rect={rect}, image_size={size}")

            # Start with existing ROI dimensions if available
            if self.roi_rect_3d:
                x_min = self.roi_rect_3d.get('x_min', 0)
                x_max = self.roi_rect_3d.get('x_max', size[0])
                y_min = self.roi_rect_3d.get('y_min', 0)
                y_max = self.roi_rect_3d.get('y_max', size[1])
                z_min = self.roi_rect_3d.get('z_min', 0)
                z_max = self.roi_rect_3d.get('z_max', size[2])
                print(f"Starting with existing ROI: x={x_min}-{x_max}, y={y_min}-{y_max}, z={z_min}-{z_max}")
            else:
                # Initialize with default thickness if no existing ROI
                x_min, x_max = 0, size[0]
                y_min, y_max = 0, size[1]
                z_min, z_max = 0, size[2]
                print("No existing ROI, initializing with full volume")

            if orientation == 'axial':
                # For axial view: X axis is width, Y axis is height
                # Update X and Y dimensions, preserve Z
                scale_x = size[0] / display_width
                scale_y = size[1] / display_height

                # Update only X and Y coordinates from the 2D ROI
                x_min = max(0, int(rect.x() * scale_x))
                x_max = min(size[0], int((rect.x() + rect.width()) * scale_x))
                y_min = max(0, int(rect.y() * scale_y))
                y_max = min(size[1], int((rect.y() + rect.height()) * scale_y))

                # If no existing ROI, set a reasonable Z thickness around current slice
                if not self.roi_rect_3d:
                    z_center = axial_index
                    z_thickness = max(1, size[2] // 10)  # Use 10% of volume thickness
                    z_min = max(0, z_center - z_thickness // 2)
                    z_max = min(size[2], z_center + z_thickness // 2)

            elif orientation == 'coronal':
                # For coronal view: X axis is width, Z axis is depth (displayed as height)
                # Update X and Z dimensions, preserve Y
                scale_x = size[0] / display_width
                scale_z = size[2] / display_height

                # Update only X and Z coordinates from the 2D ROI
                x_min = max(0, int(rect.x() * scale_x))
                x_max = min(size[0], int((rect.x() + rect.width()) * scale_x))
                z_min = max(0, int(rect.y() * scale_z))
                z_max = min(size[2], int((rect.y() + rect.height()) * scale_z))

                # If no existing ROI, set a reasonable Y thickness around current slice
                if not self.roi_rect_3d:
                    y_center = coronal_index
                    y_thickness = max(1, size[1] // 10)  # Use 10% of volume thickness
                    y_min = max(0, y_center - y_thickness // 2)
                    y_max = min(size[1], y_center + y_thickness // 2)

            elif orientation == 'sagittal':
                # For sagittal view: Y axis is height (displayed as width), Z axis is depth (displayed as height)
                # Update Y and Z dimensions, preserve X
                scale_y = size[1] / display_width
                scale_z = size[2] / display_height

                # Update only Y and Z coordinates from the 2D ROI
                y_min = max(0, int(rect.x() * scale_y))
                y_max = min(size[1], int((rect.x() + rect.width()) * scale_y))
                z_min = max(0, int(rect.y() * scale_z))
                z_max = min(size[2], int((rect.y() + rect.height()) * scale_z))

                # If no existing ROI, set a reasonable X thickness around current slice
                if not self.roi_rect_3d:
                    x_center = sagittal_index
                    x_thickness = max(1, size[0] // 10)  # Use 10% of volume thickness
                    x_min = max(0, x_center - x_thickness // 2)
                    x_max = min(size[0], x_center + x_thickness // 2)

            result = {
                'x_min': x_min, 'x_max': x_max,
                'y_min': y_min, 'y_max': y_max,
                'z_min': z_min, 'z_max': z_max,
                'source_orientation': orientation
            }
            print(f"Final 3D ROI: {result}")
            return result

        except Exception as e:
            print(f"Failed to convert ROI to 3D: {str(e)}")
            return None

    def convert_roi_to_3d(self, rect, orientation):
        """Legacy method - redirects to dimension-preserving version"""
        return self.convert_roi_to_3d_preserving_dimensions(rect, orientation)

    def propagate_roi_to_views(self, source_orientation):
        """Propagate ROI to other views based on 3D coordinates"""
        try:
            if not self.roi_rect_3d:
                return

            size = self.main_window.image.GetSize()
            display_width = 400
            display_height = 400

            views_to_update = []

            if source_orientation != 'axial':
                # Update axial view - project 3D ROI onto axial plane
                scale_x = display_width / size[0]
                scale_y = display_height / size[1]

                # Ensure we have valid coordinates for axial projection
                if 'x_min' in self.roi_rect_3d and 'y_min' in self.roi_rect_3d:
                    axial_rect = QRectF(
                        self.roi_rect_3d['x_min'] * scale_x,
                        self.roi_rect_3d['y_min'] * scale_y,
                        (self.roi_rect_3d['x_max'] - self.roi_rect_3d['x_min']) * scale_x,
                        (self.roi_rect_3d['y_max'] - self.roi_rect_3d['y_min']) * scale_y
                    )
                    views_to_update.append((self.main_window.axial_view, axial_rect))

            if source_orientation != 'coronal':
                # Update coronal view - project 3D ROI onto coronal plane
                scale_x = display_width / size[0]
                scale_z = display_height / size[2]

                # Ensure we have valid coordinates for coronal projection
                if 'x_min' in self.roi_rect_3d and 'z_min' in self.roi_rect_3d:
                    coronal_rect = QRectF(
                        self.roi_rect_3d['x_min'] * scale_x,
                        self.roi_rect_3d['z_min'] * scale_z,
                        (self.roi_rect_3d['x_max'] - self.roi_rect_3d['x_min']) * scale_x,
                        (self.roi_rect_3d['z_max'] - self.roi_rect_3d['z_min']) * scale_z
                    )
                    views_to_update.append((self.main_window.coronal_view, coronal_rect))

            if source_orientation != 'sagittal':
                # Update sagittal view - project 3D ROI onto sagittal plane
                scale_y = display_width / size[1]
                scale_z = display_height / size[2]

                # Ensure we have valid coordinates for sagittal projection
                if 'y_min' in self.roi_rect_3d and 'z_min' in self.roi_rect_3d:
                    sagittal_rect = QRectF(
                        self.roi_rect_3d['y_min'] * scale_y,
                        self.roi_rect_3d['z_min'] * scale_z,
                        (self.roi_rect_3d['y_max'] - self.roi_rect_3d['y_min']) * scale_y,
                        (self.roi_rect_3d['z_max'] - self.roi_rect_3d['z_min']) * scale_z
                    )
                    views_to_update.append((self.main_window.sagittal_view, sagittal_rect))

            # Update the views with proper error handling
            for view, rect in views_to_update:
                try:
                    # Ensure the rect has valid dimensions
                    if rect.width() > 1 and rect.height() > 1:
                        view.set_roi_from_external(rect)
                except Exception as e:
                    print(f"Error updating view {view.orientation}: {e}")

        except Exception as e:
            print(f"Failed to propagate ROI to views: {str(e)}")

    def propagate_roi_to_single_view(self, target_orientation):
        """Propagate ROI to a single specific view"""
        try:
            if not self.roi_rect_3d:
                return

            size = self.main_window.image.GetSize()
            display_width = 400
            display_height = 400

            if target_orientation == 'axial' and 'x_min' in self.roi_rect_3d and 'y_min' in self.roi_rect_3d:
                scale_x = display_width / size[0]
                scale_y = display_height / size[1]

                axial_rect = QRectF(
                    self.roi_rect_3d['x_min'] * scale_x,
                    self.roi_rect_3d['y_min'] * scale_y,
                    (self.roi_rect_3d['x_max'] - self.roi_rect_3d['x_min']) * scale_x,
                    (self.roi_rect_3d['y_max'] - self.roi_rect_3d['y_min']) * scale_y
                )
                if axial_rect.width() > 1 and axial_rect.height() > 1:
                    self.main_window.axial_view.set_roi_from_external(axial_rect)

            elif target_orientation == 'coronal' and 'x_min' in self.roi_rect_3d and 'z_min' in self.roi_rect_3d:
                scale_x = display_width / size[0]
                scale_z = display_height / size[2]

                coronal_rect = QRectF(
                    self.roi_rect_3d['x_min'] * scale_x,
                    self.roi_rect_3d['z_min'] * scale_z,
                    (self.roi_rect_3d['x_max'] - self.roi_rect_3d['x_min']) * scale_x,
                    (self.roi_rect_3d['z_max'] - self.roi_rect_3d['z_min']) * scale_z
                )
                if coronal_rect.width() > 1 and coronal_rect.height() > 1:
                    self.main_window.coronal_view.set_roi_from_external(coronal_rect)

            elif target_orientation == 'sagittal' and 'y_min' in self.roi_rect_3d and 'z_min' in self.roi_rect_3d:
                scale_y = display_width / size[1]
                scale_z = display_height / size[2]

                sagittal_rect = QRectF(
                    self.roi_rect_3d['y_min'] * scale_y,
                    self.roi_rect_3d['z_min'] * scale_z,
                    (self.roi_rect_3d['y_max'] - self.roi_rect_3d['y_min']) * scale_y,
                    (self.roi_rect_3d['z_max'] - self.roi_rect_3d['z_min']) * scale_z
                )
                if sagittal_rect.width() > 1 and sagittal_rect.height() > 1:
                    self.main_window.sagittal_view.set_roi_from_external(sagittal_rect)

        except Exception as e:
            print(f"Failed to propagate ROI to single view {target_orientation}: {str(e)}")

    def clear_roi(self):
        """Clear ROI from all views"""
        try:
            self.roi_rect_3d = None
            self.main_window.coronal_view.clear_roi()
            self.main_window.sagittal_view.clear_roi()
            self.main_window.axial_view.clear_roi()
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to clear ROI: {str(e)}")

    def get_roi_mask(self, image_array):
        """Create a mask for the ROI region"""
        try:
            if not self.roi_rect_3d:
                return None

            mask = np.zeros(image_array.shape, dtype=bool)

            # Apply ROI bounds
            x_min = max(0, self.roi_rect_3d.get('x_min', 0))
            x_max = min(image_array.shape[2], self.roi_rect_3d.get('x_max', image_array.shape[2]))
            y_min = max(0, self.roi_rect_3d.get('y_min', 0))
            y_max = min(image_array.shape[1], self.roi_rect_3d.get('y_max', image_array.shape[1]))
            z_min = max(0, self.roi_rect_3d.get('z_min', 0))
            z_max = min(image_array.shape[0], self.roi_rect_3d.get('z_max', image_array.shape[0]))

            mask[z_min:z_max, y_min:y_max, x_min:x_max] = True

            return mask
        except Exception as e:
            print(f"Failed to create ROI mask: {str(e)}")
            return None

    def update_scrollbars(self):
        try:
            self.main_window.coronal_scrollbar.setMaximum(self.main_window.image.GetHeight() - 1)
            self.main_window.sagittal_scrollbar.setMaximum(self.main_window.image.GetWidth() - 1)
            self.main_window.axial_scrollbar.setMaximum(self.main_window.image.GetDepth() - 1)

            # Enable the scrollbars now that an image has been loaded
            self.main_window.coronal_scrollbar.setEnabled(True)
            self.main_window.sagittal_scrollbar.setEnabled(True)
            self.main_window.axial_scrollbar.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to update scrollbars: {str(e)}")

    def update_views(self):
        try:
            self.update_coronal_view()
            self.update_sagittal_view()
            self.update_axial_view()
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to update views: {str(e)}")

    def update_coronal_view(self):
        try:
            coronal_index = self.main_window.coronal_scrollbar.value()
            coronal_slice = get_slice(self.main_window.image, coronal_index, orientation='coronal')
            processed_slice = self.apply_processing(coronal_slice)
            qimage = create_qimage_from_slice(processed_slice, target_size=(400, 400))
            self.main_window.coronal_view.display_image(qimage)

            # Always restore ROI if it exists and intersects current slice
            if self.roi_rect_3d and self.roi_intersects_coronal_slice(coronal_index):
                self.propagate_roi_to_single_view('coronal')
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to update coronal view: {str(e)}")

    def update_sagittal_view(self):
        try:
            sagittal_index = self.main_window.sagittal_scrollbar.value()
            sagittal_slice = get_slice(self.main_window.image, sagittal_index, orientation='sagittal')
            processed_slice = self.apply_processing(sagittal_slice)
            qimage = create_qimage_from_slice(processed_slice, target_size=(400, 400))
            self.main_window.sagittal_view.display_image(qimage)

            # Always restore ROI if it exists and intersects current slice
            if self.roi_rect_3d and self.roi_intersects_sagittal_slice(sagittal_index):
                self.propagate_roi_to_single_view('sagittal')
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to update sagittal view: {str(e)}")

    def update_axial_view(self):
        try:
            axial_index = self.main_window.axial_scrollbar.value()
            axial_slice = get_slice(self.main_window.image, axial_index, orientation='axial')
            processed_slice = self.apply_processing(axial_slice)
            qimage = create_qimage_from_slice(processed_slice, target_size=(400, 400))
            self.main_window.axial_view.display_image(qimage)

            # Always restore ROI if it exists and intersects current slice
            if self.roi_rect_3d and self.roi_intersects_axial_slice(axial_index):
                self.propagate_roi_to_single_view('axial')
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to update axial view: {str(e)}")

    def roi_intersects_coronal_slice(self, slice_index):
        """Check if ROI intersects with the current coronal slice"""
        if not self.roi_rect_3d:
            return False
        y_min = self.roi_rect_3d.get('y_min', 0)
        y_max = self.roi_rect_3d.get('y_max', 0)
        return y_min <= slice_index <= y_max

    def roi_intersects_sagittal_slice(self, slice_index):
        """Check if ROI intersects with the current sagittal slice"""
        if not self.roi_rect_3d:
            return False
        x_min = self.roi_rect_3d.get('x_min', 0)
        x_max = self.roi_rect_3d.get('x_max', 0)
        return x_min <= slice_index <= x_max

    def roi_intersects_axial_slice(self, slice_index):
        """Check if ROI intersects with the current axial slice"""
        if not self.roi_rect_3d:
            return False
        z_min = self.roi_rect_3d.get('z_min', 0)
        z_max = self.roi_rect_3d.get('z_max', 0)
        return z_min <= slice_index <= z_max

    def apply_processing(self, image):
        """Apply the SAME processing pipeline used for 2D slices - this is what 3D should use too"""
        try:
            if isinstance(image, sitk.Image):
                image_array = sitk.GetArrayFromImage(image)
            else:
                image_array = image.copy()

            print(f"Apply processing - Original range: {image_array.min()} to {image_array.max()}")

            # Apply windowing FIRST if user has applied it
            if self.main_window.windowing_applied:
                min_val, max_val = self.main_window.windowing_tool.get_values()
                print(f"Applying windowing: {min_val} to {max_val}")
                image_array = apply_windowing(image_array, min_val, max_val)
                print(f"After windowing: {image_array.min()} to {image_array.max()}")

            # Apply threshold AFTER windowing if user has applied it
            if self.main_window.threshold_applied:
                threshold_val = self.main_window.threshold_slider.value()
                print(f"Applying threshold: {threshold_val}")
                image_array = (image_array > threshold_val) * image_array
                print(f"After threshold: {image_array.min()} to {image_array.max()}")

            # Apply contrast adjustment last if user has applied it
            if self.main_window.contrast_applied:
                contrast_val = self.main_window.contrast_slider.value()
                print(f"Applying contrast: {contrast_val}")
                image_array = adjust_contrast(image_array, contrast_val)
                print(f"After contrast: {image_array.min()} to {image_array.max()}")

            if isinstance(image, sitk.Image):
                return sitk.GetImageFromArray(image_array)
            else:
                return image_array
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to apply processing: {str(e)}")
            return image

    def is_widget_valid(self, widget):
        """Check if widget is valid without using sip"""
        try:
            # Try to access a basic property of the widget
            widget.isVisible()
            return True
        except (RuntimeError, AttributeError):
            return False

    def build_3d_view(self):
        """Build 3D view using the EXACT SAME processing pipeline as 2D views"""
        try:
            # Import at function level to ensure availability
            from PyQt5.QtWidgets import QApplication, QVBoxLayout
            from PyQt5.QtCore import QTimer

            print("\n=== BUILDING 3D VIEW ===")
            print(
                f"Applied states: Threshold={self.main_window.threshold_applied}, Windowing={self.main_window.windowing_applied}, Contrast={self.main_window.contrast_applied}")

            # Invalidate the cache
            self.cached_downsampled_array = None
            self.cached_3d_vertices = None
            self.cached_3d_faces = None

            # Get the original image array
            original_image_array = sitk.GetArrayFromImage(self.main_window.image)
            print(
                f"Original image array - Shape: {original_image_array.shape}, Range: {original_image_array.min()} to {original_image_array.max()}")

            # CRITICAL FIX: Check if ANY processing is applied
            any_processing_applied = (self.main_window.threshold_applied or
                                      self.main_window.windowing_applied or
                                      self.main_window.contrast_applied)

            if any_processing_applied:
                # Use the SAME processing pipeline as 2D views
                print("Processing applied - using same pipeline as 2D views")
                processed_array = self.apply_processing(original_image_array)
                print(
                    f"Processed array for 3D - Shape: {processed_array.shape}, Range: {processed_array.min()} to {processed_array.max()}")
            else:
                # NO processing applied - use raw data
                print("NO processing applied - using raw data for 3D")
                processed_array = original_image_array.copy()
                print(
                    f"Raw array for 3D - Shape: {processed_array.shape}, Range: {processed_array.min()} to {processed_array.max()}")

            # Keep a copy of the original for density mapping (HU values)
            original_for_density = original_image_array.copy()

            # Apply ROI mask if ROI is selected
            if self.roi_rect_3d:
                roi_mask = self.get_roi_mask(processed_array)
                if roi_mask is not None:
                    processed_array = processed_array * roi_mask
                    original_for_density = original_for_density * roi_mask
                    print("Applied ROI mask to 3D rendering")

            self.cached_processed_array = processed_array

            # For better performance, downsample if the array is very large
            max_dim = 256  # Maximum dimension for 3D rendering
            original_shape = processed_array.shape

            if max(original_shape) > max_dim:
                downsample_factors = [max(1, dim // max_dim) for dim in original_shape]
                print(f"Downsampling from {original_shape} with factors {downsample_factors}")
                downsampled_array = processed_array[::downsample_factors[0], ::downsample_factors[1],
                                    ::downsample_factors[2]]
                downsampled_original = original_for_density[::downsample_factors[0], ::downsample_factors[1],
                                       ::downsample_factors[2]]
            else:
                downsampled_array = processed_array
                downsampled_original = original_for_density

            self.cached_downsampled_array = downsampled_array
            print(
                f"Final array for 3D - Shape: {downsampled_array.shape}, Range: {downsampled_array.min()} to {downsampled_array.max()}")

            # CRITICAL: Check data validity differently based on processing
            if any_processing_applied:
                # For processed data, check if we have non-zero values
                non_zero_count = np.count_nonzero(downsampled_array)
                if non_zero_count == 0:
                    raise ValueError("All data was removed by processing - try adjusting threshold/windowing values")
                print(f"Processed data: {non_zero_count} out of {downsampled_array.size} non-zero voxels")
            else:
                # For raw data, check if we have variation
                if downsampled_array.max() <= downsampled_array.min():
                    raise ValueError("No variation in raw data - cannot create 3D visualization")
                print(f"Raw data: Range {downsampled_array.min()} to {downsampled_array.max()}")

            # Ensure the empty_view has a layout
            if self.main_window.empty_view.layout() is None:
                self.main_window.empty_view.setLayout(QVBoxLayout())

            # Clear the existing layout
            layout = self.main_window.empty_view.layout()
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().setParent(None)

            # Create or update the Mayavi widget
            widget_needs_creation = (self.mayavi_widget is None or not self.is_widget_valid(self.mayavi_widget))

            if widget_needs_creation:
                print("Creating new MayaviQWidget with processed data")

                try:
                    # CRITICAL: Pass the processed data to the widget
                    self.mayavi_widget = MayaviQWidget(self.main_window.empty_view, data=downsampled_array)

                    # Set original data for density mapping
                    if hasattr(self.mayavi_widget, 'visualization') and self.mayavi_widget.visualization:
                        self.mayavi_widget.visualization.original_data = downsampled_original.astype(np.float32)
                        print("Set original data for density mapping")

                    # Add to layout
                    layout.addWidget(self.mayavi_widget)

                    # Show and update
                    self.mayavi_widget.show()
                    self.main_window.empty_view.update()

                    # Process events
                    QApplication.processEvents()

                    # Apply colorbar fix after widget creation
                    self.apply_colorbar_fix_to_widget(self.mayavi_widget)

                    print("MayaviQWidget created successfully with processed data")

                except Exception as widget_error:
                    print(f"Error creating MayaviQWidget: {widget_error}")
                    import traceback
                    traceback.print_exc()

                    # Fallback - try simple creation
                    try:
                        self.mayavi_widget = MayaviQWidget(self.main_window.empty_view)
                        layout.addWidget(self.mayavi_widget)

                        # Set data after creation with delay
                        def set_data_delayed():
                            try:
                                if (hasattr(self.mayavi_widget, 'visualization') and
                                        self.mayavi_widget.visualization):
                                    print("Setting processed data with delay")
                                    self.mayavi_widget.visualization.data = downsampled_array.astype(np.float32)
                                    self.mayavi_widget.visualization.original_data = downsampled_original.astype(
                                        np.float32)
                                    self.mayavi_widget.visualization.update_scene()

                                    # Apply colorbar fix after data is set
                                    self.apply_colorbar_fix_to_widget(self.mayavi_widget)
                                    print("Delayed data setting successful")
                            except Exception as e:
                                print(f"Error setting data: {e}")

                        QTimer.singleShot(500, set_data_delayed)
                        print("Fallback widget creation successful")

                    except Exception as fallback_error:
                        print(f"Fallback creation also failed: {fallback_error}")
                        raise

            else:
                print("Updating existing MayaviQWidget with new processed data")

                try:
                    if (hasattr(self.mayavi_widget, 'visualization') and
                            self.mayavi_widget.visualization):
                        print("Updating visualization with processed data")
                        self.mayavi_widget.visualization.data = downsampled_array.astype(np.float32)
                        self.mayavi_widget.visualization.original_data = downsampled_original.astype(np.float32)
                        self.mayavi_widget.visualization.update_scene()

                        # Apply colorbar fix after update
                        self.apply_colorbar_fix_to_widget(self.mayavi_widget)

                    # Re-add to layout if needed
                    if self.mayavi_widget.parent() != self.main_window.empty_view:
                        layout.addWidget(self.mayavi_widget)

                except Exception as update_error:
                    print(f"Error updating existing widget: {update_error}")
                    # Force recreation
                    self.mayavi_widget = None
                    QTimer.singleShot(100, self.build_3d_view)
                    return

            # Force the widget to update
            self.main_window.empty_view.update()

            # Enable the Pop Out 3D View button after rendering
            self.main_window.popout_3d_button.setEnabled(True)
            self.main_window.export_3d_button.setEnabled(True)

            # Display density statistics with delay
            QTimer.singleShot(1000, self.display_density_statistics)

            print("=== 3D VIEW BUILD COMPLETED ===\n")

        except Exception as e:
            print(f"Failed to build 3D view: {str(e)}")
            traceback.print_exc()
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self.main_window, "Error", f"Failed to build 3D view: {str(e)}")

    def display_density_statistics(self):
        """Display density statistics for the current 3D model"""
        try:
            if self.mayavi_widget and self.mayavi_widget.visualization:
                stats = self.mayavi_widget.visualization.get_density_statistics()
                if stats:
                    stats_text = (f"Density Statistics:\n"
                                  f"Min: {stats['min']:.1f}\n"
                                  f"Max: {stats['max']:.1f}\n"
                                  f"Mean: {stats['mean']:.1f}\n"
                                  f"Median: {stats['median']:.1f}\n"
                                  f"Std Dev: {stats['std']:.1f}")
                    print(stats_text)
        except Exception as e:
            print(f"Failed to display density statistics: {str(e)}")

    def popout_3d_view(self):
        try:
            # Check if 3D data is cached
            if self.mayavi_widget is None or not self.is_widget_valid(self.mayavi_widget):
                self.build_3d_view()
                return

            # Reuse the existing Mayavi widget if available
            mayavi_widget = self.mayavi_widget

            # Create a new window for the Mayavi widget if it doesn't exist or has been closed
            if self.mayavi_window is None or not self.is_widget_valid(self.mayavi_window):
                self.mayavi_window = QMainWindow()

            self.mayavi_window.setCentralWidget(mayavi_widget)
            self.mayavi_window.setWindowTitle("3D Visualization - Interactive Density Map")
            self.mayavi_window.resize(800, 600)

            # Connect the close event to clean up resources
            self.mayavi_window.closeEvent = self.close_mayavi_window

            self.mayavi_window.show()

            # Apply colorbar fix to popped out window
            self.apply_colorbar_fix_to_widget(mayavi_widget)

        except Exception as e:
            print(f"Failed to pop out 3D view: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(self.main_window, "Error", f"Failed to pop out 3D view: {str(e)}")

    def close_mayavi_window(self, event):
        try:
            # Hide the pop-out window but do not delete the widget
            self.mayavi_window.hide()

            # Re-add the widget to the original grid layout
            layout = self.main_window.empty_view.layout()
            layout.addWidget(self.mayavi_widget)
            self.main_window.empty_view.update()

            # Nullify the window reference
            self.mayavi_window = None
            event.accept()
        except Exception as e:
            print(f"Failed to close Mayavi window: {str(e)}")
            traceback.print_exc()
            event.accept()

    def update_threshold_label(self):
        try:
            self.main_window.threshold_label.setText(f"Threshold: {self.main_window.threshold_slider.value()}")
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to update threshold label: {str(e)}")

    def apply_threshold(self):
        try:
            print(f"Applying threshold: {self.main_window.threshold_slider.value()}")
            self.main_window.threshold_applied = True
            self.update_views()
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to apply threshold: {str(e)}")

    def update_contrast_label(self):
        try:
            self.main_window.contrast_label.setText(f"Contrast: {self.main_window.contrast_slider.value()}")
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to update contrast label: {str(e)}")

    def apply_contrast(self):
        try:
            print(f"Applying contrast: {self.main_window.contrast_slider.value()}")
            self.main_window.contrast_applied = True
            self.update_views()
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to apply contrast: {str(e)}")

    def apply_windowing(self):
        try:
            # Set the windowing flag to enable windowing in the processing pipeline
            self.main_window.windowing_applied = True

            # Get current windowing values
            min_val, max_val = self.main_window.windowing_tool.get_values()
            center, width = self.main_window.windowing_tool.get_center_width()

            print(f"Windowing applied: Center={center}, Width={width}, Range={min_val} to {max_val}")

            # Update all views immediately to show the windowing effect
            self.update_views()

        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to apply windowing: {str(e)}")

    def apply_filter(self):
        try:
            filter_method = self.main_window.filtering_combobox.currentText()
            filter_value = int(self.main_window.filter_value_combobox.currentText())
            if filter_method == "Gaussian Filter":
                self.filtered_image = apply_gaussian_filter(self.main_window.image, sigma=filter_value)
            elif filter_method == "Median Filter":
                self.filtered_image = apply_median_filter(self.main_window.image, size=filter_value)

            if self.filtered_image is not None:
                print("Filter applied. Updating image.")
                self.main_window.image = self.filtered_image  # Update the image with the filtered image
                self.update_views()
            else:
                print("Filtered image is None.")
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to apply filter: {str(e)}")

    def update_filter_value(self):
        try:
            if self.main_window.filtering_combobox.currentText() == "Gaussian Filter":
                self.main_window.filter_value_combobox.setCurrentIndex(0)  # Default value for Gaussian Filter is 1
            elif self.main_window.filtering_combobox.currentText() == "Median Filter":
                self.main_window.filter_value_combobox.setCurrentIndex(2)  # Default value for Median Filter is 3
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to update filter value: {str(e)}")

    def export_3d_to_stl(self):
        try:
            print("\n=== EXPORTING 3D TO STL ===")
            print(
                f"Applied states: Threshold={self.main_window.threshold_applied}, Windowing={self.main_window.windowing_applied}, Contrast={self.main_window.contrast_applied}")

            # Get the image array
            image_array = sitk.GetArrayFromImage(self.main_window.image)

            # CRITICAL FIX: Check if ANY processing is applied (same as build_3d_view)
            any_processing_applied = (self.main_window.threshold_applied or
                                      self.main_window.windowing_applied or
                                      self.main_window.contrast_applied)

            if any_processing_applied:
                # Apply the SAME processing to the image array as used for 3D
                print("Processing applied - using same pipeline as 2D/3D views")
                processed_array = self.apply_processing(image_array)
            else:
                # NO processing applied - use raw data
                print("NO processing applied - using raw data for STL export")
                processed_array = image_array.copy()

            print(f"STL Export - Array range: {processed_array.min()} to {processed_array.max()}")

            # Apply ROI mask if ROI is selected
            if self.roi_rect_3d:
                roi_mask = self.get_roi_mask(processed_array)
                if roi_mask is not None:
                    processed_array = processed_array * roi_mask
                    print("Applied ROI mask to STL export")

            # Downsample the image data for faster 3D rendering
            downsample_factor = 1  # Adjust this factor to control the level of downsampling
            downsampled_array = processed_array[::downsample_factor, ::downsample_factor, ::downsample_factor]

            # Determine appropriate iso-surface level based on data
            data_min = downsampled_array.min()
            data_max = downsampled_array.max()

            if any_processing_applied:
                # For processed data, use a low iso-level to capture processed structures
                non_zero_count = np.count_nonzero(downsampled_array)
                if non_zero_count > 0:
                    non_zero_data = downsampled_array[downsampled_array > data_min]
                    iso_level = np.percentile(non_zero_data, 10)  # Low percentile for processed data
                else:
                    raise ValueError("No data remaining after processing for STL export")
            else:
                # For raw data, use higher percentile
                if data_max > 1000:  # Likely HU values
                    iso_level = 200  # Bone threshold in HU
                    if iso_level > data_max:
                        iso_level = np.percentile(downsampled_array[downsampled_array > 0], 75)
                else:  # Other data
                    iso_level = np.percentile(downsampled_array[downsampled_array > 0], 60)

            # Ensure iso_level is valid
            iso_level = max(data_min + 0.001, min(iso_level, data_max - 0.001))
            print(f"STL Export - Using iso-surface level: {iso_level}")

            # Create the 3D mesh from the downsampled array
            vertices, faces, _, _ = measure.marching_cubes(downsampled_array, level=iso_level)

            # Retrieve the spacing information from the image metadata
            spacing = get_image_metadata(self.main_window.image)  # Correct function call
            scale_factors = spacing[::-1]  # Reverse to match the order of axes in vertices

            # Apply the scaling factors to the vertices
            vertices = vertices * scale_factors

            # Create the mesh
            exported_mesh = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
            for i, face in enumerate(faces):
                for j in range(3):
                    exported_mesh.vectors[i][j] = vertices[face[j], :]

            # Show the file dialog to save the STL file
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getSaveFileName(self.main_window, "Export 3D to STL", "",
                                                       "STL Files (*.stl);;All Files (*)", options=options)
            if file_path:
                exported_mesh.save(file_path)
                success_msg = f"3D model exported to {file_path}"
                if self.roi_rect_3d:
                    success_msg += " (ROI region only)"
                if any_processing_applied:
                    success_msg += " (with applied processing)"
                else:
                    success_msg += " (raw data)"
                QMessageBox.information(self.main_window, "Success", success_msg)

            print("=== STL EXPORT COMPLETED ===\n")

        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Failed to export 3D model: {str(e)}")

    def numpy_to_vtk_image(self, numpy_array):
        try:
            # Convert numpy array to VTK image data
            vtk_image = vtk.vtkImageData()
            depth, height, width = numpy_array.shape

            vtk_image.SetDimensions(width, height, depth)
            vtk_image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)

            # Get a pointer to the VTK image data
            vtk_array = vtk.util.numpy_support.numpy_to_vtk(numpy_array.ravel(), deep=True,
                                                            array_type=vtk.VTK_UNSIGNED_CHAR)
            vtk_image.GetPointData().SetScalars(vtk_array)

            return vtk_image
        except Exception as e:
            print(f"Failed to convert numpy array to VTK image: {str(e)}")
            traceback.print_exc()
            return None