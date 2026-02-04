# -*- coding: utf-8 -*-
"""
Lever Torque Physics Simulation
===============================
D1a & D3a: First segment is 1.5 ft long at 50° angle, so X1 ≈ 0.96 ft initially.
D1b & D3b: Same geometry but C (gold arm) is calculated so X1 = 1.5 ft initially.
D2: Horizontal arm is 1.5 ft, so X1 = 1.5 ft initially.

As the system rotates, X1 changes dynamically.
D3a/D3b has Y1 ≠ 0 (P2 elevated), so X1 changes differently as it tips!

Key insight: Torque = Force × Perpendicular distance from pivot to force's line of action.
F2 acts vertically, so its moment arm = horizontal distance X1.
"""

import pygame
import math
import sys

# ==============================================================================
# CONFIGURATION
# ==============================================================================

WINDOW_WIDTH = 2100
WINDOW_HEIGHT = 900
FPS = 60

# Colors
COLORS = {
    'bg': (15, 15, 22),
    'bg_panel': (25, 28, 35),
    'bg_panel_warn': (40, 25, 28),
    'grid': (50, 50, 65),
    'text': (240, 240, 245),
    'text_dim': (130, 135, 150),
    'f1_force': (255, 90, 90),
    'f2_force': (90, 255, 140),
    'moment_arm': (90, 175, 255),
    'y1_dim': (255, 180, 90),
    'left_arm': (160, 160, 175),
    'right_arm': (200, 165, 105),
    'pivot': (255, 195, 95),
    'weight': (130, 115, 95),
    'weight_outline': (190, 175, 145),
    'rope': (120, 115, 105),
    'balanced': (90, 255, 140),
    'unbalanced': (255, 90, 90),
    'button_start': (70, 180, 120),
    'button_reset': (180, 70, 70),
    'slider_bg': (40, 45, 55),
    'slider_fill': (80, 160, 120),
    'slider_knob': (220, 225, 235),
    'angle_indicator': (255, 100, 100),
}

# Panel group colors - shades of blue and green for matching F2 values
# Up to 6 distinct colors for different groups
PANEL_GROUP_COLORS = [
    (25, 45, 55),   # Teal/blue-green
    (35, 50, 40),   # Dark green
    (30, 35, 55),   # Deep blue
    (45, 40, 50),   # Purple-ish
    (40, 50, 45),   # Sage green
    (25, 40, 50),   # Ocean blue
]

# Tolerance for matching F2 values (within this many units = same group)
F2_MATCH_TOLERANCE = 5.0

# Physics parameters
C_DISTANCE = 3.0        # ft - horizontal distance from pivot to P1
FIRST_SEGMENT_LENGTH = 1.5  # ft - physical length of first segment (D1a/D3a bent arm)
X1_INITIAL_D2 = 1.5     # ft - initial horizontal distance to P2 for D2 (horizontal arm)
X1_INITIAL_B_VARIANTS = 1.5  # ft - initial X1 for D1b and D3b variants
WEIGHT = 300.0          # lb - weight hanging from P2
ARM_LENGTH = 3.0        # ft - physical arm length for D1 first segment and D3
SCALE = 50              # pixels per foot

# Simulation physics
MOMENT_OF_INERTIA = 35.0
ANGULAR_DAMPING = 0.25
MAX_ROTATION = 60

# ==============================================================================
# UI COMPONENTS
# ==============================================================================

class Button:
    def __init__(self, x, y, w, h, text, color, font):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.font = font
        self.hovered = False
    
    def draw(self, surface):
        c = tuple(min(255, x + 30) for x in self.color) if self.hovered else self.color
        pygame.draw.rect(surface, c, self.rect, border_radius=8)
        pygame.draw.rect(surface, COLORS['text_dim'], self.rect, 2, border_radius=8)
        txt = self.font.render(self.text, True, COLORS['text'])
        surface.blit(txt, txt.get_rect(center=self.rect.center))
    
    def update(self, pos):
        self.hovered = self.rect.collidepoint(pos)
    
    def clicked(self, pos, pressed):
        return self.rect.collidepoint(pos) and pressed


