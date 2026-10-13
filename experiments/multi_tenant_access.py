"""
Multi-Tenant Access Control for Blockchain Caching

Implements access control mechanisms for competing parties in agricultural supply chains:
1. Per-tenant cache isolation
2. Role-based access control (RBAC)
3. Differential visibility (what each party can see)
4. Audit logging
5. Encryption for sensitive data

This addresses reviewer concerns about access control in multi-tenant settings.
"""

import hashlib
import hmac
import json
import time
import secrets
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Callable
from enum import Enum
from collections import defaultdict
import base64


class Role(Enum):
    """Roles in the agricultural supply chain."""
    FARMER = "farmer"
    PROCESSOR = "processor"
    DISTRIBUTOR = "distributor"
    RETAILER = "retailer"
    REGULATOR = "regulator"
    CONSUMER = "consumer"
    ADMIN = "admin"


class Permission(Enum):
    """Permissions for data access."""
    READ_OWN = "read_own"           # Read own data
    READ_UPSTREAM = "read_upstream"  # Read data from upstream partners
    READ_DOWNSTREAM = "read_downstream"  # Read data from downstream partners
    READ_ALL = "read_all"           # Read all data (regulators)
    WRITE_OWN = "write_own"         # Write own data
    READ_AGGREGATES = "read_aggregates"  # Read aggregate statistics
    READ_SENSITIVE = "read_sensitive"    # Read sensitive fields (pricing, etc.)


# Role-Permission mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.FARMER: {
        Permission.READ_OWN,
        Permission.WRITE_OWN,
        Permission.READ_DOWNSTREAM,
        Permission.READ_AGGREGATES
    },
    Role.PROCESSOR: {
        Permission.READ_OWN,
        Permission.WRITE_OWN,
        Permission.READ_UPSTREAM,
        Permission.READ_DOWNSTREAM,
        Permission.READ_AGGREGATES
    },
    Role.DISTRIBUTOR: {
        Permission.READ_OWN,
        Permission.WRITE_OWN,
        Permission.READ_UPSTREAM,
        Permission.READ_DOWNSTREAM,
        Permission.READ_AGGREGATES
    },
    Role.RETAILER: {
        Permission.READ_OWN,
        Permission.WRITE_OWN,
        Permission.READ_UPSTREAM,
        Permission.READ_AGGREGATES
    },
    Role.REGULATOR: {
        Permission.READ_ALL,
        Permission.READ_SENSITIVE,
        Permission.READ_AGGREGATES
    },
    Role.CONSUMER: {
        Permission.READ_AGGREGATES
    },
    Role.ADMIN: {
        Permission.READ_ALL,
        Permission.WRITE_OWN,
        Permission.READ_SENSITIVE,
        Permission.READ_AGGREGATES
    }
}


