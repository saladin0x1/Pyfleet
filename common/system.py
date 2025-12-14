"""
System message types for PyFleet.
Matches: fleetspeak.system protobuf definitions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from pyfleet.common import Label


@dataclass
class MessageAckData:
    """
    Acknowledgment for received messages.
    Matches: fleetspeak.system.MessageAckData
    """
    message_ids: List[bytes] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"message_ids": [mid.hex() for mid in self.message_ids]}


@dataclass
class MessageErrorData:
    """
    Error notification for failed messages.
    Matches: fleetspeak.system.MessageErrorData
    """
    message_id: bytes = b""
    error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id.hex() if self.message_id else "",
            "error": self.error,
        }


@dataclass
class ServiceID:
    """Service identifier with signature."""
    name: str = ""
    signature: bytes = b""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "signature": self.signature.hex() if self.signature else "",
        }


@dataclass
class ClientInfoData:
    """
    Client information sent during enrollment.
    Matches: fleetspeak.system.ClientInfoData
    """
    labels: List[Label] = field(default_factory=list)
    services: List[ServiceID] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "labels": [lbl.to_dict() for lbl in self.labels],
            "services": [svc.to_dict() for svc in self.services],
        }


@dataclass
class RemoveServiceData:
    """
    Request to remove a service.
    Matches: fleetspeak.system.RemoveServiceData
    """
    name: str = ""


@dataclass
class DieRequest:
    """
    Request to terminate client.
    Matches: fleetspeak.system.DieRequest
    """
    force: bool = False


@dataclass
class RestartServiceRequest:
    """
    Request to restart a service.
    Matches: fleetspeak.system.RestartServiceRequest
    """
    name: str = ""


@dataclass
class RevokedCertificateList:
    """
    List of revoked certificates.
    Matches: fleetspeak.system.RevokedCertificateList
    """
    serials: List[bytes] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"serials": [s.hex() for s in self.serials]}
    
    def is_revoked(self, serial: bytes) -> bool:
        """Check if a certificate serial is revoked."""
        return serial in self.serials
    
    def revoke(self, serial: bytes) -> None:
        """Add a certificate serial to the revoked list."""
        if serial not in self.serials:
            self.serials.append(serial)


@dataclass
class ClientServiceConfig:
    """
    Service configuration pushed to client.
    Matches: fleetspeak.system.ClientServiceConfig
    """
    name: str = ""
    factory: str = ""
    config: bytes = b""  # Serialized service-specific config
    required_labels: List[Label] = field(default_factory=list)
    signed_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "factory": self.factory,
            "config": self.config.hex() if self.config else "",
            "required_labels": [lbl.to_dict() for lbl in self.required_labels],
            "signed_time": self.signed_time.isoformat() if self.signed_time else None,
        }


@dataclass
class ClientServiceConfigs:
    """Multiple service configurations."""
    configs: List[ClientServiceConfig] = field(default_factory=list)


@dataclass
class SignedClientServiceConfig:
    """
    Signed service configuration.
    Matches: fleetspeak.system.SignedClientServiceConfig
    """
    service_config: bytes = b""  # Serialized ClientServiceConfig
    signature: bytes = b""
