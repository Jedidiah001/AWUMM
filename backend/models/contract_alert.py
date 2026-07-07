"""
Contract Alert Model
STEP 120: Expiration Alert System
Tracks and manages contract expiration alerts
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class AlertType(Enum):
    """Types of contract alerts"""
    CRITICAL = "critical"           # ≤4 weeks remaining
    WARNING = "warning"             # 5-13 weeks remaining
    PLANNING = "planning"           # 14-26 weeks remaining
    CONTRACT_EXPIRED = "expired"    # Contract has expired


class AlertPriority(Enum):
    """Alert priority levels"""
    URGENT = 1      # Immediate action required (critical/expired)
    HIGH = 2        # Action needed soon (warning)
    MEDIUM = 3      # Plan ahead (planning)
    LOW = 4         # Informational


@dataclass
class ContractAlert:
    """
    Represents a contract expiration alert.
    
    Alerts are generated automatically when contracts approach expiration
    and can be acknowledged/dismissed by the user.
    """
    
    alert_id: str
    wrestler_id: str
    wrestler_name: str
    brand: str
    alert_type: AlertType
    priority: AlertPriority
    weeks_remaining: int
    current_salary: int
    market_value: int
    morale: int
    resign_probability: str
    created_week: int
    created_year: int
    acknowledged: bool = False
    acknowledged_week: Optional[int] = None
    acknowledged_year: Optional[int] = None
    dismissed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for JSON serialization"""
        return {
            'alert_id': self.alert_id,
            'wrestler_id': self.wrestler_id,
            'wrestler_name': self.wrestler_name,
            'brand': self.brand,
            'alert_type': self.alert_type.value,
            'priority': self.priority.value,
            'weeks_remaining': self.weeks_remaining,
            'current_salary': self.current_salary,
            'market_value': self.market_value,
            'morale': self.morale,
            'resign_probability': self.resign_probability,
            'created_week': self.created_week,
            'created_year': self.created_year,
            'acknowledged': self.acknowledged,
            'acknowledged_week': self.acknowledged_week,
            'acknowledged_year': self.acknowledged_year,
            'dismissed': self.dismissed
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ContractAlert':
        """Create alert from dictionary"""
        return ContractAlert(
            alert_id=data['alert_id'],
            wrestler_id=data['wrestler_id'],
            wrestler_name=data['wrestler_name'],
            brand=data['brand'],
            alert_type=AlertType(data['alert_type']),
            priority=AlertPriority(data['priority']),
            weeks_remaining=data['weeks_remaining'],
            current_salary=data['current_salary'],
            market_value=data['market_value'],
            morale=data['morale'],
            resign_probability=data['resign_probability'],
            created_week=data['created_week'],
            created_year=data['created_year'],
            acknowledged=data.get('acknowledged', False),
            acknowledged_week=data.get('acknowledged_week'),
            acknowledged_year=data.get('acknowledged_year'),
            dismissed=data.get('dismissed', False)
        )
    
    def acknowledge(self, current_week: int, current_year: int):
        """Mark alert as acknowledged"""
        self.acknowledged = True
        self.acknowledged_week = current_week
        self.acknowledged_year = current_year
    
    def dismiss(self):
        """Dismiss alert (remove from active view)"""
        self.dismissed = True
    
    @property
    def is_active(self) -> bool:
        """Check if alert is still active (not dismissed)"""
        return not self.dismissed
    
    @property
    def requires_action(self) -> bool:
        """Check if alert requires immediate action"""
        return self.priority in [AlertPriority.URGENT, AlertPriority.HIGH] and not self.acknowledged


class ContractAlertManager:
    """
    Manages contract expiration alerts.
    
    Generates, tracks, and manages alerts for contract expirations.
    """
    
    def __init__(self):
        self.alerts: Dict[str, ContractAlert] = {}
        self.next_alert_id = 1
    
    def generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        alert_id = f"alert_{self.next_alert_id:05d}"
        self.next_alert_id += 1
        return alert_id
    
    def create_alert(
        self,
        wrestler_id: str,
        wrestler_name: str,
        brand: str,
        weeks_remaining: int,
        current_salary: int,
        market_value: int,
        morale: int,
        resign_probability: str,
        current_week: int,
        current_year: int
    ) -> ContractAlert:
        """
        Create a new contract expiration alert.
        
        Determines alert type and priority based on weeks remaining.
        """
        # Determine alert type and priority
        if weeks_remaining == 0:
            alert_type = AlertType.CONTRACT_EXPIRED
            priority = AlertPriority.URGENT
        elif weeks_remaining <= 4:
            alert_type = AlertType.CRITICAL
            priority = AlertPriority.URGENT
        elif weeks_remaining <= 13:
            alert_type = AlertType.WARNING
            priority = AlertPriority.HIGH
        elif weeks_remaining <= 26:
            alert_type = AlertType.PLANNING
            priority = AlertPriority.MEDIUM
        else:
            # No alert needed for contracts > 26 weeks
            return None
        
        # Check if alert already exists for this wrestler
        existing_alert = self.get_alert_by_wrestler(wrestler_id)
        if existing_alert and existing_alert.is_active:
            # Update existing alert if status changed
            if existing_alert.alert_type != alert_type:
                existing_alert.alert_type = alert_type
                existing_alert.priority = priority
                existing_alert.weeks_remaining = weeks_remaining
                existing_alert.morale = morale
                existing_alert.resign_probability = resign_probability
                # Reset acknowledgment if status worsened
                if priority.value < existing_alert.priority.value:
                    existing_alert.acknowledged = False
            return existing_alert
        
        # Create new alert
        alert_id = self.generate_alert_id()
        alert = ContractAlert(
            alert_id=alert_id,
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            brand=brand,
            alert_type=alert_type,
            priority=priority,
            weeks_remaining=weeks_remaining,
            current_salary=current_salary,
            market_value=market_value,
            morale=morale,
            resign_probability=resign_probability,
            created_week=current_week,
            created_year=current_year
        )
        
        self.alerts[alert_id] = alert
        return alert
    
    def get_alert_by_wrestler(self, wrestler_id: str) -> Optional[ContractAlert]:
        """Get active alert for a specific wrestler"""
        for alert in self.alerts.values():
            if alert.wrestler_id == wrestler_id and alert.is_active:
                return alert
        return None
    
    def get_active_alerts(self) -> list:
        """Get all active (not dismissed) alerts"""
        return [a for a in self.alerts.values() if a.is_active]
    
    def get_unacknowledged_alerts(self) -> list:
        """Get all active, unacknowledged alerts"""
        return [a for a in self.alerts.values() if a.is_active and not a.acknowledged]
    
    def get_alerts_by_priority(self, priority: AlertPriority) -> list:
        """Get active alerts of specific priority"""
        return [a for a in self.alerts.values() if a.is_active and a.priority == priority]
    
    def get_alerts_by_type(self, alert_type: AlertType) -> list:
        """Get active alerts of specific type"""
        return [a for a in self.alerts.values() if a.is_active and a.alert_type == alert_type]
    
    def acknowledge_alert(self, alert_id: str, current_week: int, current_year: int) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].acknowledge(current_week, current_year)
            return True
        return False
    
    def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss an alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].dismiss()
            return True
        return False
    
    def acknowledge_all(self, current_week: int, current_year: int):
        """Acknowledge all active alerts"""
        for alert in self.get_active_alerts():
            alert.acknowledge(current_week, current_year)
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alerts by type and priority"""
        active = self.get_active_alerts()
        unack = self.get_unacknowledged_alerts()
        
        return {
            'total_active': len(active),
            'total_unacknowledged': len(unack),
            'by_priority': {
                'urgent': len(self.get_alerts_by_priority(AlertPriority.URGENT)),
                'high': len(self.get_alerts_by_priority(AlertPriority.HIGH)),
                'medium': len(self.get_alerts_by_priority(AlertPriority.MEDIUM)),
                'low': len(self.get_alerts_by_priority(AlertPriority.LOW))
            },
            'by_type': {
                'expired': len(self.get_alerts_by_type(AlertType.CONTRACT_EXPIRED)),
                'critical': len(self.get_alerts_by_type(AlertType.CRITICAL)),
                'warning': len(self.get_alerts_by_type(AlertType.WARNING)),
                'planning': len(self.get_alerts_by_type(AlertType.PLANNING))
            },
            'requires_action': len([a for a in active if a.requires_action])
        }
    
    def cleanup_expired_alerts(self, current_week: int, current_year: int, weeks_threshold: int = 52):
        """Remove old dismissed or acknowledged alerts"""
        to_remove = []
        for alert_id, alert in self.alerts.items():
            if alert.dismissed:
                # Calculate weeks since creation
                weeks_since_creation = (current_year - alert.created_year) * 52 + (current_week - alert.created_week)
                if weeks_since_creation > weeks_threshold:
                    to_remove.append(alert_id)
        
        for alert_id in to_remove:
            del self.alerts[alert_id]
        
        return len(to_remove)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize alert manager state"""
        return {
            'alerts': {alert_id: alert.to_dict() for alert_id, alert in self.alerts.items()},
            'next_alert_id': self.next_alert_id
        }
    
    def load_from_dict(self, data: Dict[str, Any]):
        """Load alert manager state from dictionary"""
        self.alerts = {
            alert_id: ContractAlert.from_dict(alert_data)
            for alert_id, alert_data in data.get('alerts', {}).items()
        }
        self.next_alert_id = data.get('next_alert_id', 1)


# Global alert manager instance
contract_alert_manager = ContractAlertManager()