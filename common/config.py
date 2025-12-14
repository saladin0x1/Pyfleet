"""
Configuration types for PyFleet.
Matches: fleetspeak configuration-related protobuf definitions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from pyfleet.common import Label


class CompressionAlgorithm(Enum):
    """Compression algorithm for messages."""
    COMPRESSION_NONE = 0
    COMPRESSION_DEFLATE = 1


@dataclass
class StdParams:
    """
    Stdout/stderr handling configuration.
    Matches: fleetspeak.daemonservice.Config.StdParams
    """
    service_name: str = ""
    flush_bytes: int = 0
    flush_time_seconds: int = 0


@dataclass
class CommunicatorConfig:
    """
    Client communication settings.
    Matches: fleetspeak.client.CommunicatorConfig
    """
    max_poll_delay_seconds: int = 60
    max_buffer_delay_seconds: int = 5
    min_failure_delay_seconds: int = 5
    failure_suicide_time_seconds: int = 3600
    compression: CompressionAlgorithm = CompressionAlgorithm.COMPRESSION_NONE
    prefer_http2: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_poll_delay_seconds": self.max_poll_delay_seconds,
            "max_buffer_delay_seconds": self.max_buffer_delay_seconds,
            "min_failure_delay_seconds": self.min_failure_delay_seconds,
            "failure_suicide_time_seconds": self.failure_suicide_time_seconds,
            "compression": self.compression.name,
            "prefer_http2": self.prefer_http2,
        }


@dataclass
class ClientState:
    """
    Persistent client state.
    Matches: fleetspeak.client.ClientState
    """
    client_key: bytes = b""
    sequencing_nonce: int = 0
    revoked_cert_serials: List[bytes] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_key": self.client_key.hex() if self.client_key else "",
            "sequencing_nonce": self.sequencing_nonce,
            "revoked_cert_serials": [s.hex() for s in self.revoked_cert_serials],
        }


@dataclass
class DaemonServiceConfig:
    """
    Configuration for daemon-managed services.
    Matches: fleetspeak.daemonservice.Config
    """
    argv: List[str] = field(default_factory=list)
    inactivity_timeout: Optional[timedelta] = None
    lazy_start: bool = False
    disable_resource_monitoring: bool = False
    resource_monitoring_sample_size: int = 20
    resource_monitoring_sample_period: Optional[timedelta] = None
    memory_limit: int = 0  # In bytes
    monitor_heartbeats: bool = False
    heartbeat_unresponsive_grace_period: Optional[timedelta] = None
    heartbeat_unresponsive_kill_period: Optional[timedelta] = None
    std_params: Optional[StdParams] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "argv": self.argv,
            "inactivity_timeout_seconds": self.inactivity_timeout.total_seconds() if self.inactivity_timeout else None,
            "lazy_start": self.lazy_start,
            "disable_resource_monitoring": self.disable_resource_monitoring,
            "resource_monitoring_sample_size": self.resource_monitoring_sample_size,
            "memory_limit": self.memory_limit,
            "monitor_heartbeats": self.monitor_heartbeats,
        }


@dataclass
class ServiceConfig:
    """
    Server service configuration.
    Matches: fleetspeak.server.ServiceConfig
    """
    name: str = ""
    factory: str = ""  # Factory type (e.g., "GRPC")
    max_parallelism: int = 10
    config: bytes = b""  # Service-specific config
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "factory": self.factory,
            "max_parallelism": self.max_parallelism,
            "config": self.config.hex() if self.config else "",
        }


@dataclass
class ServerComponentsConfig:
    """
    Server components configuration.
    Matches: fleetspeak.components.Config (partial)
    """
    configuration_name: str = ""
    trusted_cert_file: str = ""
    trusted_cert_key_file: str = ""
    server_cert_file: str = ""
    server_cert_key_file: str = ""
    public_host_port: List[str] = field(default_factory=list)
    server_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "configuration_name": self.configuration_name,
            "trusted_cert_file": self.trusted_cert_file,
            "server_cert_file": self.server_cert_file,
            "public_host_port": self.public_host_port,
            "server_name": self.server_name,
        }


@dataclass
class InputMessage:
    """
    Input to send to a process.
    Matches: fleetspeak.stdinservice.InputMessage
    """
    input: bytes = b""
    args: List[str] = field(default_factory=list)


@dataclass
class OutputMessage:
    """
    Output from a process.
    Matches: fleetspeak.stdinservice.OutputMessage
    """
    stdout: bytes = b""
    stderr: bytes = b""
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stdout": self.stdout.decode(errors="replace") if self.stdout else "",
            "stderr": self.stderr.decode(errors="replace") if self.stderr else "",
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class StartupData:
    """
    Sent by daemon service on startup.
    Matches: fleetspeak.channel.StartupData
    """
    pid: int = 0
    version: str = ""
