# enhanced_mayavi_widget.py
from mayavi import mlab
from pyface.qt import QtGui, QtCore
from mayavi.core.ui.api import MayaviScene, MlabSceneModel, SceneEditor
from traits.api import HasTraits, Instance, Array, on_trait_change
from traitsui.api import View, Item
from tvtk.pyface.scene_editor import SceneEditor
from pyface.qt.QtGui import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
from pyface.qt.QtCore import QTimer
import numpy as np
from tvtk.api import tvtk
import vtk
from mayavi.core.api import PipelineBase
from mayavi.core.ui.api import SceneEditor
from skimage import measure


class DensityColoredVisualization(HasTraits):
    scene = Instance(MlabSceneModel, ())
    data = Array(dtype=np.float32, shape=(None, None, None))

    # Predefined colormaps for bone density visualization
    COLORMAPS = {
        'Bone Density': 'bone',  # White (dense) to black (less dense)
        'Hot Metal': 'hot',  # Black-red-yellow-white (thermal style)
        'Cool to Warm': 'coolwarm',  # Blue (less dense) to red (dense)
        'Rainbow': 'jet',  # Blue-cyan-yellow-red (full spectrum)
        'Viridis': 'viridis',  # Purple-blue-green-yellow (perceptually uniform)
        'Plasma': 'plasma',  # Purple-pink-yellow-white
        'Turbo': 'turbo'  # Blue-cyan-green-yellow-orange-red
    }

    view = View(Item('scene', editor=SceneEditor(scene_class=MayaviScene), show_label=False), resizable=True)

    def __init__(self, data=None, **traits):
        super(DensityColoredVisualization, self).__init__(**traits)
        self.data = data.astype(np.float32) if data is not None else np.zeros((0, 0, 0), dtype=np.float32)
        self.current_colormap = 'bone'
        self.mesh_surface = None
        self.picker = None
        self.density_callback = None
        self.vertices = None
        self.faces = None
        self.vertex_densities = None

        if self.data.size > 0:
            self.create_density_colored_surface()
            self.setup_picker()

    def set_density_callback(self, callback):
        """Set callback function to handle density value display"""
        self.density_callback = callback

    def create_density_colored_surface(self, colormap='bone', iso_level=None):
        """Create a 3D surface where each point is colored by its density value"""
        try:
            # Clear the scene
            mlab.clf(figure=self.scene.mayavi_scene)

            # Calculate statistics for automatic iso-level determination
            data_min = float(np.min(self.data))
            data_max = float(np.max(self.data))
            data_mean = float(np.mean(self.data))
            data_std = float(np.std(self.data))

            print(f"Data statistics: min={data_min:.1f}, max={data_max:.1f}, mean={data_mean:.1f}, std={data_std:.1f}")

            # Determine iso-level for surface extraction
            if iso_level is None:
                # Use a level that captures bone while excluding soft tissue
                if data_max > 1000:  # Likely HU values
                    iso_level = 200  # Bone threshold in HU
                else:  # Normalized or processed data
                    iso_level = data_mean + 0.5 * data_std

                # Ensure iso_level is within valid range
                iso_level = max(data_min + (data_max - data_min) * 0.1,
                                min(iso_level, data_max - (data_max - data_min) * 0.1))

            print(f"Using iso-level: {iso_level}")

            # Extract surface using marching cubes
            self.vertices, self.faces, _, _ = measure.marching_cubes(
                self.data, level=iso_level, spacing=(1.0, 1.0, 1.0)
            )

            print(f"Surface extracted: {len(self.vertices)} vertices, {len(self.faces)} faces")

            # Calculate density values at each vertex by interpolating from the volume data
            self.vertex_densities = self.interpolate_density_at_vertices()

            # Create the surface mesh with density-based coloring
            self.create_colored_mesh(colormap)

            # Add a colorbar to show the density scale
            self.add_density_colorbar()

            # Render the scene
            self.scene.mayavi_scene.render()

            print(f"Density-colored surface created with {len(self.vertices)} vertices")

        except Exception as e:
            print(f"Failed to create density-colored surface: {str(e)}")
            import traceback
            traceback.print_exc()

    def interpolate_density_at_vertices(self):
        """Interpolate density values at mesh vertices from volume data"""
        try:
            vertex_densities = np.zeros(len(self.vertices))

            for i, vertex in enumerate(self.vertices):
                # Convert vertex coordinates to volume indices
                z, y, x = vertex  # Note: marching cubes returns (z, y, x) order

                # Clip coordinates to volume bounds
                z = np.clip(z, 0, self.data.shape[0] - 1)
                y = np.clip(y, 0, self.data.shape[1] - 1)
                x = np.clip(x, 0, self.data.shape[2] - 1)

                # Use trilinear interpolation for smooth density values
                z0, z1 = int(np.floor(z)), int(np.ceil(z))
                y0, y1 = int(np.floor(y)), int(np.ceil(y))
                x0, x1 = int(np.floor(x)), int(np.ceil(x))

                # Ensure indices are within bounds
                z0 = max(0, min(z0, self.data.shape[0] - 1))
                z1 = max(0, min(z1, self.data.shape[0] - 1))
                y0 = max(0, min(y0, self.data.shape[1] - 1))
                y1 = max(0, min(y1, self.data.shape[1] - 1))
                x0 = max(0, min(x0, self.data.shape[2] - 1))
                x1 = max(0, min(x1, self.data.shape[2] - 1))

                # Trilinear interpolation weights
                if z1 != z0:
                    wz = (z - z0) / (z1 - z0)
                else:
                    wz = 0.0

                if y1 != y0:
                    wy = (y - y0) / (y1 - y0)
                else:
                    wy = 0.0

                if x1 != x0:
                    wx = (x - x0) / (x1 - x0)
                else:
                    wx = 0.0

                # Interpolate density
                c000 = self.data[z0, y0, x0]
                c001 = self.data[z0, y0, x1]
                c010 = self.data[z0, y1, x0]
                c011 = self.data[z0, y1, x1]
                c100 = self.data[z1, y0, x0]
                c101 = self.data[z1, y0, x1]
                c110 = self.data[z1, y1, x0]
                c111 = self.data[z1, y1, x1]

                # Trilinear interpolation
                c00 = c000 * (1 - wx) + c001 * wx
                c01 = c010 * (1 - wx) + c011 * wx
                c10 = c100 * (1 - wx) + c101 * wx
                c11 = c110 * (1 - wx) + c111 * wx

                c0 = c00 * (1 - wy) + c01 * wy
                c1 = c10 * (1 - wy) + c11 * wy

                density = c0 * (1 - wz) + c1 * wz
                vertex_densities[i] = density

            print(f"Vertex densities: min={vertex_densities.min():.1f}, max={vertex_densities.max():.1f}")
            return vertex_densities

        except Exception as e:
            print(f"Error interpolating densities: {str(e)}")
            # Fallback: use mean density for all vertices
            return np.full(len(self.vertices), np.mean(self.data))

    def create_colored_mesh(self, colormap='bone'):
        """Create a colored mesh surface using Mayavi"""
        try:
            # Create the mesh surface
            x, y, z = self.vertices[:, 2], self.vertices[:, 1], self.vertices[:, 0]  # Convert to x,y,z order

            # Create triangular mesh
            self.mesh_surface = mlab.triangular_mesh(
                x, y, z, self.faces,
                scalars=self.vertex_densities,
                figure=self.scene.mayavi_scene
            )

            # Configure surface properties for better density visualization
            self.mesh_surface.mlab_source.dataset.point_data.scalars = self.vertex_densities
            self.mesh_surface.mlab_source.dataset.point_data.scalars.name = 'bone_density'

            # Set colormap
            self.mesh_surface.module_manager.scalar_lut_manager.lut_mode = colormap

            # Configure color mapping range
            density_min = float(np.min(self.vertex_densities))
            density_max = float(np.max(self.vertex_densities))
            self.mesh_surface.module_manager.scalar_lut_manager.data_range = [density_min, density_max]

            # Surface appearance settings
            self.mesh_surface.actor.property.specular = 0.3
            self.mesh_surface.actor.property.specular_power = 30
            self.mesh_surface.actor.property.diffuse = 0.8
            self.mesh_surface.actor.property.ambient = 0.2

            # Enable scalar visibility to show colors
            self.mesh_surface.actor.mapper.scalar_visibility = True

            print(f"Colored mesh created with density range: {density_min:.1f} to {density_max:.1f}")

        except Exception as e:
            print(f"Error creating colored mesh: {str(e)}")
            import traceback
            traceback.print_exc()

    def add_density_colorbar(self):
        """Add a colorbar showing the density scale"""
        try:
            if self.mesh_surface:
                # Add colorbar
                cb = mlab.colorbar(
                    self.mesh_surface,
                    title="Bone Density (HU)",
                    orientation='vertical',
                    figure=self.scene.mayavi_scene
                )

                # Customize colorbar appearance
                cb.scalar_bar_representation.position = [0.85, 0.1]
                cb.scalar_bar_representation.position2 = [0.1, 0.8]
                cb.label_text_property.font_size = 10

        except Exception as e:
            print(f"Error adding colorbar: {str(e)}")

    def setup_picker(self):
        """Set up picking functionality to get density values on click"""
        try:
            # Enable picking on the surface
            self.picker = self.scene.mayavi_scene.on_mouse_pick(self.on_pick, type='point')
            print("Picker setup complete - click on the bone surface to see density values")
        except Exception as e:
            print(f"Failed to setup picker: {str(e)}")

    def on_pick(self, picker_obj):
        """Handle mouse picking events to show density at clicked location"""
        try:
            if hasattr(picker_obj, 'point_id') and picker_obj.point_id >= 0:
                point_id = picker_obj.point_id

                # Get the density value at the picked vertex
                if (self.vertex_densities is not None and
                        0 <= point_id < len(self.vertex_densities)):

                    density_value = self.vertex_densities[point_id]
                    vertex_coords = self.vertices[point_id]

                    print(f"Picked vertex {point_id}")
                    print(
                        f"Vertex coordinates: ({vertex_coords[2]:.1f}, {vertex_coords[1]:.1f}, {vertex_coords[0]:.1f})")
                    print(f"Bone density: {density_value:.2f} HU")

                    # Call the callback function if set
                    if self.density_callback:
                        self.density_callback(
                            density_value,
                            (vertex_coords[2], vertex_coords[1], vertex_coords[0]),  # Convert to x,y,z
                            point_id
                        )

        except Exception as e:
            print(f"Error in pick handler: {str(e)}")

    def change_colormap(self, colormap_name):
        """Change the colormap of the bone surface"""
        try:
            if colormap_name in self.COLORMAPS:
                colormap = self.COLORMAPS[colormap_name]

                # Update surface colormap
                if self.mesh_surface:
                    self.mesh_surface.module_manager.scalar_lut_manager.lut_mode = colormap

                    # Re-render the scene
                    self.scene.mayavi_scene.render()
                    self.current_colormap = colormap

                    print(f"Changed colormap to: {colormap_name}")

        except Exception as e:
            print(f"Failed to change colormap: {str(e)}")

    def update_iso_level(self, new_iso_level):
        """Update the iso-level for surface extraction"""
        try:
            print(f"Updating iso-level to: {new_iso_level}")
            self.create_density_colored_surface(self.current_colormap, new_iso_level)
        except Exception as e:
            print(f"Error updating iso-level: {str(e)}")


