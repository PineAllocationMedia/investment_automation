"""Source-neutral V2 analytical capability contracts."""

from .contracts import (
    CAPABILITY_CONTRACT_VERSION,
    CapabilityAssessment,
    CapabilityContractError,
    CapabilityScope,
    CapabilityState,
)
from .dependencies import (
    DEPENDENCY_CONTRACT_VERSION,
    CapabilityDependency,
    DependencyContractError,
    OutputDependencyContract,
)
from .assembler import (
    ASSEMBLER_CONTRACT_VERSION,
    AssemblyContractError,
    DependencyBinding,
    DependencyResolution,
    DependencyResolutionStatus,
    OutputAvailability,
    OutputAvailabilityStatus,
    assemble_output_availability,
)

__all__ = (
    "CAPABILITY_CONTRACT_VERSION",
    "CapabilityAssessment",
    "CapabilityContractError",
    "CapabilityScope",
    "CapabilityState",
    "DEPENDENCY_CONTRACT_VERSION",
    "CapabilityDependency",
    "DependencyContractError",
    "OutputDependencyContract",
    "ASSEMBLER_CONTRACT_VERSION",
    "AssemblyContractError",
    "OutputAvailabilityStatus",
    "DependencyBinding",
    "DependencyResolutionStatus",
    "DependencyResolution",
    "OutputAvailability",
    "assemble_output_availability",
)
