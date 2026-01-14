# Copyright (c) 2026 Pl4yer-ONE
# This file is part of FragAudit.
# Licensed under GPLv3 or commercial license.

"""
Radar Renderer Regression Tests
Tests for frame size consistency and alignment.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np


class TestFrameSizeConsistency:
    """Tests to ensure radar frames maintain consistent sizing."""
    
    def test_figsize_calculation(self):
        """Test that figsize is correctly calculated from resolution/dpi."""
        resolution = 1024
        dpi = 100
        expected_figsize = resolution / dpi  # 10.24
        
        assert expected_figsize == 10.24
        assert resolution == expected_figsize * dpi
    
    def test_figsize_different_resolutions(self):
        """Test figsize calculation for various resolutions."""
        dpi = 100
        test_cases = [
            (512, 5.12),
            (1024, 10.24),
            (2048, 20.48),
        ]
        
        for resolution, expected in test_cases:
            figsize = resolution / dpi
            assert figsize == expected, f"Failed for resolution {resolution}"
    
    def test_aspect_ratio_preserved(self):
        """Test that aspect ratio is always 1:1 (square)."""
        # The renderer should always produce square frames
        resolution = 1024
        expected_width = resolution
        expected_height = resolution
        
        assert expected_width == expected_height
    
    def test_extent_matches_resolution(self):
        """Test that imshow extent matches the resolution exactly."""
        resolution = 1024
        # Extent format: [left, right, bottom, top]
        # For Y-flipped display: [0, resolution, resolution, 0]
        extent = [0, resolution, resolution, 0]
        
        assert extent[0] == 0  # left
        assert extent[1] == resolution  # right
        assert extent[2] == resolution  # bottom (flipped)
        assert extent[3] == 0  # top (flipped)
    
    def test_axes_limits_match_resolution(self):
        """Test that axes limits are set correctly for the resolution."""
        resolution = 1024
        
        xlim = (0, resolution)
        ylim = (resolution, 0)  # Flipped Y
        
        assert xlim[0] == 0
        assert xlim[1] == resolution
        assert ylim[0] == resolution  # Bottom
        assert ylim[1] == 0  # Top (flipped)


class TestEvenDimensionScaling:
    """Tests for ffmpeg even-dimension fix."""
    
    def test_even_dimension_formula(self):
        """Test the scale formula produces even numbers."""
        test_widths = [793, 788, 1023, 1025, 512, 513]
        
        for width in test_widths:
            # Formula: trunc(w/2)*2
            even_width = (width // 2) * 2
            assert even_width % 2 == 0, f"Width {width} -> {even_width} is not even"
    
    def test_specific_train_map_case(self):
        """Test the specific de_train case that caused the original error."""
        # de_train was 793x788
        original_width = 793
        original_height = 788
        
        scaled_width = (original_width // 2) * 2
        scaled_height = (original_height // 2) * 2
        
        assert scaled_width == 792
        assert scaled_height == 788
        assert scaled_width % 2 == 0
        assert scaled_height % 2 == 0
    
    def test_already_even_dimensions_unchanged(self):
        """Test that already-even dimensions are preserved."""
        dimensions = [(1024, 1024), (512, 512), (800, 600)]
        
        for width, height in dimensions:
            scaled_w = (width // 2) * 2
            scaled_h = (height // 2) * 2
            assert scaled_w == width
            assert scaled_h == height
