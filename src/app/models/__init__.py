#!/usr/bin/env python3
"""
THAMES Models Package

Contains all SQLAlchemy models for the THAMES application.
Includes both legacy VCCTL models and new THAMES models.
"""

# Import all models to make them available
from app.models.cement import Cement, CementCreate, CementUpdate, CementResponse
from app.models.fly_ash import FlyAsh, FlyAshCreate, FlyAshUpdate, FlyAshResponse
from app.models.slag import Slag, SlagCreate, SlagUpdate, SlagResponse
from app.models.aggregate import Aggregate, AggregateCreate, AggregateUpdate, AggregateResponse
# Removed InertFiller - replaced with Filler
from app.models.filler import Filler, FillerCreate, FillerUpdate, FillerResponse
from app.models.silica_fume import SilicaFume, SilicaFumeCreate, SilicaFumeUpdate, SilicaFumeResponse
from app.models.limestone import Limestone, LimestoneCreate, LimestoneUpdate, LimestoneResponse
from app.models.psd_data import PSDData, PSDDataCreate, PSDDataUpdate, PSDDataResponse
from app.models.particle_shape_set import ParticleShapeSet, ParticleShapeSetCreate, ParticleShapeSetUpdate, ParticleShapeSetResponse
from app.models.grading import Grading, GradingCreate, GradingUpdate, GradingResponse, GradingType
from app.models.operation import Operation, Result, OperationStatus, OperationType, ResultType
from app.models.db_file import DbFile, DbFileCreate, DbFileUpdate, DbFileResponse
from app.models.aggregate_sieve import AggregateSieve, AggregateSieveCreate, AggregateSieveUpdate, AggregateSieveResponse, SieveType
from app.models.mix_design import MixDesign, MixDesignCreate, MixDesignUpdate, MixDesignResponse, MixDesignComponentData, MixDesignPropertiesData
from app.models.hydration_parameters import HydrationParameters
from app.models.hydration_parameter_set import HydrationParameterSet, HydrationParameterSetCreate, HydrationParameterSetUpdate, HydrationParameterSetResponse
from app.models.temperature_profile import TemperatureProfileDB
from app.models.elastic_moduli_operation import ElasticModuliOperation
from app.models.microstructure_operation import MicrostructureOperation
from app.models.hydration_operation import HydrationOperation
from app.models.saved_hydration_operation import SavedHydrationOperation, SavedHydrationOperationCreate, SavedHydrationOperationUpdate, SavedHydrationOperationResponse

# THAMES new models - tag-based material system
from app.models.material import Material, Tag, MaterialCreate, MaterialUpdate, MaterialResponse
from app.models.material_phase import MaterialPhase, MaterialPhaseCreate, MaterialPhaseUpdate, MaterialPhaseResponse

# Export all models for easy importing
__all__ = [
    # SQLAlchemy Models (Legacy VCCTL)
    'Cement',
    'FlyAsh',
    'Slag',
    'Aggregate',
    'InertFiller',
    'Filler',
    'SilicaFume',
    'Limestone',
    'PSDData',
    'ParticleShapeSet',
    'Grading',
    'Operation',
    'Result',
    'DbFile',
    'AggregateSieve',
    'MixDesign',
    'HydrationParameters',
    'HydrationParameterSet',
    'TemperatureProfileDB',
    'ElasticModuliOperation',
    'MicrostructureOperation',
    'HydrationOperation',
    'SavedHydrationOperation',

    # THAMES new models
    'Material',
    'Tag',
    'MaterialPhase',
    
    # Pydantic Create Models
    'CementCreate',
    'FlyAshCreate',
    'SlagCreate',
    'AggregateCreate',
    'InertFillerCreate',
    'FillerCreate',
    'SilicaFumeCreate',
    'LimestoneCreate',
    'ParticleShapeSetCreate',
    'GradingCreate',
    'DbFileCreate',
    'AggregateSieveCreate',
    'MixDesignCreate',
    'HydrationParameterSetCreate',
    'SavedHydrationOperationCreate',
    'MaterialCreate',
    'MaterialPhaseCreate',
    
    # Pydantic Update Models
    'CementUpdate',
    'FlyAshUpdate',
    'SlagUpdate',
    'AggregateUpdate',
    'InertFillerUpdate',
    'FillerUpdate',
    'SilicaFumeUpdate',
    'LimestoneUpdate',
    'ParticleShapeSetUpdate',
    'GradingUpdate',
    'DbFileUpdate',
    'AggregateSieveUpdate',
    'MixDesignUpdate',
    'HydrationParameterSetUpdate',
    'SavedHydrationOperationUpdate',
    'MaterialUpdate',
    'MaterialPhaseUpdate',
    
    # Pydantic Response Models
    'CementResponse',
    'FlyAshResponse',
    'SlagResponse',
    'AggregateResponse',
    'InertFillerResponse',
    'FillerResponse',
    'SilicaFumeResponse',
    'LimestoneResponse',
    'ParticleShapeSetResponse',
    'GradingResponse',
    'DbFileResponse',
    'AggregateSieveResponse',
    'MixDesignResponse',
    'HydrationParameterSetResponse',
    'SavedHydrationOperationResponse',
    'MaterialResponse',
    'MaterialPhaseResponse',
    
    # Enumerations
    'GradingType',
    'OperationStatus',
    'OperationType',
    'ResultType',
    'SieveType',
]


