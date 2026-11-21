"""SQLAlchemy tables. Pseudonymous device IDs only; no personal data is stored."""
from datetime import datetime, timezone
from sqlalchemy import (Column, Integer, String, Float, DateTime, Boolean,
                        ForeignKey, Text, JSON, UniqueConstraint)
from sqlalchemy.orm import relationship
from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class DeviceSession(Base):
    __tablename__ = "device_sessions"
    device_id = Column(String(64), primary_key=True)
    consent_status = Column(Boolean, nullable=False, default=False)
    session_start = Column(DateTime, nullable=False, default=utcnow)
    session_end = Column(DateTime, nullable=True)
    locations = relationship("DeviceLocation", back_populates="session", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="session", cascade="all, delete-orphan")


class DeviceLocation(Base):
    __tablename__ = "device_locations"
    __table_args__ = (UniqueConstraint("device_id", "timestamp", name="uq_device_ts"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("device_sessions.device_id"), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    accuracy = Column(Float, nullable=True)
    source = Column(String(32), nullable=False, default="GNSS")
    session = relationship("DeviceSession", back_populates="locations")


class Alert(Base):
    __tablename__ = "alerts"
    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("device_sessions.device_id"), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(32), nullable=False)
    reasons = Column(JSON, nullable=False, default=list)
    status = Column(String(24), nullable=False, default="NEW")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    stationary_minutes = Column(Float, nullable=True)
    breakdown = Column(JSON, nullable=True)         # S/I/C/T/M sub-scores
    response_note = Column(Text, nullable=True)     # human reviewer note
    welfare_check_considered = Column(Boolean, nullable=True)
    session = relationship("DeviceSession", back_populates="alerts")


class GeographicalZone(Base):
    __tablename__ = "geographical_zones"
    zone_id = Column(String(64), primary_key=True)
    zone_type = Column(String(32), nullable=False)   # populated | isolated | incident_history
    name = Column(String(128), nullable=True)
    geometry = Column(JSON, nullable=False)          # GeoJSON geometry
    context_score = Column(Float, nullable=False, default=0)
