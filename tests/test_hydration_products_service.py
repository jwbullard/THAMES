#!/usr/bin/env python3
"""
Unit tests for HydrationProductsService.

Tests the service that provides hydration product data, defaults,
and suggested products for THAMES simulations.
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


class TestHydrationProductsService:
    """Tests for HydrationProductsService."""

    @pytest.fixture
    def service(self):
        """Create service instance for each test."""
        return HydrationProductsService()

    # =========================================================================
    # Suggested Products Tests
    # =========================================================================

    def test_get_suggested_products(self, service):
        """Test getting suggested products."""
        suggested = service.get_suggested_products()

        assert len(suggested) > 0
        assert "CSHQ" in suggested
        assert "Portlandite" in suggested
        assert "ettr" in suggested
        assert "monosulf-AlFe" in suggested

    def test_get_suggested_products_for_portland(self, service):
        """Test suggested products for portland cement."""
        suggested = service.get_suggested_products_for_cement_type("portland")

        assert "CSHQ" in suggested
        assert "Portlandite" in suggested
        assert "ettr" in suggested
        assert "ettr-AlFe" in suggested

    def test_get_suggested_products_for_limestone(self, service):
        """Test suggested products for limestone-blended cement."""
        suggested = service.get_suggested_products_for_cement_type("limestone")

        assert "CSHQ" in suggested
        assert "Portlandite" in suggested
        assert "C4AcH11" in suggested  # Monocarboaluminate
        assert "C4Ac0.5H12" in suggested  # Hemicarboaluminate

    def test_get_suggested_products_for_slag(self, service):
        """Test suggested products for slag-blended cement."""
        suggested = service.get_suggested_products_for_cement_type("slag")

        assert "CSHQ" in suggested
        assert "Portlandite" in suggested
        assert "hydrotalc-pyro" in suggested  # Hydrotalcite

    def test_suggested_always_includes_cshq_portlandite(self, service):
        """Test that CSHQ and Portlandite are always suggested."""
        for cement_type in ["portland", "blended", "pozzolanic", "limestone", "slag", "unknown"]:
            suggested = service.get_suggested_products_for_cement_type(cement_type)
            assert "CSHQ" in suggested, f"CSHQ missing for {cement_type}"
            assert "Portlandite" in suggested, f"Portlandite missing for {cement_type}"

    # =========================================================================
    # Product Data Tests
    # =========================================================================

    def test_get_product_data_cshq(self, service):
        """Test getting CSHQ product data."""
        data = service.get_product_data("CSHQ")

        assert data is not None
        assert data.gems_name == "CSHQ"
        assert data.display_name == "C-S-H (CSHQ model)"
        assert data.category == ProductCategory.CALCIUM_SILICATE_HYDRATE
        assert len(data.default_affinity) > 0
        assert data.poresize_distribution is not None
        assert data.rd_values is not None

    def test_get_product_data_portlandite(self, service):
        """Test getting Portlandite product data."""
        data = service.get_product_data("Portlandite")

        assert data is not None
        assert data.gems_name == "Portlandite"
        assert data.category == ProductCategory.CALCIUM_HYDROXIDE
        assert len(data.default_affinity) > 0

        # Check affinity for CSHQ
        cshq_affinity = next(
            (a for a in data.default_affinity if a["affinityphase"] == "CSHQ"),
            None
        )
        assert cshq_affinity is not None
        assert cshq_affinity["contactanglevalue"] == 0  # High affinity

    def test_get_product_data_ettringite(self, service):
        """Test getting ettringite product data."""
        data = service.get_product_data("ettr")

        assert data is not None
        assert data.category == ProductCategory.AFT
        assert len(data.default_affinity) > 0

        # Check affinity for clinker (should avoid)
        alite_affinity = next(
            (a for a in data.default_affinity if a["affinityphase"] == "Alite"),
            None
        )
        assert alite_affinity is not None
        assert alite_affinity["contactanglevalue"] == 180  # No affinity

    def test_get_product_data_unknown(self, service):
        """Test getting unknown product returns None."""
        data = service.get_product_data("UnknownPhase")
        assert data is None

    # =========================================================================
    # Default Affinity Tests
    # =========================================================================

    def test_get_default_affinity_cshq(self, service):
        """Test getting default affinity for CSHQ."""
        affinity = service.get_default_affinity("CSHQ")

        assert len(affinity) > 0

        # CSHQ should have affinity for clinker phases
        alite_affinity = next(
            (a for a in affinity if a["affinityphase"] == "Alite"),
            None
        )
        assert alite_affinity is not None
        assert alite_affinity["contactanglevalue"] == 30  # Good affinity

    def test_get_default_affinity_unknown(self, service):
        """Test getting default affinity for unknown phase returns empty list."""
        affinity = service.get_default_affinity("UnknownPhase")
        assert affinity == []

    def test_get_default_contact_angle(self, service):
        """Test getting default contact angle."""
        angle = service.get_default_contact_angle()
        assert angle == 90  # Neutral

    # =========================================================================
    # C-S-H Special Data Tests
    # =========================================================================

    def test_get_cshq_poresize_distribution(self, service):
        """Test getting CSHQ poresize distribution."""
        psd = service.get_cshq_poresize_distribution()

        assert len(psd) > 0
        assert len(psd) == len(CSHQ_PORESIZE_DISTRIBUTION)

        # Check structure
        assert "diameter" in psd[0]
        assert "volumefraction" in psd[0]

        # Check values sum close to 1
        total = sum(entry["volumefraction"] for entry in psd)
        assert abs(total - 1.0) < 0.01

    def test_get_cshq_rd_values(self, service):
        """Test getting CSHQ Rd values."""
        rd = service.get_cshq_rd_values()

        assert len(rd) == 2

        # Check K
        k_rd = next((r for r in rd if r["Rdelement"] == "K"), None)
        assert k_rd is not None
        assert abs(k_rd["Rdvalue"] - 0.42) < 0.01

        # Check Na
        na_rd = next((r for r in rd if r["Rdelement"] == "Na"), None)
        assert na_rd is not None
        assert abs(na_rd["Rdvalue"] - 0.42) < 0.01

    def test_has_special_csh_data(self, service):
        """Test checking for special C-S-H data."""
        assert service.has_special_csh_data("CSHQ") is True
        assert service.has_special_csh_data("Portlandite") is False
        assert service.has_special_csh_data("ettr") is False

    # =========================================================================
    # Category Tests
    # =========================================================================

    def test_get_products_by_category(self, service):
        """Test getting products grouped by category."""
        by_category = service.get_products_by_category()

        assert ProductCategory.CALCIUM_SILICATE_HYDRATE in by_category
        assert ProductCategory.CALCIUM_HYDROXIDE in by_category
        assert ProductCategory.AFT in by_category
        assert ProductCategory.AFM in by_category

        assert "CSHQ" in by_category[ProductCategory.CALCIUM_SILICATE_HYDRATE]
        assert "Portlandite" in by_category[ProductCategory.CALCIUM_HYDROXIDE]
        assert "ettr" in by_category[ProductCategory.AFT]

    def test_get_category_for_phase(self, service):
        """Test getting category for a phase."""
        assert service.get_category_for_phase("CSHQ") == ProductCategory.CALCIUM_SILICATE_HYDRATE
        assert service.get_category_for_phase("Portlandite") == ProductCategory.CALCIUM_HYDROXIDE
        assert service.get_category_for_phase("ettr") == ProductCategory.AFT
        assert service.get_category_for_phase("monosulf-AlFe") == ProductCategory.AFM
        assert service.get_category_for_phase("Unknown") is None

    # =========================================================================
    # Display Name and Description Tests
    # =========================================================================

    def test_get_display_name(self, service):
        """Test getting display names."""
        assert service.get_display_name("CSHQ") == "C-S-H (CSHQ model)"
        assert service.get_display_name("ettr") == "Ettringite"
        assert service.get_display_name("C4AsH12") == "Monosulfate-12"
        assert service.get_display_name("UnknownPhase") == "UnknownPhase"

    def test_get_description(self, service):
        """Test getting descriptions."""
        desc = service.get_description("CSHQ")
        assert "calcium silicate hydrate" in desc.lower()

        desc = service.get_description("ettr")
        assert "ettringite" in desc.lower() or "aft" in desc.lower()

        desc = service.get_description("UnknownPhase")
        assert desc == ""

    # =========================================================================
    # Available Products Tests
    # =========================================================================

    def test_get_all_available_products(self, service):
        """Test getting all available products."""
        products = service.get_all_available_products()

        assert len(products) > 0
        assert len(products) == len(SUGGESTED_PRODUCTS) + len(ADDITIONAL_PRODUCTS)

        # Check both suggested and additional products are included
        for name in SUGGESTED_PRODUCTS.keys():
            assert name in products
        for name in ADDITIONAL_PRODUCTS.keys():
            assert name in products

    # =========================================================================
    # Singleton Tests
    # =========================================================================

    def test_singleton_pattern(self):
        """Test that get_hydration_products_service returns same instance."""
        # Reset singleton for test
        import app.services.hydration_products_service as module
        module._hydration_products_service = None

        service1 = get_hydration_products_service()
        service2 = get_hydration_products_service()

        assert service1 is service2


# =============================================================================
# Data Validation Tests
# =============================================================================

class TestHydrationProductsData:
    """Tests for the hydration products data structures."""

    def test_suggested_products_have_required_fields(self):
        """Test that all suggested products have required fields."""
        for name, data in SUGGESTED_PRODUCTS.items():
            assert data.gems_name == name, f"{name}: gems_name mismatch"
            assert data.display_name, f"{name}: missing display_name"
            assert data.category is not None, f"{name}: missing category"
            assert isinstance(data.default_affinity, list), f"{name}: affinity not a list"

    def test_additional_products_have_required_fields(self):
        """Test that all additional products have required fields."""
        for name, data in ADDITIONAL_PRODUCTS.items():
            assert data.gems_name == name, f"{name}: gems_name mismatch"
            assert data.display_name, f"{name}: missing display_name"
            assert data.category is not None, f"{name}: missing category"
            assert isinstance(data.default_affinity, list), f"{name}: affinity not a list"

    def test_affinity_entries_have_required_fields(self):
        """Test that all affinity entries have required fields."""
        all_products = {**SUGGESTED_PRODUCTS, **ADDITIONAL_PRODUCTS}

        for name, data in all_products.items():
            for i, entry in enumerate(data.default_affinity):
                assert "affinityphase" in entry, f"{name} affinity {i}: missing affinityphase"
                assert "contactanglevalue" in entry, f"{name} affinity {i}: missing contactanglevalue"
                assert 0 <= entry["contactanglevalue"] <= 180, \
                    f"{name} affinity {i}: invalid angle {entry['contactanglevalue']}"

    def test_psd_entries_have_required_fields(self):
        """Test that PSD entries have required fields."""
        for i, entry in enumerate(CSHQ_PORESIZE_DISTRIBUTION):
            assert "diameter" in entry, f"PSD entry {i}: missing diameter"
            assert "volumefraction" in entry, f"PSD entry {i}: missing volumefraction"
            assert entry["diameter"] > 0, f"PSD entry {i}: diameter must be positive"
            assert entry["volumefraction"] >= 0, f"PSD entry {i}: volumefraction must be non-negative"

    def test_rd_entries_have_required_fields(self):
        """Test that Rd entries have required fields."""
        for i, entry in enumerate(CSHQ_RD_VALUES):
            assert "Rdelement" in entry, f"Rd entry {i}: missing Rdelement"
            assert "Rdvalue" in entry, f"Rd entry {i}: missing Rdvalue"
            assert entry["Rdvalue"] >= 0, f"Rd entry {i}: Rdvalue must be non-negative"


# =============================================================================
# Contact Angle Logic Tests
# =============================================================================

class TestContactAngleLogic:
    """Tests for contact angle values and their meanings."""

    def test_cshq_has_affinity_for_clinker(self):
        """Test that C-S-H has affinity for clinker phases (low contact angle)."""
        data = SUGGESTED_PRODUCTS["CSHQ"]

        alite_affinity = next(
            (a for a in data.default_affinity if a["affinityphase"] == "Alite"),
            None
        )
        assert alite_affinity is not None
        assert alite_affinity["contactanglevalue"] < 90  # Good affinity

    def test_portlandite_avoids_clinker(self):
        """Test that Portlandite avoids clinker phases (high contact angle)."""
        data = SUGGESTED_PRODUCTS["Portlandite"]

        alite_affinity = next(
            (a for a in data.default_affinity if a["affinityphase"] == "Alite"),
            None
        )
        assert alite_affinity is not None
        assert alite_affinity["contactanglevalue"] == 180  # No affinity

    def test_afm_has_affinity_for_aft(self):
        """Test that AFm phases have affinity for AFt phases."""
        data = SUGGESTED_PRODUCTS["monosulf-AlFe"]

        ettr_affinity = next(
            (a for a in data.default_affinity if a["affinityphase"] == "ettr"),
            None
        )
        assert ettr_affinity is not None
        assert ettr_affinity["contactanglevalue"] == 0  # High affinity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