@dataclass
class Tenant:
    """Represents a tenant (organization) in the system."""
    tenant_id: str
    name: str
    role: Role
    encryption_key: str = field(default_factory=lambda: secrets.token_hex(32))
    api_key: str = field(default_factory=lambda: secrets.token_urlsafe(32))

    # Supply chain relationships
    upstream_partners: Set[str] = field(default_factory=set)
    downstream_partners: Set[str] = field(default_factory=set)

    # Data ownership
    owned_products: Set[str] = field(default_factory=set)
    owned_farms: Set[str] = field(default_factory=set)

    def has_permission(self, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS.get(self.role, set())


@dataclass
class AuditLogEntry:
    """Entry in the audit log."""
    timestamp: float
    tenant_id: str
    action: str
    resource: str
    granted: bool
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataVisibility:
    """Defines what fields are visible to different roles."""
    public_fields: Set[str] = field(default_factory=lambda: {
        'product_id', 'event_type', 'timestamp', 'location'
    })
    partner_fields: Set[str] = field(default_factory=lambda: {
        'quality_score', 'certifications', 'batch_id'
    })
    sensitive_fields: Set[str] = field(default_factory=lambda: {
        'price', 'cost', 'margin', 'supplier_details'
    })
    owner_only_fields: Set[str] = field(default_factory=lambda: {
        'internal_notes', 'employee_id', 'internal_quality_issues'
    })


class SimpleEncryption:
    """Simple encryption for sensitive data (use proper crypto in production)."""

    @staticmethod
    def encrypt(data: str, key: str) -> str:
        """Encrypt data with key using XOR (demo only - use AES in production)."""
        key_bytes = hashlib.sha256(key.encode()).digest()
        data_bytes = data.encode()
        encrypted = bytes(d ^ key_bytes[i % len(key_bytes)]
                         for i, d in enumerate(data_bytes))
        return base64.b64encode(encrypted).decode()

    @staticmethod
    def decrypt(encrypted: str, key: str) -> str:
        """Decrypt data with key."""
        key_bytes = hashlib.sha256(key.encode()).digest()
        encrypted_bytes = base64.b64decode(encrypted.encode())
        decrypted = bytes(d ^ key_bytes[i % len(key_bytes)]
                         for i, d in enumerate(encrypted_bytes))
        return decrypted.decode()


class AccessControlManager:
    """Manages access control for multi-tenant caching system."""

    def __init__(self):
        self.tenants: Dict[str, Tenant] = {}
        self.audit_log: List[AuditLogEntry] = []
        self.visibility = DataVisibility()

        # API key to tenant mapping
        self.api_key_map: Dict[str, str] = {}

    def register_tenant(self, tenant: Tenant) -> str:
        """Register a new tenant."""
        self.tenants[tenant.tenant_id] = tenant
        self.api_key_map[tenant.api_key] = tenant.tenant_id

        self._log_audit(tenant.tenant_id, "REGISTER", f"tenant:{tenant.tenant_id}", True)
        return tenant.api_key

    def authenticate(self, api_key: str) -> Optional[Tenant]:
        """Authenticate a request by API key."""
        tenant_id = self.api_key_map.get(api_key)
        if tenant_id:
            return self.tenants.get(tenant_id)
        return None

    def add_partnership(self, upstream_id: str, downstream_id: str):
        """Establish a supply chain partnership."""
        if upstream_id in self.tenants and downstream_id in self.tenants:
            self.tenants[upstream_id].downstream_partners.add(downstream_id)
            self.tenants[downstream_id].upstream_partners.add(upstream_id)

    def check_access(self, tenant: Tenant, resource_type: str,
                     resource_id: str, owner_id: str) -> bool:
        """
        Check if tenant can access a resource.

        Args:
            tenant: The requesting tenant
            resource_type: Type of resource (product, farm, trace, aggregate)
            resource_id: ID of the resource
            owner_id: Tenant ID of the resource owner

        Returns:
            True if access is granted
        """
        # Admin and regulators can read all
        if tenant.has_permission(Permission.READ_ALL):
            self._log_audit(tenant.tenant_id, "READ", f"{resource_type}:{resource_id}", True,
                          {'reason': 'READ_ALL permission'})
            return True

        # Owner can always access own data
        if owner_id == tenant.tenant_id:
            self._log_audit(tenant.tenant_id, "READ", f"{resource_type}:{resource_id}", True,
                          {'reason': 'owner'})
            return True

        # Check partner relationships
        if owner_id in tenant.upstream_partners and tenant.has_permission(Permission.READ_UPSTREAM):
            self._log_audit(tenant.tenant_id, "READ", f"{resource_type}:{resource_id}", True,
                          {'reason': 'upstream partner'})
            return True

        if owner_id in tenant.downstream_partners and tenant.has_permission(Permission.READ_DOWNSTREAM):
            self._log_audit(tenant.tenant_id, "READ", f"{resource_type}:{resource_id}", True,
                          {'reason': 'downstream partner'})
            return True

        # Aggregates are generally accessible
        if resource_type == 'aggregate' and tenant.has_permission(Permission.READ_AGGREGATES):
            self._log_audit(tenant.tenant_id, "READ", f"{resource_type}:{resource_id}", True,
                          {'reason': 'aggregate access'})
            return True

        # Access denied
        self._log_audit(tenant.tenant_id, "READ", f"{resource_type}:{resource_id}", False,
                      {'reason': 'no permission'})
        return False

    def filter_fields(self, tenant: Tenant, data: Dict, owner_id: str) -> Dict:
        """
        Filter data fields based on tenant's visibility permissions.

        Returns a copy of data with only visible fields.
        """
        result = {}

        is_owner = owner_id == tenant.tenant_id
        is_partner = (owner_id in tenant.upstream_partners or
                     owner_id in tenant.downstream_partners)
        has_sensitive = tenant.has_permission(Permission.READ_SENSITIVE)

        for key, value in data.items():
            # Public fields - everyone can see
            if key in self.visibility.public_fields:
                result[key] = value

            # Partner fields - partners and owners
            elif key in self.visibility.partner_fields:
                if is_owner or is_partner or has_sensitive:
                    result[key] = value

            # Sensitive fields - only with permission
            elif key in self.visibility.sensitive_fields:
                if has_sensitive or is_owner:
                    result[key] = value

            # Owner-only fields
            elif key in self.visibility.owner_only_fields:
                if is_owner:
                    result[key] = value

            # Unknown fields - default to partner visibility
            else:
                if is_owner or is_partner or has_sensitive:
                    result[key] = value

        return result

    def _log_audit(self, tenant_id: str, action: str, resource: str,
                   granted: bool, details: Dict = None):
        """Add entry to audit log."""
        entry = AuditLogEntry(
            timestamp=time.time(),
            tenant_id=tenant_id,
            action=action,
            resource=resource,
            granted=granted,
            details=details or {}
        )
        self.audit_log.append(entry)

        # Keep only last 10000 entries
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-10000:]

    def get_audit_log(self, tenant_id: str = None,
                      start_time: float = None,
                      end_time: float = None) -> List[AuditLogEntry]:
        """Query audit log with filters."""
        results = self.audit_log

        if tenant_id:
            results = [e for e in results if e.tenant_id == tenant_id]

        if start_time:
            results = [e for e in results if e.timestamp >= start_time]

        if end_time:
            results = [e for e in results if e.timestamp <= end_time]

        return results


