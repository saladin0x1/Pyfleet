"""
Resource monitoring types for PyFleet.
Matches: fleetspeak.monitoring and fleetspeak.server.resource protobuf definitions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


@dataclass
class AggregatedResourceUsage:
    """
    Aggregated resource usage statistics.
    Matches: fleetspeak.monitoring.AggregatedResourceUsage
    """
    mean_user_cpu_rate: float = 0.0
    max_user_cpu_rate: float = 0.0
    mean_system_cpu_rate: float = 0.0
    max_system_cpu_rate: float = 0.0
    mean_resident_memory: float = 0.0  # In bytes
    max_resident_memory: int = 0       # In bytes
    max_num_fds: int = 0               # Peak file descriptors
    mean_num_fds: float = 0.0          # Average file descriptors
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mean_user_cpu_rate": self.mean_user_cpu_rate,
            "max_user_cpu_rate": self.max_user_cpu_rate,
            "mean_system_cpu_rate": self.mean_system_cpu_rate,
            "max_system_cpu_rate": self.max_system_cpu_rate,
            "mean_resident_memory": self.mean_resident_memory,
            "max_resident_memory": self.max_resident_memory,
            "max_num_fds": self.max_num_fds,
            "mean_num_fds": self.mean_num_fds,
        }


@dataclass
class ResourceUsageData:
    """
    Full resource usage report.
    Matches: fleetspeak.monitoring.ResourceUsageData
    """
    scope: str = ""                          # Resource scope
    pid: int = 0                              # Process ID
    version: str = ""                         # Client/service version
    process_start_time: Optional[datetime] = None
    data_timestamp: Optional[datetime] = None
    resource_usage: Optional[AggregatedResourceUsage] = None
    debug_status: str = ""
    process_terminated: bool = False
    
    def __post_init__(self):
        if self.resource_usage is None:
            self.resource_usage = AggregatedResourceUsage()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.scope,
            "pid": self.pid,
            "version": self.version,
            "process_start_time": self.process_start_time.isoformat() if self.process_start_time else None,
            "data_timestamp": self.data_timestamp.isoformat() if self.data_timestamp else None,
            "resource_usage": self.resource_usage.to_dict() if self.resource_usage else None,
            "debug_status": self.debug_status,
            "process_terminated": self.process_terminated,
        }


class KillReason(Enum):
    """Reason for process termination."""
    UNSPECIFIED = 0
    HEARTBEAT_FAILURE = 1
    MEMORY_EXCEEDED = 2


@dataclass
class KillNotification:
    """
    Process termination notice.
    Matches: fleetspeak.monitoring.KillNotification
    """
    service: str = ""
    pid: int = 0
    version: str = ""
    process_start_time: Optional[datetime] = None
    killed_when: Optional[datetime] = None
    reason: KillReason = KillReason.UNSPECIFIED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service,
            "pid": self.pid,
            "version": self.version,
            "process_start_time": self.process_start_time.isoformat() if self.process_start_time else None,
            "killed_when": self.killed_when.isoformat() if self.killed_when else None,
            "reason": self.reason.name,
        }


@dataclass
class ClientResourceUsageRecord:
    """
    Server-side client resource usage record.
    Matches: fleetspeak.server.ClientResourceUsageRecord
    """
    scope: str = ""
    pid: int = 0
    process_start_time: Optional[datetime] = None
    client_timestamp: Optional[datetime] = None
    server_timestamp: Optional[datetime] = None
    process_terminated: bool = False
    mean_user_cpu_rate: float = 0.0
    max_user_cpu_rate: float = 0.0
    mean_system_cpu_rate: float = 0.0
    max_system_cpu_rate: float = 0.0
    mean_resident_memory_mib: int = 0
    max_resident_memory_mib: int = 0
    mean_num_fds: int = 0
    max_num_fds: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scope": self.scope,
            "pid": self.pid,
            "process_start_time": self.process_start_time.isoformat() if self.process_start_time else None,
            "client_timestamp": self.client_timestamp.isoformat() if self.client_timestamp else None,
            "server_timestamp": self.server_timestamp.isoformat() if self.server_timestamp else None,
            "process_terminated": self.process_terminated,
            "mean_user_cpu_rate": self.mean_user_cpu_rate,
            "max_user_cpu_rate": self.max_user_cpu_rate,
            "mean_system_cpu_rate": self.mean_system_cpu_rate,
            "max_system_cpu_rate": self.max_system_cpu_rate,
            "mean_resident_memory_mib": self.mean_resident_memory_mib,
            "max_resident_memory_mib": self.max_resident_memory_mib,
            "mean_num_fds": self.mean_num_fds,
            "max_num_fds": self.max_num_fds,
        }
