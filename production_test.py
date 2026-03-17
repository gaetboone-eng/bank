#!/usr/bin/env python3
"""
Production API Testing for Tenant Ledger
Tests specific production endpoints with real user data
"""

import requests
import sys
import json
from datetime import datetime, timezone

class ProductionAPITester:
    def __init__(self, base_url="https://tenant-ledger-16.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failures = []

    def run_test(self, name, method, endpoint, expected_status=200, data=None, params=None, validate_func=None):
        """Run a single API test with optional validation"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json() if response.content else {}
            except:
                response_data = {}

            # Custom validation
            if success and validate_func:
                validation_result = validate_func(response_data)
                if not validation_result:
                    success = False
                    print(f"❌ Failed - Validation failed")
                    self.failures.append(f"{name}: Validation failed")

            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                return True, response_data
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text}")
                
                if response.status_code != expected_status:
                    self.failures.append(f"{name}: Expected {expected_status}, got {response.status_code}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failures.append(f"{name}: Exception - {str(e)}")
            return False, {}

    def test_login(self, email, password):
        """Test login with production credentials"""
        def validate_login(data):
            return 'access_token' in data and 'user' in data
        
        success, response = self.run_test(
            "Production Login",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password},
            validate_func=validate_login
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            print(f"   Logged in as: {response['user']['name']} ({response['user']['email']})")
            return True
        return False

    def test_get_tenants(self, expected_count=52):
        """Test get tenants - should return 52 tenants from Notion sync"""
        def validate_tenants(data):
            if not isinstance(data, list):
                print(f"   Expected list, got {type(data)}")
                return False
            if len(data) != expected_count:
                print(f"   Expected {expected_count} tenants, got {len(data)}")
                return False
            # Check tenant structure
            if data and not all('id' in tenant and 'name' in tenant and 'rent_amount' in tenant for tenant in data):
                print("   Missing required tenant fields")
                return False
            print(f"   Found {len(data)} tenants ✓")
            return True
        
        return self.run_test(
            "Get All Tenants (52 expected)",
            "GET",
            "tenants",
            200,
            validate_func=validate_tenants
        )

    def test_get_transactions(self, expected_count=97):
        """Test get transactions - should return 97 transactions from banking"""
        def validate_transactions(data):
            if not isinstance(data, list):
                print(f"   Expected list, got {type(data)}")
                return False
            if len(data) != expected_count:
                print(f"   Expected {expected_count} transactions, got {len(data)}")
                return False
            # Check transaction structure
            if data and not all('id' in tx and 'amount' in tx and 'description' in tx for tx in data):
                print("   Missing required transaction fields")
                return False
            print(f"   Found {len(data)} transactions ✓")
            return True
        
        return self.run_test(
            "Get All Transactions (97 expected)",
            "GET",
            "transactions",
            200,
            validate_func=validate_transactions
        )

    def test_monthly_status_dec_2025(self):
        """Test monthly status for December 2025 - should show 10 paid, 42 unpaid"""
        def validate_dec_2025(data):
            if not isinstance(data, dict):
                print(f"   Expected dict, got {type(data)}")
                return False
            
            summary = data.get('summary', {})
            paid_count = summary.get('paid_count', 0)
            unpaid_count = summary.get('unpaid_count', 0)
            
            print(f"   December 2025: {paid_count} paid, {unpaid_count} unpaid")
            
            if paid_count != 10:
                print(f"   Expected 10 paid, got {paid_count}")
                return False
            if unpaid_count != 42:
                print(f"   Expected 42 unpaid, got {unpaid_count}")
                return False
            
            # Check 28th-to-28th period calculation
            date_range = data.get('date_range', {})
            if not date_range.get('start') or not date_range.get('end'):
                print("   Missing date range information")
                return False
            
            print(f"   Period: {date_range.get('start')[:10]} to {date_range.get('end')[:10]} ✓")
            return True
        
        return self.run_test(
            "Monthly Status December 2025",
            "GET",
            "payments/monthly-status",
            200,
            params={"month": 12, "year": 2025},
            validate_func=validate_dec_2025
        )

    def test_monthly_status_feb_2026(self):
        """Test monthly status for February 2026 - should show 14 paid, 38 unpaid"""
        def validate_feb_2026(data):
            if not isinstance(data, dict):
                print(f"   Expected dict, got {type(data)}")
                return False
            
            summary = data.get('summary', {})
            paid_count = summary.get('paid_count', 0)
            unpaid_count = summary.get('unpaid_count', 0)
            
            print(f"   February 2026: {paid_count} paid, {unpaid_count} unpaid")
            
            if paid_count != 14:
                print(f"   Expected 14 paid, got {paid_count}")
                return False
            if unpaid_count != 38:
                print(f"   Expected 38 unpaid, got {unpaid_count}")
                return False
            
            # Check 28th-to-28th period calculation
            date_range = data.get('date_range', {})
            if not date_range.get('start') or not date_range.get('end'):
                print("   Missing date range information")
                return False
            
            print(f"   Period: {date_range.get('start')[:10]} to {date_range.get('end')[:10]} ✓")
            return True
        
        return self.run_test(
            "Monthly Status February 2026",
            "GET",
            "payments/monthly-status",
            200,
            params={"month": 2, "year": 2026},
            validate_func=validate_feb_2026
        )

    def test_auto_match_transactions(self):
        """Test auto-matching algorithm"""
        def validate_auto_match(data):
            if not isinstance(data, dict):
                print(f"   Expected dict, got {type(data)}")
                return False
            
            if 'message' not in data:
                print("   Missing message field")
                return False
            
            matches = data.get('matches', [])
            by_rule = data.get('by_rule', 0)
            by_name = data.get('by_name', 0)
            
            print(f"   Auto-matched: {len(matches)} transactions")
            print(f"   By learned rules: {by_rule}, By name matching: {by_name}")
            
            return True
        
        return self.run_test(
            "Auto-Match Transactions",
            "POST",
            "transactions/auto-match",
            200,
            validate_func=validate_auto_match
        )

    def test_dashboard_stats(self):
        """Test dashboard stats"""
        def validate_dashboard(data):
            if not isinstance(data, dict):
                print(f"   Expected dict, got {type(data)}")
                return False
            
            total_tenants = data.get('total_tenants', 0)
            paid_tenants = data.get('paid_tenants', 0)
            unpaid_tenants = data.get('unpaid_tenants', 0)
            total_balance = data.get('total_balance', 0)
            
            print(f"   Dashboard: {total_tenants} tenants, {paid_tenants} paid, bank balance: €{total_balance}")
            
            if total_tenants != 52:
                print(f"   Expected 52 total tenants, got {total_tenants}")
                return False
            
            return True
        
        return self.run_test(
            "Dashboard Statistics",
            "GET",
            "dashboard/stats",
            200,
            validate_func=validate_dashboard
        )

    def test_notion_sync(self):
        """Test Notion sync integration"""
        def validate_notion_sync(data):
            if not isinstance(data, dict):
                print(f"   Expected dict, got {type(data)}")
                return False
            
            count = data.get('count', 0)
            message = data.get('message', '')
            
            print(f"   Notion sync: {message}")
            print(f"   Synced: {count} tenants")
            
            return 'count' in data and count > 0
        
        return self.run_test(
            "Notion Integration - Sync Tenants",
            "POST",
            "tenants/sync-notion",
            200,
            validate_func=validate_notion_sync
        )

    def test_enable_banking_aspsps(self):
        """Test Enable Banking integration - get available banks"""
        def validate_aspsps(data):
            if not isinstance(data, list):
                print(f"   Expected list, got {type(data)}")
                return False
            
            print(f"   Available banks: {len(data)}")
            if data:
                print(f"   Sample bank: {data[0].get('name', 'Unknown')}")
            
            return len(data) > 0
        
        return self.run_test(
            "Enable Banking - Get Available Banks",
            "GET",
            "banking/aspsps",
            200,
            params={"country": "FR"},
            validate_func=validate_aspsps
        )

    def test_connected_banks(self):
        """Test connected banks"""
        return self.run_test(
            "Get Connected Banks",
            "GET",
            "banking/connected",
            200
        )

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print(f"📊 PRODUCTION TEST RESULTS")
        print(f"{'='*60}")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_run - self.tests_passed}")
        
        if self.failures:
            print(f"\n❌ FAILED TESTS:")
            for failure in self.failures:
                print(f"   • {failure}")
        
        if self.tests_passed == self.tests_run:
            print(f"\n🎉 ALL PRODUCTION TESTS PASSED!")
            return 0
        else:
            print(f"\n⚠️ {self.tests_run - self.tests_passed} TEST(S) FAILED")
            return 1

def main():
    print("🚀 Starting Tenant Ledger PRODUCTION API Tests...")
    print("Testing with real production data and credentials")
    
    tester = ProductionAPITester()
    
    # Production credentials from review request
    email = "gaet.boone@gmail.com"
    password = "TenantLedger2024!"
    
    try:
        # 1. Authentication
        print("\n📋 AUTHENTICATION FLOW")
        if not tester.test_login(email, password):
            print("❌ Authentication failed - cannot continue with other tests")
            return 1

        # 2. High Priority Backend Tests (from review request)
        print("\n📊 HIGH PRIORITY BACKEND TESTS")
        
        # Test 52 tenants from Notion sync
        tester.test_get_tenants(52)
        
        # Test 97 transactions from banking
        tester.test_get_transactions(97)
        
        # Test monthly status endpoints with specific data
        tester.test_monthly_status_dec_2025()  # 10 paid, 42 unpaid
        tester.test_monthly_status_feb_2026()  # 14 paid, 38 unpaid
        
        # Test auto-matching algorithm
        tester.test_auto_match_transactions()
        
        # Test dashboard stats
        tester.test_dashboard_stats()
        
        # 3. Integration Tests
        print("\n🔗 INTEGRATION TESTS")
        
        # Test Notion integration
        tester.test_notion_sync()
        
        # Test Enable Banking integration
        tester.test_enable_banking_aspsps()
        tester.test_connected_banks()
        
        return tester.print_summary()
        
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())