class Slider:
    """Horizontal slider for adjusting values."""
    
    def __init__(self, x, y, width, height, label, min_val, max_val, initial, font, unit="lb", decimals=0):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial
        self.font = font
        self.dragging = False
        self.knob_radius = height // 2 + 4
        self.unit = unit          # Unit label (lb, ft, etc.)
        self.decimals = decimals  # Number of decimal places to display
    
    def draw(self, surface):
        # Label above slider
        lbl = self.font.render(self.label, True, COLORS['text'])
        surface.blit(lbl, (self.rect.x, self.rect.y - 25))
        
        # Background track
        pygame.draw.rect(surface, COLORS['slider_bg'], self.rect, border_radius=self.rect.height // 2)
        
        # Filled portion
        fill_width = ((self.value - self.min_val) / (self.max_val - self.min_val)) * self.rect.width
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
        pygame.draw.rect(surface, COLORS['slider_fill'], fill_rect, border_radius=self.rect.height // 2)
        
        # Knob
        knob_x = self.rect.x + fill_width
        knob_y = self.rect.y + self.rect.height // 2
        pygame.draw.circle(surface, COLORS['slider_knob'], (int(knob_x), int(knob_y)), self.knob_radius)
        pygame.draw.circle(surface, COLORS['slider_fill'], (int(knob_x), int(knob_y)), self.knob_radius - 3)
        
        # Value label with configurable decimals and unit
        if self.decimals == 0:
            val_txt = self.font.render(f"{self.value:.0f} {self.unit}", True, COLORS['text'])
        elif self.decimals == 1:
            val_txt = self.font.render(f"{self.value:.1f} {self.unit}", True, COLORS['text'])
        else:
            val_txt = self.font.render(f"{self.value:.2f} {self.unit}", True, COLORS['text'])
        surface.blit(val_txt, (self.rect.right + 15, self.rect.y - 3))
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check if clicked on knob or track
            if self.rect.collidepoint(event.pos) or self._knob_hit(event.pos):
                self.dragging = True
                self._update_value(event.pos[0])
        
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_value(event.pos[0])
    
    def _knob_hit(self, pos):
        fill_width = ((self.value - self.min_val) / (self.max_val - self.min_val)) * self.rect.width
        knob_x = self.rect.x + fill_width
        knob_y = self.rect.y + self.rect.height // 2
        dist = math.sqrt((pos[0] - knob_x)**2 + (pos[1] - knob_y)**2)
        return dist <= self.knob_radius
    
    def _update_value(self, mouse_x):
        rel_x = mouse_x - self.rect.x
        rel_x = max(0, min(self.rect.width, rel_x))
        self.value = self.min_val + (rel_x / self.rect.width) * (self.max_val - self.min_val)
    
    def get_value(self):
        return self.value
    
    def reset(self, value):
        """Reset slider to a specific value."""
        self.value = max(self.min_val, min(self.max_val, value))

# ==============================================================================
# LEVER DIAGRAM
# ==============================================================================

class LeverDiagram:
    """
    Lever system with physics simulation.
    
    D1a & D3a: First segment is 1.5 ft at 50° angle -> X1 ≈ 0.96 ft
    D1b & D3b: C (gold arm) calculated so X1 = 1.5 ft initially
    D2: Horizontal arm is 1.5 ft -> X1 = 1.5 ft
    
    As they rotate, X1 changes. D3a/D3b has Y1 ≠ 0, so its X1 changes differently!
    
    Diagram Types:
      1 = D1a (L-shape, original arm2_length)
      2 = D2  (horizontal arm)
      3 = D3a (angled arm, no bend, original arm2_length)
      4 = D1b (L-shape, arm2 calculated for X1=1.5)
      5 = D3b (angled arm, no bend, arm2 calculated for X1=1.5)
    """
    
    def __init__(self, diagram_type, name):
        self.diagram_type = diagram_type
        self.name = name
        
        # Gray arm angle from horizontal (goes UP-LEFT)
        self.gray_angle = 40  # degrees
        
        # Arm lengths - can be adjusted via sliders
        # arm1_length: horizontal distance from pivot to P1 (grey arm projection)
        # arm2_length: gold arm length (first segment for D1, full arm for D2/D3)
        self.arm1_length = C_DISTANCE          # 3.0 ft default (horizontal projection)
        self.arm2_length = FIRST_SEGMENT_LENGTH  # 1.5 ft default (overridden for types 4,5)
        
        # Flag to indicate if this diagram uses X1-constrained arm2 calculation
        # Types 4 (D1b) and 5 (D3b) have arm2 calculated from X1 = 1.5 constraint
        self.x1_constrained = (diagram_type in [4, 5])
        
        # Gold arm configuration - types 4 and 5 mirror types 1 and 3
        if diagram_type in [1, 4]:
            # D1a and D1b: L-shaped arm
            self.gold_angle = 90 - self.gray_angle  # 50° from horizontal
            self.has_bend = True
        elif diagram_type == 2:
            # D2: horizontal arm
            self.gold_angle = 0
            self.has_bend = False
        else:
            # D3a and D3b: angled arm, no bend
            self.gold_angle = 90 - self.gray_angle
            self.has_bend = False
        
        # Physics state
        self.rotation = 0.0
        self.angular_velocity = 0.0
        
        # Forces
        self.f1 = 200.0
        self.f2_result = 0.0
        
        # X1 will be calculated based on arm2_length
        self.x1_initial = 0.0
        self.x1_current = 0.0
        self.net_torque = 0.0
        
        # Velocity tracking for P1 and P2
        # v = ω × r (angular velocity times distance from pivot)
        self.v1_magnitude = 0.0  # P1 velocity magnitude (ft/s)
        self.v1_x = 0.0          # P1 velocity X component
        self.v1_y = 0.0          # P1 velocity Y component
        self.v2_magnitude = 0.0  # P2 velocity magnitude (ft/s)
        self.v2_x = 0.0          # P2 velocity X component
        self.v2_y = 0.0          # P2 velocity Y component
        
        # Initial calculation of X1 (and arm2 for constrained types)
        self._recalculate_x1_initial()
    
    def _recalculate_x1_initial(self, x1_target=None):
        """
        Recalculate initial X1 based on current arm2_length.
        
        For D1b (type 4) and D3b (type 5), the arm2_length is CALCULATED
        from the x1_target value (which comes from the arm2 slider).
        
        Args:
            x1_target: For b-variants, this is the desired X1 value to achieve.
                       The arm2_length will be calculated to make X1 = x1_target.
        """
        # Gold arm base angle = 50° from horizontal
        gold_base_angle = (180 - self.gray_angle) - 90  # = 50°
        cos_gold = math.cos(math.radians(gold_base_angle))
        
        if self.diagram_type == 2:
            # D2: horizontal arm, X1 equals arm2 length directly
            self.x1_initial = self.arm2_length
            
        elif self.x1_constrained:
            # D1b (type 4) and D3b (type 5): X1 is set by x1_target
            # Calculate arm2_length to achieve this: arm2 = X1 / cos(50°)
            # x1_target comes from the arm2 slider value
            self.x1_initial = x1_target if x1_target is not None else X1_INITIAL_B_VARIANTS
            self.arm2_length = self.x1_initial / cos_gold
            
        else:
            # D1a (type 1) and D3a (type 3): arm at 50° from horizontal
            # X1 = horizontal projection of arm2_length
            self.x1_initial = self.arm2_length * cos_gold
        
        self.x1_current = self.x1_initial
    
    def set_arm_lengths(self, arm1_length, arm2_length):
        """
        Update arm lengths from slider values.
        
        For X1-constrained diagrams (D1b, D3b), the arm2 slider value is used
        as the X1 target, and arm2_length is calculated to achieve that X1.
        """
        self.arm1_length = arm1_length
        
        if self.x1_constrained:
            # For b-variants: arm2 slider value = desired X1 initial
            # arm2_length is calculated in _recalculate_x1_initial()
            self._recalculate_x1_initial(x1_target=arm2_length)
        else:
            # For a-variants and D2: arm2 slider directly sets arm2_length
            self.arm2_length = arm2_length
            self._recalculate_x1_initial()
    
    def set_f1(self, f1):
        self.f1 = f1
    
    def reset(self):
        """Reset physics state (rotation, velocity). Arm lengths are handled by sliders."""
        self.rotation = 0.0
        self.angular_velocity = 0.0
        # Reset x1_current to x1_initial (arm lengths already set via set_arm_lengths)
        self.x1_current = self.x1_initial
    
    def update(self, dt, simulating):
        """Update physics simulation."""
        rot = math.radians(self.rotation)
        
        # X1 = horizontal distance from pivot to P2
        # As system rotates, X1 changes based on the initial angle
        self.x1_current = self.x1_initial * math.cos(rot)
        self.x1_current = max(0.1, abs(self.x1_current))
        
        # F2 = force at P2 from lever mechanics: F2 = (F1 * C) / X1
        # Use arm1_length (horizontal distance to P1) instead of C_DISTANCE
        self.f2_result = (self.f1 * self.arm1_length) / self.x1_current
        
        if not simulating:
            self.net_torque = 0
            # Keep velocity values visible when paused (don't zero them out)
            # This lets the user see the last velocity state
            return
        
        # Physics simulation
        # C_current: horizontal distance from pivot to P1 (where F1 pushes down)
        # Uses arm1_length which represents the horizontal projection at rest
        c_current = self.arm1_length * math.cos(rot)
        c_current = max(0.1, abs(c_current))
        
        # Torques:
        # - F1 pushes DOWN on P1 (left side) -> tries to tip left (CCW rotation)
        # - 300lb weight pulls DOWN on P2 (right side) -> tries to tip right (CW rotation)
        # - We need F1 to counterbalance the weight
        
        torque_f1 = self.f1 * c_current  # CCW (positive) - lifts right side
        torque_weight = WEIGHT * self.x1_current  # CW (negative) - pulls right side down
        
        # Net torque: positive = CCW (left tips down), negative = CW (right tips down)
        self.net_torque = torque_f1 - torque_weight
        
        accel = self.net_torque / MOMENT_OF_INERTIA
        self.angular_velocity += accel * dt
        self.angular_velocity *= (1 - ANGULAR_DAMPING * dt)
        self.rotation += self.angular_velocity * dt
        self.rotation = max(-MAX_ROTATION, min(MAX_ROTATION, self.rotation))
        
        # Calculate velocities for P1 and P2
        # v = ω × r where ω is in rad/s and r is distance from pivot in ft
        omega = math.radians(self.angular_velocity)  # Convert deg/s to rad/s
        
        # P1 velocity: gray arm length from pivot
        gray_length = self.arm1_length / math.cos(math.radians(self.gray_angle))
        self.v1_magnitude = abs(omega * gray_length)
        
        # P1 velocity direction is perpendicular to gray arm
        gray_rad = math.radians(180 - self.gray_angle) + rot
        # Perpendicular direction (90° rotated, sign depends on angular velocity direction)
        if self.angular_velocity >= 0:
            perp_angle = gray_rad + math.pi / 2
        else:
            perp_angle = gray_rad - math.pi / 2
        self.v1_x = self.v1_magnitude * math.cos(perp_angle)
        self.v1_y = -self.v1_magnitude * math.sin(perp_angle)  # Flip for screen coords
        
        # P2 velocity: depends on diagram type
        # Types 4 and 5 behave like types 1 and 3 respectively
        effective_type = self.diagram_type
        if effective_type == 4:
            effective_type = 1  # D1b behaves like D1a
        elif effective_type == 5:
            effective_type = 3  # D3b behaves like D3a
        
        if effective_type == 1:
            # D1a/D1b: P2 is at the end of the L-shape, compute effective radius
            gold_base_angle = (180 - self.gray_angle) - 90
            rest_bend_x = self.arm2_length * math.cos(math.radians(gold_base_angle))
            rest_bend_y = self.arm2_length * math.sin(math.radians(gold_base_angle))
            # P2 is directly below bend at pivot Y level
            p2_radius = math.sqrt(rest_bend_x**2 + 0**2)  # rest_p2_y = 0 relative to pivot
            # Actually need full distance from pivot to P2
            p2_radius = math.sqrt(rest_bend_x**2 + rest_bend_y**2)
        else:
            # D2 and D3a/D3b: P2 is at end of arm2
            p2_radius = self.arm2_length
        
        self.v2_magnitude = abs(omega * p2_radius)
        
        # P2 velocity direction perpendicular to line from pivot to P2
        if effective_type == 2:
            gold_rad = rot  # Horizontal at rest
        else:
            gold_base_angle = (180 - self.gray_angle) - 90
            gold_rad = math.radians(gold_base_angle) + rot
        
        if self.angular_velocity >= 0:
            perp_angle = gold_rad + math.pi / 2
        else:
            perp_angle = gold_rad - math.pi / 2
        self.v2_x = self.v2_magnitude * math.cos(perp_angle)
        self.v2_y = -self.v2_magnitude * math.sin(perp_angle)

# ==============================================================================
# MAIN SIMULATION
# ==============================================================================

class Simulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Lever Physics Simulation")
        self.clock = pygame.time.Clock()
        
        # Fonts
        try:
            self.font_lg = pygame.font.SysFont('Segoe UI', 26, bold=True)
            self.font_md = pygame.font.SysFont('Segoe UI', 18)
            self.font_sm = pygame.font.SysFont('Segoe UI', 14)
            self.font_xs = pygame.font.SysFont('Segoe UI', 12)
        except:
            self.font_lg = pygame.font.Font(None, 30)
            self.font_md = pygame.font.Font(None, 22)
            self.font_sm = pygame.font.Font(None, 18)
            self.font_xs = pygame.font.Font(None, 14)
        
        self.running = True
        self.simulating = False
        
        # Create diagrams - 5 total:
        # D1a (type 1): Original L-shape
        # D1b (type 4): L-shape with X1 = 1.5 ft constraint
        # D2  (type 2): Horizontal arm
        # D3a (type 3): Original angled arm (no bend)
        # D3b (type 5): Angled arm with X1 = 1.5 ft constraint
        self.d1a = LeverDiagram(1, "Diagram 1a")
        self.d1b = LeverDiagram(4, "Diagram 1b")
        self.d2 = LeverDiagram(2, "Diagram 2")
        self.d3a = LeverDiagram(3, "Diagram 3a")
        self.d3b = LeverDiagram(5, "Diagram 3b")
        self.diagrams = [self.d1a, self.d1b, self.d2, self.d3a, self.d3b]
        
        # F1 Slider (center)
        self.f1_slider = Slider(
            WINDOW_WIDTH // 2 - 125, WINDOW_HEIGHT - 100, 200, 16,
            "F1 (applied at P1):", 10, 300, 200, self.font_md, "lb", 0
        )
        
        # Arm1 Length Slider (grey arm - left side)
        # This controls the horizontal distance C from pivot to P1
        self.arm1_slider = Slider(
            50, WINDOW_HEIGHT - 100, 180, 16,
            "Arm1 Length (Grey):", 1.0, 6.0, C_DISTANCE, self.font_md, "ft", 1
        )
        
        # Arm2 Length Slider (gold arm - right side)
        # For D1a, D2, D3a: controls gold arm length directly
        # For D1b, D3b: controls X1 initial (arm length is calculated)
        self.arm2_slider = Slider(
            WINDOW_WIDTH - 320, WINDOW_HEIGHT - 100, 180, 16,
            "Arm2/X1 (Gold):", 0.5, 4.0, FIRST_SEGMENT_LENGTH, self.font_md, "ft", 2
        )
        
        self._update_forces()
        self._update_arm_lengths()
        
        # Buttons
        cx = WINDOW_WIDTH // 2
        self.btn_start = Button(cx - 160, WINDOW_HEIGHT - 55, 140, 40,
                                "▶ START", COLORS['button_start'], self.font_md)
        self.btn_reset = Button(cx + 20, WINDOW_HEIGHT - 55, 140, 40,
                                "↺ RESET", COLORS['button_reset'], self.font_md)
    
    def _update_forces(self):
        """Update F1 force on all diagrams from slider value."""
        f1 = self.f1_slider.get_value()
        for d in self.diagrams:
            d.set_f1(f1)
    
    def _update_arm_lengths(self):
        """Update arm lengths on all diagrams from slider values."""
        arm1 = self.arm1_slider.get_value()
        arm2 = self.arm2_slider.get_value()
        for d in self.diagrams:
            d.set_arm_lengths(arm1, arm2)
    
    def _get_panel_colors_by_f2(self):
        """
        Assign panel colors based on F2 value grouping.
        Diagrams with F2 values within F2_MATCH_TOLERANCE get the same color.
        Returns a list of colors for each diagram panel.
        """
        # Get F2 values for all diagrams
        f2_values = [d.f2_result for d in self.diagrams]
        
        # Assign group IDs - diagrams with similar F2 get same group
        group_ids = [-1] * len(f2_values)
        current_group = 0
        
        for i in range(len(f2_values)):
            if group_ids[i] == -1:
                # Start a new group with this diagram
                group_ids[i] = current_group
                
                # Find all other diagrams that match this F2 value
                for j in range(i + 1, len(f2_values)):
                    if group_ids[j] == -1:
                        if abs(f2_values[i] - f2_values[j]) <= F2_MATCH_TOLERANCE:
                            group_ids[j] = current_group
                
                current_group += 1
        
        # Map group IDs to colors (cycle through available colors if needed)
        panel_colors = []
        for gid in group_ids:
            color_idx = gid % len(PANEL_GROUP_COLORS)
            panel_colors.append(PANEL_GROUP_COLORS[color_idx])
        
        return panel_colors
    
    def reset(self):
        """Reset simulation state and all slider values to defaults."""
        self.simulating = False
        
        # Reset all sliders to their default values
        self.f1_slider.reset(200.0)                  # Default F1
        self.arm1_slider.reset(C_DISTANCE)           # Default grey arm (3.0 ft)
        self.arm2_slider.reset(FIRST_SEGMENT_LENGTH) # Default gold arm (1.5 ft)
        
        # Update diagrams with reset slider values
        self._update_forces()
        self._update_arm_lengths()
        
        # Reset all diagram physics states
        for d in self.diagrams:
            d.reset()
    
    def draw_arrow(self, surf, start, end, color, width=4):
        pygame.draw.line(surf, color, start, end, width)
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.sqrt(dx*dx + dy*dy)
        if length < 1:
            return
        dx, dy = dx/length, dy/length
        px, py = -dy, dx
        hs = 12
        p1 = (end[0] - hs*dx + hs*0.4*px, end[1] - hs*dy + hs*0.4*py)
        p2 = (end[0] - hs*dx - hs*0.4*px, end[1] - hs*dy - hs*0.4*py)
        pygame.draw.polygon(surf, color, [end, p1, p2])
    
    def draw_rotated_text(self, surf, text, font, color, center_x, center_y, angle_deg, offset_perpendicular=0):
        """
        Draw text rotated to a specific angle, centered at a position.
        
        Args:
            surf: Surface to draw on
            text: Text string to render
            font: Font to use
            color: Text color
            center_x, center_y: Center position for the text
            angle_deg: Rotation angle in degrees (positive = CCW)
            offset_perpendicular: Offset perpendicular to the text direction (positive = left of direction)
        """
        # Render text to surface
        text_surf = font.render(text, True, color)
        
        # Rotate the text surface (pygame rotates CCW for positive angles)
        rotated_surf = pygame.transform.rotate(text_surf, angle_deg)
        
        # Calculate perpendicular offset if needed
        angle_rad = math.radians(angle_deg)
        perp_x = -math.sin(angle_rad) * offset_perpendicular
        perp_y = -math.cos(angle_rad) * offset_perpendicular
        
        # Get the rect and center it at the target position with offset
        rotated_rect = rotated_surf.get_rect()
        rotated_rect.center = (center_x + perp_x, center_y + perp_y)
        
        # Blit the rotated text
        surf.blit(rotated_surf, rotated_rect)
    
    def draw_90_angle(self, surf, pivot, arm1_end, arm2_end, color):
        """Draw 90° indicator between two arms."""
        dx1 = arm1_end[0] - pivot[0]
        dy1 = arm1_end[1] - pivot[1]
        len1 = math.sqrt(dx1*dx1 + dy1*dy1)
        if len1 > 0:
            dx1, dy1 = dx1/len1, dy1/len1
        
        dx2 = arm2_end[0] - pivot[0]
        dy2 = arm2_end[1] - pivot[1]
        len2 = math.sqrt(dx2*dx2 + dy2*dy2)
        if len2 > 0:
            dx2, dy2 = dx2/len2, dy2/len2
        
        size = 20
        corner1 = (pivot[0] + dx1 * size, pivot[1] + dy1 * size)
        corner2 = (pivot[0] + dx2 * size, pivot[1] + dy2 * size)
        corner_mid = (pivot[0] + (dx1 + dx2) * size, pivot[1] + (dy1 + dy2) * size)
        
        pygame.draw.line(surf, color, corner1, corner_mid, 3)
        pygame.draw.line(surf, color, corner2, corner_mid, 3)
    
    def draw_diagram(self, surf, diag, cx, cy):
        """Draw lever diagram with F2 value shown next to arrow."""
        rot = diag.rotation
        rot_rad = math.radians(rot)
        
        pivot_x, pivot_y = cx, cy
        
        # Horizontal reference line (Y=0)
        line_y = pivot_y
        pygame.draw.line(surf, COLORS['grid'],
                        (cx - 190, line_y), (cx + 170, line_y), 2)
        
        # ============================================================
        # GRAY ARM - uses arm1_length (horizontal projection)
        # ============================================================
        gray_rad = math.radians(180 - diag.gray_angle) + rot_rad
        # Calculate actual arm length from horizontal projection (arm1_length = C)
        gray_length = diag.arm1_length / math.cos(math.radians(diag.gray_angle))
        
        p1_x = pivot_x + gray_length * SCALE * math.cos(gray_rad)
        p1_y = pivot_y - gray_length * SCALE * math.sin(gray_rad)
        
        pygame.draw.line(surf, COLORS['left_arm'],
                        (pivot_x, pivot_y), (p1_x, p1_y), 8)
        
        # C label - rotated along the arm, centered on it
        c_mid_x = (pivot_x + p1_x) / 2
        c_mid_y = (pivot_y + p1_y) / 2
        # Gray arm angle for text rotation (convert from radians, adjust for pygame's CCW rotation)
        gray_text_angle = math.degrees(gray_rad)
        # Offset perpendicular to arm (positive = above arm in screen coords)
        self.draw_rotated_text(surf, f"C={diag.arm1_length:.1f}ft", self.font_sm, 
                               COLORS['left_arm'], c_mid_x, c_mid_y, gray_text_angle, offset_perpendicular=15)
        
        # P1 marker
        pygame.draw.circle(surf, COLORS['f1_force'], (int(p1_x), int(p1_y)), 6)
        p1_lbl = self.font_xs.render("P1", True, COLORS['f1_force'])
        surf.blit(p1_lbl, (p1_x - 20, p1_y - 25))
        
        # F1 ARROW with value and velocity
        self.draw_arrow(surf, (p1_x, p1_y - 10), (p1_x, p1_y + 50), COLORS['f1_force'])
        f1_lbl = self.font_md.render(f"F1={diag.f1:.0f}", True, COLORS['f1_force'])
        surf.blit(f1_lbl, (p1_x - 35, p1_y + 55))
        # Show P1 velocity magnitude
        v1_lbl = self.font_xs.render(f"|V1|={diag.v1_magnitude:.2f} ft/s", True, COLORS['f1_force'])
        surf.blit(v1_lbl, (p1_x - 45, p1_y + 75))
        
        # ============================================================
        # GOLD ARM - RIGIDLY LOCKED TO GRAY ARM
        # The entire assembly rotates as ONE piece around the pivot
        # ============================================================
        
        # Gray arm angle (in world coords): starts at 180 - gray_angle degrees
        # Gold arm is at a FIXED angle relative to gray arm
        
        # Map types 4 and 5 to their visual equivalents (1 and 3)
        visual_type = diag.diagram_type
        if visual_type == 4:
            visual_type = 1  # D1b looks like D1a
        elif visual_type == 5:
            visual_type = 3  # D3b looks like D3a
        
        if visual_type == 1:
            # D1a/D1b: L-shaped arm, all one rigid piece
            # First segment: 90° to gray arm, uses arm2_length
            # Second segment: STRAIGHT DOWN (vertical at rest)
            # P2 ends at Y = 0 (pivot level)
            
            # First segment uses arm2_length (slider-controlled for D1a, calculated for D1b)
            gold_base_angle = (180 - diag.gray_angle) - 90  # = 50° from horizontal
            
            # At rest positions (before rotation)
            rest_bend_x = pivot_x + diag.arm2_length * SCALE * math.cos(math.radians(gold_base_angle))
            rest_bend_y = pivot_y - diag.arm2_length * SCALE * math.sin(math.radians(gold_base_angle))
            rest_p2_x = rest_bend_x  # P2 is directly below bend
            rest_p2_y = pivot_y      # P2 at Y=0 (pivot level)
            
            # Rotate both points around pivot as one rigid body
            def rotate_pt(px, py, cx, cy, angle):
                dx, dy = px - cx, py - cy
                c, s = math.cos(angle), math.sin(angle)
                return cx + dx*c + dy*s, cy - dx*s + dy*c
            
            bend_x, bend_y = rotate_pt(rest_bend_x, rest_bend_y, pivot_x, pivot_y, rot_rad)
            p2_x, p2_y = rotate_pt(rest_p2_x, rest_p2_y, pivot_x, pivot_y, rot_rad)
            
            pygame.draw.line(surf, COLORS['right_arm'],
                           (pivot_x, pivot_y), (bend_x, bend_y), 8)
            pygame.draw.line(surf, COLORS['right_arm'],
                           (bend_x, bend_y), (p2_x, p2_y), 8)
            pygame.draw.circle(surf, COLORS['right_arm'], (int(bend_x), int(bend_y)), 6)
            
            # 90° angle label at center of angle (between gray and gold arms)
            # Bisector direction between gray arm and gold arm
            gray_dir_x = (p1_x - pivot_x)
            gray_dir_y = (p1_y - pivot_y)
            gold_dir_x = (bend_x - pivot_x)
            gold_dir_y = (bend_y - pivot_y)
            # Normalize and average
            gray_len = math.sqrt(gray_dir_x**2 + gray_dir_y**2)
            gold_len = math.sqrt(gold_dir_x**2 + gold_dir_y**2)
            bisect_x = (gray_dir_x/gray_len + gold_dir_x/gold_len) / 2
            bisect_y = (gray_dir_y/gray_len + gold_dir_y/gold_len) / 2
            ninety_lbl = self.font_sm.render("90°", True, COLORS['angle_indicator'])
            surf.blit(ninety_lbl, (pivot_x + bisect_x * 45 - 12, pivot_y + bisect_y * 45 - 8))
            
        elif visual_type == 2:
            # D2: Straight horizontal arm at rest, rigidly attached
            # At rest, gold arm points to the right (0°)
            # Angle between grey (150°) and gold (0°) = 150° - LOCKED
            gold_base_angle = 0  # horizontal at rest
            gold_rad = math.radians(gold_base_angle) + rot_rad
            
            # P2 position - horizontal arm uses arm2_length (adjustable)
            p2_x = pivot_x + diag.arm2_length * SCALE * math.cos(gold_rad)
            p2_y = pivot_y - diag.arm2_length * SCALE * math.sin(gold_rad)
            
            pygame.draw.line(surf, COLORS['right_arm'],
                           (pivot_x, pivot_y), (p2_x, p2_y), 8)
            
            # 150° angle label at center of angle (between gray and gold arms)
            gray_dir_x = (p1_x - pivot_x)
            gray_dir_y = (p1_y - pivot_y)
            gold_dir_x = (p2_x - pivot_x)
            gold_dir_y = (p2_y - pivot_y)
            gray_len = math.sqrt(gray_dir_x**2 + gray_dir_y**2)
            gold_len = math.sqrt(gold_dir_x**2 + gold_dir_y**2)
            bisect_x = (gray_dir_x/gray_len + gold_dir_x/gold_len) / 2
            bisect_y = (gray_dir_y/gray_len + gold_dir_y/gold_len) / 2
            angle_lbl = self.font_sm.render("150°", True, COLORS['angle_indicator'])
            surf.blit(angle_lbl, (pivot_x + bisect_x * 50 - 15, pivot_y + bisect_y * 50 - 8))
            
        else:
            # D3a/D3b: Same as D1's first segment (90° to gray), but NO drop
            # P2 stays elevated, arm uses arm2_length (slider for D3a, calculated for D3b)
            gold_base_angle = (180 - diag.gray_angle) - 90  # = 50° from horizontal
            gold_rad = math.radians(gold_base_angle) + rot_rad
            
            # P2 position - arm uses arm2_length
            arm_len = diag.arm2_length * SCALE
            p2_x = pivot_x + arm_len * math.cos(gold_rad)
            p2_y = pivot_y - arm_len * math.sin(gold_rad)
            
            pygame.draw.line(surf, COLORS['right_arm'],
                           (pivot_x, pivot_y), (p2_x, p2_y), 8)
            
            # 90° angle label at center of angle (between gray and gold arms)
            gray_dir_x = (p1_x - pivot_x)
            gray_dir_y = (p1_y - pivot_y)
            gold_dir_x = (p2_x - pivot_x)
            gold_dir_y = (p2_y - pivot_y)
            gray_len = math.sqrt(gray_dir_x**2 + gray_dir_y**2)
            gold_len = math.sqrt(gold_dir_x**2 + gold_dir_y**2)
            bisect_x = (gray_dir_x/gray_len + gold_dir_x/gold_len) / 2
            bisect_y = (gray_dir_y/gray_len + gold_dir_y/gold_len) / 2
            ninety_lbl = self.font_sm.render("90°", True, COLORS['angle_indicator'])
            surf.blit(ninety_lbl, (pivot_x + bisect_x * 45 - 12, pivot_y + bisect_y * 45 - 8))
        
        # Arm length label - rotated along the gold arm, centered on it
        # For visual_type 1 (L-shape), label goes on first segment (pivot to bend)
        # For visual_type 2 and 3, label goes on the arm (pivot to p2)
        if visual_type == 1:
            # L-shape: label on first segment (pivot to bend)
            gold_mid_x = (pivot_x + bend_x) / 2
            gold_mid_y = (pivot_y + bend_y) / 2
            # Calculate angle from pivot to bend
            gold_text_angle = math.degrees(math.atan2(pivot_y - bend_y, bend_x - pivot_x))
        else:
            # D2 and D3: label on arm (pivot to p2)
            gold_mid_x = (pivot_x + p2_x) / 2
            gold_mid_y = (pivot_y + p2_y) / 2
            # Calculate angle from pivot to p2
            gold_text_angle = math.degrees(math.atan2(pivot_y - p2_y, p2_x - pivot_x))
        
        # Format label text based on whether arm2 is calculated or set
        if diag.x1_constrained:
            arm_label_text = f"C={diag.arm2_length:.2f}ft"
        else:
            arm_label_text = f"{diag.arm2_length:.1f}ft"
        
        # Draw rotated text, offset perpendicular to avoid overlapping the arm
        self.draw_rotated_text(surf, arm_label_text, self.font_sm, COLORS['right_arm'],
                               gold_mid_x, gold_mid_y, gold_text_angle, offset_perpendicular=-15)
        
        # ============================================================
        # P2, F2, Weight
        # ============================================================
        
        pygame.draw.circle(surf, COLORS['f2_force'], (int(p2_x), int(p2_y)), 6)
        p2_lbl = self.font_xs.render("P2", True, COLORS['f2_force'])
        surf.blit(p2_lbl, (p2_x + 10, p2_y - 20))
        
        # F2 ARROW with VALUE shown next to it!
        f2_len = 50 + min(diag.f2_result / 5, 30)
        self.draw_arrow(surf, (p2_x, p2_y + 5), (p2_x, p2_y - f2_len), COLORS['f2_force'])
        
        # F2 value label RIGHT NEXT TO the arrow
        f2_val_lbl = self.font_md.render(f"F2={diag.f2_result:.0f}", True, COLORS['f2_force'])
        surf.blit(f2_val_lbl, (p2_x + 15, p2_y - f2_len + 10))
        # Show P2 velocity magnitude
        v2_lbl = self.font_xs.render(f"|V2|={diag.v2_magnitude:.2f} ft/s", True, COLORS['f2_force'])
        surf.blit(v2_lbl, (p2_x + 15, p2_y - f2_len + 30))
        
        # Weight (longer rope to reduce clutter)
        rope_len = 128
        wt_top = p2_y + rope_len
        pygame.draw.line(surf, COLORS['rope'], (p2_x, p2_y), (p2_x, wt_top), 2)
        
        wt, wb, wh = 32, 45, 30
        pts = [(p2_x - wt/2, wt_top), (p2_x + wt/2, wt_top),
               (p2_x + wb/2, wt_top + wh), (p2_x - wb/2, wt_top + wh)]
        pygame.draw.polygon(surf, COLORS['weight'], pts)
        pygame.draw.polygon(surf, COLORS['weight_outline'], pts, 2)
        pygame.draw.circle(surf, COLORS['weight_outline'], (int(p2_x), int(wt_top)), 4, 2)
        
        wt_lbl = self.font_xs.render("300 lb", True, COLORS['text'])
        surf.blit(wt_lbl, (p2_x - 20, wt_top + wh/2 - 6))
        
        # ============================================================
        # X1 dimension
        # ============================================================
        dim_y = line_y + 20
        x1_pixels = diag.x1_current * SCALE
        
        pygame.draw.line(surf, COLORS['moment_arm'],
                        (pivot_x, dim_y), (pivot_x + x1_pixels, dim_y), 2)
        pygame.draw.line(surf, COLORS['moment_arm'],
                        (pivot_x, dim_y - 5), (pivot_x, dim_y + 5), 2)
        pygame.draw.line(surf, COLORS['moment_arm'],
                        (pivot_x + x1_pixels, dim_y - 5), (pivot_x + x1_pixels, dim_y + 5), 2)
        
        x1_lbl = self.font_sm.render(f"X1 = {diag.x1_current:.2f} ft", True, COLORS['moment_arm'])
        surf.blit(x1_lbl, (pivot_x + x1_pixels/2 - 35, dim_y + 8))
        
        # Y1 indicator for D3a/D3b (visual_type 3)
        if visual_type == 3:
            y1_val = abs(p2_y - pivot_y) / SCALE
            if y1_val > 0.1:
                pygame.draw.line(surf, COLORS['y1_dim'],
                               (p2_x + 30, pivot_y), (p2_x + 30, p2_y), 2)
                pygame.draw.line(surf, COLORS['y1_dim'],
                               (p2_x + 25, pivot_y), (p2_x + 35, pivot_y), 2)
                pygame.draw.line(surf, COLORS['y1_dim'],
                               (p2_x + 25, p2_y), (p2_x + 35, p2_y), 2)
                y1_lbl = self.font_xs.render(f"Y1 = {y1_val:.1f} ft", True, COLORS['y1_dim'])
                surf.blit(y1_lbl, (p2_x + 40, (pivot_y + p2_y)/2 - 8))
        else:
            y1_lbl = self.font_xs.render("Y1 = 0", True, COLORS['text_dim'])
            surf.blit(y1_lbl, (p2_x + 20, pivot_y + 5))
        
        # ============================================================
        # Pivot
        # ============================================================
        pygame.draw.circle(surf, COLORS['pivot'], (int(pivot_x), int(pivot_y)), 12)
        pygame.draw.circle(surf, COLORS['bg'], (int(pivot_x), int(pivot_y)), 5)
        piv_lbl = self.font_xs.render("Pivot", True, COLORS['pivot'])
        surf.blit(piv_lbl, (pivot_x - 35, pivot_y + 18))
        
        # Title
        title = self.font_lg.render(diag.name, True, COLORS['text'])
        surf.blit(title, (cx - title.get_width()//2, cy - 240))
        
        # Subtitle explaining the variant - positioned closer to title
        if diag.x1_constrained:
            subtitle = self.font_xs.render(f"X1={diag.x1_initial:.2f} ft (C calc'd)", True, COLORS['moment_arm'])
        else:
            subtitle = self.font_xs.render(f"X1={diag.x1_initial:.2f} ft", True, COLORS['text_dim'])
        surf.blit(subtitle, (cx - subtitle.get_width()//2, cy - 220))
        
        # ============================================================
        # Velocity Component Table - below diagram
        # ============================================================
        table_y = cy + 250  # Position below the diagram
        table_x = cx - 90   # Center the table
        
        # Angular velocity display (ω)
        omega_lbl = self.font_sm.render(f"ω = {diag.angular_velocity:.2f} °/s", True, COLORS['pivot'])
        surf.blit(omega_lbl, (table_x + 35, table_y - 38))
        
        # Table header
        hdr = self.font_sm.render("Velocity Components", True, COLORS['text'])
        surf.blit(hdr, (table_x + 10, table_y - 20))
        
        # Draw table background
        table_rect = pygame.Rect(table_x, table_y, 180, 55)
        pygame.draw.rect(surf, COLORS['slider_bg'], table_rect, border_radius=4)
        pygame.draw.rect(surf, COLORS['text_dim'], table_rect, 1, border_radius=4)
        
        # Column headers
        col_x = self.font_xs.render("Vx", True, COLORS['text_dim'])
        col_y = self.font_xs.render("Vy", True, COLORS['text_dim'])
        surf.blit(col_x, (table_x + 70, table_y + 3))
        surf.blit(col_y, (table_x + 130, table_y + 3))
        
        # Horizontal separator line
        pygame.draw.line(surf, COLORS['text_dim'], 
                        (table_x + 5, table_y + 18), (table_x + 175, table_y + 18), 1)
        
        # V1 row (P1 velocity)
        v1_row = self.font_xs.render("V1:", True, COLORS['f1_force'])
        v1_x_val = self.font_xs.render(f"{diag.v1_x:+.2f}", True, COLORS['f1_force'])
        v1_y_val = self.font_xs.render(f"{diag.v1_y:+.2f}", True, COLORS['f1_force'])
        surf.blit(v1_row, (table_x + 8, table_y + 22))
        surf.blit(v1_x_val, (table_x + 55, table_y + 22))
        surf.blit(v1_y_val, (table_x + 115, table_y + 22))
        
        # V2 row (P2 velocity)
        v2_row = self.font_xs.render("V2:", True, COLORS['f2_force'])
        v2_x_val = self.font_xs.render(f"{diag.v2_x:+.2f}", True, COLORS['f2_force'])
        v2_y_val = self.font_xs.render(f"{diag.v2_y:+.2f}", True, COLORS['f2_force'])
        surf.blit(v2_row, (table_x + 8, table_y + 38))
        surf.blit(v2_x_val, (table_x + 55, table_y + 38))
        surf.blit(v2_y_val, (table_x + 115, table_y + 38))
    
    def draw_header(self):
        t = self.font_lg.render("Lever Physics: F2 = F1 × C / X1", True, COLORS['text'])
        self.screen.blit(t, (WINDOW_WIDTH//2 - t.get_width()//2, 10))
        
        s = self.font_sm.render(
            "D1a/D3a: Standard arm length | D1b/D3b: Arm calculated so X1 = 1.5 ft | D3a/D3b: Y1 ≠ 0 (elevated P2)",
            True, COLORS['text_dim'])
        self.screen.blit(s, (WINDOW_WIDTH//2 - s.get_width()//2, 42))
        
        if self.simulating:
            st = "⚡ SIMULATING"
            c = COLORS['balanced']
        else:
            st = "Press START to simulate"
            c = COLORS['text_dim']
        st_surf = self.font_md.render(st, True, c)
        self.screen.blit(st_surf, (WINDOW_WIDTH//2 - st_surf.get_width()//2, 65))
    
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            mpos = pygame.mouse.get_pos()
            clicked = False
            
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        self.running = False
                    elif e.key == pygame.K_SPACE:
                        self.simulating = not self.simulating
                    elif e.key == pygame.K_r:
                        self.reset()
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    clicked = True
                
                # Handle all slider events
                self.f1_slider.handle_event(e)
                self.arm1_slider.handle_event(e)
                self.arm2_slider.handle_event(e)
            
            # Update forces and arm lengths from slider values
            self._update_forces()
            self._update_arm_lengths()
            
            self.btn_start.update(mpos)
            self.btn_reset.update(mpos)
            
            # Toggle simulation on/off with start button
            if self.btn_start.clicked(mpos, clicked):
                self.simulating = not self.simulating
            if self.btn_reset.clicked(mpos, clicked):
                self.reset()
            
            # Update start button text and color based on simulation state
            if self.simulating:
                self.btn_start.text = "⏸ STOP"
                self.btn_start.color = COLORS['button_reset']
            else:
                self.btn_start.text = "▶ START"
                self.btn_start.color = COLORS['button_start']
            
            # Update ALL diagrams
            for d in self.diagrams:
                d.update(dt, self.simulating)
            
            # Draw
            self.screen.fill(COLORS['bg'])
            
            # Layout for 5 diagrams in a row
            pw = WINDOW_WIDTH // 5 - 12
            ph = WINDOW_HEIGHT - 200
            
            # Group diagrams by F2 value (within tolerance = same color)
            # Assign colors dynamically based on F2 matching
            panel_colors = self._get_panel_colors_by_f2()
            
            # Draw panels with group-based colors
            for i in range(5):
                px = 10 + i * (pw + 10)
                pygame.draw.rect(self.screen, panel_colors[i], (px, 90, pw, ph), border_radius=10)
            
            # Calculate center X positions for each diagram
            centers = [
                WINDOW_WIDTH // 10 + 5,          # D1a center
                3 * WINDOW_WIDTH // 10 + 5,      # D1b center
                WINDOW_WIDTH // 2,                # D2 center
                7 * WINDOW_WIDTH // 10 - 5,      # D3a center
                9 * WINDOW_WIDTH // 10 - 5,      # D3b center
            ]
            for d, cx in zip(self.diagrams, centers):
                self.draw_diagram(self.screen, d, cx, 350)
            
            self.draw_header()
            
            # Draw all sliders
            self.f1_slider.draw(self.screen)
            self.arm1_slider.draw(self.screen)
            self.arm2_slider.draw(self.screen)
            
            self.btn_start.draw(self.screen)
            self.btn_reset.draw(self.screen)
            
            inst = self.font_xs.render(
                "[SPACE] Toggle • [R] Reset • [ESC] Quit • Drag sliders to adjust F1 and arm lengths",
                True, COLORS['text_dim'])
            self.screen.blit(inst, (WINDOW_WIDTH//2 - inst.get_width()//2, WINDOW_HEIGHT - 15))
            
            pygame.display.flip()
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    print("=" * 70)
    print("  Lever Physics Simulation")
    print("=" * 70)
    print()
    print("  5 Diagrams:")
    print("    D1a: L-shape arm, arm2 length from slider")
    print("    D1b: L-shape arm, X1 from slider (arm2 is calculated)")
    print("    D2:  Horizontal arm")
    print("    D3a: Angled arm (no drop), arm2 length from slider")
    print("    D3b: Angled arm (no drop), X1 from slider (arm2 is calculated)")
    print()
    print("  Drag sliders to adjust:")
    print("    - F1: Applied force at P1")
    print("    - Arm1 Length (Grey): Horizontal distance from pivot to P1")
    print("    - Arm2/X1 (Gold): For D1a/D2/D3a sets arm length directly")
    print("                      For D1b/D3b sets X1 initial (arm is calculated)")
    print()
    print("  Press START to simulate all five diagrams.")
    print()
    
    Simulation().run()
