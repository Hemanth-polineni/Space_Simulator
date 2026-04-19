# visualization/animator.py
"""
Real-Time Split-View Animator
==============================
Left panel  → 3D orbital simulation (live, continuous)
Right panel → Telemetry dashboard (live orbital parameters)
Layout built with matplotlib GridSpec for precise column sizing.
"""

import itertools
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.animation as animation
from collections import deque
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from visualization.earth import draw_earth
from physics.propagator import propagate_all
from detection.collision import check_collisions
from telemetry.calculator import OrbitalCalculator

OBJECT_COLORS = ['cyan', 'lime', 'orange', 'magenta',
                 'yellow', 'white', 'coral', 'aquamarine']

# ─────────────────────────────────────────────────────────────────
# Axis setup helpers
# ─────────────────────────────────────────────────────────────────

def _setup_3d_axes(fig, subplot_spec):
    """Creates the 3D orbital view on the left panel."""
    ax = fig.add_subplot(subplot_spec, projection='3d')
    ax.set_facecolor('black')
    for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
        pane.fill = False
        pane.set_edgecolor('#222222')

    ax.tick_params(colors='#555555', labelsize=5)
    for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
        axis.label.set_color('#555555')
        axis.label.set_fontsize(6)

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.grid(True, color='gray', alpha=0.1)

    limit = 8.5e6
    ax.set_xlim([-limit, limit])
    ax.set_ylim([-limit, limit])
    ax.set_zlim([-limit, limit])
    ax.set_title('🛰️  Orbital Simulation  —  Real Time',
                 color='white', fontsize=12, pad=12)
    return ax


def _setup_telemetry_axes(fig, subplot_spec):
    """
    Creates the right-side telemetry panel.
    It's a plain 2D axes with all decorations turned off —
    we draw only text onto it, positioned manually.
    """
    ax = fig.add_subplot(subplot_spec)
    ax.set_facecolor('#0a0a0f')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')           # No ticks, no borders — clean canvas
    return ax


# ─────────────────────────────────────────────────────────────────
# Telemetry panel renderer
# ─────────────────────────────────────────────────────────────────

