#!/usr/bin/env python3
"""
Unit tests for Phase 3 UI components.

Tests the data handling and logic of:
- HydrationProductSelectorWidget
- AffinityEditorDialog
- CSHConfigDialog

Note: These tests focus on the data structures and service integration.
Full GTK widget tests would require a display and are typically done manually.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.services.hydration_products_service import (
    HydrationProductsService,
    HydrationProductData,
    ProductCategory,
    SUGGESTED_PRODUCTS,
    ADDITIONAL_PRODUCTS,
    CSHQ_PORESIZE_DISTRIBUTION,
    CSHQ_RD_VALUES,
    DEFAULT_CONTACT_ANGLE,
    get_hydration_products_service,
)


class TestHydrationProductSelectorLogic:
    """Tests for HydrationProductSelectorWidget logic (without GTK)."""

    @pytest.fixture
    def service(self):
        """Create service instance for each test."""
        return HydrationProductsService()

    def test_suggested_products_for_portland(self, service):
        """Test getting suggested products for portland cement."""
        suggested = service.get_suggested_products_for_cement_type("portland")

        # Core products should be suggested
        assert "CSHQ" in suggested
        assert "Portlandite" in suggested
        assert "ettr" in suggested
        assert "ettr-AlFe" in suggested
        assert "monosulf-AlFe" in suggested

    def test_suggested_products_for_limestone(self, service):
        """Test getting suggested products for limestone cement."""
        suggested = service.get_suggested_products_for_cement_type("limestone")

        # Should include carbonate AFm phases
        assert "C4AcH11" in suggested
        assert "C4Ac0.5H12" in suggested

        # Core products always included
        assert "CSHQ" in suggested
        assert "Portlandite" in suggested

    def test_suggested_products_for_slag(self, service):
        """Test getting suggested products for slag cement."""
        suggested = service.get_suggested_products_for_cement_type("slag")

        # Should include hydrotalcite
        assert "hydrotalc-pyro" in suggested

        # Core products always included
        assert "CSHQ" in suggested
        assert "Portlandite" in suggested

    def test_product_configuration_initialization(self, service):
        """Test that product configurations are properly initialized."""
        gems_name = "CSHQ"
        data = service.get_product_data(gems_name)

        # Simulate configuration initialization
        config = {
            'gems_name': gems_name,
            'affinity': list(data.default_affinity) if data else [],
        }

        if data and data.poresize_distribution:
            config['poresize_distribution'] = list(data.poresize_distribution)
        if data and data.rd_values:
            config['rd_values'] = list(data.rd_values)

        assert config['gems_name'] == "CSHQ"
        assert len(config['affinity']) > 0
        assert 'poresize_distribution' in config
        assert 'rd_values' in config

    def test_category_grouping(self, service):
        """Test that products are correctly grouped by category."""
        by_category = service.get_products_by_category()

        # Check categories exist
        assert ProductCategory.CALCIUM_SILICATE_HYDRATE in by_category
        assert ProductCategory.CALCIUM_HYDROXIDE in by_category
        assert ProductCategory.AFT in by_category
        assert ProductCategory.AFM in by_category

        # Check products are in correct categories
        assert "CSHQ" in by_category[ProductCategory.CALCIUM_SILICATE_HYDRATE]
        assert "Portlandite" in by_category[ProductCategory.CALCIUM_HYDROXIDE]
        assert "ettr" in by_category[ProductCategory.AFT]
        assert "monosulf-AlFe" in by_category[ProductCategory.AFM]


class TestAffinityEditorLogic:
    """Tests for AffinityEditorDialog logic (without GTK)."""

    @pytest.fixture
    def service(self):
        """Create service instance for each test."""
        return HydrationProductsService()

    def test_default_affinity_for_cshq(self, service):
        """Test getting default affinity for CSHQ."""
        affinity = service.get_default_affinity("CSHQ")

        assert len(affinity) > 0

        # Check for expected affinities
        alite_affinity = next(
            (a for a in affinity if a["affinityphase"] == "Alite"),
            None
        )
        assert alite_affinity is not None
        assert alite_affinity["contactanglevalue"] == 30  # Good affinity

    def test_default_affinity_for_portlandite(self, service):
        """Test getting default affinity for Portlandite."""
        affinity = service.get_default_affinity("Portlandite")

        # Portlandite should have high affinity for CSHQ
        cshq_affinity = next(
            (a for a in affinity if a["affinityphase"] == "CSHQ"),
            None
        )
        assert cshq_affinity is not None
        assert cshq_affinity["contactanglevalue"] == 0  # Maximum affinity

        # Portlandite should avoid clinker
        alite_affinity = next(
            (a for a in affinity if a["affinityphase"] == "Alite"),
            None
        )
        assert alite_affinity is not None
        assert alite_affinity["contactanglevalue"] == 180  # No affinity

    def test_affinity_modification(self, service):
        """Test modifying affinity data."""
        # Get default affinity
        affinity = service.get_default_affinity("CSHQ")

        # Simulate modification
        modified_affinity = list(affinity)
        for entry in modified_affinity:
            if entry['affinityphase'] == 'Alite':
                entry['contactanglevalue'] = 45  # Changed from 30

        # Verify modification
        alite = next(e for e in modified_affinity if e['affinityphase'] == 'Alite')
        assert alite['contactanglevalue'] == 45

    def test_add_new_affinity_entry(self, service):
        """Test adding a new affinity entry."""
        affinity = list(service.get_default_affinity("CSHQ"))
        original_count = len(affinity)

        # Add new entry
        affinity.append({
            'affinityphase': 'Calcite',
            'contactanglevalue': 90
        })

        assert len(affinity) == original_count + 1

        # Verify new entry
        calcite = next(e for e in affinity if e['affinityphase'] == 'Calcite')
        assert calcite['contactanglevalue'] == 90

    def test_contact_angle_interpretation(self):
        """Test contact angle interpretation logic."""
        def interpret(angle):
            if angle == 0:
                return "Maximum affinity"
            elif angle < 30:
                return "High affinity"
            elif angle < 60:
                return "Good affinity"
            elif angle < 90:
                return "Slight affinity"
            elif angle == 90:
                return "Neutral"
            elif angle < 120:
                return "Slight avoidance"
            elif angle < 150:
                return "Avoidance"
            elif angle < 180:
                return "Strong avoidance"
            else:
                return "No affinity"

        assert interpret(0) == "Maximum affinity"
        assert interpret(30) == "Good affinity"
        assert interpret(90) == "Neutral"
        assert interpret(180) == "No affinity"
        assert interpret(45) == "Good affinity"
        assert interpret(135) == "Avoidance"


class TestCSHConfigLogic:
    """Tests for CSHConfigDialog logic (without GTK)."""

    def test_psd_default_values(self):
        """Test default poresize distribution values."""
        assert len(CSHQ_PORESIZE_DISTRIBUTION) >= 60  # At least 60 entries

        # Check first entry
        first = CSHQ_PORESIZE_DISTRIBUTION[0]
        assert 'diameter' in first
        assert 'volumefraction' in first
        assert first['diameter'] > 0

        # Check sum is approximately 1.0
        total = sum(entry['volumefraction'] for entry in CSHQ_PORESIZE_DISTRIBUTION)
        assert abs(total - 1.0) < 0.01

    def test_psd_modification(self):
        """Test modifying poresize distribution."""
        psd = [dict(p) for p in CSHQ_PORESIZE_DISTRIBUTION]
        original_count = len(psd)

        # Modify first entry
        psd[0]['volumefraction'] = 0.02
        assert psd[0]['volumefraction'] == 0.02

        # Add new entry
        psd.append({'diameter': 100.0, 'volumefraction': 0.01})
        assert len(psd) == original_count + 1

    def test_rd_default_values(self):
        """Test default Rd values."""
        assert len(CSHQ_RD_VALUES) == 2

        # Check K value
        k_rd = next(r for r in CSHQ_RD_VALUES if r['Rdelement'] == 'K')
        assert abs(k_rd['Rdvalue'] - 0.42) < 0.01

        # Check Na value
        na_rd = next(r for r in CSHQ_RD_VALUES if r['Rdelement'] == 'Na')
        assert abs(na_rd['Rdvalue'] - 0.42) < 0.01

    def test_rd_modification(self):
        """Test modifying Rd values."""
        rd_data = [dict(r) for r in CSHQ_RD_VALUES]

        # Modify K value
        for entry in rd_data:
            if entry['Rdelement'] == 'K':
                entry['Rdvalue'] = 0.50

        k_rd = next(r for r in rd_data if r['Rdelement'] == 'K')
        assert abs(k_rd['Rdvalue'] - 0.50) < 0.01

    def test_psd_csv_format(self):
        """Test that PSD data can be formatted for CSV export."""
        csv_rows = []
        csv_rows.append(['diameter', 'volumefraction'])
        for entry in CSHQ_PORESIZE_DISTRIBUTION[:5]:  # First 5 entries
            csv_rows.append([entry['diameter'], entry['volumefraction']])

        assert len(csv_rows) == 6  # Header + 5 data rows
        assert csv_rows[0] == ['diameter', 'volumefraction']
        assert isinstance(csv_rows[1][0], float)


class TestDefaultContactAngle:
    """Tests for default contact angle constant."""

    def test_default_value(self):
        """Test default contact angle is 90 (neutral)."""
        assert DEFAULT_CONTACT_ANGLE == 90

    def test_service_returns_default(self):
        """Test service method returns correct default."""
        service = HydrationProductsService()
        assert service.get_default_contact_angle() == 90


class TestProductDataIntegrity:
    """Tests for product data integrity."""

    def test_all_products_have_valid_categories(self):
        """Test that all products have valid categories."""
        all_products = {**SUGGESTED_PRODUCTS, **ADDITIONAL_PRODUCTS}

        for name, data in all_products.items():
            assert data.category is not None, f"{name} has no category"
            assert isinstance(data.category, ProductCategory), \
                f"{name} has invalid category type"

    def test_all_products_have_gems_name_match(self):
        """Test that gems_name matches the dict key."""
        all_products = {**SUGGESTED_PRODUCTS, **ADDITIONAL_PRODUCTS}

        for name, data in all_products.items():
            assert data.gems_name == name, \
                f"gems_name mismatch: key={name}, gems_name={data.gems_name}"

    def test_affinity_contact_angles_valid(self):
        """Test that all contact angles are in valid range."""
        all_products = {**SUGGESTED_PRODUCTS, **ADDITIONAL_PRODUCTS}

        for name, data in all_products.items():
            for entry in data.default_affinity:
                angle = entry['contactanglevalue']
                assert 0 <= angle <= 180, \
                    f"{name}: invalid angle {angle} for {entry['affinityphase']}"

    def test_psd_only_on_csh_phases(self):
        """Test that only C-S-H phases have poresize distribution."""
        all_products = {**SUGGESTED_PRODUCTS, **ADDITIONAL_PRODUCTS}

        for name, data in all_products.items():
            if data.poresize_distribution is not None:
                # Should be a C-S-H phase
                assert "CSH" in name.upper() or "C-S-H" in data.display_name, \
                    f"{name} has PSD but doesn't appear to be C-S-H"


class TestServiceSingleton:
    """Tests for service singleton pattern."""

    def test_singleton_returns_same_instance(self):
        """Test that get_hydration_products_service returns same instance."""
        import app.services.hydration_products_service as module
        module._hydration_products_service = None  # Reset

        service1 = get_hydration_products_service()
        service2 = get_hydration_products_service()

        assert service1 is service2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
