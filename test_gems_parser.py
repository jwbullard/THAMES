#!/usr/bin/env python3
"""
Test script for GEMS Parser Service

This script tests the GEMS parser with the actual thames-dch.dat file.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from app.services.gems_parser_service import GEMSParserService


def main():
    """Test the GEMS parser."""

    # Path to GEMS data directory
    gems_data_dir = Path(__file__).parent / "src" / "data" / "gems"

    print("=" * 70)
    print("GEMS Parser Service Test")
    print("=" * 70)
    print(f"\nGEMS Data Directory: {gems_data_dir}")
    print(f"DCH File: {gems_data_dir / 'thames-dch.dat'}")

    # Initialize parser
    try:
        parser = GEMSParserService(gems_data_dir)
        print("\n✅ Parser initialized successfully!")
    except Exception as e:
        print(f"\n❌ Parser initialization failed: {e}")
        return 1

    # Print summary
    print("\n" + "=" * 70)
    print(parser.get_summary())
    print("=" * 70)

    # Test phase queries
    print("\n📋 Testing Phase Queries:")
    print("-" * 70)

    # Test first 5 phases
    phases = parser.get_all_phases()[:5]
    for phase in phases:
        print(f"\nPhase {phase.index + 1}: '{phase.name}'")
        print(f"  - Class code: {phase.class_code}")
        print(f"  - Number of DCs: {phase.num_dcs}")
        print(f"  - DC indices: {phase.dc_indices[:5]}{'...' if len(phase.dc_indices) > 5 else ''}")

        # Show first 3 DCs for this phase
        dcs_for_phase = parser.get_dcs_for_phase(phase.name)[:3]
        if dcs_for_phase:
            print(f"  - First {len(dcs_for_phase)} DCs:")
            for dc in dcs_for_phase:
                print(f"      {dc.index + 1}. {dc.name} (class: {dc.class_code}, M={dc.molar_mass:.6f} kg/mol)")

    # Test aq_gen phase specifically (should be first phase)
    print("\n" + "=" * 70)
    print("🔍 Detailed Test: 'aq_gen' Phase (Aqueous Solution)")
    print("=" * 70)

    aq_gen = parser.get_phase('aq_gen')
    if aq_gen:
        print(f"Phase: {aq_gen.name}")
        print(f"Index: {aq_gen.index}")
        print(f"Number of DCs: {aq_gen.num_dcs}")
        print(f"First DC index: {aq_gen.dc_indices[0]}")
        print(f"Last DC index: {aq_gen.dc_indices[-1]}")
        print(f"\nFirst 10 DCs in aq_gen:")

        dcs = parser.get_dcs_for_phase('aq_gen')[:10]
        for dc in dcs:
            print(f"  {dc.index:3d}. {dc.name:16s} (M={dc.molar_mass:.4f} kg/mol)")
    else:
        print("❌ Phase 'aq_gen' not found!")

    # Test gas_gen phase
    print("\n" + "=" * 70)
    print("🔍 Detailed Test: 'gas_gen' Phase (Gas Phase)")
    print("=" * 70)

    gas_gen = parser.get_phase('gas_gen')
    if gas_gen:
        print(f"Phase: {gas_gen.name}")
        print(f"Index: {gas_gen.index}")
        print(f"Number of DCs: {gas_gen.num_dcs}")
        print(f"DC indices: {gas_gen.dc_indices}")
        print(f"\nAll DCs in gas_gen:")

        dcs = parser.get_dcs_for_phase('gas_gen')
        for dc in dcs:
            print(f"  {dc.index:3d}. {dc.name:16s} (M={dc.molar_mass:.4f} kg/mol)")
    else:
        print("❌ Phase 'gas_gen' not found!")

    # Test solid phases
    print("\n" + "=" * 70)
    print("🔍 Testing Phase Type Filters:")
    print("=" * 70)

    aqueous_phases = parser.get_solution_phases()
    solid_phases = parser.get_solid_phases()
    gas_phases = parser.get_gas_phases()

    print(f"\nAqueous phases: {len(aqueous_phases)}")
    for p in aqueous_phases[:3]:
        print(f"  - {p.name} (class: {p.class_code}, {p.num_dcs} DCs)")

    print(f"\nSolid phases: {len(solid_phases)}")
    for p in solid_phases[:5]:
        print(f"  - {p.name} (class: {p.class_code}, {p.num_dcs} DCs)")

    print(f"\nGas phases: {len(gas_phases)}")
    for p in gas_phases[:3]:
        print(f"  - {p.name} (class: {p.class_code}, {p.num_dcs} DCs)")

    # Test validation
    print("\n" + "=" * 70)
    print("🧪 Testing Phase-DC Validation:")
    print("=" * 70)

    # Valid case
    if aq_gen:
        valid_dcs = aq_gen.dc_names[:3]
        is_valid, msg = parser.validate_phase_dc_configuration('aq_gen', valid_dcs)
        print(f"\nTest 1 - Valid DCs for aq_gen: {valid_dcs[:3]}")
        print(f"  Result: {'✅ Valid' if is_valid else '❌ Invalid'}")
        if msg:
            print(f"  Message: {msg}")

    # Invalid case
    invalid_dcs = ['FakeDC1', 'FakeDC2']
    is_valid, msg = parser.validate_phase_dc_configuration('aq_gen', invalid_dcs)
    print(f"\nTest 2 - Invalid DCs for aq_gen: {invalid_dcs}")
    print(f"  Result: {'✅ Valid' if is_valid else '❌ Invalid'}")
    if msg:
        print(f"  Message: {msg}")

    # Test cement-related solid phases
    print("\n" + "=" * 70)
    print("🔍 Cement-Related Solid Phases:")
    print("=" * 70)

    cement_phases = ['C3S', 'C2S', 'C3A', 'C4AF', 'CSH', 'Portlandite', 'ettr']
    for phase_name in cement_phases:
        phase = parser.get_phase(phase_name)
        if phase:
            print(f"\n{phase_name}:")
            print(f"  - Index: {phase.index}")
            print(f"  - Class: {phase.class_code}")
            print(f"  - DCs: {phase.num_dcs}")
            if phase.num_dcs > 0:
                dcs = parser.get_dcs_for_phase(phase_name)
                print(f"  - DC names: {[dc.name for dc in dcs]}")
        else:
            print(f"\n{phase_name}: Not found")

    print("\n" + "=" * 70)
    print("✅ All tests completed successfully!")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
