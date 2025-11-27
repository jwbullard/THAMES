#!/usr/bin/env python3
"""
Unit tests for MicgenInputService

Tests PSD discretization, weighted combination, phase aggregation,
and complete input file generation.
"""

import pytest
import numpy as np
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from app.services.micgen_input_service import MicgenInputService, MicgenInputGenerationError
from app.models.mix_design import MixDesign, MixDesignComponentData
from app.models.psd_data import PSDData
from app.models.material import Material
from app.models.material_phase import MaterialPhase
from app.services.phase_id_mapping_service import PhaseIdMapping


@pytest.fixture
def mock_services():
    """Create mock service dependencies."""
    mock_material_service = Mock()
    mock_psd_service = Mock()

    return {
        'material': mock_material_service,
        'psd': mock_psd_service
    }


@pytest.fixture
def service(mock_services):
    """Create MicgenInputService instance with mocked dependencies."""
    return MicgenInputService(
        material_service=mock_services['material'],
        psd_service=mock_services['psd']
    )


class TestPSDDiscretization:
    """Test PSD discretization methods."""

    def test_discretize_rosin_rammler(self, service):
        """Test Rosin-Rammler distribution discretization."""
        d50 = 15.0
        n = 1.0
        dmax = 75.0

        size_classes = service._discretize_rosin_rammler(d50, n, dmax)

        # Check format
        assert isinstance(size_classes, list)
        assert len(size_classes) > 0
        assert all(isinstance(sc, tuple) and len(sc) == 2 for sc in size_classes)

        # Check diameters are sorted
        diameters = [d for d, _ in size_classes]
        assert diameters == sorted(diameters)

        # Check fractions sum to ~1.0
        total_fraction = sum(f for _, f in size_classes)
        assert abs(total_fraction - 1.0) < 0.01

        # Check all fractions are positive
        assert all(f > 0 for _, f in size_classes)

        # Check diameter range
        assert min(diameters) >= 0.25
        assert max(diameters) <= dmax * 1.1  # Allow slight overshoot

    def test_discretize_log_normal(self, service):
        """Test Log-Normal distribution discretization."""
        median = 15.0
        spread = 0.5

        size_classes = service._discretize_log_normal(median, spread)

        # Check format
        assert isinstance(size_classes, list)
        assert len(size_classes) > 0

        # Check fractions sum to ~1.0
        total_fraction = sum(f for _, f in size_classes)
        assert abs(total_fraction - 1.0) < 0.01

        # Check diameters are sorted
        diameters = [d for d, _ in size_classes]
        assert diameters == sorted(diameters)

        # For log-normal, median should be near the peak
        max_fraction_idx = max(range(len(size_classes)),
                              key=lambda i: size_classes[i][1])
        peak_diameter = size_classes[max_fraction_idx][0]
        # Peak should be within reasonable range of median
        assert 0.5 * median < peak_diameter < 2.0 * median

    def test_discretize_fuller_thompson(self, service):
        """Test Fuller-Thompson distribution discretization."""
        exponent = 0.5
        dmax = 50.0

        size_classes = service._discretize_fuller_thompson(exponent, dmax)

        # Check format
        assert isinstance(size_classes, list)
        assert len(size_classes) > 0

        # Check fractions sum to ~1.0
        total_fraction = sum(f for _, f in size_classes)
        assert abs(total_fraction - 1.0) < 0.01

        # Check max diameter
        diameters = [d for d, _ in size_classes]
        assert max(diameters) <= dmax * 1.1

    def test_parse_custom_psd(self, service):
        """Test custom PSD parsing from JSON."""
        custom_points = json.dumps([
            [1.0, 0.1],
            [5.0, 0.3],
            [10.0, 0.4],
            [20.0, 0.2]
        ])

        size_classes = service._parse_custom_psd(custom_points)

        # Check format
        assert len(size_classes) == 4
        assert size_classes[0] == (1.0, 0.1)
        assert size_classes[1] == (5.0, 0.3)
        assert size_classes[2] == (10.0, 0.4)
        assert size_classes[3] == (20.0, 0.2)

    def test_parse_custom_psd_normalizes(self, service):
        """Test custom PSD normalizes fractions if they don't sum to 1.0."""
        custom_points = json.dumps([
            [1.0, 0.5],
            [5.0, 1.5]
        ])

        size_classes = service._parse_custom_psd(custom_points)

        # Should normalize to sum = 1.0
        total = sum(f for _, f in size_classes)
        assert abs(total - 1.0) < 0.01
        assert abs(size_classes[0][1] - 0.25) < 0.01  # 0.5/2.0
        assert abs(size_classes[1][1] - 0.75) < 0.01  # 1.5/2.0


