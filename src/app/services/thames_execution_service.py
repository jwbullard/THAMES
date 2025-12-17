#!/usr/bin/env python3
"""
THAMES Execution Service

Manages execution of THAMES-Hydration simulations including:
- Process lifecycle management (start, monitor, cancel, cleanup)
- Progress monitoring via JSON progress files
- Real-time output capture and logging
- Integration with HydrationInputService for input generation
"""

import os
import sys
import json
import time
import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from app.models.operation import Operation, OperationStatus, OperationType
from app.services.hydration_input_service import (
    HydrationInputService,
    HydrationInputConfig,
    MaterialPhaseData,
    get_hydration_input_service,
)
from app.database.service import DatabaseService


class THAMESSimulationStatus(str, Enum):
    """Status of THAMES hydration simulation execution."""
    PREPARING = "PREPARING"
    GENERATING_INPUTS = "GENERATING_INPUTS"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


@dataclass
class THAMESProgress:
    """Container for THAMES simulation progress information."""

    # Current simulation state
    current_time: float = 0.0  # Current simulation time (days)
    final_time: float = 28.0  # Target end time (days)
    iteration: int = 0

    # Phase volume fractions (from THAMES output)
    phase_volumes: Dict[str, float] = None

    # Progress metrics
    percent_complete: float = 0.0
    estimated_time_remaining: float = 0.0  # Wall-clock hours

    # Timestamps
    last_update: datetime = None
    start_time: datetime = None

    def __post_init__(self):
        if self.phase_volumes is None:
            self.phase_volumes = {}
        if self.last_update is None:
            self.last_update = datetime.now()
        if self.start_time is None:
            self.start_time = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert progress to dictionary format."""
        return {
            'current_time': self.current_time,
            'final_time': self.final_time,
            'iteration': self.iteration,
            'phase_volumes': self.phase_volumes,
            'percent_complete': self.percent_complete,
            'estimated_time_remaining': self.estimated_time_remaining,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
        }


class THAMESExecutionService:
    """
    Service for executing and monitoring THAMES-Hydration simulations.

    This service handles:
    1. Input file generation via HydrationInputService
    2. THAMES-Hydration process execution
    3. Progress monitoring
    4. Operation status management
    """

    def __init__(
        self,
        database_service: DatabaseService,
        hydration_input_service: Optional[HydrationInputService] = None,
    ):
        """
        Initialize the THAMES execution service.

        Args:
            database_service: Database service for operation tracking
            hydration_input_service: Service for generating input files
        """
        self.database_service = database_service
        self.hydration_input_service = (hydration_input_service or
                                         get_hydration_input_service())
        self.logger = logging.getLogger('THAMES.ExecutionService')

        # Process management
        self.active_simulations: Dict[str, Dict[str, Any]] = {}
        self.progress_callbacks: Dict[str, List[Callable]] = {}

        # Get directories service
        from app.services.service_container import get_service_container
        service_container = get_service_container()
        self.operations_dir = service_container.directories_service.get_operations_path()

        # Find THAMES-Hydration executable
        self._locate_thames_executable()

        # Configuration
        self.progress_update_interval = 5.0  # seconds

    def _locate_thames_executable(self):
        """Locate the THAMES-Hydration executable."""
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running in PyInstaller bundle
            project_root = Path(sys._MEIPASS)
        else:
            # Running in development
            project_root = Path(__file__).parent.parent.parent.parent

        # Platform-specific executable name
        exe_name = 'thames.exe' if sys.platform == 'win32' else 'thames'

        # Primary location: top-level bin/ folder
        self.thames_binary = project_root / "bin" / exe_name

        # Alternative locations to check (fallbacks)
        alt_paths = [
            project_root / "backend" / "bin" / exe_name,
            project_root / "backend" / "thames-hydration" / "bin" / exe_name,
        ]

        if not self.thames_binary.exists():
            for alt_path in alt_paths:
                if alt_path.exists():
                    self.thames_binary = alt_path
                    break

        self.logger.info(f"THAMES executable path: {self.thames_binary}")

    def start_simulation(
        self,
        operation_name: str,
        material_phases: List[MaterialPhaseData],
        config: HydrationInputConfig,
        microstructure_path: Path,
        source_microstructure_operation: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Start a THAMES hydration simulation.

        Args:
            operation_name: Name of the operation
            material_phases: Material phase data from mix design
            config: Hydration input configuration
            microstructure_path: Path to the microstructure file
            source_microstructure_operation: Name of the source microstructure operation (for lineage tracking)
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (success, error_messages)
        """
        # Store source operation name for use when creating the operation record
        self._current_source_operation = source_microstructure_operation
        errors = []

        try:
            self.logger.info(f"Starting THAMES simulation for: {operation_name}")

            # Check if simulation already running
            if operation_name in self.active_simulations:
                errors.append(f"Simulation already running: {operation_name}")
                return False, errors

            # Check THAMES executable exists
            if not self.thames_binary.exists():
                errors.append(f"THAMES executable not found: {self.thames_binary}")
                return False, errors

            # Check microstructure file exists
            if not microstructure_path.exists():
                errors.append(f"Microstructure file not found: {microstructure_path}")
                return False, errors

            # Create operation directory
            operation_dir = self.operations_dir / operation_name
            operation_dir.mkdir(parents=True, exist_ok=True)

            # Update status to PREPARING
            self._update_operation_status(operation_name, OperationStatus.RUNNING)

            # Generate input files
            self.logger.info("Generating THAMES input files...")
            success, gen_errors, generated_files = self.hydration_input_service.generate_all_inputs(
                output_dir=operation_dir,
                operation_name=operation_name,
                material_phases=material_phases,
                config=config,
                microstructure_file=microstructure_path,
            )

            if not success:
                errors.extend(gen_errors)
                self._update_operation_status(operation_name, OperationStatus.ERROR)
                return False, errors

            # Copy or link microstructure file to operation directory
            micro_dest = operation_dir / microstructure_path.name
            if not micro_dest.exists():
                import shutil
                shutil.copy2(microstructure_path, micro_dest)

            # Also copy the pimg file (phase ID mapping) for elastic calculations
            pimg_path = microstructure_path.with_suffix('.pimg')
            if pimg_path.exists():
                pimg_dest = operation_dir / pimg_path.name
                if not pimg_dest.exists():
                    import shutil
                    shutil.copy2(pimg_path, pimg_dest)
                    self.logger.info(f"Copied pimg file to hydration directory: {pimg_dest}")
            else:
                self.logger.warning(f"Pimg file not found at {pimg_path} - elastic calculations may fail")

            # Start THAMES process
            simulation_info = self._start_thames_process(
                operation_name,
                operation_dir,
                generated_files.get('simparams'),
                micro_dest,
                config.final_time,
                config,  # Pass config for runtime options (verbose, xyz, etc.)
            )

            if not simulation_info:
                errors.append("Failed to start THAMES process")
                self._update_operation_status(operation_name, OperationStatus.ERROR)
                return False, errors

            # Register simulation
            self.active_simulations[operation_name] = simulation_info
            if progress_callback:
                self._add_progress_callback(operation_name, progress_callback)

            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitor_simulation,
                args=(operation_name,),
                daemon=True
            )
            monitor_thread.start()
            simulation_info['monitor_thread'] = monitor_thread

            self.logger.info(f"THAMES simulation started: {operation_name}")
            return True, errors

        except Exception as e:
            self.logger.error(f"Failed to start THAMES simulation: {e}")
            errors.append(f"Exception: {str(e)}")
            self._update_operation_status(operation_name, OperationStatus.ERROR)
            return False, errors

    def _start_thames_process(
        self,
        operation_name: str,
        operation_dir: Path,
        simparams_path: Path,
        microstructure_path: Path,
        final_time: float,
        config: Optional[HydrationInputConfig] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Start the THAMES-Hydration process.

        Args:
            operation_name: Operation name
            operation_dir: Working directory
            simparams_path: Path to simparams.json
            microstructure_path: Path to microstructure file
            final_time: Target simulation time (days)
            config: Hydration input configuration with runtime options

        Returns:
            Simulation info dict or None if failed
        """
        try:
            # Prepare log files
            stdout_log = operation_dir / f"{operation_name}_stdout.log"
            stderr_log = operation_dir / f"{operation_name}_stderr.log"

            # THAMES reads from stdin (input.in contains all interactive inputs)
            # Format: thames [options] < input.in
            # Options:
            #   -o <folder>  Output folder (default "Result")
            #   -v           Verbose output
            #   -s           Suppress warnings
            #   -x           Create 3D visualization files for Ovito
            input_in_path = operation_dir / "input.in"
            if not input_in_path.exists():
                self.logger.error(f"input.in not found: {input_in_path}")
                return None

            # Build command with options from config
            output_folder = "Result"
            if config and config.output_folder:
                output_folder = config.output_folder

            cmd = [
                str(self.thames_binary),
                "-o", output_folder,
            ]

            # Add optional flags based on config
            if config:
                if config.verbose:
                    cmd.append("-v")
                if config.suppress_warnings:
                    cmd.append("-s")
                if config.create_xyz_files:
                    cmd.append("-x")

            self.logger.info(f"Starting THAMES: {' '.join(cmd)} < input.in")
            self.logger.info(f"Working directory: {operation_dir}")

            # Open input.in for stdin
            stdin_file = open(input_in_path, 'r')

            # Start process with stdin from input.in
            popen_kwargs = {
                'cwd': str(operation_dir),
                'stdin': stdin_file,
                'stdout': open(stdout_log, 'w'),
                'stderr': open(stderr_log, 'w'),
                'text': True,
            }

            # Hide console window on Windows
            if sys.platform == 'win32':
                popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(cmd, **popen_kwargs)

            # Create progress tracker
            progress = THAMESProgress(
                final_time=final_time,
                start_time=datetime.now(),
            )

            simulation_info = {
                'process': process,
                'status': THAMESSimulationStatus.STARTING,
                'progress': progress,
                'operation_dir': operation_dir,
                'stdout_log': stdout_log,
                'stderr_log': stderr_log,
                'simparams_path': simparams_path,
                'microstructure_path': microstructure_path,
                'stdin_file': stdin_file,  # Keep handle to close later
            }

            return simulation_info

        except Exception as e:
            self.logger.error(f"Failed to start THAMES process: {e}")
            # Clean up stdin file if opened
            if 'stdin_file' in locals():
                stdin_file.close()
            return None

    def _monitor_simulation(self, operation_name: str):
        """Monitor a running THAMES simulation in background thread."""
        self.logger.info(f"Starting simulation monitoring: {operation_name}")

        try:
            simulation_info = self.active_simulations[operation_name]
            process = simulation_info['process']

            while operation_name in self.active_simulations:
                # Check if process is still running
                return_code = process.poll()

                if return_code is not None:
                    # Process finished
                    if return_code == 0:
                        simulation_info['status'] = THAMESSimulationStatus.COMPLETED
                        self._update_operation_status(operation_name, OperationStatus.COMPLETED)
                        self.logger.info(f"THAMES simulation completed: {operation_name}")
                    else:
                        simulation_info['status'] = THAMESSimulationStatus.ERROR
                        self._update_operation_status(operation_name, OperationStatus.ERROR)
                        self.logger.error(f"THAMES simulation failed (exit {return_code}): {operation_name}")

                    # Final progress update
                    simulation_info['progress'].percent_complete = 100.0
                    self._notify_progress_callbacks(operation_name)

                    # Cleanup
                    self._cleanup_simulation(operation_name)
                    break

                # Update progress
                simulation_info['status'] = THAMESSimulationStatus.RUNNING
                self._update_progress(operation_name)
                self._notify_progress_callbacks(operation_name)

                # Sleep before next check
                time.sleep(self.progress_update_interval)

        except Exception as e:
            self.logger.error(f"Error monitoring simulation: {e}")
            if operation_name in self.active_simulations:
                self.active_simulations[operation_name]['status'] = THAMESSimulationStatus.ERROR
                self._update_operation_status(operation_name, OperationStatus.ERROR)

        self.logger.info(f"Monitoring ended: {operation_name}")

    def _update_progress(self, operation_name: str):
        """Update progress information for a simulation."""
        try:
            simulation_info = self.active_simulations[operation_name]
            progress = simulation_info['progress']
            operation_dir = simulation_info['operation_dir']

            # Try to read THAMES progress file
            progress_file = operation_dir / "thames_progress.json"
            if progress_file.exists():
                self._parse_thames_progress(progress, progress_file)
            else:
                # Fallback: estimate from elapsed time
                self._estimate_progress_from_time(progress, simulation_info)

            progress.last_update = datetime.now()

        except Exception as e:
            self.logger.error(f"Error updating progress: {e}")

    def _parse_thames_progress(self, progress: THAMESProgress, progress_file: Path):
        """Parse THAMES progress from JSON file."""
        try:
            with open(progress_file, 'r') as f:
                data = json.load(f)

            progress.current_time = data.get('current_time', 0.0)
            progress.iteration = data.get('iteration', 0)
            progress.phase_volumes = data.get('phase_volumes', {})

            # Calculate percent complete
            if progress.final_time > 0:
                progress.percent_complete = min(
                    (progress.current_time / progress.final_time) * 100.0,
                    99.0  # Cap at 99% until actually complete
                )

            # Estimate remaining time
            elapsed = (datetime.now() - progress.start_time).total_seconds()
            if progress.percent_complete > 0 and elapsed > 10:
                total_estimated = elapsed * (100.0 / progress.percent_complete)
                remaining = max(total_estimated - elapsed, 0)
                progress.estimated_time_remaining = remaining / 3600.0

        except Exception as e:
            self.logger.debug(f"Could not parse THAMES progress: {e}")

    def _estimate_progress_from_time(self, progress: THAMESProgress, simulation_info: Dict):
        """Estimate progress based on elapsed wall-clock time."""
        elapsed = (datetime.now() - progress.start_time).total_seconds()

        # Rough estimate: 1 day of simulation time per 2 minutes of real time
        # This is a placeholder - actual speed depends on system size and complexity
        estimated_days_per_minute = 0.5
        estimated_current_time = (elapsed / 60.0) * estimated_days_per_minute

        progress.current_time = min(estimated_current_time, progress.final_time * 0.99)

        if progress.final_time > 0:
            progress.percent_complete = min(
                (progress.current_time / progress.final_time) * 100.0,
                99.0
            )

    def cancel_simulation(self, operation_name: str) -> bool:
        """Cancel a running THAMES simulation."""
        try:
            if operation_name not in self.active_simulations:
                self.logger.warning(f"No active simulation: {operation_name}")
                return False

            simulation_info = self.active_simulations[operation_name]
            process = simulation_info.get('process')

            if process and process.poll() is None:
                self.logger.info(f"Terminating THAMES simulation: {operation_name}")
                process.terminate()

                time.sleep(2.0)

                if process.poll() is None:
                    process.kill()
                    self.logger.warning(f"Force killed: {operation_name}")

            simulation_info['status'] = THAMESSimulationStatus.CANCELLED
            self._update_operation_status(operation_name, OperationStatus.CANCELLED)
            self._cleanup_simulation(operation_name)

            return True

        except Exception as e:
            self.logger.error(f"Failed to cancel simulation: {e}")
            return False

    def get_simulation_status(self, operation_name: str) -> Optional[THAMESSimulationStatus]:
        """Get the current status of a simulation."""
        if operation_name in self.active_simulations:
            return self.active_simulations[operation_name].get('status')
        return None

    def get_simulation_progress(self, operation_name: str) -> Optional[THAMESProgress]:
        """Get the current progress of a simulation."""
        if operation_name in self.active_simulations:
            return self.active_simulations[operation_name].get('progress')
        return None

    def is_simulation_active(self, operation_name: str) -> bool:
        """Check if a simulation is currently active."""
        return operation_name in self.active_simulations

    def get_active_simulations(self) -> List[str]:
        """Get list of currently active simulation names."""
        return list(self.active_simulations.keys())

    def _add_progress_callback(self, operation_name: str, callback: Callable):
        """Add a progress callback for an operation."""
        if operation_name not in self.progress_callbacks:
            self.progress_callbacks[operation_name] = []
        self.progress_callbacks[operation_name].append(callback)

    def _notify_progress_callbacks(self, operation_name: str):
        """Notify all registered progress callbacks."""
        if operation_name in self.progress_callbacks:
            simulation_info = self.active_simulations.get(operation_name)
            if simulation_info:
                progress = simulation_info.get('progress')
                for callback in self.progress_callbacks[operation_name]:
                    try:
                        callback(operation_name, progress)
                    except Exception as e:
                        self.logger.error(f"Progress callback error: {e}")

    def _update_operation_status(self, operation_name: str, status: OperationStatus):
        """Update operation status in database."""
        try:
            with self.database_service.get_session() as session:
                operation = session.query(Operation).filter_by(name=operation_name).first()

                if not operation:
                    self.logger.info(f"Creating operation: {operation_name}")

                    # Look up parent microstructure operation ID if source name was provided
                    parent_operation_id = None
                    if hasattr(self, '_current_source_operation') and self._current_source_operation:
                        parent_op = session.query(Operation).filter_by(
                            name=self._current_source_operation
                        ).first()
                        if parent_op:
                            parent_operation_id = parent_op.id
                            self.logger.info(f"Linking to parent operation: {self._current_source_operation} (id={parent_operation_id})")
                        else:
                            self.logger.warning(f"Parent operation not found: {self._current_source_operation}")

                    operation = Operation(
                        name=operation_name,
                        operation_type=OperationType.HYDRATION.value,
                        notes=f"THAMES hydration simulation",
                        parent_operation_id=parent_operation_id
                    )
                    session.add(operation)
                    session.flush()

                operation.status = status.value
                if status == OperationStatus.RUNNING:
                    operation.mark_started()
                elif status == OperationStatus.COMPLETED:
                    operation.mark_completed()
                elif status == OperationStatus.ERROR:
                    operation.mark_error("THAMES simulation failed")
                elif status == OperationStatus.CANCELLED:
                    operation.mark_cancelled()

                session.commit()

        except Exception as e:
            self.logger.error(f"Error updating operation status: {e}")

    def _cleanup_simulation(self, operation_name: str):
        """Clean up simulation resources."""
        try:
            if operation_name in self.active_simulations:
                simulation_info = self.active_simulations[operation_name]

                # Close file handles
                process = simulation_info.get('process')
                if process:
                    if hasattr(process.stdout, 'close'):
                        try:
                            process.stdout.close()
                        except:
                            pass
                    if hasattr(process.stderr, 'close'):
                        try:
                            process.stderr.close()
                        except:
                            pass

                # Close stdin file (input.in)
                stdin_file = simulation_info.get('stdin_file')
                if stdin_file:
                    try:
                        stdin_file.close()
                    except:
                        pass

                del self.active_simulations[operation_name]

                if operation_name in self.progress_callbacks:
                    del self.progress_callbacks[operation_name]

                self.logger.info(f"Cleaned up: {operation_name}")

        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")


# =============================================================================
# Module-level singleton
# =============================================================================

_thames_execution_service: Optional[THAMESExecutionService] = None


def get_thames_execution_service(
    database_service: Optional[DatabaseService] = None
) -> THAMESExecutionService:
    """
    Get the THAMESExecutionService singleton.

    Args:
        database_service: Database service (required on first call)

    Returns:
        THAMESExecutionService instance
    """
    global _thames_execution_service

    if _thames_execution_service is None:
        if database_service is None:
            from app.services.service_container import get_service_container
            database_service = get_service_container().database_service

        _thames_execution_service = THAMESExecutionService(database_service)

    return _thames_execution_service