def get_all_models():
    """Get list of all SQLAlchemy model classes."""
    return [
        # Legacy VCCTL models
        Cement,
        FlyAsh,
        Slag,
        Aggregate,
        InertFiller,
        Filler,
        SilicaFume,
        Limestone,
        ParticleShapeSet,
        Grading,
        Operation,
        Result,
        DbFile,
        AggregateSieve,
        MixDesign,
        HydrationParameters,
        HydrationParameterSet,
        TemperatureProfileDB,
        ElasticModuliOperation,
        MicrostructureOperation,
        HydrationOperation,
        SavedHydrationOperation,
        # THAMES new models
        Material,
        Tag,
        MaterialPhase,
        PSDData,
    ]


def get_model_by_name(model_name: str):
    """Get model class by name."""
    model_map = {
        # Legacy VCCTL models
        'cement': Cement,
        'fly_ash': FlyAsh,
        'slag': Slag,
        'aggregate': Aggregate,
        'filler': Filler,
        'silica_fume': SilicaFume,
        'limestone': Limestone,
        'particle_shape_set': ParticleShapeSet,
        'grading': Grading,
        'operation': Operation,
        'mix_design': MixDesign,
        'hydration_parameters': HydrationParameters,
        'temperature_profile': TemperatureProfileDB,
        'elastic_moduli_operation': ElasticModuliOperation,
        'microstructure_operation': MicrostructureOperation,
        'hydration_operation': HydrationOperation,
        # THAMES new models
        'material': Material,
        'tag': Tag,
        'material_phase': MaterialPhase,
        'psd_data': PSDData,
    }
    return model_map.get(model_name.lower())


def get_create_model_by_name(model_name: str):
    """Get Pydantic create model by name."""
    create_model_map = {
        'cement': CementCreate,
        'fly_ash': FlyAshCreate,
        'slag': SlagCreate,
        'aggregate': AggregateCreate,
        'filler': FillerCreate,
        'silica_fume': SilicaFumeCreate,
        'limestone': LimestoneCreate,
        'particle_shape_set': ParticleShapeSetCreate,
        'grading': GradingCreate,
        'mix_design': MixDesignCreate,
        # THAMES new models
        'material': MaterialCreate,
        'material_phase': MaterialPhaseCreate,
        'psd_data': PSDDataCreate,
    }
    return create_model_map.get(model_name.lower())


def get_update_model_by_name(model_name: str):
    """Get Pydantic update model by name."""
    update_model_map = {
        'cement': CementUpdate,
        'fly_ash': FlyAshUpdate,
        'slag': SlagUpdate,
        'aggregate': AggregateUpdate,
        'filler': FillerUpdate,
        'silica_fume': SilicaFumeUpdate,
        'limestone': LimestoneUpdate,
        'particle_shape_set': ParticleShapeSetUpdate,
        'grading': GradingUpdate,
        'mix_design': MixDesignUpdate,
        # THAMES new models
        'material': MaterialUpdate,
        'material_phase': MaterialPhaseUpdate,
        'psd_data': PSDDataUpdate,
    }
    return update_model_map.get(model_name.lower())


def get_response_model_by_name(model_name: str):
    """Get Pydantic response model by name."""
    response_model_map = {
        'cement': CementResponse,
        'fly_ash': FlyAshResponse,
        'slag': SlagResponse,
        'aggregate': AggregateResponse,
        'filler': FillerResponse,
        'silica_fume': SilicaFumeResponse,
        'limestone': LimestoneResponse,
        'particle_shape_set': ParticleShapeSetResponse,
        'grading': GradingResponse,
        'mix_design': MixDesignResponse,
        # THAMES new models
        'material': MaterialResponse,
        'material_phase': MaterialPhaseResponse,
        'psd_data': PSDDataResponse,
    }
    return response_model_map.get(model_name.lower())