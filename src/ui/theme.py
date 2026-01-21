"""
FragAudit Theme Configuration
GitHub-inspired dark theme
"""

# Color Palette - GitHub Dark Mode
COLORS = {
    # Base (GitHub dark default)
    "bg_dark": "#0d1117",          # canvas default
    "bg_medium": "#161b22",        # canvas subtle
    "bg_light": "#21262d",         # canvas inset
    "bg_hover": "#30363d",         # neutral muted
    
    # Accent (GitHub colors)
    "accent_blue": "#58a6ff",      # accent emphasis
    "accent_green": "#3fb950",     # success emphasis
    "accent_red": "#f85149",       # danger emphasis
    "accent_yellow": "#d29922",    # warning emphasis
    "accent_purple": "#a371f7",    # done emphasis
    "accent_cyan": "#58a6ff",      # primary (use blue as main)
    "accent_orange": "#d29922",    # attention
    
    # Text
    "text_primary": "#f0f6fc",     # fg default
    "text_secondary": "#8b949e",   # fg muted  
    "text_muted": "#6e7681",       # fg subtle
    
    # Borders
    "border": "#30363d",           # border default
    "border_focus": "#58a6ff",     # accent emphasis
    
    # Rating colors
    "rating_high": "#3fb950",      # > 1.1 (green)
    "rating_mid": "#d29922",       # 0.9 - 1.1 (yellow)
    "rating_low": "#f85149",       # < 0.9 (red)
    
    # Team colors (CS2)
    "team_ct": "#58a6ff",          # CT Blue
    "team_t": "#d29922",           # T Orange/Gold
}

# Fonts
FONTS = {
    "heading_large": ("Segoe UI", 24, "bold"),
    "heading": ("Segoe UI", 18, "bold"),
    "subheading": ("Segoe UI", 14, "bold"),
    "body": ("Segoe UI", 12),
    "body_bold": ("Segoe UI", 12, "bold"),
    "small": ("Segoe UI", 10),
    "mono": ("Consolas", 11),
    "mono_small": ("Consolas", 10),
}

# Widget Styling - GitHub style
BUTTON = {
    "corner_radius": 6,
    "border_width": 1,
    "fg_color": "#238636",         # green button
    "hover_color": "#2ea043",      # green hover
    "text_color": "#ffffff",
    "border_color": "#238636",     # same as fg_color
}

BUTTON_SECONDARY = {
    "corner_radius": 6,
    "border_width": 1,
    "fg_color": "#21262d",
    "hover_color": "#30363d",
    "text_color": "#c9d1d9",
    "border_color": "#30363d",
}

BUTTON_PRIMARY = {
    "corner_radius": 6,
    "border_width": 0,
    "fg_color": "#238636",
    "hover_color": "#2ea043",
    "text_color": "#ffffff",
}

ENTRY = {
    "corner_radius": 6,
    "border_width": 1,
    "fg_color": "#0d1117",
    "border_color": "#30363d",
    "text_color": "#c9d1d9",
    "placeholder_text_color": "#6e7681",
}

FRAME = {
    "corner_radius": 6,
    "fg_color": "#161b22",
    "border_width": 1,
    "border_color": "#30363d",
}

CARD = {
    "corner_radius": 6,
    "fg_color": "#161b22",
    "border_width": 1,
    "border_color": "#30363d",
}

# Severity colors for mistake cards
SEVERITY_COLORS = {
    "high": "#f85149",     # red
    "medium": "#d29922",   # yellow
    "low": "#58a6ff",      # blue
}

# Layout
PADDING = {
    "small": 5,
    "medium": 10,
    "large": 20,
    "xlarge": 30,
}

# Window
WINDOW = {
    "width": 1400,
    "height": 900,
    "min_width": 1200,
    "min_height": 700,
}