class TestPSDConversion:
    """Test PSD to dict and size class conversion."""

    def test_psd_to_dict_rosin_rammler(self, service):
        """Test converting Rosin-Rammler PSD to dict."""
        psd = Mock(
            psd_mode="rosin_rammler",
            psd_d50=15.0,
            psd_n=1.0,
            psd_dmax=75.0
        )

        result = service._psd_to_dict(psd, resolution=1.0)

        assert result['mode'] == 'rosin_rammler'
        assert 'size_classes_um' in result
        assert len(result['size_classes_um']) > 0
        assert result['raw_psd'] == psd

    def test_psd_to_dict_log_normal(self, service):
        """Test converting Log-Normal PSD to dict."""
        psd = Mock(
            psd_mode="log_normal",
            psd_median=15.0,
            psd_spread=0.5
        )

        result = service._psd_to_dict(psd, resolution=1.0)

        assert result['mode'] == 'log_normal'
        assert 'size_classes_um' in result

    def test_psd_to_dict_custom(self, service):
        """Test converting Custom PSD to dict."""
        psd = Mock(
            psd_mode="custom",
            psd_custom_points=json.dumps([[1.0, 0.5], [10.0, 0.5]])
        )

        result = service._psd_to_dict(psd, resolution=1.0)

        assert result['mode'] == 'custom'
        assert len(result['size_classes_um']) == 2

    def test_convert_psd_to_size_classes(self, service):
        """Test converting micrometers to voxels."""
        psd_dict = {
            'mode': 'log_normal',
            'size_classes_um': [
                (1.0, 0.2),
                (5.0, 0.3),
                (10.0, 0.3),
                (20.0, 0.2)
            ]
        }
        resolution = 2.0  # 2 um/voxel

        size_classes = service._convert_psd_to_size_classes(psd_dict, resolution)

        # Check conversion: diameter_voxels = diameter_um / resolution
        assert len(size_classes) == 4
        assert size_classes[0]['diameter_voxels'] == 0.5  # 1.0 / 2.0
        assert size_classes[1]['diameter_voxels'] == 2.5  # 5.0 / 2.0
        assert size_classes[2]['diameter_voxels'] == 5.0  # 10.0 / 2.0
        assert size_classes[3]['diameter_voxels'] == 10.0  # 20.0 / 2.0

        # Check fractions are preserved
        total = sum(sc['volume_fraction'] for sc in size_classes)
        assert abs(total - 1.0) < 0.01

    def test_convert_psd_filters_small_particles(self, service):
        """Test that particles < 0.5 voxels are filtered."""
        psd_dict = {
            'mode': 'custom',
            'size_classes_um': [
                (0.2, 0.1),  # 0.2/1.0 = 0.2 voxels -> FILTERED
                (0.4, 0.2),  # 0.4/1.0 = 0.4 voxels -> FILTERED
                (1.0, 0.3),  # 1.0/1.0 = 1.0 voxels -> KEPT
                (5.0, 0.4)   # 5.0/1.0 = 5.0 voxels -> KEPT
            ]
        }
        resolution = 1.0

        size_classes = service._convert_psd_to_size_classes(psd_dict, resolution)

        # Should only have 2 size classes (>= 0.5 voxels)
        assert len(size_classes) == 2
        assert size_classes[0]['diameter_voxels'] == 1.0
        assert size_classes[1]['diameter_voxels'] == 5.0

        # Fractions should be renormalized
        total = sum(sc['volume_fraction'] for sc in size_classes)
        assert abs(total - 1.0) < 0.01
        # Original fractions were 0.3 and 0.4, renormalized to 3/7 and 4/7
        assert abs(size_classes[0]['volume_fraction'] - 0.3/0.7) < 0.01
        assert abs(size_classes[1]['volume_fraction'] - 0.4/0.7) < 0.01