class TelemetryPanel:
    """
    Manages all text elements on the right-hand dashboard.

    Creates text objects once, then updates their content
    every frame — much faster than clearing and redrawing.
    
    Features:
    - Individual scrollable panels for each satellite
    - Click satellite name to toggle expand/collapse
    - Smooth animations for expansion/collapse
    - Visual scroll indicators
    """

    # Vertical spacing constants
    _HEADER_Y      = 0.97          # Header at top
    _FIRST_SECTION_Y = 0.87        # First satellite section starts here
    _SECTION_HEIGHT = 0.20         # Pixel height allocated per section
    _SECTION_SPACING = 0.23        # Space between section starts (includes gap)
    _LINE_H        = 0.028         # Height per data line
    _NAME_H        = 0.025         # Height of satellite name header
    _FOOTER_Y      = 0.06          # Footer at bottom

    def __init__(self, ax, objects: list):
        self.ax      = ax
        self.objects = objects
        self._texts  = {}   # key → matplotlib Text object
        self._patches = {} # key → matplotlib patches (for scroll bars, etc)
        
        # Per-object scroll state
        self._scroll_offsets = {}  # obj_idx → scroll offset
        self._max_scrolls = {}     # obj_idx → max scroll
        self._expanded = {}        # obj_idx → expanded state
        self._expand_progress = {} # obj_idx → animation progress (0.0-1.0)
        
        for idx in range(len(objects)):
            self._scroll_offsets[idx] = 0.0
            self._max_scrolls[idx] = 0.0
            self._expanded[idx] = True  # Start expanded
            self._expand_progress[idx] = 1.0

        self._build_static_labels()
        self._build_dynamic_labels()
        self._calculate_max_scrolls()

    # ── Construction ─────────────────────────────────────────────

    def _calculate_max_scrolls(self):
        """Calculate maximum scroll distance for each object."""
        n_rows = 8  # Altitude, Speed, Inclination, Periapsis, Apoapsis, Period, Eccentricity, Orbits
        # Content height: satellite name + separator + data rows
        content_height = self._NAME_H + 0.006 + (self._LINE_H * n_rows)
        # Visible height: the section height minus name header
        visible_height = self._SECTION_HEIGHT - self._NAME_H - 0.01
        
        for idx in range(len(self.objects)):
            self._max_scrolls[idx] = max(0, content_height - visible_height)

    def _get_section_bounds(self, obj_idx):
        """Get Y bounds for a specific object's section."""
        section_top = self._FIRST_SECTION_Y - (obj_idx * self._SECTION_SPACING)
        section_bottom = section_top - self._SECTION_HEIGHT
        return section_top, section_bottom

    def _adjust_y_for_object(self, y, obj_idx):
        """Apply scroll offset for specific object."""
        offset = self._scroll_offsets[obj_idx]
        collapse_factor = self._expand_progress[obj_idx]
        return y + offset * collapse_factor

    def _on_scroll(self, event):
        """Handle mouse wheel scroll events."""
        if event.inaxes != self.ax:
            return
        
        # Find which object section the mouse is over
        if event.ydata is None:
            return
        
        for idx in range(len(self.objects)):
            if not self._expanded[idx]:
                continue  # Only scroll expanded sections
                
            section_top, section_bottom = self._get_section_bounds(idx)
            if section_bottom <= event.ydata <= section_top:
                scroll_step = 0.015
                self._scroll_offsets[idx] += scroll_step if event.button == 'up' else -scroll_step
                self._scroll_offsets[idx] = max(-self._max_scrolls[idx], 
                                                 min(0, self._scroll_offsets[idx]))
                break

    def _on_click(self, event):
        """Handle mouse click events on satellite names."""
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        
        # Check if click is on a satellite name button
        for idx in range(len(self.objects)):
            key = f'id_{idx}'
            if key in self._texts:
                section_top, _ = self._get_section_bounds(idx)
                # Clickable area: satellite name row
                if abs(event.ydata - section_top) < 0.02 and 0.02 < event.xdata < 0.40:
                    self._toggle_expand(idx)

    def _toggle_expand(self, obj_idx):
        """Toggle expand/collapse state for an object."""
        self._expanded[obj_idx] = not self._expanded[obj_idx]

    def _t(self, key, x, y, text='', color='white', fontsize=9,
           ha='left', weight='normal', family='monospace'):
        """Helper: create one text element and register it."""
        obj = self.ax.text(
            x, y, text,
            color=color, fontsize=fontsize,
            ha=ha, va='top',
            fontweight=weight,
            fontfamily=family,
            transform=self.ax.transAxes
        )
        self._texts[key] = obj
        return obj

    def _build_static_labels(self):
        """Build static layout with individual sections per object."""
        # Global header
        self._t('header', 0.5, self._HEADER_Y,
                'TELEMETRY',
                color='#00ffff', fontsize=10,
                ha='center', weight='bold')

        self._t('div_top', 0.05, self._HEADER_Y - 0.02,
                '─' * 40,
                color='#333355', fontsize=7)

        # Build individual sections for each object
        labels = ['Altitude', 'Speed', 'Inclination',
                  'Periapsis', 'Apoapsis', 'Period', 'Eccentricity', 'Orbits']

        for idx, obj in enumerate(self.objects):
            section_top, section_bottom = self._get_section_bounds(idx)
            
            # Satellite name (clickable button)
            self._t(f'id_{idx}', 0.05, section_top,
                    f'▶  {obj.obj_id}',
                    color=obj.base_color, fontsize=8, weight='bold')
            
            # Section separator (right after name)
            sep_y = section_top - self._NAME_H - 0.003
            self._t(f'sep_{idx}', 0.05, sep_y,
                    '─' * 35,
                    color='#222244', fontsize=6)

            # Static labels for this section (data rows)
            for row, label in enumerate(labels):
                y = sep_y - 0.004 - (self._LINE_H * (row + 0.5))
                self._t(f'lbl_{idx}_{row}', 0.08, y,
                        f'{label:<12}',
                        color='#777788', fontsize=7)
        
        # Footer divider
        self._t('footer_div', 0.05, self._FOOTER_Y + 0.025,
                '─' * 40,
                color='#333355', fontsize=7)
    def _build_dynamic_labels(self):
        """Value placeholders — updated every frame."""
        n_rows = 8    # Must match labels list above
        for idx in range(len(self.objects)):
            section_top, _ = self._get_section_bounds(idx)
            sep_y = section_top - self._NAME_H - 0.003
            for row in range(n_rows):
                y = sep_y - 0.004 - (self._LINE_H * (row + 0.5))
                self._t(f'val_{idx}_{row}', 0.55, y,
                        '---', color='white', fontsize=7, ha='left')

        # Footer: simulation-wide stats
        self._t('footer_time',    0.05, self._FOOTER_Y,       '', color='white',   fontsize=8)
        self._t('footer_alerts',  0.05, self._FOOTER_Y - 0.025, '', color='#ff4444', fontsize=7)
        self._t('footer_frame',   0.05, self._FOOTER_Y - 0.048, '', color='#555566', fontsize=6)

    # ── Per-frame update ─────────────────────────────────────────

    def update(self, telemetry_data: dict, elapsed_s: int,
               frame: int, alert_count: int):
        """
        Refreshes all dynamic text values and positions.

        Called every animation frame. Updates content, animations, 
        and scroll positions.

        Parameters
        ----------
        telemetry_data : dict  — { obj_id: {param: value, ...}, ... }
        elapsed_s      : int   — simulated seconds elapsed
        frame          : int   — animation frame count
        alert_count    : int   — cumulative collision alerts
        """
        # Update expand/collapse animations (smooth easing)
        for idx in range(len(self.objects)):
            target = 1.0 if self._expanded[idx] else 0.0
            current = self._expand_progress[idx]
            # Smooth interpolation
            self._expand_progress[idx] += (target - current) * 0.15

        # Update telemetry values
        for idx, obj in enumerate(self.objects):
            data = telemetry_data.get(obj.obj_id, {})

            values = [
                f"{data.get('altitude_km',    0):>10.2f}  km",
                f"{data.get('speed_ms',       0):>10.1f}  m/s",
                f"{data.get('inclination_deg',0):>10.2f}  °",
                f"{data.get('periapsis_km',   0):>10.2f}  km",
                f"{data.get('apoapsis_km',    0):>10.2f}  km",
                f"{data.get('period_min',     0):>10.2f}  min",
                f"{data.get('eccentricity',   0):>10.6f}",
                f"{data.get('orbit_count',    0):>10d}",
            ]

            for row, val_str in enumerate(values):
                key = f'val_{idx}_{row}'
                color = obj.color if row == 0 else 'white'
                self._texts[key].set_text(val_str)
                self._texts[key].set_color(color)

        # Update footer
        h, rem = divmod(int(elapsed_s), 3600)
        m, s = divmod(rem, 60)
        self._texts['footer_time'].set_text(
            f'⏱  Mission Time:  {h:02d}h {m:02d}m {s:02d}s'
        )
        alert_color = '#ff4444' if alert_count > 0 else '#336633'
        alert_icon = '⚠️ ' if alert_count > 0 else '✅'
        self._texts['footer_alerts'].set_text(
            f'{alert_icon}  Alerts:  {alert_count}'
        )
        self._texts['footer_alerts'].set_color(alert_color)
        self._texts['footer_frame'].set_text(
            f'Frame: {frame:,}'
        )
        
        # Update all text positions based on expand/collapse and scroll
        self._update_all_positions()

    def _update_all_positions(self):
        """Update positions of all text elements with animations and scrolling."""
        labels = ['Altitude', 'Speed', 'Inclination',
                  'Periapsis', 'Apoapsis', 'Period', 'Eccentricity', 'Orbits']
        
        for idx in range(len(self.objects)):
            section_top, _ = self._get_section_bounds(idx)
            expand_factor = self._expand_progress[idx]
            
            # Update satellite name (with toggle indicator)
            arrow = '▼' if self._expanded[idx] else '▶'
            self._texts[f'id_{idx}'].set_text(f'{arrow}  {self.objects[idx].obj_id}')
            self._texts[f'id_{idx}'].set_y(section_top)
            
            # Separator position
            sep_y = section_top - self._NAME_H - 0.003
            self._texts[f'sep_{idx}'].set_y(sep_y)
            sep_alpha = expand_factor * 0.6 + 0.1
            self._texts[f'sep_{idx}'].set_alpha(sep_alpha)
            
            # Update data rows
            for row, label in enumerate(labels):
                base_y = sep_y - 0.004 - (self._LINE_H * (row + 0.5))
                
                # Apply scroll offset when expanded
                if self._expanded[idx]:
                    y = base_y - self._scroll_offsets[idx]
                else:
                    y = base_y
                
                label_key = f'lbl_{idx}_{row}'
                value_key = f'val_{idx}_{row}'
                
                self._texts[label_key].set_y(y)
                self._texts[value_key].set_y(y)
                
                # Fade in/out with expansion
                self._texts[label_key].set_alpha(expand_factor * 0.9)
                self._texts[value_key].set_alpha(expand_factor)
        
        # Draw scroll indicators
        self._draw_scroll_indicators()

    def _draw_scroll_indicators(self):
        """Update visual scroll indicators for each scrollable section."""
        for idx in range(len(self.objects)):
            if not self._expanded[idx]:
                continue
            
            scroll_offset = self._scroll_offsets[idx]
            max_scroll = self._max_scrolls[idx]
            
            # Only show indicator if there's content to scroll
            if max_scroll > 0:
                scroll_ratio = -scroll_offset / max_scroll  # 0 = top, 1 = bottom
                sep_key = f'sep_{idx}'
                if sep_key in self._texts:
                    # Blend separator color based on scroll position
                    color_intensity = max(0.3, 0.4 + (scroll_ratio * 0.3))
                    self._texts[sep_key].set_alpha(color_intensity)