class EnhancedMayaviQWidget(QWidget):
    def __init__(self, parent=None, data=None):
        try:
            QWidget.__init__(self, parent)

            # Create the main layout
            layout = QVBoxLayout(self)

            # Create control panel
            control_panel = self.create_control_panel()
            layout.addWidget(control_panel)

            # Create the visualization
            self.visualization = DensityColoredVisualization(data=data)
            self.visualization.set_density_callback(self.on_density_picked)

            # Create the Mayavi widget
            self.ui = self.visualization.edit_traits(parent=self, kind='subpanel').control
            layout.addWidget(self.ui)

            # Create status label for density display
            self.density_label = QLabel("Click on the bone surface to see density values")
            self.density_label.setStyleSheet("""
                QLabel {
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    padding: 5px;
                    font-weight: bold;
                    color: #333;
                }
            """)
            layout.addWidget(self.density_label)

            self.setLayout(layout)

        except Exception as e:
            print(f"Failed to initialize EnhancedMayaviQWidget: {str(e)}")

    def create_control_panel(self):
        """Create control panel with colormap and threshold selection"""
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)

        # Colormap selection
        colormap_label = QLabel("Density Color Map:")
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(list(DensityColoredVisualization.COLORMAPS.keys()))
        self.colormap_combo.setCurrentText('Bone Density')
        self.colormap_combo.currentTextChanged.connect(self.on_colormap_changed)

        # Refresh button to regenerate surface
        self.refresh_button = QPushButton("Refresh Surface")
        self.refresh_button.clicked.connect(self.refresh_surface)

        # Add widgets to layout
        control_layout.addWidget(colormap_label)
        control_layout.addWidget(self.colormap_combo)
        control_layout.addWidget(self.refresh_button)
        control_layout.addStretch()

        return control_widget

    def on_colormap_changed(self, colormap_name):
        """Handle colormap change"""
        try:
            self.visualization.change_colormap(colormap_name)
        except Exception as e:
            print(f"Error changing colormap: {str(e)}")

    def refresh_surface(self):
        """Refresh the bone surface"""
        try:
            self.visualization.create_density_colored_surface(self.visualization.current_colormap)
        except Exception as e:
            print(f"Error refreshing surface: {str(e)}")

    def on_density_picked(self, density_value, world_coords, vertex_id):
        """Handle density value picked from 3D visualization"""
        try:
            # Update the density display label
            self.density_label.setText(
                f"Bone Density: {density_value:.2f} HU | "
                f"Position: ({world_coords[0]:.1f}, {world_coords[1]:.1f}, {world_coords[2]:.1f}) | "
                f"Vertex ID: {vertex_id}"
            )

            # You can also emit a signal here if you want to update other parts of your application

        except Exception as e:
            print(f"Error handling density pick: {str(e)}")


# Backward compatibility - keep the original class name but use enhanced version
class MayaviQWidget(EnhancedMayaviQWidget):
    """Backward compatible class that uses the enhanced version"""
    pass


# Keep the original Visualization class for backward compatibility
class Visualization(DensityColoredVisualization):
    """Backward compatible class that uses the enhanced version"""
    pass