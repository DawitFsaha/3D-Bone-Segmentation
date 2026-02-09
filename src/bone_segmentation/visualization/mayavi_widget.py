# mayavi_widget.py - Fixed to use processed data correctly
from mayavi import mlab
from pyface.qt import QtGui
from mayavi.core.ui.api import MayaviScene, MlabSceneModel, SceneEditor
from traits.api import HasTraits, Instance, Array
from traitsui.api import View, Item
from tvtk.pyface.scene_editor import SceneEditor
from pyface.qt.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
import numpy as np
from tvtk.api import tvtk
from skimage import measure


class MayaviQWidget(QWidget):
    def __init__(self, parent=None, data=None):
        try:
            QWidget.__init__(self, parent)

            # Create visualization first
            self.visualization = Visualization(data=data)

            # Create layout for the entire widget
            main_layout = QVBoxLayout(self)

            # Create control panel
            control_panel = self.create_control_panel()
            main_layout.addWidget(control_panel)

            # Create mayavi scene with minimal initialization
            try:
                self.ui = self.visualization.edit_traits(parent=self, kind='subpanel').control
                main_layout.addWidget(self.ui)
            except Exception as ui_error:
                print(f"Error creating UI: {ui_error}")
                # Create a placeholder widget
                placeholder = QWidget()
                placeholder.setMinimumSize(400, 400)
                main_layout.addWidget(placeholder)
                self.ui = placeholder

            # Connect control panel signals
            self.connect_controls()

            # Set parent widget reference
            if hasattr(self.visualization, 'set_parent_widget'):
                self.visualization.set_parent_widget(self)

            self.setLayout(main_layout)

            print("MayaviQWidget initialized successfully")

        except Exception as e:
            print(f"Failed to initialize MayaviQWidget: {str(e)}")
            # Create minimal fallback
            self.visualization = None
            self.ui = QWidget()
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("3D Visualization Error"))
            layout.addWidget(self.ui)

    def create_control_panel(self):
        """Create control panel for visualization options"""
        try:
            control_widget = QWidget()
            layout = QHBoxLayout(control_widget)

            # Color map selection
            colormap_label = QLabel("Color Map:")
            colormap_label.setFont(QFont('Arial', 9))
            self.colormap_combo = QComboBox()
            self.colormap_combo.addItems(['bone', 'hot', 'cool', 'viridis', 'plasma', 'jet', 'rainbow'])
            self.colormap_combo.setCurrentText('bone')  # Set bone as default

            # Transparency control
            self.transparency_checkbox = QCheckBox("Semi-transparent")
            self.transparency_checkbox.setChecked(False)  # CHANGED: Default to solid (not transparent)

            # Color bar toggle
            self.colorbar_checkbox = QCheckBox("Show Color Bar")
            self.colorbar_checkbox.setChecked(True)

            # Density info label
            self.density_info_label = QLabel("Click on 3D model to see density values")
            self.density_info_label.setFont(QFont('Arial', 9))
            self.density_info_label.setStyleSheet("color: blue; font-weight: bold;")

            layout.addWidget(colormap_label)
            layout.addWidget(self.colormap_combo)
            layout.addWidget(self.transparency_checkbox)
            layout.addWidget(self.colorbar_checkbox)
            layout.addWidget(self.density_info_label)
            layout.addStretch()

            return control_widget
        except Exception as e:
            print(f"Failed to create control panel: {str(e)}")
            return QWidget()

    def connect_controls(self):
        """Connect control panel signals to visualization updates"""
        try:
            self.colormap_combo.currentTextChanged.connect(self.update_colormap)
            self.transparency_checkbox.toggled.connect(self.update_transparency)
            self.colorbar_checkbox.toggled.connect(self.update_colorbar)
        except Exception as e:
            print(f"Failed to connect controls: {str(e)}")

    def update_colormap(self, colormap_name):
        """Update the colormap of the visualization"""
        try:
            print(f"Widget received colormap change request: {colormap_name}")

            # Update the Show Color Bar checkbox state based on colormap
            if colormap_name == 'bone':
                # For uniform white bone, hide color bar and uncheck the checkbox
                self.colorbar_checkbox.setChecked(False)
            else:
                # For other colormaps, show color bar and check the checkbox
                self.colorbar_checkbox.setChecked(True)

            if self.visualization and hasattr(self.visualization, 'set_colormap'):
                self.visualization.set_colormap(colormap_name)
            else:
                print("Visualization not available for colormap change")
        except Exception as e:
            print(f"Failed to update colormap from widget: {str(e)}")

    def update_transparency(self, is_transparent):
        """Update transparency of the visualization"""
        try:
            opacity = 0.7 if is_transparent else 1.0  # 0.7 for transparent, 1.0 for solid
            if self.visualization and hasattr(self.visualization, 'set_opacity'):
                self.visualization.set_opacity(opacity)
        except Exception as e:
            print(f"Failed to update transparency: {str(e)}")

    def update_colorbar(self, show_colorbar):
        """Toggle colorbar visibility"""
        try:
            print(f"Widget colorbar toggle request: {show_colorbar}")
            if self.visualization and hasattr(self.visualization, 'toggle_colorbar'):
                self.visualization.toggle_colorbar(show_colorbar)

                # Additional fix for embedded view
                if show_colorbar:
                    # Delay the colorbar enforcement to ensure it takes effect
                    QTimer.singleShot(200, lambda: self.visualization.ensure_colorbar_visible(
                        self.visualization.current_colorbar) if self.visualization.current_colorbar else None)

        except Exception as e:
            print(f"Failed to update colorbar: {str(e)}")

    def update_density_info(self, density_value, position):
        """Update density information display"""
        try:
            if density_value is not None:
                self.density_info_label.setText(
                    f"Density: {density_value:.1f} HU at position ({position[0]:.1f}, {position[1]:.1f}, {position[2]:.1f})"
                )
            else:
                self.density_info_label.setText("Click on 3D model to see density values")
        except Exception as e:
            print(f"Failed to update density info: {str(e)}")


