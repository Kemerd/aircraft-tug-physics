# -*- coding: utf-8 -*-
"""
Aircraft Tug Force Calculator
=============================
Calculates the handle force required to move an aircraft using a lever-based tug.

Layout:
- LEFT: Controls (weight, surface, incline, arm lengths)
- CENTER: 6 lever diagrams (click to select)
- RIGHT: Detailed results for selected diagram

Physics:
- Rolling resistance: F_roll = μ × W × cos(θ)
- Grade resistance: F_grade = W × sin(θ)
- Handle force: F_handle = F_pull × C / X
"""

import pygame
import math
import sys

# ==============================================================================
# CONFIGURATION
# ==============================================================================

WINDOW_WIDTH = 1700
WINDOW_HEIGHT = 900
FPS = 60

# Colors
COLORS = {
    'bg': (15, 15, 22),
    'bg_panel': (25, 28, 35),
    'bg_selected': (40, 55, 70),
    'grid': (50, 50, 65),
    'text': (240, 240, 245),
    'text_dim': (130, 135, 150),
    'text_highlight': (255, 220, 100),
    'f_handle': (255, 90, 90),
    'f_pull': (90, 255, 140),
    'f_ground': (255, 180, 90),
    'moment_arm': (90, 175, 255),
    'left_arm': (160, 160, 175),
    'right_arm': (200, 165, 105),
    'pivot': (255, 195, 95),
    'tire': (60, 60, 70),
    'tire_rim': (120, 120, 130),
    'aircraft': (100, 150, 200),
    'button_active': (70, 180, 120),
    'button_inactive': (50, 55, 65),
    'button_hover': (80, 90, 100),
    'slider_bg': (40, 45, 55),
    'slider_fill': (80, 160, 120),
    'slider_knob': (220, 225, 235),
    'angle_indicator': (255, 100, 100),
    'motor_specs': (180, 140, 255),
    'warning': (255, 100, 100),
    'good': (100, 255, 140),
    'selection_border': (100, 200, 255),
}

# Friction coefficients
FRICTION_PRESETS = {
    'Clean Concrete': 0.015,
    'Asphalt': 0.020,
    'Gravel': 0.035,
    'Dirt Road': 0.045,
    'Grass': 0.070,
}

# Physical defaults
DEFAULT_AIRCRAFT_WEIGHT = 3000.0
DEFAULT_INCLINE = 0.0
TIRE_DIAMETER_IN = 10.0
TIRE_RADIUS_FT = (TIRE_DIAMETER_IN / 2) / 12
DEFAULT_HANDLE_LENGTH = 3.0
DEFAULT_AIRCRAFT_ARM = 1.5
GRAY_ARM_ANGLE = 40
TARGET_SPEED_MPH = 3.0
TARGET_SPEED_FPS = TARGET_SPEED_MPH * 5280 / 3600
SCALE = 38

# Layout constants
LEFT_PANEL_WIDTH = 200
RIGHT_PANEL_WIDTH = 280
CENTER_START = LEFT_PANEL_WIDTH + 20
CENTER_WIDTH = WINDOW_WIDTH - LEFT_PANEL_WIDTH - RIGHT_PANEL_WIDTH - 40

# ==============================================================================
# UI COMPONENTS
# ==============================================================================

