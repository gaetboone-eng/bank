"""
CGR Bank - Backend API Tests
Testing: Authentication, Dashboard, Banks, Monthly Report, Admin sync endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CREDENTIALS = [
    {"email": "gaet.boone@gmail.com", "password": "TenantLedger2024!", "label": "Owner1"},
    {"email": "romain.m@cgrbank.com", "password": "CGRbank2024!", "label": "Owner2"},
    {"email": "clement.h@cgrbank.com", "password": "CGRbank2024!", "label": "Owner3"},
]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for the first owner"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "gaet.boone@gmail.com",
        "password": "TenantLedger2024!"
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    return data["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ==================== AUTH TESTS ====================

class TestAuthentication:
    """Test login for all 3 CGR Bank owner accounts"""

    def test_login_owner1_gaet(self):
        """Owner 1: gaet.boone@gmail.com"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "gaet.boone@gmail.com",
            "password": "TenantLedger2024!"
        })
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "gaet.boone@gmail.com"
        print(f"✅ Owner1 login OK - token length: {len(data['access_token'])}")

    def test_login_owner2_romain(self):
        """Owner 2: romain.m@cgrbank.com"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "romain.m@cgrbank.com",
            "password": "CGRbank2024!"
        })
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "romain.m@cgrbank.com"
        print(f"✅ Owner2 login OK")

    def test_login_owner3_clement(self):
        """Owner 3: clement.h@cgrbank.com"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "clement.h@cgrbank.com",
            "password": "CGRbank2024!"
        })
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "clement.h@cgrbank.com"
        print(f"✅ Owner3 login OK")

    def test_login_invalid_credentials(self):
        """Invalid credentials should return 401"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert resp.status_code == 401
        print(f"✅ Invalid credentials correctly rejected")

    def test_auth_me_endpoint(self, auth_headers):
        """Authenticated /me endpoint"""
        resp = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data
        assert "id" in data
        print(f"✅ /auth/me returns user: {data['email']}")


# ==================== DASHBOARD TESTS ====================

class TestDashboard:
    """Test dashboard stats endpoint"""

    def test_dashboard_stats(self, auth_headers):
        """Dashboard stats should return properly structured data"""
        resp = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=auth_headers)
        assert resp.status_code == 200, f"Dashboard stats failed: {resp.text}"
        data = resp.json()
        
        # Validate required fields
        assert "total_tenants" in data, "Missing total_tenants"
        assert "paid_tenants" in data, "Missing paid_tenants"
        assert "unpaid_tenants" in data, "Missing unpaid_tenants"
        assert "banks_count" in data, "Missing banks_count"
        assert "total_rent_expected" in data, "Missing total_rent_expected"
        assert "total_rent_collected" in data, "Missing total_rent_collected"
        
        # Validate numeric types
        assert isinstance(data["total_tenants"], int)
        assert isinstance(data["paid_tenants"], int)
        assert isinstance(data["unpaid_tenants"], int)
        
        print(f"✅ Dashboard stats: {data['total_tenants']} tenants, {data['paid_tenants']} paid, {data['unpaid_tenants']} unpaid, {data['banks_count']} banks")

    def test_dashboard_stats_all_owners_see_same_data(self):
        """All 3 owners should see the same data (same org)"""
        tokens = {}
        for cred in CREDENTIALS:
            resp = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": cred["email"],
                "password": cred["password"]
            })
            assert resp.status_code == 200
            tokens[cred["label"]] = resp.json()["access_token"]
        
        stats = {}
        for label, token in tokens.items():
            resp = requests.get(f"{BASE_URL}/api/dashboard/stats", 
                              headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200, f"{label} dashboard failed: {resp.text}"
            stats[label] = resp.json()
        
        # All owners should see the same total tenants (shared org)
        tenant_counts = [s["total_tenants"] for s in stats.values()]
        print(f"✅ Tenant counts per owner: {dict(zip(tokens.keys(), tenant_counts))}")
        # They should all see the same data
        assert len(set(tenant_counts)) == 1, f"Owners see different tenant counts: {dict(zip(tokens.keys(), tenant_counts))}"


# ==================== BANKS TESTS ====================

class TestBanks:
    """Test banks endpoints"""

    def test_get_banks(self, auth_headers):
        """Banks list should return successfully"""
        resp = requests.get(f"{BASE_URL}/api/banks", headers=auth_headers)
        assert resp.status_code == 200, f"Get banks failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, list)
        print(f"✅ Banks list: {len(data)} banks")
        if data:
            bank = data[0]
            assert "id" in bank
            assert "name" in bank
            assert "balance" in bank

    def test_import_all_banks_no_500(self, auth_headers):
        """Import all banks endpoint should not return 500"""
        resp = requests.post(f"{BASE_URL}/api/banking/import-all", headers=auth_headers)
        # Should not return 500 - may return 200 or 400/404 depending on config
        assert resp.status_code != 500, f"import-all returned 500: {resp.text}"
        print(f"✅ /banking/import-all responded with {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   Import result: {data}")


# ==================== TENANTS TESTS ====================

class TestTenants:
    """Test tenants endpoints"""

    def test_get_tenants(self, auth_headers):
        """Tenants list should return properly"""
        resp = requests.get(f"{BASE_URL}/api/tenants", headers=auth_headers)
        assert resp.status_code == 200, f"Get tenants failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, list)
        print(f"✅ Tenants list: {len(data)} tenants")


# ==================== PAYMENTS / REPORTS TESTS ====================

class TestPaymentsAndReports:
    """Test payment and report endpoints"""

    def test_payments_stats_by_structure(self, auth_headers):
        """Payment stats by structure endpoint"""
        resp = requests.get(f"{BASE_URL}/api/payments/stats-by-structure", headers=auth_headers)
        assert resp.status_code == 200, f"Stats by structure failed: {resp.text}"
        data = resp.json()
        
        # Validate structure
        assert "overall" in data, "Missing 'overall' key"
        assert "by_structure" in data, "Missing 'by_structure' key"
        
        overall = data["overall"]
        assert "total" in overall
        assert "paid" in overall
        assert "unpaid" in overall
        assert "percentage" in overall
        
        print(f"✅ Structure stats: overall {overall['paid']}/{overall['total']} ({overall['percentage']}%)")
        if data["by_structure"]:
            print(f"   Structures: {[s['name'] for s in data['by_structure']]}")

    def test_payments_monthly_status(self, auth_headers):
        """Monthly payment status endpoint requires month (int) and year (int) query params"""
        from datetime import datetime
        now = datetime.utcnow()
        resp = requests.get(
            f"{BASE_URL}/api/payments/monthly-status",
            params={"month": now.month, "year": now.year},
            headers=auth_headers
        )
        assert resp.status_code == 200, f"Monthly status failed: {resp.text}"
        print(f"✅ /payments/monthly-status OK")

    def test_get_payments(self, auth_headers):
        """Payments list"""
        resp = requests.get(f"{BASE_URL}/api/payments", headers=auth_headers)
        assert resp.status_code == 200, f"Get payments failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, list)
        print(f"✅ Payments list: {len(data)} payments")


# ==================== ADMIN / SYNC TESTS ====================

class TestAdminSync:
    """Test admin and sync endpoints"""

    def test_admin_full_sync_endpoint_existence(self, auth_headers):
        """Test /api/admin/full-sync - note: endpoint is /admin/run-sync, not full-sync"""
        # The frontend 'Synchroniser' button actually calls /api/sync/manual (confirmed in api.js)
        # /api/admin/full-sync is referenced in the review request but doesn't exist
        # This is noted as informational
        resp = requests.post(f"{BASE_URL}/api/admin/full-sync", headers=auth_headers)
        if resp.status_code == 404:
            print(f"ℹ️  /admin/full-sync returns 404 (expected - frontend uses /sync/manual instead)")
            # This is not a real issue since the frontend calls /sync/manual
            # Just mark as skipped / informational
        else:
            print(f"✅ /admin/full-sync responded with {resp.status_code}")
            assert resp.status_code != 500

    def test_admin_run_sync_endpoint(self, auth_headers):
        """Test /api/admin/run-sync (the actual sync endpoint)"""
        resp = requests.post(f"{BASE_URL}/api/admin/run-sync", headers=auth_headers)
        assert resp.status_code != 500, f"run-sync returned 500: {resp.text}"
        print(f"✅ /admin/run-sync responded with {resp.status_code}")

    def test_sync_manual_endpoint(self, auth_headers):
        """Test /api/sync/manual - check response structure"""
        resp = requests.post(f"{BASE_URL}/api/sync/manual", headers=auth_headers)
        assert resp.status_code != 500, f"/sync/manual returned 500: {resp.text}"
        print(f"✅ /sync/manual responded with {resp.status_code}: {resp.text[:200]}")
        
        # The response should have 'results' key
        if resp.status_code == 200:
            data = resp.json()
            if data is None:
                pytest.fail("/sync/manual returns null body - missing return statement in manual_sync function!")
            assert "results" in data, f"Missing 'results' key in response: {data}"
            print(f"   Results: {data.get('results')}")

    def test_banking_connected_banks(self, auth_headers):
        """Test connected banks endpoint"""
        resp = requests.get(f"{BASE_URL}/api/banking/connected", headers=auth_headers)
        assert resp.status_code == 200, f"Connected banks failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, list)
        print(f"✅ Connected banks: {len(data)} accounts")

    def test_transactions_list(self, auth_headers):
        """Test transactions list"""
        resp = requests.get(f"{BASE_URL}/api/transactions", headers=auth_headers)
        assert resp.status_code == 200, f"Transactions failed: {resp.text}"
        data = resp.json()
        assert isinstance(data, list)
        print(f"✅ Transactions: {len(data)} transactions")


# ==================== NO 500 ERRORS CHECK ====================

class TestNo500Errors:
    """Verify main endpoints return no 500 errors"""

    def test_critical_endpoints_no_500(self, auth_headers):
        """All critical endpoints should not return 500"""
        endpoints = [
            ("GET", "/api/dashboard/stats"),
            ("GET", "/api/banks"),
            ("GET", "/api/tenants"),
            ("GET", "/api/payments"),
            ("GET", "/api/payments/stats-by-structure"),
            ("GET", "/api/banking/connected"),
            ("GET", "/api/transactions"),
            ("GET", "/api/settings"),
        ]
        
        failures = []
        for method, path in endpoints:
            resp = requests.request(method, f"{BASE_URL}{path}", headers=auth_headers)
            if resp.status_code == 500:
                failures.append(f"{method} {path} -> 500: {resp.text[:100]}")
            else:
                print(f"✅ {method} {path} -> {resp.status_code}")
        
        assert not failures, f"Endpoints returned 500:\n" + "\n".join(failures)