class TestPSDCombination:
    """Test weighted PSD combination."""

    def test_combine_single_contribution(self, service, mock_services):
        """Test that single contribution returns its PSD directly."""
        psd = Mock(
            psd_mode="log_normal",
            psd_median=15.0,
            psd_spread=0.5
        )
        mock_services['psd'].get_by_id.return_value = psd

        contributions = [{'psd_data_id': 1, 'mass_fraction': 1.0}]

        result = service._combine_psd_data(contributions, resolution=1.0)

        assert result['mode'] == 'log_normal'
        assert 'size_classes_um' in result

    def test_combine_multiple_contributions_weighted(self, service, mock_services):
        """Test weighted combination of multiple PSDs."""
        # Create two different PSDs
        psd1 = Mock(
            psd_mode="custom",
            psd_custom_points=json.dumps([
                [10.0, 1.0]  # Single size class at 10 um
            ])
        )
        psd2 = Mock(
            psd_mode="custom",
            psd_custom_points=json.dumps([
                [2.0, 1.0]  # Single size class at 2 um
            ])
        )

        # Mock service to return appropriate PSD
        def get_psd_by_id(psd_id):
            if psd_id == 1:
                return psd1
            elif psd_id == 2:
                return psd2
            return None

        mock_services['psd'].get_by_id.side_effect = get_psd_by_id

        # 60% coarse, 40% fine
        contributions = [
            {'psd_data_id': 1, 'mass_fraction': 0.6},
            {'psd_data_id': 2, 'mass_fraction': 0.4}
        ]

        result = service._combine_psd_data(contributions, resolution=1.0)

        # Should have combined mode
        assert result['mode'] == 'combined'
        assert 'size_classes_um' in result

        # Should have both diameter points
        size_classes = result['size_classes_um']
        diameters = [d for d, _ in size_classes]
        assert 2.0 in diameters
        assert 10.0 in diameters

        # Check weighted fractions (should be 0.4 at 2um, 0.6 at 10um)
        fractions_dict = {d: f for d, f in size_classes}
        assert abs(fractions_dict[2.0] - 0.4) < 0.01
        assert abs(fractions_dict[10.0] - 0.6) < 0.01

        # Total should be 1.0
        total = sum(f for _, f in size_classes)
        assert abs(total - 1.0) < 0.01

    def test_combine_interpolates_correctly(self, service, mock_services):
        """Test that combination interpolates between points."""
        # Create two PSDs with different diameter points
        psd1 = Mock(
            psd_mode="custom",
            psd_custom_points=json.dumps([
                [5.0, 0.5],
                [15.0, 0.5]
            ])
        )
        psd2 = Mock(
            psd_mode="custom",
            psd_custom_points=json.dumps([
                [10.0, 1.0]
            ])
        )

        def get_psd_by_id(psd_id):
            return psd1 if psd_id == 1 else psd2

        mock_services['psd'].get_by_id.side_effect = get_psd_by_id

        contributions = [
            {'psd_data_id': 1, 'mass_fraction': 0.5},
            {'psd_data_id': 2, 'mass_fraction': 0.5}
        ]

        result = service._combine_psd_data(contributions, resolution=1.0)

        # Should have 3 diameter points (5, 10, 15)
        size_classes = result['size_classes_um']
        diameters = sorted([d for d, _ in size_classes])
        assert diameters == [5.0, 10.0, 15.0]

        # Total should be 1.0
        total = sum(f for _, f in size_classes)
        assert abs(total - 1.0) < 0.01


class TestPhaseAggregation:
    """Test phase data aggregation from mix design."""

    @pytest.mark.skip(reason="Phase aggregation methods not yet fully implemented")
    def test_aggregate_phases_by_name_single_material(self, service):
        """Test aggregating phases from single material."""
        pass

    @pytest.mark.skip(reason="Phase aggregation methods not yet fully implemented")
    def test_aggregate_phases_combines_duplicates(self, service):
        """Test that duplicate phases from different materials are combined."""
        pass

    def test_calculate_solids_volume_fraction(self, service):
        """Test normalization to solids basis."""
        phase_total = 0.45  # 45% on total system basis
        total_solids = 0.75  # 75% solids in system

        solids_basis = service._calculate_solids_volume_fraction(
            phase_total, total_solids
        )

        # Should be 0.45 / 0.75 = 0.6
        assert abs(solids_basis - 0.6) < 0.01

    def test_calculate_solids_volume_fraction_error(self, service):
        """Test error when total solids is zero."""
        with pytest.raises(MicgenInputGenerationError):
            service._calculate_solids_volume_fraction(0.5, 0.0)


class TestInputGeneration:
    """Test complete input file generation."""

    @pytest.mark.skip(reason="Full input generation not yet fully wired - needs mix design with real components")
    def test_generate_basic_structure(self, service, mock_services, tmp_path):
        """Test that basic input file structure is generated."""
        pass

    @pytest.mark.skip(reason="Full input generation not yet fully wired - needs mix design with real components")
    def test_generate_validates_system_size(self, service, mock_services, tmp_path):
        """Test that system size validation works."""
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