class Button:
    def __init__(self, x, y, w, h, text, font, active=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.active = active
        self.hovered = False
    
    def draw(self, surface):
        if self.active:
            color = COLORS['button_active']
        elif self.hovered:
            color = COLORS['button_hover']
        else:
            color = COLORS['button_inactive']
        
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        pygame.draw.rect(surface, COLORS['text_dim'], self.rect, 2, border_radius=6)
        txt = self.font.render(self.text, True, COLORS['text'])
        surface.blit(txt, txt.get_rect(center=self.rect.center))
    
    def update(self, pos):
        self.hovered = self.rect.collidepoint(pos)
    
    def clicked(self, pos, pressed):
        return self.rect.collidepoint(pos) and pressed


class Slider:
    def __init__(self, x, y, width, height, label, min_val, max_val, initial, font, 
                 unit="", decimals=1, color=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial
        self.font = font
        self.dragging = False
        self.knob_radius = height // 2 + 4
        self.unit = unit
        self.decimals = decimals
        self.color = color or COLORS['slider_fill']
    
    def draw(self, surface):
        # Label above
        lbl = self.font.render(self.label, True, COLORS['text'])
        surface.blit(lbl, (self.rect.x, self.rect.y - 20))
        
        # Track
        pygame.draw.rect(surface, COLORS['slider_bg'], self.rect, 
                        border_radius=self.rect.height // 2)
        
        # Fill
        if self.min_val < 0 and self.max_val > 0:
            center_x = self.rect.x + self.rect.width * (-self.min_val) / (self.max_val - self.min_val)
            value_x = self.rect.x + ((self.value - self.min_val) / (self.max_val - self.min_val)) * self.rect.width
            fill_left = min(center_x, value_x)
            fill_right = max(center_x, value_x)
            fill_rect = pygame.Rect(fill_left, self.rect.y, fill_right - fill_left, self.rect.height)
            pygame.draw.rect(surface, self.color, fill_rect, border_radius=self.rect.height // 2)
            pygame.draw.line(surface, COLORS['text_dim'], 
                           (center_x, self.rect.y - 2), (center_x, self.rect.y + self.rect.height + 2), 2)
        else:
            fill_width = ((self.value - self.min_val) / (self.max_val - self.min_val)) * self.rect.width
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
            pygame.draw.rect(surface, self.color, fill_rect, border_radius=self.rect.height // 2)
        
        # Knob
        knob_x = self.rect.x + ((self.value - self.min_val) / (self.max_val - self.min_val)) * self.rect.width
        knob_y = self.rect.y + self.rect.height // 2
        pygame.draw.circle(surface, COLORS['slider_knob'], (int(knob_x), int(knob_y)), self.knob_radius)
        pygame.draw.circle(surface, self.color, (int(knob_x), int(knob_y)), self.knob_radius - 3)
        
        # Value
        if self.decimals == 0:
            val_str = f"{self.value:.0f}"
        elif self.decimals == 1:
            val_str = f"{self.value:.1f}"
        else:
            val_str = f"{self.value:.2f}"
        
        if self.min_val < 0 and self.max_val > 0 and self.value > 0:
            val_str = "+" + val_str
        
        val_txt = self.font.render(f"{val_str} {self.unit}", True, COLORS['text'])
        surface.blit(val_txt, (self.rect.x, self.rect.y + self.rect.height + 5))
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) or self._knob_hit(event.pos):
                self.dragging = True
                self._update_value(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_value(event.pos[0])
    
    def _knob_hit(self, pos):
        knob_x = self.rect.x + ((self.value - self.min_val) / (self.max_val - self.min_val)) * self.rect.width
        knob_y = self.rect.y + self.rect.height // 2
        return math.sqrt((pos[0] - knob_x)**2 + (pos[1] - knob_y)**2) <= self.knob_radius
    
    def _update_value(self, mouse_x):
        rel_x = max(0, min(self.rect.width, mouse_x - self.rect.x))
        self.value = self.min_val + (rel_x / self.rect.width) * (self.max_val - self.min_val)
    
    def get_value(self):
        return self.value
    
    def reset(self, value):
        self.value = max(self.min_val, min(self.max_val, value))


# ==============================================================================
# LEVER DIAGRAM
# ==============================================================================

class TugDiagram:
    def __init__(self, diagram_type, name, handle_length=3.0, aircraft_arm=1.5,
                 x1_constrained=False):
        self.diagram_type = diagram_type
        self.name = name
        self.gray_angle = GRAY_ARM_ANGLE
        self.handle_length = handle_length
        self.aircraft_arm = aircraft_arm
        self.x1_constrained = x1_constrained
        
        # Configure based on type
        if diagram_type in [1, 2]:
            self.gold_angle = 90 - self.gray_angle
            self.has_bend = True
        elif diagram_type == 3:
            self.gold_angle = 0
            self.has_bend = False
        elif diagram_type in [4, 5]:
            self.gold_angle = 90 - self.gray_angle
            self.has_bend = False
        else:
            self.gold_angle = 0
            self.has_bend = False
        
        self.x1_initial = 0.0
        self.x1_current = 0.0
        self.f_handle = 0.0
        self.f_pull = 0.0
        
        # Per-diagram calculated values
        self.motor_torque = 0.0
        self.motor_power_hp = 0.0
        self.motor_power_w = 0.0
        
        # Click detection rect (set during draw)
        self.panel_rect = None
        
        self._recalculate_geometry()
    
    def _recalculate_geometry(self, x1_target=None):
        gold_base_angle = (180 - self.gray_angle) - 90
        cos_gold = math.cos(math.radians(gold_base_angle))
        
        if self.diagram_type == 3 or self.diagram_type == 6:
            self.x1_initial = self.aircraft_arm
        elif self.x1_constrained:
            self.x1_initial = x1_target if x1_target is not None else 1.5
            self.aircraft_arm = self.x1_initial / cos_gold
        else:
            self.x1_initial = self.aircraft_arm * cos_gold
        
        self.x1_current = self.x1_initial
    
    def set_arm_lengths(self, handle_length, aircraft_arm):
        self.handle_length = handle_length
        if self.x1_constrained:
            self._recalculate_geometry(x1_target=aircraft_arm)
        else:
            self.aircraft_arm = aircraft_arm
            self._recalculate_geometry()
    
    def calculate_forces(self, f_pull):
        """Calculate handle force and motor specs for this specific config."""
        self.f_pull = f_pull
        
        if self.handle_length > 0.01:
            self.f_handle = (f_pull * self.x1_current) / self.handle_length
        else:
            self.f_handle = 0.0
        
        # Motor specs for THIS diagram's handle force
        # Motor needs to provide equivalent force at the tire
        self.motor_torque = abs(self.f_handle) * TIRE_RADIUS_FT
        omega = TARGET_SPEED_FPS / TIRE_RADIUS_FT
        power_ft_lb_s = self.motor_torque * omega
        self.motor_power_hp = power_ft_lb_s / 550
        self.motor_power_w = self.motor_power_hp * 745.7
        
        return self.f_handle
    
    def contains_point(self, pos):
        """Check if position is inside this diagram's panel."""
        if self.panel_rect:
            return self.panel_rect.collidepoint(pos)
        return False


# ==============================================================================
# MAIN CALCULATOR
# ==============================================================================

class TugCalculator:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Aircraft Tug Force Calculator")
        self.clock = pygame.time.Clock()
        
        # Fonts
        try:
            self.font_lg = pygame.font.SysFont('Segoe UI', 22, bold=True)
            self.font_md = pygame.font.SysFont('Segoe UI', 15)
            self.font_sm = pygame.font.SysFont('Segoe UI', 13)
            self.font_xs = pygame.font.SysFont('Segoe UI', 11)
            self.font_title = pygame.font.SysFont('Segoe UI', 20, bold=True)
        except:
            self.font_lg = pygame.font.Font(None, 26)
            self.font_md = pygame.font.Font(None, 18)
            self.font_sm = pygame.font.Font(None, 16)
            self.font_xs = pygame.font.Font(None, 14)
            self.font_title = pygame.font.Font(None, 24)
        
        self.running = True
        
        # State
        self.aircraft_weight = DEFAULT_AIRCRAFT_WEIGHT
        self.incline_deg = DEFAULT_INCLINE
        self.current_surface = 'Clean Concrete'
        self.friction_coeff = FRICTION_PRESETS[self.current_surface]
        
        # Calculated base values
        self.f_rolling = 0.0
        self.f_grade = 0.0
        self.f_pull_total = 0.0
        
        # Create 6 diagrams
        self.diagrams = [
            TugDiagram(1, "D1a: L-Shape", 3.0, 1.5, False),
            TugDiagram(2, "D1b: L-Shape (X1)", 3.0, 1.5, True),
            TugDiagram(3, "D2: Horizontal", 3.0, 1.5, False),
            TugDiagram(4, "D3a: Angled", 3.0, 1.5, False),
            TugDiagram(5, "D3b: Angled (X1)", 3.0, 1.5, True),
            TugDiagram(6, "D4: Extended", 4.0, 2.0, False),
        ]
        
        # Selected diagram index (0-5)
        self.selected_idx = 0
        
        # ==================================================================
        # LEFT PANEL CONTROLS
        # ==================================================================
        left_x = 20
        
        # Weight slider
        self.weight_slider = Slider(
            left_x, 80, 160, 12,
            "Aircraft Weight:", 500, 10000, DEFAULT_AIRCRAFT_WEIGHT,
            self.font_sm, "lb", 0, COLORS['aircraft']
        )
        
        # Surface buttons
        self.surface_buttons = []
        btn_y = 150
        for i, (name, coeff) in enumerate(FRICTION_PRESETS.items()):
            btn = Button(left_x, btn_y + i * 32, 160, 28, name, self.font_sm,
                        active=(name == self.current_surface))
            self.surface_buttons.append((btn, name, coeff))
        
        # Incline slider
        self.incline_slider = Slider(
            left_x, 330, 160, 12,
            "Incline:", -2.0, 2.0, DEFAULT_INCLINE,
            self.font_sm, "°", 1, COLORS['angle_indicator']
        )
        
        # Arm sliders
        self.handle_slider = Slider(
            left_x, 420, 160, 12,
            "Handle Arm (X):", 1.0, 6.0, DEFAULT_HANDLE_LENGTH,
            self.font_sm, "ft", 1, COLORS['left_arm']
        )
        
        self.aircraft_arm_slider = Slider(
            left_x, 500, 160, 12,
            "Aircraft Arm (C):", 0.5, 4.0, DEFAULT_AIRCRAFT_ARM,
            self.font_sm, "ft", 2, COLORS['right_arm']
        )
        
        # Reset button
        self.btn_reset = Button(left_x, 580, 160, 35, "RESET", self.font_md)
        
        self._update_calculations()
    
    def _update_calculations(self):
        """Update all calculations."""
        self.aircraft_weight = self.weight_slider.get_value()
        self.incline_deg = self.incline_slider.get_value()
        incline_rad = math.radians(self.incline_deg)
        
        # Base forces (same for all diagrams)
        self.f_rolling = self.friction_coeff * self.aircraft_weight * math.cos(incline_rad)
        self.f_grade = self.aircraft_weight * math.sin(incline_rad)
        self.f_pull_total = self.f_rolling + self.f_grade
        
        # Update each diagram
        handle_len = self.handle_slider.get_value()
        aircraft_arm = self.aircraft_arm_slider.get_value()
        
        for diag in self.diagrams:
            if diag.diagram_type == 6:
                diag.set_arm_lengths(handle_len + 1.0, aircraft_arm + 0.5)
            else:
                diag.set_arm_lengths(handle_len, aircraft_arm)
            diag.calculate_forces(self.f_pull_total)
    
    def _select_surface(self, name, coeff):
        self.current_surface = name
        self.friction_coeff = coeff
        for btn, n, _ in self.surface_buttons:
            btn.active = (n == name)
        self._update_calculations()
    
    def reset(self):
        self.weight_slider.reset(DEFAULT_AIRCRAFT_WEIGHT)
        self.incline_slider.reset(DEFAULT_INCLINE)
        self.handle_slider.reset(DEFAULT_HANDLE_LENGTH)
        self.aircraft_arm_slider.reset(DEFAULT_AIRCRAFT_ARM)
        self._select_surface('Clean Concrete', FRICTION_PRESETS['Clean Concrete'])
        self.selected_idx = 0
    
    def draw_arrow(self, surf, start, end, color, width=3):
        pygame.draw.line(surf, color, start, end, width)
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.sqrt(dx*dx + dy*dy)
        if length < 1:
            return
        dx, dy = dx/length, dy/length
        px, py = -dy, dx
        hs = 9
        p1 = (end[0] - hs*dx + hs*0.4*px, end[1] - hs*dy + hs*0.4*py)
        p2 = (end[0] - hs*dx - hs*0.4*px, end[1] - hs*dy - hs*0.4*py)
        pygame.draw.polygon(surf, color, [end, p1, p2])
    
    def draw_tire(self, surf, cx, cy, radius_px):
        pygame.draw.circle(surf, COLORS['tire'], (int(cx), int(cy)), int(radius_px))
        pygame.draw.circle(surf, COLORS['tire_rim'], (int(cx), int(cy)), int(radius_px * 0.5))
        pygame.draw.circle(surf, COLORS['pivot'], (int(cx), int(cy)), int(radius_px * 0.2))
    
    def draw_diagram(self, surf, diag, px, py, pw, ph, selected=False):
        """Draw a diagram panel. Returns the panel rect for click detection."""
        # Store rect for click detection
        diag.panel_rect = pygame.Rect(px, py, pw, ph)
        
        # Background
        bg_color = COLORS['bg_selected'] if selected else COLORS['bg_panel']
        pygame.draw.rect(surf, bg_color, diag.panel_rect, border_radius=8)
        
        # Selection border
        if selected:
            pygame.draw.rect(surf, COLORS['selection_border'], diag.panel_rect, 3, border_radius=8)
        
        # Title
        title = self.font_sm.render(diag.name, True, COLORS['text'])
        surf.blit(title, (px + pw//2 - title.get_width()//2, py + 8))
        
        # Diagram center
        pivot_x = px + pw // 2
        pivot_y = py + ph // 2 + 15
        
        # Ground line
        pygame.draw.line(surf, COLORS['grid'], 
                        (pivot_x - 80, pivot_y + 12), (pivot_x + 80, pivot_y + 12), 1)
        
        # GRAY ARM (Handle)
        gray_rad = math.radians(180 - diag.gray_angle)
        gray_length = diag.handle_length / math.cos(math.radians(diag.gray_angle))
        p1_x = pivot_x + gray_length * SCALE * math.cos(gray_rad)
        p1_y = pivot_y - gray_length * SCALE * math.sin(gray_rad)
        
        pygame.draw.line(surf, COLORS['left_arm'], (pivot_x, pivot_y), (p1_x, p1_y), 5)
        pygame.draw.circle(surf, COLORS['f_handle'], (int(p1_x), int(p1_y)), 4)
        
        # Handle force arrow
        f_arrow_len = 30 + min(abs(diag.f_handle) / 10, 20)
        self.draw_arrow(surf, (p1_x, p1_y - 3), (p1_x, p1_y + f_arrow_len), COLORS['f_handle'])
        
        # Handle force value
        f_lbl = self.font_sm.render(f"{diag.f_handle:.0f} lb", True, COLORS['f_handle'])
        surf.blit(f_lbl, (p1_x - 22, p1_y + f_arrow_len + 1))
        
        # GOLD ARM
        visual_type = diag.diagram_type
        if visual_type == 2:
            visual_type = 1
        elif visual_type == 5:
            visual_type = 4
        
        if visual_type == 1:
            # L-shape
            gold_base_angle = (180 - diag.gray_angle) - 90
            bend_x = pivot_x + diag.aircraft_arm * SCALE * math.cos(math.radians(gold_base_angle))
            bend_y = pivot_y - diag.aircraft_arm * SCALE * math.sin(math.radians(gold_base_angle))
            p2_x, p2_y = bend_x, pivot_y
            pygame.draw.line(surf, COLORS['right_arm'], (pivot_x, pivot_y), (bend_x, bend_y), 5)
            pygame.draw.line(surf, COLORS['right_arm'], (bend_x, bend_y), (p2_x, p2_y), 5)
            pygame.draw.circle(surf, COLORS['right_arm'], (int(bend_x), int(bend_y)), 3)
        elif visual_type == 3 or visual_type == 6:
            # Horizontal
            p2_x = pivot_x + diag.aircraft_arm * SCALE
            p2_y = pivot_y
            pygame.draw.line(surf, COLORS['right_arm'], (pivot_x, pivot_y), (p2_x, p2_y), 5)
        else:
            # Angled
            gold_base_angle = (180 - diag.gray_angle) - 90
            p2_x = pivot_x + diag.aircraft_arm * SCALE * math.cos(math.radians(gold_base_angle))
            p2_y = pivot_y - diag.aircraft_arm * SCALE * math.sin(math.radians(gold_base_angle))
            pygame.draw.line(surf, COLORS['right_arm'], (pivot_x, pivot_y), (p2_x, p2_y), 5)
        
        # P2 and pull arrow
        pygame.draw.circle(surf, COLORS['f_pull'], (int(p2_x), int(p2_y)), 4)
        pull_len = 25 + min(abs(diag.f_pull) / 20, 15)
        self.draw_arrow(surf, (p2_x + 2, p2_y), (p2_x + pull_len, p2_y), COLORS['f_pull'])
        
        # X1 dimension
        x1_px = diag.x1_current * SCALE
        dim_y = pivot_y + 25
        pygame.draw.line(surf, COLORS['moment_arm'], (pivot_x, dim_y), (pivot_x + x1_px, dim_y), 1)
        x1_lbl = self.font_xs.render(f"X1={diag.x1_current:.2f}", True, COLORS['moment_arm'])
        surf.blit(x1_lbl, (pivot_x + x1_px/2 - 20, dim_y + 2))
        
        # Tire
        self.draw_tire(surf, pivot_x, pivot_y, TIRE_RADIUS_FT * SCALE * 1.8)
    
    def draw_left_panel(self):
        """Draw the left controls panel."""
        # Panel background
        pygame.draw.rect(self.screen, COLORS['bg_panel'], 
                        (0, 0, LEFT_PANEL_WIDTH, WINDOW_HEIGHT))
        
        # Title
        title = self.font_title.render("Controls", True, COLORS['text'])
        self.screen.blit(title, (20, 15))
        
        # Separator
        pygame.draw.line(self.screen, COLORS['text_dim'], (15, 50), (LEFT_PANEL_WIDTH - 15, 50), 1)
        
        # Draw all controls
        self.weight_slider.draw(self.screen)
        
        # Surface label
        surf_lbl = self.font_sm.render("Surface Type:", True, COLORS['text'])
        self.screen.blit(surf_lbl, (20, 130))
        
        for btn, _, _ in self.surface_buttons:
            btn.draw(self.screen)
        
        self.incline_slider.draw(self.screen)
        self.handle_slider.draw(self.screen)
        self.aircraft_arm_slider.draw(self.screen)
        self.btn_reset.draw(self.screen)
        
        # Instructions
        inst1 = self.font_xs.render("Click diagram to", True, COLORS['text_dim'])
        inst2 = self.font_xs.render("see its details →", True, COLORS['text_dim'])
        self.screen.blit(inst1, (20, 640))
        self.screen.blit(inst2, (20, 655))
    
    def draw_right_panel(self):
        """Draw the right results panel for selected diagram."""
        rx = WINDOW_WIDTH - RIGHT_PANEL_WIDTH
        
        # Panel background
        pygame.draw.rect(self.screen, COLORS['bg_panel'], 
                        (rx, 0, RIGHT_PANEL_WIDTH, WINDOW_HEIGHT))
        
        # Get selected diagram
        diag = self.diagrams[self.selected_idx]
        
        # Title
        title = self.font_title.render("Results", True, COLORS['text'])
        self.screen.blit(title, (rx + 15, 15))
        
        # Selected diagram name
        sel_lbl = self.font_md.render(f"Selected: {diag.name}", True, COLORS['selection_border'])
        self.screen.blit(sel_lbl, (rx + 15, 45))
        
        pygame.draw.line(self.screen, COLORS['text_dim'], (rx + 10, 75), (rx + RIGHT_PANEL_WIDTH - 10, 75), 1)
        
        # ==================================================================
        # FORCE BREAKDOWN (for this diagram)
        # ==================================================================
        y = 90
        
        fb_title = self.font_md.render("Force Breakdown", True, COLORS['text'])
        self.screen.blit(fb_title, (rx + 15, y))
        
        y += 25
        surf_lbl = self.font_sm.render(f"{self.current_surface}", True, COLORS['text_dim'])
        self.screen.blit(surf_lbl, (rx + 15, y))
        
        y += 18
        coeff_lbl = self.font_xs.render(f"μ = {self.friction_coeff:.3f}", True, COLORS['text_dim'])
        self.screen.blit(coeff_lbl, (rx + 15, y))
        
        y += 22
        roll_lbl = self.font_sm.render(f"Rolling Resistance:", True, COLORS['text'])
        self.screen.blit(roll_lbl, (rx + 15, y))
        roll_val = self.font_sm.render(f"{self.f_rolling:.1f} lb", True, COLORS['f_ground'])
        self.screen.blit(roll_val, (rx + 15, y + 16))
        
        y += 40
        grade_color = COLORS['good'] if self.f_grade <= 0 else COLORS['warning']
        grade_lbl = self.font_sm.render(f"Grade Resistance:", True, COLORS['text'])
        self.screen.blit(grade_lbl, (rx + 15, y))
        grade_val = self.font_sm.render(f"{self.f_grade:+.1f} lb", True, grade_color)
        self.screen.blit(grade_val, (rx + 15, y + 16))
        
        if self.f_grade < 0:
            help_lbl = self.font_xs.render("(downhill assists)", True, COLORS['good'])
            self.screen.blit(help_lbl, (rx + 15, y + 32))
        
        y += 55
        pygame.draw.line(self.screen, COLORS['text_dim'], (rx + 15, y), (rx + RIGHT_PANEL_WIDTH - 15, y), 1)
        
        y += 10
        pull_lbl = self.font_md.render("Total Pull Force:", True, COLORS['text'])
        self.screen.blit(pull_lbl, (rx + 15, y))
        pull_val = self.font_lg.render(f"{self.f_pull_total:.1f} lb", True, COLORS['f_pull'])
        self.screen.blit(pull_val, (rx + 15, y + 22))
        
        # ==================================================================
        # HANDLE FORCE (the main output)
        # ==================================================================
        y += 65
        pygame.draw.line(self.screen, COLORS['f_handle'], (rx + 10, y), (rx + RIGHT_PANEL_WIDTH - 10, y), 2)
        
        y += 10
        handle_title = self.font_md.render("Handle Force Required:", True, COLORS['text'])
        self.screen.blit(handle_title, (rx + 15, y))
        
        y += 22
        handle_val = self.font_lg.render(f"{diag.f_handle:.1f} lb", True, COLORS['f_handle'])
        self.screen.blit(handle_val, (rx + 15, y))
        
        y += 30
        # Effort assessment
        if diag.f_handle <= 50:
            note, note_color = "Easy for most adults", COLORS['good']
        elif diag.f_handle <= 100:
            note, note_color = "Moderate effort", COLORS['text_highlight']
        elif diag.f_handle <= 150:
            note, note_color = "Significant effort", COLORS['warning']
        else:
            note, note_color = "Motor recommended", COLORS['warning']
        
        note_lbl = self.font_sm.render(note, True, note_color)
        self.screen.blit(note_lbl, (rx + 15, y))
        
        # ==================================================================
        # MOTOR SPECS (for this diagram)
        # ==================================================================
        y += 40
        pygame.draw.line(self.screen, COLORS['motor_specs'], (rx + 10, y), (rx + RIGHT_PANEL_WIDTH - 10, y), 2)
        
        y += 10
        motor_title = self.font_md.render(f"Motor Specs @ {TARGET_SPEED_MPH:.0f} mph", True, COLORS['motor_specs'])
        self.screen.blit(motor_title, (rx + 15, y))
        
        y += 22
        
        # Torque in multiple units
        # Conversions: 1 lb-ft = 1.35582 Nm, 1 Nm = 10.1972 kg.cm
        torque_nm = diag.motor_torque * 1.35582
        torque_kgcm = torque_nm * 10.1972
        
        torque_lbl1 = self.font_sm.render(f"Torque: {diag.motor_torque:.2f} lb-ft", True, COLORS['text'])
        self.screen.blit(torque_lbl1, (rx + 15, y))
        
        y += 18
        torque_lbl2 = self.font_sm.render(f"        {torque_nm:.2f} Nm", True, COLORS['text'])
        self.screen.blit(torque_lbl2, (rx + 15, y))
        
        y += 18
        torque_lbl3 = self.font_sm.render(f"        {torque_kgcm:.1f} kg.cm", True, COLORS['text'])
        self.screen.blit(torque_lbl3, (rx + 15, y))
        
        y += 22
        hp_lbl = self.font_sm.render(f"Power: {diag.motor_power_hp:.3f} HP", True, COLORS['text'])
        self.screen.blit(hp_lbl, (rx + 15, y))
        
        y += 18
        watt_lbl = self.font_sm.render(f"       {diag.motor_power_w:.1f} W", True, COLORS['text'])
        self.screen.blit(watt_lbl, (rx + 15, y))
        
        y += 22
        wheel_lbl = self.font_xs.render(f"(Based on {TIRE_DIAMETER_IN:.0f}\" wheel)", True, COLORS['text_dim'])
        self.screen.blit(wheel_lbl, (rx + 15, y))
        
        # ==================================================================
        # GEOMETRY INFO
        # ==================================================================
        y += 35
        pygame.draw.line(self.screen, COLORS['text_dim'], (rx + 10, y), (rx + RIGHT_PANEL_WIDTH - 10, y), 1)
        
        y += 10
        geom_title = self.font_md.render("Geometry", True, COLORS['text'])
        self.screen.blit(geom_title, (rx + 15, y))
        
        y += 22
        x_lbl = self.font_sm.render(f"Handle Arm (X): {diag.handle_length:.1f} ft", True, COLORS['left_arm'])
        self.screen.blit(x_lbl, (rx + 15, y))
        
        y += 18
        c_lbl = self.font_sm.render(f"Aircraft Arm (C): {diag.aircraft_arm:.2f} ft", True, COLORS['right_arm'])
        self.screen.blit(c_lbl, (rx + 15, y))
        
        y += 18
        x1_lbl = self.font_sm.render(f"X1 (horiz dist): {diag.x1_current:.2f} ft", True, COLORS['moment_arm'])
        self.screen.blit(x1_lbl, (rx + 15, y))
        
        y += 18
        if diag.x1_current > 0.01:
            ma = diag.handle_length / diag.x1_current
            ma_lbl = self.font_sm.render(f"Mech. Advantage: {ma:.2f}x", True, COLORS['text_dim'])
        else:
            ma_lbl = self.font_sm.render("Mech. Advantage: --", True, COLORS['text_dim'])
        self.screen.blit(ma_lbl, (rx + 15, y))
    
    def run(self):
        while self.running:
            mpos = pygame.mouse.get_pos()
            clicked = False
            
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        self.running = False
                    elif e.key == pygame.K_r:
                        self.reset()
                    elif e.key == pygame.K_1:
                        self.selected_idx = 0
                    elif e.key == pygame.K_2:
                        self.selected_idx = 1
                    elif e.key == pygame.K_3:
                        self.selected_idx = 2
                    elif e.key == pygame.K_4:
                        self.selected_idx = 3
                    elif e.key == pygame.K_5:
                        self.selected_idx = 4
                    elif e.key == pygame.K_6:
                        self.selected_idx = 5
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    clicked = True
                
                self.weight_slider.handle_event(e)
                self.incline_slider.handle_event(e)
                self.handle_slider.handle_event(e)
                self.aircraft_arm_slider.handle_event(e)
            
            # Update buttons
            for btn, _, _ in self.surface_buttons:
                btn.update(mpos)
            self.btn_reset.update(mpos)
            
            for btn, name, coeff in self.surface_buttons:
                if btn.clicked(mpos, clicked):
                    self._select_surface(name, coeff)
            
            if self.btn_reset.clicked(mpos, clicked):
                self.reset()
            
            # Check diagram clicks
            if clicked:
                for i, diag in enumerate(self.diagrams):
                    if diag.contains_point(mpos):
                        self.selected_idx = i
                        break
            
            self._update_calculations()
            
            # ==============================================================
            # DRAWING
            # ==============================================================
            self.screen.fill(COLORS['bg'])
            
            # Header
            title = self.font_lg.render("Aircraft Tug Force Calculator", True, COLORS['text'])
            title_x = LEFT_PANEL_WIDTH + (CENTER_WIDTH // 2) - (title.get_width() // 2) + 10
            self.screen.blit(title, (title_x, 15))
            
            # Draw 6 diagrams in center (3x2 grid)
            diagram_start_x = LEFT_PANEL_WIDTH + 20
            diagram_start_y = 55
            diagram_w = (CENTER_WIDTH - 30) // 3
            diagram_h = (WINDOW_HEIGHT - 80) // 2
            gap = 10
            
            for row in range(2):
                for col in range(3):
                    idx = row * 3 + col
                    px = diagram_start_x + col * (diagram_w + gap)
                    py = diagram_start_y + row * (diagram_h + gap)
                    self.draw_diagram(self.screen, self.diagrams[idx], 
                                     px, py, diagram_w, diagram_h,
                                     selected=(idx == self.selected_idx))
            
            # Draw panels
            self.draw_left_panel()
            self.draw_right_panel()
            
            # Footer
            footer = self.font_xs.render("[1-6] Select diagram | [R] Reset | [ESC] Quit", True, COLORS['text_dim'])
            self.screen.blit(footer, (LEFT_PANEL_WIDTH + CENTER_WIDTH//2 - footer.get_width()//2 + 10, 
                                     WINDOW_HEIGHT - 18))
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    
    print("=" * 60)
    print("  Aircraft Tug Force Calculator")
    print("=" * 60)
    print()
    print("  Click on a diagram to see detailed results.")
    print("  Or press 1-6 to select.")
    print()
    
    TugCalculator().run()
