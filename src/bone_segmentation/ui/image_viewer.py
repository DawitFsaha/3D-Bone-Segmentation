# image_viewer.py
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QBrush, QColor, QWheelEvent, QMouseEvent, QImage, QPen, QCursor


class DirectROI(QGraphicsRectItem):
    """A direct ROI rectangle with immediate updates"""

    def __init__(self, rect, viewer, parent=None):
        super().__init__(rect, parent)
        self.setPen(QPen(QColor(255, 0, 0), 2))
        self.setBrush(QBrush(QColor(255, 0, 0, 30)))
        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)

        self.viewer = viewer  # Direct reference to viewer
        self.resize_margin = 15
        self.is_resizing = False
        self.resize_direction = None
        self.mouse_press_pos = QPointF()
        self.mouse_press_rect = QRectF()
        self.last_update_rect = QRectF()

        # Timer for throttled updates during rapid mouse movements
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._delayed_update)
        self.update_timer.setSingleShot(True)
        self.pending_update = False

    def get_resize_direction(self, pos):
        """Determine resize direction"""
        rect = self.rect()
        margin = self.resize_margin

        # Check all edges and corners
        left = pos.x() <= margin
        right = pos.x() >= rect.width() - margin
        top = pos.y() <= margin
        bottom = pos.y() >= rect.height() - margin

        if left and top:
            return 'nw'  # northwest
        elif right and top:
            return 'ne'  # northeast
        elif left and bottom:
            return 'sw'  # southwest
        elif right and bottom:
            return 'se'  # southeast
        elif top:
            return 'n'  # north
        elif bottom:
            return 's'  # south
        elif left:
            return 'w'  # west
        elif right:
            return 'e'  # east
        return None

    def get_cursor(self, direction):
        """Get cursor for direction"""
        cursors = {
            'nw': Qt.SizeFDiagCursor, 'se': Qt.SizeFDiagCursor,
            'ne': Qt.SizeBDiagCursor, 'sw': Qt.SizeBDiagCursor,
            'n': Qt.SizeVerCursor, 's': Qt.SizeVerCursor,
            'w': Qt.SizeHorCursor, 'e': Qt.SizeHorCursor
        }
        return cursors.get(direction, Qt.ArrowCursor)

    def hoverMoveEvent(self, event):
        if not self.is_resizing:
            direction = self.get_resize_direction(event.pos())
            cursor = self.get_cursor(direction) if direction else Qt.SizeAllCursor
            self.setCursor(cursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        if not self.is_resizing:
            self.setCursor(Qt.ArrowCursor)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_press_pos = event.pos()
            self.mouse_press_rect = QRectF(self.rect())
            self.resize_direction = self.get_resize_direction(event.pos())

            if self.resize_direction:
                self.is_resizing = True
                self.setFlag(QGraphicsRectItem.ItemIsMovable, False)
                self.setCursor(self.get_cursor(self.resize_direction))
                event.accept()
                return
            else:
                self.setFlag(QGraphicsRectItem.ItemIsMovable, True)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_resizing and self.resize_direction:
            self.perform_resize(event.pos())
            # IMMEDIATE update to other views with throttling
            self.notify_change_immediate()
            event.accept()
        else:
            super().mouseMoveEvent(event)
            # Also handle move updates
            if not self.is_resizing:
                self.notify_change_immediate()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_resizing = False
            self.resize_direction = None
            self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
            self.setCursor(Qt.ArrowCursor)
            # Final update
            self.notify_change()

        try:
            super().mouseReleaseEvent(event)
        except RuntimeError:
            pass

    def perform_resize(self, pos):
        """Direct resize with full bidirectional support"""
        try:
            diff = pos - self.mouse_press_pos
            new_rect = QRectF(self.mouse_press_rect)

            # Apply resize in all directions
            if 'n' in self.resize_direction:  # North (top)
                new_rect.setTop(new_rect.top() + diff.y())
            if 's' in self.resize_direction:  # South (bottom)
                new_rect.setBottom(new_rect.bottom() + diff.y())
            if 'w' in self.resize_direction:  # West (left)
                new_rect.setLeft(new_rect.left() + diff.x())
            if 'e' in self.resize_direction:  # East (right)
                new_rect.setRight(new_rect.right() + diff.x())

            # Handle flipping when dragging past opposite edge
            if new_rect.width() < 0:
                left, right = new_rect.left(), new_rect.right()
                new_rect.setLeft(right)
                new_rect.setRight(left)
                # Flip direction
                self.resize_direction = self.resize_direction.replace('w', 'temp').replace('e', 'w').replace('temp',
                                                                                                             'e')

            if new_rect.height() < 0:
                top, bottom = new_rect.top(), new_rect.bottom()
                new_rect.setTop(bottom)
                new_rect.setBottom(top)
                # Flip direction
                self.resize_direction = self.resize_direction.replace('n', 'temp').replace('s', 'n').replace('temp',
                                                                                                             's')

            # Minimum size
            min_size = 5
            if new_rect.width() < min_size:
                if 'w' in self.resize_direction:
                    new_rect.setLeft(new_rect.right() - min_size)
                else:
                    new_rect.setRight(new_rect.left() + min_size)

            if new_rect.height() < min_size:
                if 'n' in self.resize_direction:
                    new_rect.setTop(new_rect.bottom() - min_size)
                else:
                    new_rect.setBottom(new_rect.top() + min_size)

            self.setRect(new_rect)

        except Exception as e:
            print(f"Error in resize: {e}")

    def notify_change_immediate(self):
        """Immediate notification with throttling for better performance"""
        try:
            # Use throttled updates during rapid mouse movements
            if not self.update_timer.isActive():
                self.notify_change()
                self.update_timer.start(16)  # ~60 FPS updates
            else:
                self.pending_update = True
        except Exception as e:
            print(f"Error in immediate notification: {e}")

    def _delayed_update(self):
        """Handle delayed updates"""
        try:
            if self.pending_update:
                self.notify_change()
                self.pending_update = False
        except Exception as e:
            print(f"Error in delayed update: {e}")

    def notify_change(self):
        """Notify viewer of changes"""
        try:
            current_rect = self.get_final_rect()
            # Only update if rect actually changed significantly
            if not current_rect.isValid() or current_rect.isEmpty():
                return

            # Check if change is significant enough (avoid micro-updates)
            if (abs(current_rect.x() - self.last_update_rect.x()) < 1 and
                    abs(current_rect.y() - self.last_update_rect.y()) < 1 and
                    abs(current_rect.width() - self.last_update_rect.width()) < 1 and
                    abs(current_rect.height() - self.last_update_rect.height()) < 1):
                return

            self.last_update_rect = current_rect
            self.viewer.on_roi_changed_direct(current_rect)
        except Exception as e:
            print(f"Error notifying change: {e}")

    def get_final_rect(self):
        """Get final rectangle including position"""
        rect = self.rect()
        pos = self.pos()
        return QRectF(rect.x() + pos.x(), rect.y() + pos.y(), rect.width(), rect.height())

    def itemChange(self, change, value):
        """Handle position changes"""
        try:
            result = super().itemChange(change, value)
            if change == QGraphicsRectItem.ItemPositionHasChanged and not self.is_resizing:
                self.notify_change_immediate()
            return result
        except Exception as e:
            print(f"Error in itemChange: {e}")
            return value


class ImageViewer(QGraphicsView):
    roi_changed = pyqtSignal(QRectF, str)

    def __init__(self, orientation='axial', parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFixedSize(400, 400)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.set_background_color(QColor(255, 255, 253))

        self._zoom = 0
        self._initial_scale = 1
        self._max_zoom = 50
        self._is_panning = False
        self._pan_start_x = 0
        self._pan_start_y = 0
        self._stored_transform = self.transform()
        self._stored_scroll_pos = QPointF(0, 0)

        # ROI variables
        self._is_drawing_roi = False
        self._roi_start_point = QPointF()
        self._roi_current_rect = None
        self._roi_rect = None
        self._roi_graphics_item = None
        self._external_roi_update = False

        # Add reference to functions for direct access
        self.functions = None

        # Force immediate updates
        self._force_immediate_updates = True

    def set_functions_reference(self, functions):
        """Set reference to MainWindowFunctions"""
        self.functions = functions

    def on_roi_changed_direct(self, rect):
        """Direct ROI change handler with immediate propagation"""
        try:
            if not self._external_roi_update and self.functions:
                self._roi_rect = rect
                print(f"Direct ROI change in {self.orientation}: {rect}")
                # Immediate propagation to other views
                self.functions.on_roi_changed_immediate(rect, self.orientation)

                # Force immediate visual updates in other views
                if self._force_immediate_updates:
                    self._trigger_other_view_updates()
        except Exception as e:
            print(f"Error in direct ROI change: {e}")

    def _trigger_other_view_updates(self):
        """Trigger immediate visual updates in other views"""
        try:
            if not self.functions or not hasattr(self.functions, 'main_window'):
                return

            main_window = self.functions.main_window

            # Force other views to update their display immediately
            views_to_update = []
            if self.orientation != 'coronal':
                views_to_update.append(main_window.coronal_view)
            if self.orientation != 'sagittal':
                views_to_update.append(main_window.sagittal_view)
            if self.orientation != 'axial':
                views_to_update.append(main_window.axial_view)

            for view in views_to_update:
                try:
                    # Force immediate scene update
                    view.scene.update()
                    view.update()
                    view.viewport().update()
                except Exception as e:
                    print(f"Error updating view {view.orientation}: {e}")

        except Exception as e:
            print(f"Error triggering other view updates: {e}")

    def set_background_color(self, color):
        self.scene.setBackgroundBrush(QBrush(color))

    def display_image(self, qimage):
        try:
            roi_rect = self._roi_rect
            self.scene.clear()
            self._roi_graphics_item = None

            pixmap = QPixmap.fromImage(qimage)
            scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._pixmap_item = QGraphicsPixmapItem(scaled_pixmap)
            self._pixmap_item.setTransformationMode(Qt.SmoothTransformation)
            self.scene.addItem(self._pixmap_item)
            self.setSceneRect(QRectF(self._pixmap_item.boundingRect()))

            self.center_image()

            if roi_rect is not None:
                self._roi_rect = roi_rect
                self._redraw_roi()

            self.apply_stored_transform_and_scroll()
        except Exception as e:
            print(f"Failed to display image: {str(e)}")

    def _redraw_roi(self):
        """Redraw ROI"""
        try:
            if self._roi_rect is not None and not self._external_roi_update:
                self._roi_graphics_item = DirectROI(self._roi_rect, self)
                self._roi_graphics_item.setAcceptHoverEvents(True)
                self.scene.addItem(self._roi_graphics_item)

                # Force immediate visual update
                self.scene.update(self._roi_rect)
                self.update()
        except Exception as e:
            print(f"Failed to redraw ROI: {str(e)}")

    def set_roi_from_external(self, rect):
        """Set ROI from other views with immediate visual feedback"""
        try:
            print(f"Setting external ROI in {self.orientation}: {rect}")
            self._external_roi_update = True

            # Remove existing ROI graphics item
            if self._roi_graphics_item:
                try:
                    self.scene.removeItem(self._roi_graphics_item)
                except:
                    pass
                self._roi_graphics_item = None

            # Set the new ROI rect
            self._roi_rect = rect

            # If rect is valid and not empty, create new ROI graphics
            if rect is not None and not rect.isEmpty():
                # Create and add new ROI graphics item
                self._roi_graphics_item = DirectROI(rect, self)
                self._roi_graphics_item.setAcceptHoverEvents(True)
                self.scene.addItem(self._roi_graphics_item)

                print(f"ROI graphics item added to {self.orientation} view")

                # Force multiple immediate visual updates
                self.scene.update()
                self.update()
                self.viewport().update()

                # Additional forced update after a brief moment
                QTimer.singleShot(1, self._force_final_update)
                QTimer.singleShot(10, self._force_final_update)  # Extra update for reliability
            else:
                print(f"Clearing ROI in {self.orientation} view")

            self._external_roi_update = False
        except Exception as e:
            print(f"Failed to set external ROI in {self.orientation}: {str(e)}")
            self._external_roi_update = False

    def _force_final_update(self):
        """Force a final visual update"""
        try:
            # Force scene invalidation and redraw
            self.scene.invalidate()
            self.scene.update()
            self.update()
            self.viewport().update()
            self.repaint()  # Force immediate repaint

            # Debug: Check if ROI graphics item exists and is visible
            if self._roi_graphics_item:
                print(f"ROI graphics item exists in {self.orientation}, rect: {self._roi_graphics_item.rect()}")
                # Make sure it's visible
                self._roi_graphics_item.setVisible(True)
                self._roi_graphics_item.update()
        except Exception as e:
            print(f"Error in force final update: {e}")

    def clear_roi(self):
        """Clear ROI"""
        try:
            self._roi_rect = None
            if self._roi_graphics_item:
                try:
                    self.scene.removeItem(self._roi_graphics_item)
                except:
                    pass
                self._roi_graphics_item = None

            empty_rect = QRectF()
            self.roi_changed.emit(empty_rect, self.orientation)

            # Force visual update
            self.scene.update()
            self.update()
        except Exception as e:
            print(f"Failed to clear ROI: {str(e)}")

    def get_roi_rect(self):
        return self._roi_rect

    def center_image(self):
        try:
            scene_rect = self.scene.sceneRect()
            view_rect = self.viewport().rect()

            if scene_rect.width() < view_rect.width():
                x_offset = (view_rect.width() - scene_rect.width()) / 2
            else:
                x_offset = 0

            if scene_rect.height() < view_rect.height():
                y_offset = (view_rect.height() - scene_rect.height()) / 2
            else:
                y_offset = 0

            self.setSceneRect(scene_rect.adjusted(-x_offset, -y_offset, x_offset, y_offset))
        except Exception as e:
            print(f"Failed to center image: {str(e)}")

    def reset_zoom(self):
        try:
            self.resetTransform()
            self._zoom = 0
            self._initial_scale = 1
        except Exception as e:
            print(f"Failed to reset zoom: {str(e)}")

    def store_current_transform_and_scroll(self):
        try:
            self._stored_transform = self.transform()
            self._stored_scroll_pos = QPointF(
                self.horizontalScrollBar().value(),
                self.verticalScrollBar().value()
            )
        except Exception as e:
            print(f"Failed to store transform: {str(e)}")

    def apply_stored_transform_and_scroll(self):
        try:
            self.setTransform(self._stored_transform)
            self.horizontalScrollBar().setValue(int(self._stored_scroll_pos.x()))
            self.verticalScrollBar().setValue(int(self._stored_scroll_pos.y()))
        except Exception as e:
            print(f"Failed to apply transform: {str(e)}")

    def wheelEvent(self, event: QWheelEvent):
        try:
            zoom_in_factor = 1.06
            zoom_out_factor = 1 / zoom_in_factor

            if event.angleDelta().y() > 0:
                if self._zoom >= self._max_zoom:
                    return
                zoom_factor = zoom_in_factor
                self._zoom += 1
            else:
                zoom_factor = zoom_out_factor
                self._zoom -= 1

            current_scale = self.transform().m11()
            new_scale = current_scale * zoom_factor

            if new_scale < self._initial_scale:
                self.reset_zoom()
                return

            self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
            self.scale(zoom_factor, zoom_factor)
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.store_current_transform_and_scroll()
        except Exception as e:
            print(f"Failed to process wheel event: {str(e)}")

    def mousePressEvent(self, event: QMouseEvent):
        try:
            if event.button() == Qt.RightButton:
                self._is_drawing_roi = True
                self._roi_start_point = self.mapToScene(event.pos())

                if self._roi_current_rect is not None:
                    self.scene.removeItem(self._roi_current_rect)
                    self._roi_current_rect = None

            elif event.button() == Qt.LeftButton:
                item = self.itemAt(event.pos())
                if isinstance(item, DirectROI):
                    super().mousePressEvent(event)
                    return

                self._is_panning = True
                self._pan_start_x = event.x()
                self._pan_start_y = event.y()
                self.setCursor(Qt.ClosedHandCursor)

            super().mousePressEvent(event)
        except Exception as e:
            print(f"Failed to process mouse press: {str(e)}")

    def mouseMoveEvent(self, event: QMouseEvent):
        try:
            if self._is_drawing_roi:
                current_point = self.mapToScene(event.pos())

                if self._roi_current_rect is not None:
                    self.scene.removeItem(self._roi_current_rect)

                rect = QRectF(self._roi_start_point, current_point).normalized()
                pen = QPen(QColor(255, 0, 0), 2)
                brush = QBrush(QColor(255, 0, 0, 30))
                self._roi_current_rect = self.scene.addRect(rect, pen, brush)

            elif self._is_panning:
                delta_x = event.x() - self._pan_start_x
                delta_y = event.y() - self._pan_start_y
                self._pan_start_x = event.x()
                self._pan_start_y = event.y()

                self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta_x)
                self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta_y)
                self.store_current_transform_and_scroll()

            super().mouseMoveEvent(event)
        except Exception as e:
            print(f"Failed to process mouse move: {str(e)}")

    def mouseReleaseEvent(self, event: QMouseEvent):
        try:
            if event.button() == Qt.RightButton and self._is_drawing_roi:
                self._is_drawing_roi = False
                current_point = self.mapToScene(event.pos())
                final_rect = QRectF(self._roi_start_point, current_point).normalized()

                if final_rect.width() > 5 and final_rect.height() > 5:
                    self._roi_rect = final_rect

                    if self._roi_current_rect is not None:
                        self.scene.removeItem(self._roi_current_rect)
                        self._roi_current_rect = None

                    self._redraw_roi()
                    self.roi_changed.emit(self._roi_rect, self.orientation)
                else:
                    if self._roi_current_rect is not None:
                        self.scene.removeItem(self._roi_current_rect)
                        self._roi_current_rect = None

            elif event.button() == Qt.LeftButton:
                self._is_panning = False
                self.setCursor(Qt.ArrowCursor)

            super().mouseReleaseEvent(event)
        except Exception as e:
            print(f"Failed to process mouse release: {str(e)}")

    def add_roi_overlay(self, x0, y0, x1, y1):
        """Legacy method for compatibility"""
        pass