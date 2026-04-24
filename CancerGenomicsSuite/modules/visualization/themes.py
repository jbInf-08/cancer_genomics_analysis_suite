"""
Themes Module

Provides comprehensive theme management and styling for the Cancer Genomics Analysis Suite.
Includes predefined themes, color palettes, and customization options for visualizations.
"""

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import json
import colorsys

logger = logging.getLogger(__name__)


class ThemeType(Enum):
    """Types of visualization themes."""
    SCIENTIFIC = "scientific"
    PUBLICATION = "publication"
    PRESENTATION = "presentation"
    DARK = "dark"
    LIGHT = "light"
    COLORBLIND = "colorblind"
    MINIMAL = "minimal"
    MODERN = "modern"
    CLASSIC = "classic"


class ColorPaletteType(Enum):
    """Types of color palettes."""
    CATEGORICAL = "categorical"
    SEQUENTIAL = "sequential"
    DIVERGING = "diverging"
    QUALITATIVE = "qualitative"


@dataclass
class ColorPalette:
    """Represents a color palette."""
    name: str
    palette_type: ColorPaletteType
    colors: List[str]
    description: str = ""
    max_colors: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_colors(self, n_colors: int = None) -> List[str]:
        """Get colors from the palette."""
        if n_colors is None:
            n_colors = len(self.colors)
        
        if n_colors <= len(self.colors):
            return self.colors[:n_colors]
        else:
            # Interpolate colors if more are needed
            return self._interpolate_colors(n_colors)
    
    def _interpolate_colors(self, n_colors: int) -> List[str]:
        """Interpolate colors to get more shades."""
        if len(self.colors) < 2:
            return self.colors * n_colors
        
        # Convert hex colors to RGB
        rgb_colors = [self._hex_to_rgb(color) for color in self.colors]
        
        # Create interpolation
        interpolated = []
        for i in range(n_colors):
            ratio = i / (n_colors - 1) if n_colors > 1 else 0
            color_idx = ratio * (len(rgb_colors) - 1)
            
            if color_idx == int(color_idx):
                # Exact match
                interpolated.append(self.colors[int(color_idx)])
            else:
                # Interpolate between two colors
                idx1 = int(color_idx)
                idx2 = min(idx1 + 1, len(rgb_colors) - 1)
                weight = color_idx - idx1
                
                r = int(rgb_colors[idx1][0] * (1 - weight) + rgb_colors[idx2][0] * weight)
                g = int(rgb_colors[idx1][1] * (1 - weight) + rgb_colors[idx2][1] * weight)
                b = int(rgb_colors[idx1][2] * (1 - weight) + rgb_colors[idx2][2] * weight)
                
                interpolated.append(f"#{r:02x}{g:02x}{b:02x}")
        
        return interpolated
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert palette to dictionary."""
        return {
            'name': self.name,
            'palette_type': self.palette_type.value,
            'colors': self.colors,
            'description': self.description,
            'max_colors': self.max_colors,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColorPalette':
        """Create palette from dictionary."""
        data['palette_type'] = ColorPaletteType(data['palette_type'])
        return cls(**data)


@dataclass
class VisualizationTheme:
    """Represents a complete visualization theme."""
    name: str
    theme_type: ThemeType
    description: str = ""
    
    # Color settings
    primary_color: str = "#1f77b4"
    secondary_color: str = "#ff7f0e"
    background_color: str = "#ffffff"
    text_color: str = "#000000"
    grid_color: str = "#cccccc"
    
    # Font settings
    font_family: str = "Arial"
    font_size: int = 12
    title_font_size: int = 16
    label_font_size: int = 10
    
    # Layout settings
    figure_size: Tuple[int, int] = (10, 6)
    dpi: int = 300
    line_width: float = 1.5
    marker_size: float = 6.0
    
    # Style settings
    grid_style: str = "whitegrid"
    palette: str = "husl"
    alpha: float = 0.8
    
    # Plotly specific
    plotly_template: str = "plotly_white"
    plotly_colorscale: str = "viridis"
    
    # Custom settings
    custom_styles: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert theme to dictionary."""
        return {
            'name': self.name,
            'theme_type': self.theme_type.value,
            'description': self.description,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'background_color': self.background_color,
            'text_color': self.text_color,
            'grid_color': self.grid_color,
            'font_family': self.font_family,
            'font_size': self.font_size,
            'title_font_size': self.title_font_size,
            'label_font_size': self.label_font_size,
            'figure_size': self.figure_size,
            'dpi': self.dpi,
            'line_width': self.line_width,
            'marker_size': self.marker_size,
            'grid_style': self.grid_style,
            'palette': self.palette,
            'alpha': self.alpha,
            'plotly_template': self.plotly_template,
            'plotly_colorscale': self.plotly_colorscale,
            'custom_styles': self.custom_styles,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VisualizationTheme':
        """Create theme from dictionary."""
        data['theme_type'] = ThemeType(data['theme_type'])
        return cls(**data)


class ThemeManager:
    """
    Manages visualization themes and color palettes.
    
    Features:
    - Predefined themes for different use cases
    - Custom color palettes
    - Theme customization and inheritance
    - Export/import functionality
    - Color accessibility validation
    - Integration with matplotlib, seaborn, and plotly
    """
    
    def __init__(self):
        """Initialize ThemeManager."""
        self.themes = {}
        self.palettes = {}
        self.current_theme = None
        self.current_palette = None
        
        # Initialize default themes and palettes
        self._initialize_default_themes()
        self._initialize_default_palettes()
        
        # Set default theme
        self.set_current_theme("scientific")
    
    def _initialize_default_themes(self):
        """Initialize default visualization themes."""
        # Scientific theme
        scientific_theme = VisualizationTheme(
            name="scientific",
            theme_type=ThemeType.SCIENTIFIC,
            description="Clean, professional theme for scientific publications",
            primary_color="#1f77b4",
            secondary_color="#ff7f0e",
            background_color="#ffffff",
            text_color="#000000",
            grid_color="#e0e0e0",
            font_family="Times New Roman",
            font_size=12,
            title_font_size=14,
            label_font_size=10,
            figure_size=(8, 6),
            dpi=300,
            line_width=1.5,
            marker_size=6.0,
            grid_style="whitegrid",
            palette="Set2",
            alpha=0.8,
            plotly_template="plotly_white",
            plotly_colorscale="viridis"
        )
        self.themes["scientific"] = scientific_theme
        
        # Publication theme
        publication_theme = VisualizationTheme(
            name="publication",
            theme_type=ThemeType.PUBLICATION,
            description="High-quality theme optimized for journal publications",
            primary_color="#2E86AB",
            secondary_color="#A23B72",
            background_color="#ffffff",
            text_color="#2c3e50",
            grid_color="#bdc3c7",
            font_family="Arial",
            font_size=11,
            title_font_size=16,
            label_font_size=9,
            figure_size=(7, 5),
            dpi=300,
            line_width=2.0,
            marker_size=8.0,
            grid_style="white",
            palette="Set1",
            alpha=0.9,
            plotly_template="plotly_white",
            plotly_colorscale="plasma"
        )
        self.themes["publication"] = publication_theme
        
        # Dark theme
        dark_theme = VisualizationTheme(
            name="dark",
            theme_type=ThemeType.DARK,
            description="Dark theme for presentations and modern interfaces",
            primary_color="#00d4ff",
            secondary_color="#ff6b6b",
            background_color="#1a1a1a",
            text_color="#ffffff",
            grid_color="#404040",
            font_family="Arial",
            font_size=12,
            title_font_size=16,
            label_font_size=10,
            figure_size=(10, 6),
            dpi=300,
            line_width=1.5,
            marker_size=6.0,
            grid_style="darkgrid",
            palette="husl",
            alpha=0.8,
            plotly_template="plotly_dark",
            plotly_colorscale="viridis"
        )
        self.themes["dark"] = dark_theme
        
        # Colorblind-friendly theme
        colorblind_theme = VisualizationTheme(
            name="colorblind",
            theme_type=ThemeType.COLORBLIND,
            description="Colorblind-friendly theme with accessible colors",
            primary_color="#1f77b4",
            secondary_color="#ff7f0e",
            background_color="#ffffff",
            text_color="#000000",
            grid_color="#cccccc",
            font_family="Arial",
            font_size=12,
            title_font_size=16,
            label_font_size=10,
            figure_size=(10, 6),
            dpi=300,
            line_width=1.5,
            marker_size=6.0,
            grid_style="whitegrid",
            palette="colorblind",
            alpha=0.8,
            plotly_template="plotly_white",
            plotly_colorscale="viridis"
        )
        self.themes["colorblind"] = colorblind_theme
        
        # Minimal theme
        minimal_theme = VisualizationTheme(
            name="minimal",
            theme_type=ThemeType.MINIMAL,
            description="Minimal theme with clean, simple styling",
            primary_color="#333333",
            secondary_color="#666666",
            background_color="#ffffff",
            text_color="#333333",
            grid_color="#f0f0f0",
            font_family="Arial",
            font_size=12,
            title_font_size=14,
            label_font_size=10,
            figure_size=(8, 6),
            dpi=300,
            line_width=1.0,
            marker_size=4.0,
            grid_style="white",
            palette="gray",
            alpha=0.7,
            plotly_template="plotly_white",
            plotly_colorscale="greys"
        )
        self.themes["minimal"] = minimal_theme
    
    def _initialize_default_palettes(self):
        """Initialize default color palettes."""
        # Categorical palettes
        categorical_palettes = {
            "Set1": ColorPalette(
                name="Set1",
                palette_type=ColorPaletteType.CATEGORICAL,
                colors=["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#ffff33", "#a65628", "#f781bf"],
                description="High contrast categorical colors",
                max_colors=8
            ),
            "Set2": ColorPalette(
                name="Set2",
                palette_type=ColorPaletteType.CATEGORICAL,
                colors=["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494", "#b3b3b3"],
                description="Pastel categorical colors",
                max_colors=8
            ),
            "colorblind": ColorPalette(
                name="colorblind",
                palette_type=ColorPaletteType.CATEGORICAL,
                colors=["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"],
                description="Colorblind-friendly categorical colors",
                max_colors=8
            )
        }
        
        # Sequential palettes
        sequential_palettes = {
            "viridis": ColorPalette(
                name="viridis",
                palette_type=ColorPaletteType.SEQUENTIAL,
                colors=["#440154", "#482777", "#3f4a8a", "#31678e", "#26838f", "#1f9d8a", "#6cce5a", "#b6de2b", "#fee825"],
                description="Perceptually uniform sequential colors",
                max_colors=9
            ),
            "plasma": ColorPalette(
                name="plasma",
                palette_type=ColorPaletteType.SEQUENTIAL,
                colors=["#0d0887", "#46039f", "#7201a8", "#9c179e", "#bd3786", "#d8576b", "#ed7953", "#fb9f3a", "#f0f921"],
                description="High contrast sequential colors",
                max_colors=9
            ),
            "inferno": ColorPalette(
                name="inferno",
                palette_type=ColorPaletteType.SEQUENTIAL,
                colors=["#000004", "#1b0c42", "#4a0e4e", "#781c6d", "#a52c60", "#cf4446", "#ed6925", "#fb9a06", "#fcffa4"],
                description="Dark to light sequential colors",
                max_colors=9
            )
        }
        
        # Diverging palettes
        diverging_palettes = {
            "RdBu": ColorPalette(
                name="RdBu",
                palette_type=ColorPaletteType.DIVERGING,
                colors=["#67001f", "#b2182b", "#d6604d", "#f4a582", "#fddbc7", "#f7f7f7", "#d1e5f0", "#92c5de", "#4393c3", "#2166ac", "#053061"],
                description="Red to blue diverging colors",
                max_colors=11
            ),
            "RdYlBu": ColorPalette(
                name="RdYlBu",
                palette_type=ColorPaletteType.DIVERGING,
                colors=["#a50026", "#d73027", "#f46d43", "#fdae61", "#fee090", "#ffffbf", "#e0f3f8", "#abd9e9", "#74add1", "#4575b4", "#313695"],
                description="Red-yellow-blue diverging colors",
                max_colors=11
            )
        }
        
        # Combine all palettes
        self.palettes.update(categorical_palettes)
        self.palettes.update(sequential_palettes)
        self.palettes.update(diverging_palettes)
    
    def create_theme(self, name: str, theme_type: ThemeType, **kwargs) -> VisualizationTheme:
        """
        Create a custom theme.
        
        Args:
            name: Theme name
            theme_type: Type of theme
            **kwargs: Theme parameters
            
        Returns:
            VisualizationTheme: Created theme
        """
        theme = VisualizationTheme(name=name, theme_type=theme_type, **kwargs)
        self.themes[name] = theme
        logger.info(f"Created custom theme: {name}")
        return theme
    
    def create_palette(self, name: str, palette_type: ColorPaletteType, 
                      colors: List[str], **kwargs) -> ColorPalette:
        """
        Create a custom color palette.
        
        Args:
            name: Palette name
            palette_type: Type of palette
            colors: List of hex colors
            **kwargs: Palette parameters
            
        Returns:
            ColorPalette: Created palette
        """
        palette = ColorPalette(name=name, palette_type=palette_type, colors=colors, **kwargs)
        self.palettes[name] = palette
        logger.info(f"Created custom palette: {name}")
        return palette
    
    def set_current_theme(self, theme_name: str):
        """
        Set the current active theme.
        
        Args:
            theme_name: Name of theme to set
        """
        if theme_name in self.themes:
            self.current_theme = self.themes[theme_name]
            self._apply_theme()
            logger.info(f"Set current theme to: {theme_name}")
        else:
            raise ValueError(f"Theme {theme_name} not found")
    
    def set_current_palette(self, palette_name: str):
        """
        Set the current active palette.
        
        Args:
            palette_name: Name of palette to set
        """
        if palette_name in self.palettes:
            self.current_palette = self.palettes[palette_name]
            self._apply_palette()
            logger.info(f"Set current palette to: {palette_name}")
        else:
            raise ValueError(f"Palette {palette_name} not found")
    
    def _apply_theme(self):
        """Apply the current theme to matplotlib and seaborn."""
        if not self.current_theme:
            return
        
        theme = self.current_theme
        
        # Apply matplotlib settings
        plt.rcParams.update({
            'figure.figsize': theme.figure_size,
            'figure.dpi': theme.dpi,
            'font.family': theme.font_family,
            'font.size': theme.font_size,
            'axes.titlesize': theme.title_font_size,
            'axes.labelsize': theme.label_font_size,
            'xtick.labelsize': theme.label_font_size,
            'ytick.labelsize': theme.label_font_size,
            'legend.fontsize': theme.label_font_size,
            'lines.linewidth': theme.line_width,
            'lines.markersize': theme.marker_size,
            'axes.facecolor': theme.background_color,
            'figure.facecolor': theme.background_color,
            'text.color': theme.text_color,
            'axes.labelcolor': theme.text_color,
            'xtick.color': theme.text_color,
            'ytick.color': theme.text_color,
            'grid.color': theme.grid_color,
            'axes.grid': True,
            'grid.alpha': theme.alpha
        })
        
        # Apply seaborn settings
        sns.set_style(theme.grid_style)
        sns.set_palette(theme.palette)
    
    def _apply_palette(self):
        """Apply the current palette to seaborn."""
        if not self.current_palette:
            return
        
        colors = self.current_palette.get_colors()
        sns.set_palette(colors)
    
    def get_plotly_colorscale(self, palette_name: str = None) -> List[List[Union[float, str]]]:
        """
        Get plotly colorscale from palette.
        
        Args:
            palette_name: Name of palette (uses current if None)
            
        Returns:
            List of colorscale values for plotly
        """
        if palette_name is None:
            if not self.current_palette:
                return px.colors.sequential.Viridis
            palette = self.current_palette
        else:
            if palette_name not in self.palettes:
                raise ValueError(f"Palette {palette_name} not found")
            palette = self.palettes[palette_name]
        
        colors = palette.get_colors()
        n_colors = len(colors)
        
        colorscale = []
        for i, color in enumerate(colors):
            position = i / (n_colors - 1) if n_colors > 1 else 0
            colorscale.append([position, color])
        
        return colorscale
    
    def get_plotly_template(self, theme_name: str = None) -> str:
        """
        Get plotly template from theme.
        
        Args:
            theme_name: Name of theme (uses current if None)
            
        Returns:
            str: Plotly template name
        """
        if theme_name is None:
            if not self.current_theme:
                return "plotly_white"
            return self.current_theme.plotly_template
        else:
            if theme_name not in self.themes:
                raise ValueError(f"Theme {theme_name} not found")
            return self.themes[theme_name].plotly_template
    
    def validate_color_accessibility(self, colors: List[str]) -> Dict[str, Any]:
        """
        Validate color accessibility for colorblind users.
        
        Args:
            colors: List of hex colors
            
        Returns:
            Dict with accessibility information
        """
        # Convert to RGB
        rgb_colors = []
        for color in colors:
            hex_color = color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            rgb_colors.append(rgb)
        
        # Check contrast ratios and colorblind accessibility
        results = {
            'total_colors': len(colors),
            'contrast_ratios': [],
            'colorblind_safe': True,
            'recommendations': []
        }
        
        # Simple contrast check (would need more sophisticated algorithm in practice)
        for i, color1 in enumerate(rgb_colors):
            for j, color2 in enumerate(rgb_colors[i+1:], i+1):
                # Calculate simple contrast ratio
                contrast = self._calculate_contrast_ratio(color1, color2)
                results['contrast_ratios'].append({
                    'color1': colors[i],
                    'color2': colors[j],
                    'contrast_ratio': contrast
                })
                
                if contrast < 3.0:  # WCAG AA standard
                    results['recommendations'].append(
                        f"Low contrast between {colors[i]} and {colors[j]}"
                    )
        
        return results
    
    def _calculate_contrast_ratio(self, color1: Tuple[int, int, int], 
                                color2: Tuple[int, int, int]) -> float:
        """Calculate contrast ratio between two colors."""
        # Convert to relative luminance
        def get_luminance(rgb):
            r, g, b = [c / 255.0 for c in rgb]
            r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
            g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
            b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        lum1 = get_luminance(color1)
        lum2 = get_luminance(color2)
        
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        
        return (lighter + 0.05) / (darker + 0.05)
    
    def export_theme(self, theme_name: str, format: str = "json") -> str:
        """
        Export theme configuration.
        
        Args:
            theme_name: Theme to export
            format: Export format (json, yaml)
            
        Returns:
            str: Exported configuration
        """
        if theme_name not in self.themes:
            raise ValueError(f"Theme {theme_name} not found")
        
        theme = self.themes[theme_name]
        
        if format == "json":
            return json.dumps(theme.to_dict(), indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def export_palette(self, palette_name: str, format: str = "json") -> str:
        """
        Export palette configuration.
        
        Args:
            palette_name: Palette to export
            format: Export format (json, yaml)
            
        Returns:
            str: Exported configuration
        """
        if palette_name not in self.palettes:
            raise ValueError(f"Palette {palette_name} not found")
        
        palette = self.palettes[palette_name]
        
        if format == "json":
            return json.dumps(palette.to_dict(), indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def import_theme(self, config: str, format: str = "json") -> str:
        """
        Import theme configuration.
        
        Args:
            config: Configuration string
            format: Import format (json, yaml)
            
        Returns:
            str: Theme name
        """
        if format == "json":
            theme_data = json.loads(config)
            theme = VisualizationTheme.from_dict(theme_data)
            self.themes[theme.name] = theme
            return theme.name
        else:
            raise ValueError(f"Unsupported import format: {format}")
    
    def import_palette(self, config: str, format: str = "json") -> str:
        """
        Import palette configuration.
        
        Args:
            config: Configuration string
            format: Import format (json, yaml)
            
        Returns:
            str: Palette name
        """
        if format == "json":
            palette_data = json.loads(config)
            palette = ColorPalette.from_dict(palette_data)
            self.palettes[palette.name] = palette
            return palette.name
        else:
            raise ValueError(f"Unsupported import format: {format}")
    
    def get_available_themes(self) -> List[str]:
        """Get list of available theme names."""
        return list(self.themes.keys())
    
    def get_available_palettes(self) -> List[str]:
        """Get list of available palette names."""
        return list(self.palettes.keys())
    
    def get_theme_info(self, theme_name: str) -> Dict[str, Any]:
        """Get information about a theme."""
        if theme_name not in self.themes:
            raise ValueError(f"Theme {theme_name} not found")
        
        theme = self.themes[theme_name]
        return {
            'name': theme.name,
            'type': theme.theme_type.value,
            'description': theme.description,
            'colors': {
                'primary': theme.primary_color,
                'secondary': theme.secondary_color,
                'background': theme.background_color,
                'text': theme.text_color
            },
            'fonts': {
                'family': theme.font_family,
                'size': theme.font_size,
                'title_size': theme.title_font_size
            }
        }
    
    def get_palette_info(self, palette_name: str) -> Dict[str, Any]:
        """Get information about a palette."""
        if palette_name not in self.palettes:
            raise ValueError(f"Palette {palette_name} not found")
        
        palette = self.palettes[palette_name]
        return {
            'name': palette.name,
            'type': palette.palette_type.value,
            'description': palette.description,
            'colors': palette.colors,
            'max_colors': palette.max_colors
        }