class MultiTenantCache:
    """
    Cache with multi-tenant access control.

    Features:
    - Per-tenant cache isolation
    - Access control enforcement
    - Field-level visibility filtering
    - Encrypted storage for sensitive data
    - Audit logging
    """

    def __init__(self, capacity_per_tenant: int = 1000):
        self.capacity_per_tenant = capacity_per_tenant
        self.access_control = AccessControlManager()

        # Per-tenant caches
        self.tenant_caches: Dict[str, Dict[str, Any]] = defaultdict(dict)

        # Shared cache for aggregates (with access control)
        self.shared_cache: Dict[str, Any] = {}

        # Data ownership mapping
        self.resource_owners: Dict[str, str] = {}  # resource_id -> tenant_id

        # Stats
        self.stats = {
            'hits': 0,
            'misses': 0,
            'access_denied': 0,
            'filtered_fields': 0
        }

    def register_tenant(self, tenant: Tenant) -> str:
        """Register a tenant and return their API key."""
        return self.access_control.register_tenant(tenant)

    def put(self, api_key: str, key: str, value: Any,
            resource_type: str = 'data',
            encrypt_sensitive: bool = True) -> bool:
        """
        Store data in tenant's cache.

        Args:
            api_key: Tenant's API key
            key: Cache key
            value: Data to cache
            resource_type: Type of resource
            encrypt_sensitive: Whether to encrypt sensitive fields

        Returns:
            True if successful
        """
        tenant = self.access_control.authenticate(api_key)
        if not tenant:
            return False

        # Check write permission
        if not tenant.has_permission(Permission.WRITE_OWN):
            return False

        # Encrypt sensitive fields if requested
        if encrypt_sensitive and isinstance(value, dict):
            value = self._encrypt_sensitive(value, tenant.encryption_key)

        # Store in tenant's cache
        cache = self.tenant_caches[tenant.tenant_id]

        # Evict if at capacity
        if len(cache) >= self.capacity_per_tenant and key not in cache:
            oldest_key = next(iter(cache))
            del cache[oldest_key]

        cache[key] = {
            'value': value,
            'timestamp': time.time(),
            'resource_type': resource_type
        }

        # Record ownership
        self.resource_owners[key] = tenant.tenant_id

        return True

    def get(self, api_key: str, key: str, owner_id: str = None) -> Optional[Any]:
        """
        Get data from cache with access control.

        Args:
            api_key: Tenant's API key
            key: Cache key
            owner_id: Owner of the data (if known)

        Returns:
            Data if accessible, None otherwise
        """
        tenant = self.access_control.authenticate(api_key)
        if not tenant:
            self.stats['access_denied'] += 1
            return None

        # Determine owner
        if owner_id is None:
            owner_id = self.resource_owners.get(key, tenant.tenant_id)

        # Check access
        owner_cache = self.tenant_caches.get(owner_id, {})
        if key not in owner_cache:
            self.stats['misses'] += 1
            return None

        entry = owner_cache[key]
        resource_type = entry.get('resource_type', 'data')

        if not self.access_control.check_access(tenant, resource_type, key, owner_id):
            self.stats['access_denied'] += 1
            return None

        self.stats['hits'] += 1
        value = entry['value']

        # Decrypt if needed
        owner_tenant = self.access_control.tenants.get(owner_id)
        if owner_tenant and isinstance(value, dict):
            value = self._decrypt_sensitive(value, owner_tenant.encryption_key)

        # Filter fields based on visibility
        if isinstance(value, dict):
            original_fields = len(value)
            value = self.access_control.filter_fields(tenant, value, owner_id)
            self.stats['filtered_fields'] += original_fields - len(value)

        return value

    def get_aggregate(self, api_key: str, agg_key: str) -> Optional[Any]:
        """Get aggregate data (shared across tenants with permission)."""
        tenant = self.access_control.authenticate(api_key)
        if not tenant:
            self.stats['access_denied'] += 1
            return None

        if not tenant.has_permission(Permission.READ_AGGREGATES):
            self.stats['access_denied'] += 1
            return None

        if agg_key in self.shared_cache:
            self.stats['hits'] += 1
            return self.shared_cache[agg_key]

        self.stats['misses'] += 1
        return None

    def put_aggregate(self, api_key: str, agg_key: str, value: Any) -> bool:
        """Store aggregate data in shared cache."""
        tenant = self.access_control.authenticate(api_key)
        if not tenant:
            return False

        # Only admin can write aggregates
        if tenant.role != Role.ADMIN:
            return False

        self.shared_cache[agg_key] = {
            'value': value,
            'timestamp': time.time()
        }
        return True

    def _encrypt_sensitive(self, data: Dict, key: str) -> Dict:
        """Encrypt sensitive fields in data."""
        result = data.copy()
        for field in self.access_control.visibility.sensitive_fields:
            if field in result:
                result[field] = {
                    '_encrypted': True,
                    '_value': SimpleEncryption.encrypt(
                        json.dumps(result[field]), key
                    )
                }
        return result

    def _decrypt_sensitive(self, data: Dict, key: str) -> Dict:
        """Decrypt sensitive fields in data."""
        result = data.copy()
        for field, value in result.items():
            if isinstance(value, dict) and value.get('_encrypted'):
                try:
                    decrypted = SimpleEncryption.decrypt(value['_value'], key)
                    result[field] = json.loads(decrypted)
                except:
                    result[field] = None
        return result

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self.stats['hits'] + self.stats['misses']
        return {
            **self.stats,
            'hit_rate': self.stats['hits'] / total if total > 0 else 0,
            'tenant_count': len(self.tenant_caches),
            'total_entries': sum(len(c) for c in self.tenant_caches.values()),
            'shared_entries': len(self.shared_cache)
        }