class Visualization(HasTraits):
    scene = Instance(MlabSceneModel, ())
    data = Array(dtype=np.float32, shape=(None, None, None))

    view = View(Item('scene', editor=SceneEditor(scene_class=MayaviScene), show_label=False), resizable=True)

    def __init__(self, data=None, **traits):
        super(Visualization, self).__init__(**traits)
        self.data = data.astype(np.float32) if data is not None else np.zeros((0, 0, 0), dtype=np.float32)
        self.current_surface = None
        self.current_colorbar = None
        self.picker_callback = None
        self.parent_widget = None
        self.mesh_data = None
        self.original_data = None
        self.scalar_bar_widget = None
        self.colorbar_pending = False
        self.interactor_ready = False

        if self.data.size > 0:
            self.original_data = self.data.copy()
            # Delay scene update to ensure proper initialization
            QTimer.singleShot(300, self._delayed_update_scene)

    def set_parent_widget(self, widget):
        """Set reference to parent widget for callbacks"""
        self.parent_widget = widget

    def _delayed_update_scene(self):
        """Delayed scene update to ensure proper initialization"""
        try:
            # Simple activation attempt
            try:
                self.scene.activated = True
            except Exception as activation_error:
                print(f"Could not set scene activated: {activation_error}")

            # Check if interactor is ready with simple method
            self.interactor_ready = self._check_interactor_ready()

            if self.interactor_ready:
                print("Interactor ready, proceeding with scene update")
            else:
                print("Interactor not ready, proceeding without advanced features")

            self.update_scene()
        except Exception as e:
            print(f"Error in delayed scene update: {e}")

    def _check_interactor_ready(self):
        """Simple check if the VTK interactor is ready"""
        try:
            scene = self.scene.mayavi_scene
            return hasattr(scene, 'interactor') and scene.interactor is not None
        except:
            return False

    def update_scene(self):
        """FIXED: Use processed data correctly without automatic bone segmentation"""
        try:
            # Clear the scene
            mlab.clf(figure=self.scene.mayavi_scene)

            if self.data.size == 0:
                return

            print(f"Building 3D visualization with data shape: {self.data.shape}")
            print(f"Data range: {self.data.min()} to {self.data.max()}")

            # FIXED: Don't automatically apply bone thresholding
            # Use the data as provided - it should already be processed

            # Check if we have meaningful data variation
            data_min = self.data.min()
            data_max = self.data.max()

            if data_max <= data_min:
                print("No variation in data - cannot create 3D surface")
                return

            # Check if data appears to be already thresholded (lots of zeros)
            non_zero_count = np.count_nonzero(self.data)
            total_count = self.data.size
            zero_percentage = (total_count - non_zero_count) / total_count * 100

            print(
                f"Data analysis: {non_zero_count}/{total_count} non-zero voxels ({100 - zero_percentage:.1f}% non-zero)")

            if zero_percentage > 50:
                # Data appears to be already processed/thresholded
                # Use a low iso-level to capture the processed data
                iso_level = data_min + (data_max - data_min) * 0.01  # Very low threshold
                print(f"Using low iso-level for processed data: {iso_level}")
            else:
                # Data appears to be raw - use median as iso-level
                iso_level = np.median(self.data[self.data > data_min])
                print(f"Using median iso-level for raw data: {iso_level}")

            # Ensure iso_level is valid
            iso_level = max(data_min + 0.001, min(iso_level, data_max - 0.001))
            print(f"Final iso-surface level: {iso_level}")

            # Store iso_level for later use
            self.current_iso_level = iso_level

            # Generate mesh using marching cubes
            try:
                vertices, faces, normals, values = measure.marching_cubes(
                    self.data,
                    level=iso_level,
                    step_size=1
                )
                print(f"Generated mesh: {len(vertices)} vertices, {len(faces)} faces")

                # Store mesh data for picking
                self.mesh_data = {
                    'vertices': vertices,
                    'faces': faces,
                    'normals': normals,
                    'values': values
                }

                # CRITICAL FIX: Sample density values correctly for surface visualization
                density_values = self.sample_density_at_vertices_for_surface(vertices, iso_level)
                print(f"Surface density values range: {density_values.min():.1f} to {density_values.max():.1f}")

                # Create triangular mesh with scalar data
                mesh = mlab.triangular_mesh(
                    vertices[:, 0], vertices[:, 1], vertices[:, 2], faces,
                    scalars=density_values,
                    figure=self.scene.mayavi_scene
                )

                # Configure the surface properties safely
                try:
                    mesh.actor.property.opacity = 1.0  # CHANGED: Default to solid (not transparent)

                    # Set up the scalar visualization
                    lut_manager = mesh.module_manager.scalar_lut_manager

                    # CRITICAL FIX: Apply the selected colormap from the dropdown, don't auto-select
                    if hasattr(self, 'parent_widget') and self.parent_widget and hasattr(self.parent_widget,
                                                                                         'colormap_combo'):
                        selected_colormap = self.parent_widget.colormap_combo.currentText()
                    else:
                        selected_colormap = 'bone'  # Default to bone (uniform white)

                    print(f"Applying selected colormap: {selected_colormap}")

                    if selected_colormap == 'bone':
                        # Apply uniform white bone appearance
                        print("Applying uniform white bone colormap on initial build")
                        self.apply_white_bone_colormap(lut_manager)
                    else:
                        # Apply the selected standard colormap
                        lut_manager.lut_mode = selected_colormap
                        # Set up appropriate range for the surface
                        self.setup_surface_lut_range(mesh, density_values, iso_level)

                        # ADDITIONAL: Delayed range enforcement to ensure it sticks
                        QTimer.singleShot(200, lambda: self.enforce_medical_range(lut_manager))

                    print(f"Colormap configured correctly")

                except Exception as lut_error:
                    print(f"Warning: LUT setup error: {lut_error}")

                # Create scalar bar with better error handling
                self.setup_scalar_bar_safe(lut_manager)

                # Store references with fixed medical range
                self.current_surface = mesh
                self.current_colorbar = lut_manager
                self.current_density_range = (-100, 2000)  # Fixed medical CT range

                # Set up interactive picking
                self.setup_picker()

                # Add instruction text
                try:
                    mlab.text(0.02, 0.95, "Click on the model to see values",
                              width=0.3, color=(1, 1, 1), figure=self.scene.mayavi_scene)
                except Exception as text_error:
                    print(f"Warning: Could not add instruction text: {text_error}")

                # Set reasonable camera view
                mlab.view(azimuth=45, elevation=60, distance='auto', figure=self.scene.mayavi_scene)

                # Final render
                self.scene.mayavi_scene.render()

                print("3D visualization completed successfully")

            except Exception as mc_error:
                print(f"Marching cubes approach failed: {mc_error}")
                print("Attempting volume rendering fallback...")
                self.create_volume_rendering()

        except Exception as e:
            print(f"Failed to update scene: {str(e)}")
            import traceback
            traceback.print_exc()

    def sample_density_at_vertices_for_surface(self, vertices, iso_level):
        """FIXED: Sample density values appropriate for surface visualization"""
        try:
            # Choose which data to use for density mapping
            if self.original_data is not None:
                data_to_sample = self.original_data
                print("Sampling surface density from original data")
            else:
                data_to_sample = self.data
                print("Sampling surface density from processed data")

            # Get data dimensions
            max_z, max_y, max_x = data_to_sample.shape

            # Sample the data at vertex positions
            try:
                from scipy.ndimage import map_coordinates

                # Prepare coordinates for scipy interpolation (z, y, x order)
                coords = np.array([
                    vertices[:, 2],  # z coordinates
                    vertices[:, 1],  # y coordinates
                    vertices[:, 0]  # x coordinates
                ])

                # Clamp coordinates to valid range
                coords[0] = np.clip(coords[0], 0, max_z - 1)
                coords[1] = np.clip(coords[1], 0, max_y - 1)
                coords[2] = np.clip(coords[2], 0, max_x - 1)

                # Use trilinear interpolation
                raw_density_values = map_coordinates(
                    data_to_sample,
                    coords,
                    order=1,
                    mode='nearest'
                )

            except ImportError:
                print("SciPy not available, using nearest neighbor sampling")
                z_indices = np.clip(np.round(vertices[:, 2]).astype(int), 0, max_z - 1)
                y_indices = np.clip(np.round(vertices[:, 1]).astype(int), 0, max_y - 1)
                x_indices = np.clip(np.round(vertices[:, 0]).astype(int), 0, max_x - 1)

                raw_density_values = data_to_sample[z_indices, y_indices, x_indices]

            print(f"Raw sampled density range: {raw_density_values.min():.1f} to {raw_density_values.max():.1f}")
            print(f"Surface iso-level: {iso_level:.1f}")

            # CRITICAL FIX: The issue is that vertices can sample from anywhere in the volume
            # but the surface represents tissues around the iso-level

            # Strategy: Filter out density values that are way off from the iso-level
            # and focus on the tissue types that should actually be on this surface

            if self.original_data is not None and iso_level > 100:
                # For bone/high density surfaces in HU data
                print("Detected bone surface - filtering for bone densities")

                # Bone surface should only show bone densities, not air or soft tissue
                # Filter to keep only values that make sense for bone surface
                bone_mask = raw_density_values > 150  # Minimum bone HU

                if np.sum(bone_mask) > len(raw_density_values) * 0.3:  # At least 30% bone
                    # Use only bone densities
                    bone_densities = raw_density_values[bone_mask]

                    # Set non-bone areas to minimum bone density for consistent coloring
                    min_bone = bone_densities.min()
                    max_bone = bone_densities.max()

                    # Create filtered density values
                    filtered_densities = np.where(bone_mask, raw_density_values, min_bone)

                    print(f"Filtered bone surface range: {min_bone:.1f} to {max_bone:.1f} HU")
                    return filtered_densities.astype(np.float32)

            elif self.original_data is not None and 0 < iso_level <= 100:
                # For soft tissue surfaces in HU data
                print("Detected soft tissue surface - filtering for soft tissue densities")

                # Soft tissue surface should show soft tissue variation
                soft_tissue_mask = (raw_density_values >= -100) & (raw_density_values <= 300)

                if np.sum(soft_tissue_mask) > len(raw_density_values) * 0.5:
                    # Use soft tissue range
                    filtered_densities = np.clip(raw_density_values, -100, 300)
                    print(
                        f"Soft tissue surface range: {filtered_densities.min():.1f} to {filtered_densities.max():.1f} HU")
                    return filtered_densities.astype(np.float32)

            elif self.original_data is not None and iso_level <= 0:
                # For air/low density surfaces
                print("Detected air/low density surface")

                # Keep the range around air densities
                filtered_densities = np.clip(raw_density_values, -1000, 100)
                print(f"Air surface range: {filtered_densities.min():.1f} to {filtered_densities.max():.1f} HU")
                return filtered_densities.astype(np.float32)

            else:
                # For processed data or when filtering doesn't work
                print("Using percentile-based filtering for surface")

                # Remove extreme outliers and focus on the central range
                q10 = np.percentile(raw_density_values, 10)
                q90 = np.percentile(raw_density_values, 90)

                # Expand range slightly to avoid too narrow coloring
                range_size = q90 - q10
                if range_size < 50:  # Very narrow range
                    center = (q10 + q90) / 2
                    q10 = center - 25
                    q90 = center + 25

                filtered_densities = np.clip(raw_density_values, q10, q90)
                print(f"Percentile filtered range: {q10:.1f} to {q90:.1f}")
                return filtered_densities.astype(np.float32)

        except Exception as e:
            print(f"Error sampling surface density: {e}")
            import traceback
            traceback.print_exc()

            # Return values around the iso-level as fallback
            if iso_level > 100:
                # Bone range
                fallback_min = 200
                fallback_max = 1000
            elif iso_level > 0:
                # Soft tissue range
                fallback_min = 0
                fallback_max = 200
            else:
                # Air range
                fallback_min = -500
                fallback_max = 0

            # Create gradient across vertices for some visual variation
            fallback_values = np.linspace(fallback_min, fallback_max, len(vertices))
            print(f"Using fallback density range: {fallback_min} to {fallback_max}")
            return fallback_values.astype(np.float32)

    def setup_surface_lut_range(self, mesh, density_values, iso_level):
        """Set up LUT range appropriate for surface visualization"""
        try:
            # Get the LUT manager
            lut_manager = mesh.module_manager.scalar_lut_manager

            min_density = float(density_values.min())
            max_density = float(density_values.max())

            print(f"Surface density range for LUT: {min_density:.1f} to {max_density:.1f}")
            print(f"Iso-level: {iso_level:.1f}")

            # FIXED: Use standard medical CT range from -100 to 2000 HU
            range_min = -100  # Air and low density tissues
            range_max = 2000  # Dense bone and contrast

            print(f"Setting fixed medical CT range: {range_min} to {range_max} HU")

            # Multiple methods to ensure the range is applied correctly
            success = False

            # Method 1: Direct data_range setting
            try:
                lut_manager.use_default_range = False
                lut_manager.data_range = (range_min, range_max)
                print("Method 1: Set data_range successfully")
                success = True
            except Exception as e1:
                print(f"Method 1 failed: {e1}")

            # Method 2: LUT table range
            try:
                if hasattr(lut_manager, 'lut') and hasattr(lut_manager.lut, 'table_range'):
                    lut_manager.lut.table_range = (range_min, range_max)
                    print("Method 2: Set table_range successfully")
                    success = True
            except Exception as e2:
                print(f"Method 2 failed: {e2}")

            # Method 3: Force LUT range via scalar bar
            try:
                if hasattr(lut_manager, 'scalar_bar') and lut_manager.scalar_bar:
                    # Force the scalar bar to use our range
                    sb = lut_manager.scalar_bar
                    if hasattr(sb, 'lookup_table'):
                        sb.lookup_table.table_range = (range_min, range_max)
                        print("Method 3: Set scalar bar lookup table range")
                        success = True
            except Exception as e3:
                print(f"Method 3 failed: {e3}")

            # Method 4: Manual LUT modification
            try:
                lut = lut_manager.lut
                if lut:
                    lut.table_range = (range_min, range_max)
                    lut.modified()
                    print("Method 4: Direct LUT modification successful")
                    success = True
            except Exception as e4:
                print(f"Method 4 failed: {e4}")

            # Force update with all possible methods
            try:
                if hasattr(lut_manager, 'data_changed'):
                    lut_manager.data_changed = True
                if hasattr(lut_manager, 'lut'):
                    lut_manager.lut.modified()
                if hasattr(lut_manager, 'scalar_bar'):
                    lut_manager.scalar_bar.modified()
                print("Forced all LUT updates")
            except Exception as update_error:
                print(f"LUT update failed: {update_error}")

            if success:
                print("LUT range successfully set to -100 to 2000 HU")
            else:
                print("WARNING: All LUT range setting methods failed")

            return success

        except Exception as e:
            print(f"Failed to setup surface LUT range: {e}")
            return False

    def setup_proper_lut_range(self, mesh, density_values):
        """Legacy method that calls the new surface-specific method"""
        # For backward compatibility, use the surface-specific method
        iso_level = getattr(self, 'current_iso_level', np.median(density_values))
        return self.setup_surface_lut_range(mesh, density_values, iso_level)

    def sample_density_at_vertices_legacy(self, vertices, use_original=False):
        """Sample the data at vertex positions to get density values with proper interpolation"""
        try:
            # Choose which data to use
            if use_original and self.original_data is not None:
                data_to_sample = self.original_data
                print("Sampling from original data")
            else:
                data_to_sample = self.data
                print("Sampling from processed data")

            # Get data dimensions
            max_z, max_y, max_x = data_to_sample.shape
            print(f"Data shape for sampling: {data_to_sample.shape}")
            print(f"Vertex coordinates range: x={vertices[:, 0].min():.1f}-{vertices[:, 0].max():.1f}, "
                  f"y={vertices[:, 1].min():.1f}-{vertices[:, 1].max():.1f}, "
                  f"z={vertices[:, 2].min():.1f}-{vertices[:, 2].max():.1f}")

            # Use scipy's interpolation for more accurate sampling
            try:
                from scipy.ndimage import map_coordinates

                # Prepare coordinates for scipy interpolation (z, y, x order)
                # Note: vertices from marching cubes are in (x, y, z) order
                coords = np.array([
                    vertices[:, 2],  # z coordinates
                    vertices[:, 1],  # y coordinates
                    vertices[:, 0]  # x coordinates
                ])

                # Clamp coordinates to valid range
                coords[0] = np.clip(coords[0], 0, max_z - 1)  # z
                coords[1] = np.clip(coords[1], 0, max_y - 1)  # y
                coords[2] = np.clip(coords[2], 0, max_x - 1)  # x

                # Use trilinear interpolation for smooth density values
                density_values = map_coordinates(
                    data_to_sample,
                    coords,
                    order=1,  # Linear interpolation
                    mode='nearest'  # Use nearest for out-of-bounds
                )

                print(f"Interpolated density values range: {density_values.min():.1f} to {density_values.max():.1f}")

            except ImportError:
                print("SciPy not available, falling back to nearest neighbor sampling")
                # Fallback to nearest neighbor if scipy is not available
                z_indices = np.clip(np.round(vertices[:, 2]).astype(int), 0, max_z - 1)
                y_indices = np.clip(np.round(vertices[:, 1]).astype(int), 0, max_y - 1)
                x_indices = np.clip(np.round(vertices[:, 0]).astype(int), 0, max_x - 1)

                density_values = data_to_sample[z_indices, y_indices, x_indices]
                print(
                    f"Nearest neighbor density values range: {density_values.min():.1f} to {density_values.max():.1f}")

            return density_values.astype(np.float32)

        except Exception as e:
            print(f"Error sampling density at vertices: {e}")
            import traceback
            traceback.print_exc()

            # Return uniform fallback values
            fallback_value = float(np.mean(self.data[self.data > 0])) if np.any(self.data > 0) else 1.0
            print(f"Using fallback density value: {fallback_value}")
            return np.full(len(vertices), fallback_value, dtype=np.float32)

    def create_volume_rendering(self):
        """Fallback volume rendering if marching cubes fails"""
        try:
            print("Creating volume rendering as fallback")
            vol = mlab.pipeline.volume(
                mlab.pipeline.scalar_field(self.data, figure=self.scene.mayavi_scene),
                figure=self.scene.mayavi_scene
            )
            vol.lut_manager.lut_mode = 'bone'
            self.current_surface = vol
            self.current_colorbar = vol.lut_manager
        except Exception as e:
            print(f"Volume rendering also failed: {e}")

    def setup_scalar_bar_safe(self, lut_manager):
        """Safely set up scalar bar with multiple fallback approaches"""
        try:
            if not self.interactor_ready:
                print("Skipping scalar bar - interactor not ready")
                return False

            # Method 1: Standard approach
            try:
                lut_manager.show_scalar_bar = True

                if hasattr(lut_manager, 'scalar_bar'):
                    sb = lut_manager.scalar_bar
                    sb.title = "Density (HU)"
                    sb.label_format = "%.0f"

                    # Safe property setting for medical visualization
                    self.safe_setattr(sb, 'number_of_labels', 8)
                    self.safe_setattr(sb, 'position', (0.85, 0.1))
                    self.safe_setattr(sb, 'position2', (0.1, 0.8))

                    # Set specific range for medical CT
                    try:
                        if hasattr(sb, 'range'):
                            sb.range = (-100, 2000)
                        print("Applied medical CT range to scalar bar")
                    except Exception as sb_range_error:
                        print(f"Failed to set scalar bar range: {sb_range_error}")

                    print("Scalar bar configured successfully")
                    return True

            except Exception as sb_error:
                print(f"Standard scalar bar setup failed: {sb_error}")

            return False

        except Exception as e:
            print(f"Scalar bar setup completely failed: {e}")
            return False

    def safe_setattr(self, obj, attr, value):
        """Safely set an attribute if it exists"""
        try:
            if obj and hasattr(obj, attr):
                setattr(obj, attr, value)
                return True
            else:
                # For some VTK objects, the attribute might exist but not be settable in the usual way
                # Try alternative approach for data_changed
                if attr == 'data_changed' and hasattr(obj, 'lut'):
                    obj.lut.modified()
                    return True
        except Exception as e:
            print(f"Failed to set {attr}: {e}")
        return False

    def setup_picker(self):
        """Set up interactive picking with better error handling"""
        try:
            if not self.interactor_ready:
                print("Skipping picker setup - interactor not ready")
                return

            # Clean up existing picker
            if self.picker_callback:
                try:
                    self.scene.mayavi_scene.on_mouse_pick(self.picker_callback, remove=True)
                except:
                    pass

            # Try to set up new picker
            try:
                picker = self.scene.mayavi_scene.on_mouse_pick(self.on_pick, type='cell')
                if picker:
                    picker.tolerance = 0.01
                    self.picker_callback = picker
                    print("Picker setup completed successfully")
                else:
                    print("Picker setup returned None")
            except Exception as picker_error:
                print(f"Cell picker failed: {picker_error}")

        except Exception as e:
            print(f"Failed to setup picker: {str(e)}")

    def on_pick(self, picker_obj):
        """Handle mouse picking events"""
        try:
            print("Pick event triggered")

            if not hasattr(picker_obj, 'actor') or not picker_obj.actor:
                print("No actor found in picker")
                return

            picked_point = np.array(picker_obj.pick_position)
            print(f"Raw picked point: {picked_point}")

            if self.data is None or self.data.size == 0:
                print("No data available for picking")
                return

            max_z, max_y, max_x = self.data.shape

            x_idx = int(np.clip(round(picked_point[0]), 0, max_x - 1))
            y_idx = int(np.clip(round(picked_point[1]), 0, max_y - 1))
            z_idx = int(np.clip(round(picked_point[2]), 0, max_z - 1))

            # Use original data for density if available
            if self.original_data is not None:
                density_value = float(self.original_data[z_idx, y_idx, x_idx])
            else:
                density_value = float(self.data[z_idx, y_idx, x_idx])

            print(f"Density value at picked location: {density_value}")

            if self.parent_widget:
                self.parent_widget.update_density_info(density_value, picked_point)

            self.add_pick_marker(picked_point, density_value)

        except Exception as e:
            print(f"Failed to handle pick event: {str(e)}")
            import traceback
            traceback.print_exc()

    def add_pick_marker(self, position, density_value):
        """Add a visual marker at the picked position"""
        try:
            print(f"Adding marker at position: {position} with density: {density_value}")

            marker = mlab.points3d(
                [position[0]], [position[1]], [position[2]],
                [1],
                scale_factor=5.0,
                color=(1, 0, 0),
                figure=self.scene.mayavi_scene,
                mode='sphere'
            )

            text_pos = position + np.array([2, 2, 2])
            text_label = mlab.text3d(
                text_pos[0], text_pos[1], text_pos[2],
                f"{density_value:.1f}",
                scale=3.0,
                color=(1, 1, 0),
                figure=self.scene.mayavi_scene
            )

            self.scene.mayavi_scene.render()

            print("Marker added successfully")

        except Exception as e:
            print(f"Failed to add pick marker: {str(e)}")
            import traceback
            traceback.print_exc()

    def set_colormap(self, colormap_name):
        """Change the colormap of the current surface"""
        try:
            print(f"Setting colormap to: {colormap_name}")

            if not self.current_surface or not hasattr(self.current_surface, 'module_manager'):
                print("No current surface available for colormap change")
                return

            # Get the LUT manager
            lut_manager = self.current_surface.module_manager.scalar_lut_manager
            old_mode = getattr(lut_manager, 'lut_mode', 'unknown')

            print(f"Changing from '{old_mode}' to '{colormap_name}'")

            # Handle custom bone colormap (uniform white)
            if colormap_name == 'bone':
                self.apply_white_bone_colormap(lut_manager)
            else:
                # CRITICAL FIX: Always restore scalar coloring when switching away from white_bone
                if self.current_surface and hasattr(self.current_surface, 'actor'):
                    try:
                        # Re-enable scalar coloring for density mapping
                        self.current_surface.actor.mapper.scalar_visibility = True
                        print("Re-enabled scalar coloring for density mapping")

                        # Reset any uniform color settings
                        self.current_surface.actor.property.color = (
                        1.0, 1.0, 1.0)  # Reset to white, but scalar coloring will override

                        # Restore color bar if it was hidden
                        if hasattr(lut_manager, '_original_scalar_bar_state'):
                            lut_manager.show_scalar_bar = lut_manager._original_scalar_bar_state
                            delattr(lut_manager, '_original_scalar_bar_state')
                            print("Restored color bar display")

                    except Exception as restore_error:
                        print(f"Failed to restore scalar coloring: {restore_error}")

                # Change to standard colormap
                lut_manager.lut_mode = colormap_name

                # Clear custom colormap flags
                if hasattr(lut_manager, '_custom_colormap_applied'):
                    delattr(lut_manager, '_custom_colormap_applied')
                if hasattr(lut_manager, '_uniform_white'):
                    delattr(lut_manager, '_uniform_white')

            # Multiple update strategies (with better error handling)
            update_methods = [
                lambda: self.safe_setattr(lut_manager, 'data_changed', True),
                lambda: lut_manager.lut.modified() if hasattr(lut_manager, 'lut') else None,
                lambda: self.safe_setattr(self.current_surface.module_manager, 'data_changed', True) if hasattr(
                    self.current_surface, 'module_manager') else None,
                lambda: self.current_surface.mlab_source.update() if hasattr(self.current_surface,
                                                                             'mlab_source') else None,
                lambda: self.current_surface.update() if hasattr(self.current_surface, 'update') else None,
                lambda: self.current_surface.actor.mapper.modified() if hasattr(self.current_surface,
                                                                                'actor') and hasattr(
                    self.current_surface.actor, 'mapper') else None,
            ]

            successful_updates = 0
            for i, method in enumerate(update_methods):
                try:
                    result = method()
                    if result is not None:
                        successful_updates += 1
                except Exception as method_error:
                    print(f"Update method {i + 1} failed: {method_error}")

            print(f"Applied {successful_updates}/{len(update_methods)} update methods")

            # Force a complete refresh when switching away from bone (uniform white)
            if colormap_name != 'bone' and hasattr(lut_manager, '_uniform_white'):
                self.force_colormap_refresh(lut_manager)

            # Force render with multiple attempts and delayed color bar setup
            render_attempts = 0
            max_attempts = 3

            def attempt_render():
                nonlocal render_attempts
                try:
                    self.scene.mayavi_scene.render()
                    render_attempts += 1
                    print(f"Render attempt {render_attempts} completed")

                    # On final render attempt, ensure color bar is properly setup
                    if render_attempts == max_attempts and colormap_name != 'bone':
                        self.ensure_colorbar_visible(lut_manager)

                    if render_attempts < max_attempts:
                        QTimer.singleShot(50 * render_attempts, attempt_render)

                except Exception as render_error:
                    print(f"Render attempt {render_attempts + 1} failed: {render_error}")

            attempt_render()

            # Verify the change
            if colormap_name != 'bone':
                new_mode = getattr(lut_manager, 'lut_mode', 'unknown')
                print(f"Colormap change completed: '{old_mode}' -> '{new_mode}'")
            else:
                print(f"Custom uniform white bone colormap applied")

        except Exception as e:
            print(f"Failed to set colormap: {str(e)}")
            import traceback
            traceback.print_exc()

    def apply_white_bone_colormap(self, lut_manager):
        """Apply uniform white bone color (no density mapping)"""
        try:
            print("Applying uniform white bone color")

            # Method 1: Try to set uniform color via actor material properties
            try:
                if self.current_surface and hasattr(self.current_surface, 'actor'):
                    # Set the actor to use a uniform white color
                    self.current_surface.actor.property.color = (1.0, 1.0, 1.0)  # Pure white

                    # Disable scalar coloring to use uniform color
                    self.current_surface.actor.mapper.scalar_visibility = False

                    # Set material properties for realistic bone appearance
                    self.current_surface.actor.property.ambient = 0.3  # Ambient lighting
                    self.current_surface.actor.property.diffuse = 0.7  # Diffuse reflection
                    self.current_surface.actor.property.specular = 0.3  # Specular highlight
                    self.current_surface.actor.property.specular_power = 20  # Shininess

                    print("Applied uniform white color via actor properties")
                    return

            except Exception as actor_error:
                print(f"Actor color method failed: {actor_error}")

            # Method 2: Fallback - create uniform LUT
            try:
                # Get the LUT (lookup table)
                lut = lut_manager.lut.table.to_array()

                # Set all colors to the same white bone color
                # Use a slightly off-white for more realistic bone appearance
                bone_white_r = 248  # Slightly off pure white
                bone_white_g = 248
                bone_white_b = 255  # Very slight blue tint like real bone

                for i in range(len(lut)):
                    lut[i][0] = bone_white_r  # Red
                    lut[i][1] = bone_white_g  # Green
                    lut[i][2] = bone_white_b  # Blue
                    lut[i][3] = 255  # Alpha (fully opaque)

                # Apply the uniform lookup table
                lut_manager.lut.table = lut
                lut_manager.lut.modified()
                lut_manager.data_changed = True

                print("Applied uniform white color via LUT")

            except Exception as lut_error:
                print(f"LUT uniform color method failed: {lut_error}")

            # Mark that custom colormap is applied
            lut_manager._custom_colormap_applied = True
            lut_manager._uniform_white = True  # Flag for uniform white

            # Hide color bar since uniform color doesn't need density mapping display
            try:
                if hasattr(lut_manager, 'show_scalar_bar'):
                    lut_manager._original_scalar_bar_state = lut_manager.show_scalar_bar
                    lut_manager.show_scalar_bar = False
                    print("Hid color bar for uniform white display")
            except Exception as colorbar_error:
                print(f"Failed to hide color bar: {colorbar_error}")

            print("Uniform white bone color applied successfully")

        except Exception as e:
            print(f"Failed to apply uniform white bone color: {e}")
            # Fallback to hot colormap if custom fails (since "bone" is now uniform white)
            try:
                lut_manager.lut_mode = 'hot'
                print("Fallback to hot colormap")
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")

    def force_colormap_refresh(self, lut_manager):
        """Force a complete refresh when switching from bone (uniform white) to other colormaps"""
        try:
            print("Forcing complete colormap refresh")

            # Ensure color bar is visible
            try:
                lut_manager.show_scalar_bar = True
                print("Ensured color bar is visible")
            except Exception as cb_error:
                print(f"Failed to show color bar: {cb_error}")

            # Force LUT to rebuild completely
            if hasattr(lut_manager, 'lut'):
                lut_manager.lut.modified()
                if hasattr(lut_manager.lut, 'build'):
                    lut_manager.lut.build()

            # Force mapper to update
            if self.current_surface and hasattr(self.current_surface, 'actor'):
                mapper = self.current_surface.actor.mapper
                if mapper:
                    mapper.update()
                    mapper.modified()

                # Force actor to update
                self.current_surface.actor.modified()

            # Force scene render
            if hasattr(self.scene, 'mayavi_scene'):
                self.scene.mayavi_scene.render()

            print("Complete colormap refresh completed")

        except Exception as e:
            print(f"Force refresh failed: {e}")

    def ensure_colorbar_visible(self, lut_manager):
        """Ensure color bar is visible in embedded view"""
        try:
            print("Ensuring color bar is visible in embedded view")

            # Multiple approaches to force color bar visibility
            methods_tried = 0

            # Method 1: Direct scalar bar manipulation
            try:
                if hasattr(lut_manager, 'scalar_bar') and lut_manager.scalar_bar:
                    lut_manager.scalar_bar.visibility = True
                    methods_tried += 1
                    print("Method 1: Set scalar_bar.visibility = True")
            except Exception as e1:
                print(f"Method 1 failed: {e1}")

            # Method 2: Force show_scalar_bar
            try:
                lut_manager.show_scalar_bar = True
                methods_tried += 1
                print("Method 2: Set show_scalar_bar = True")
            except Exception as e2:
                print(f"Method 2 failed: {e2}")

            # Method 3: Recreate scalar bar if needed
            try:
                if not hasattr(lut_manager, 'scalar_bar') or not lut_manager.scalar_bar:
                    # Force creation of scalar bar
                    lut_manager.show_scalar_bar = False
                    lut_manager.show_scalar_bar = True
                    methods_tried += 1
                    print("Method 3: Recreated scalar bar")
            except Exception as e3:
                print(f"Method 3 failed: {e3}")

            # Method 4: Force render and update
            try:
                if hasattr(self.scene, 'mayavi_scene'):
                    self.scene.mayavi_scene.render()
                    # Additional render after small delay
                    QTimer.singleShot(100, lambda: self.scene.mayavi_scene.render())
                    methods_tried += 1
                    print("Method 4: Forced additional renders")
            except Exception as e4:
                print(f"Method 4 failed: {e4}")

            print(f"Color bar visibility enforcement: {methods_tried} methods attempted")

        except Exception as e:
            print(f"Ensure colorbar visible failed: {e}")

    def enforce_medical_range(self, lut_manager):
        """Enforce the medical CT range (-100 to 2000) with delayed application"""
        try:
            print("Enforcing medical CT range with delayed application")

            range_min, range_max = -100, 2000

            # Try multiple enforcement methods
            methods_successful = 0

            # Method 1: LUT manager data range
            try:
                lut_manager.use_default_range = False
                lut_manager.data_range = (range_min, range_max)
                methods_successful += 1
                print("Enforced via data_range")
            except Exception as e1:
                print(f"Enforcement method 1 failed: {e1}")

            # Method 2: Direct LUT table range
            try:
                if hasattr(lut_manager, 'lut'):
                    lut_manager.lut.table_range = (range_min, range_max)
                    lut_manager.lut.modified()
                    methods_successful += 1
                    print("Enforced via LUT table_range")
            except Exception as e2:
                print(f"Enforcement method 2 failed: {e2}")

            # Method 3: Scalar bar range (if available)
            try:
                if hasattr(lut_manager, 'scalar_bar') and lut_manager.scalar_bar:
                    if hasattr(lut_manager.scalar_bar, 'lookup_table'):
                        lut_manager.scalar_bar.lookup_table.table_range = (range_min, range_max)
                        methods_successful += 1
                        print("Enforced via scalar bar lookup table")
            except Exception as e3:
                print(f"Enforcement method 3 failed: {e3}")

            # Force render to apply changes
            try:
                if hasattr(self.scene, 'mayavi_scene'):
                    self.scene.mayavi_scene.render()
                    print("Forced render after range enforcement")
            except Exception as render_error:
                print(f"Render after enforcement failed: {render_error}")

            print(f"Medical range enforcement: {methods_successful} methods succeeded")

        except Exception as e:
            print(f"Medical range enforcement failed: {e}")

    def set_opacity(self, opacity):
        """Change the opacity of the current surface"""
        try:
            if self.current_surface and hasattr(self.current_surface, 'actor'):
                self.current_surface.actor.property.opacity = opacity
                self.scene.mayavi_scene.render()
                print(f"Updated opacity to: {opacity}")
        except Exception as e:
            print(f"Failed to set opacity: {str(e)}")

    def toggle_colorbar(self, show):
        """Toggle colorbar visibility with enhanced embedded view support"""
        try:
            print(f"Toggling colorbar: {show}")

            if self.current_colorbar and hasattr(self.current_colorbar, 'show_scalar_bar'):
                # Check if interactor is ready
                if hasattr(self.scene.mayavi_scene, 'interactor') and self.scene.mayavi_scene.interactor:
                    self.current_colorbar.show_scalar_bar = show

                    # Force update with multiple methods for embedded view
                    if hasattr(self.current_colorbar, 'scalar_bar'):
                        self.current_colorbar.scalar_bar.visibility = show

                        if show:
                            # Additional configuration for embedded view
                            try:
                                sb = self.current_colorbar.scalar_bar
                                sb.title = "Density (HU)"
                                sb.label_format = "%.0f"
                                # Force position and size for embedded view
                                if hasattr(sb, 'position'):
                                    sb.position = (0.85, 0.1)
                                if hasattr(sb, 'position2'):
                                    sb.position2 = (0.1, 0.8)
                                # Set medical CT range
                                if hasattr(sb, 'range'):
                                    sb.range = (-100, 2000)
                                print("Applied colorbar configuration for embedded view with medical range")
                            except Exception as config_error:
                                print(f"Colorbar configuration error: {config_error}")

                    # Multiple render attempts to ensure visibility
                    self.scene.mayavi_scene.render()
                    QTimer.singleShot(50, lambda: self.scene.mayavi_scene.render())
                    QTimer.singleShot(150, lambda: self.scene.mayavi_scene.render())

                    print(f"Colorbar visibility set to: {show}")
                else:
                    print("Interactor not ready, deferring colorbar toggle")
                    # Store the desired state and try again later
                    self.colorbar_pending = show
                    QTimer.singleShot(100, lambda: self.toggle_colorbar(show))
            else:
                print("No colorbar available to toggle")

        except Exception as e:
            print(f"Failed to toggle colorbar: {str(e)}")
            import traceback
            traceback.print_exc()

    def get_density_statistics(self):
        """Get density statistics for the current data"""
        try:
            if self.data.size > 0:
                non_zero_data = self.data[self.data > 0]
                if len(non_zero_data) > 0:
                    stats = {
                        'min': float(non_zero_data.min()),
                        'max': float(non_zero_data.max()),
                        'mean': float(non_zero_data.mean()),
                        'std': float(non_zero_data.std()),
                        'median': float(np.median(non_zero_data))
                    }
                    return stats
            return None
        except Exception as e:
            print(f"Failed to get density statistics: {str(e)}")
            return None