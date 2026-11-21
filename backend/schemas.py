"""SHARED API CONTRACTS. Frontend, simulation and tests all depend on these shapes."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict


class RiskLevel(str, Enum):
    NORMAL = "NORMAL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    HIGH_PRIORITY = "HIGH_PRIORITY_VERIFICATION"


class AlertStatus(str, Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    UNDER_REVIEW = "UNDER_REVIEW"
    DISMISSED = "DISMISSED"          # false positive
    RESOLVED = "RESOLVED"


class PositionSource(str, Enum):
    GNSS = "GNSS"
    NAVIC = "NAVIC"
    GPS = "GPS"
    SIMULATED = "SIMULATED"


# ---------- Inbound ----------
class LocationUpdate(BaseModel):
    device_id: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$",
                           description="Pseudonymous device/session ID (no personal data)")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timestamp: datetime
    accuracy: Optional[float] = Field(None, ge=0, description="Horizontal accuracy in metres")
    source: PositionSource = PositionSource.GNSS
    consent: bool = Field(True, description="Device owner consented to location sharing")


class AlertStatusUpdate(BaseModel):
    status: AlertStatus
    note: Optional[str] = Field(None, max_length=500)
    welfare_check_considered: Optional[bool] = None


# ---------- Outbound ----------
class RiskBreakdown(BaseModel):
    S: float; I: float; C: float; T: float; M: float
    total: float
    contributions: Dict[str, float]   # weighted points per factor


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    alert_id: int
    device_id: str
    latitude: float
    longitude: float
    risk_score: float
    risk_level: str
    reasons: List[str]
    status: str
    created_at: datetime
    stationary_minutes: Optional[float] = None
    breakdown: Optional[Dict[str, Any]] = None
    response_note: Optional[str] = None
    welfare_check_considered: Optional[bool] = None


class DeviceOut(BaseModel):
    device_id: str
    latitude: float
    longitude: float
    timestamp: datetime
    accuracy: Optional[float] = None
    source: str
    stationary_minutes: float = 0
    risk_score: float = 0
    risk_level: str = RiskLevel.NORMAL.value
    consent: bool = True
    reasons: List[str] = []
    breakdown: Optional[Dict[str, Any]] = None


class LocationResult(BaseModel):
    accepted: bool
    duplicate: bool = False
    device_id: str
    stationary_minutes: float = 0
    risk_score: float = 0
    risk_level: str = RiskLevel.NORMAL.value
    alert_id: Optional[int] = None
    message: str = ""


class StatisticsOut(BaseModel):
    participating_devices: int
    unusual_stationary_patterns: int
    pending_alerts: int
    high_priority_alerts: int
    resolved_alerts: int
    alert_trend: List[Dict[str, Any]]
    risk_distribution: Dict[str, int]
    geo_distribution: Dict[str, int] = {}
    anomaly_stats: Dict[str, Any] = {}


class WSEvent(BaseModel):
    """Envelope for every /ws/alerts message."""
    type: str   # alert_created | alert_updated | device_update | simulation_status | connectivity | reset
    data: Dict[str, Any]