# Example usage and testing
if __name__ == "__main__":
    print("Testing Multi-Tenant Access Control")
    print("=" * 60)

    # Create cache
    cache = MultiTenantCache(capacity_per_tenant=100)

    # Register tenants
    farmer = Tenant(
        tenant_id="FARM-001",
        name="Green Valley Farm",
        role=Role.FARMER
    )
    farmer.owned_farms.add("FARM-001")
    farmer_key = cache.register_tenant(farmer)

    processor = Tenant(
        tenant_id="PROC-001",
        name="Fresh Foods Processing",
        role=Role.PROCESSOR
    )
    processor_key = cache.register_tenant(processor)

    regulator = Tenant(
        tenant_id="REG-001",
        name="Food Safety Authority",
        role=Role.REGULATOR
    )
    regulator_key = cache.register_tenant(regulator)

    # Establish partnership
    cache.access_control.add_partnership("FARM-001", "PROC-001")

    # Farmer stores data
    trace_data = {
        'product_id': 'PROD-001',
        'event_type': 'harvest',
        'timestamp': time.time(),
        'location': 'Field A',
        'quality_score': 95,
        'price': 2.50,  # Sensitive
        'internal_notes': 'Good yield this season'  # Owner only
    }

    cache.put(farmer_key, 'trace:PROD-001', trace_data, resource_type='trace')
    print(f"Farmer stored trace data")

    # Farmer retrieves own data (sees everything)
    farmer_view = cache.get(farmer_key, 'trace:PROD-001')
    print(f"\nFarmer's view: {list(farmer_view.keys())}")

    # Processor retrieves partner data (sees partner fields)
    processor_view = cache.get(processor_key, 'trace:PROD-001', owner_id='FARM-001')
    print(f"Processor's view: {list(processor_view.keys()) if processor_view else 'Access denied'}")

    # Regulator retrieves data (sees all including sensitive)
    regulator_view = cache.get(regulator_key, 'trace:PROD-001', owner_id='FARM-001')
    print(f"Regulator's view: {list(regulator_view.keys()) if regulator_view else 'Access denied'}")

    # Print audit log
    print(f"\nAudit log entries: {len(cache.access_control.audit_log)}")
    for entry in cache.access_control.audit_log[-3:]:
        print(f"  {entry.tenant_id}: {entry.action} {entry.resource} -> {'GRANTED' if entry.granted else 'DENIED'}")

    # Print stats
    print(f"\nCache stats: {cache.get_stats()}")