# ─────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────

def run_simulation(objects: list, dt: int = 10, trail_length: int = 200):
    """
    Launches the split-view real-time simulation.

    Left  → 3D orbital view (continuous, no frame limit)
    Right → Live telemetry dashboard

    Parameters
    ----------
    objects      : list of SpaceObject
    dt           : int — physics seconds per animation frame
    trail_length : int — rolling trail buffer length
    """

    # ── Assign colors ─────────────────────────────────────────────
    for idx, obj in enumerate(objects):
        obj.base_color = OBJECT_COLORS[idx % len(OBJECT_COLORS)]
        obj.color      = obj.base_color

    # ── One OrbitalCalculator per object ──────────────────────────
    calculators = {obj.obj_id: OrbitalCalculator(obj.obj_id) for obj in objects}

    # ── Rolling trail buffers ─────────────────────────────────────
    trail_buffers = {
        obj.obj_id: deque([obj.position.copy()], maxlen=trail_length)
        for obj in objects
    }

    # ── Simulation-wide state ─────────────────────────────────────
    state = {"frame": 0, "elapsed_s": 0, "alerts": 0}

    # ── Figure layout using GridSpec ──────────────────────────────
    # GridSpec splits the figure into columns.
    # width_ratios=[2.2, 1] → 3D view gets ~69% of width, dashboard ~31%
    fig = plt.figure(figsize=(17, 9), facecolor='#05050f')
    gs  = gridspec.GridSpec(
        1, 2,
        figure=fig,
        width_ratios=[2.2, 1],
        wspace=0.04               # Tight gap between panels
    )

    ax_3d  = _setup_3d_axes(fig, gs[0])
    ax_hud = _setup_telemetry_axes(fig, gs[1])

    draw_earth(ax_3d)

    # ── Build telemetry panel (creates all text objects once) ──────
    panel = TelemetryPanel(ax_hud, objects)
    
    # ── Connect event handlers ────────────────────────────────────────
    fig.canvas.mpl_connect('scroll_event', panel._on_scroll)
    fig.canvas.mpl_connect('button_press_event', panel._on_click)

    # ── 3D plot elements ──────────────────────────────────────────
    scatter_plots, trail_lines, id_labels = [], [], []

    for obj in objects:
        sc = ax_3d.scatter([], [], [], s=55, color=obj.base_color,
                           depthshade=True, zorder=5)
        ln, = ax_3d.plot([], [], [], '-', lw=1.0, alpha=0.65,
                          color=obj.base_color)
        lbl = ax_3d.text(0, 0, 0, obj.obj_id, color=obj.base_color,
                          fontsize=8, fontweight='bold')
        scatter_plots.append(sc)
        trail_lines.append(ln)
        id_labels.append(lbl)

    # ── Per-frame update ──────────────────────────────────────────
    def update(_):
        # 1 — Reset collision colors
        for obj in objects:
            obj.reset_color()
        # 2 — Physics step
        propagate_all(objects, dt)
        # 3 — Collision detection
        events = check_collisions(objects)
        state["alerts"] += len(events)
        # 4 — Compute telemetry + update trail buffers
        telemetry_data = {}
        for obj in objects:
            trail_buffers[obj.obj_id].append(obj.position.copy())
            telemetry_data[obj.obj_id] = calculators[obj.obj_id].compute(
                obj.position, obj.velocity
            )

        # 5 — Redraw 3D objects
        for idx, obj in enumerate(objects):
            pos   = obj.position
            trail = np.array(trail_buffers[obj.obj_id])

            scatter_plots[idx]._offsets3d = ([pos[0]], [pos[1]], [pos[2]])
            scatter_plots[idx].set_color(obj.color)

            trail_lines[idx].set_data(trail[:, 0], trail[:, 1])
            trail_lines[idx].set_3d_properties(trail[:, 2])
            trail_lines[idx].set_color(obj.color)

            id_labels[idx].set_position((pos[0], pos[1]))
            id_labels[idx].set_3d_properties(pos[2], zdir='z')

        # 6 — Refresh telemetry dashboard
        state["elapsed_s"] += dt
        state["frame"]     += 1
        panel.update(telemetry_data, state["elapsed_s"],
                     state["frame"], state["alerts"])

        return scatter_plots + trail_lines + id_labels

    # ── Launch ────────────────────────────────────────────────────
    ani = animation.FuncAnimation(
        fig,
        update,
        frames=itertools.count(),
        interval=20,
        blit=False
    )

    plt.tight_layout(pad=0.5)
    plt.show()