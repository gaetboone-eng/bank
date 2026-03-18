import requests
import sys
import json
from datetime import datetime, timezone

class TenantLedgerAPITester:
    def __init__(self, base_url="https://tenant-finance-mgr.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_resources = {
            'banks': [],
            'tenants': [],
            'transactions': []
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
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
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_register(self, email, password, name):
        """Test user registration"""
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data={"email": email, "password": password, "name": name}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            return True
        return False

    def test_login(self, email, password):
        """Test user login"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            return True
        return False

    def test_get_me(self):
        """Test get current user"""
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        return success

    def test_create_bank(self, name, iban=None, balance=0.0, color="#064E3B"):
        """Test bank creation"""
        success, response = self.run_test(
            "Create Bank",
            "POST",
            "banks",
            200,
            data={"name": name, "iban": iban, "balance": balance, "color": color}
        )
        if success and 'id' in response:
            self.created_resources['banks'].append(response['id'])
            return response['id']
        return None

    def test_get_banks(self):
        """Test get banks"""
        success, response = self.run_test(
            "Get Banks",
            "GET",
            "banks",
            200
        )
        return success, response if success else []

    def test_update_bank(self, bank_id, name=None, balance=None):
        """Test bank update"""
        update_data = {}
        if name:
            update_data['name'] = name
        if balance is not None:
            update_data['balance'] = balance
        
        success, response = self.run_test(
            "Update Bank",
            "PUT",
            f"banks/{bank_id}",
            200,
            data=update_data
        )
        return success

    def test_delete_bank(self, bank_id):
        """Test bank deletion"""
        success, response = self.run_test(
            "Delete Bank",
            "DELETE",
            f"banks/{bank_id}",
            200
        )
        if success and bank_id in self.created_resources['banks']:
            self.created_resources['banks'].remove(bank_id)
        return success

    def test_create_tenant(self, name, property_address, rent_amount, email=None, phone=None, due_day=1):
        """Test tenant creation"""
        success, response = self.run_test(
            "Create Tenant",
            "POST",
            "tenants",
            200,
            data={
                "name": name,
                "email": email,
                "phone": phone,
                "property_address": property_address,
                "rent_amount": rent_amount,
                "due_day": due_day
            }
        )
        if success and 'id' in response:
            self.created_resources['tenants'].append(response['id'])
            return response['id']
        return None

    def test_get_tenants(self):
        """Test get tenants"""
        success, response = self.run_test(
            "Get Tenants",
            "GET",
            "tenants",
            200
        )
        return success, response if success else []

    def test_get_tenant(self, tenant_id):
        """Test get single tenant"""
        success, response = self.run_test(
            "Get Single Tenant",
            "GET",
            f"tenants/{tenant_id}",
            200
        )
        return success

    def test_update_tenant(self, tenant_id, name=None, rent_amount=None):
        """Test tenant update"""
        update_data = {}
        if name:
            update_data['name'] = name
        if rent_amount is not None:
            update_data['rent_amount'] = rent_amount
        
        success, response = self.run_test(
            "Update Tenant",
            "PUT",
            f"tenants/{tenant_id}",
            200,
            data=update_data
        )
        return success

    def test_delete_tenant(self, tenant_id):
        """Test tenant deletion"""
        success, response = self.run_test(
            "Delete Tenant",
            "DELETE",
            f"tenants/{tenant_id}",
            200
        )
        if success and tenant_id in self.created_resources['tenants']:
            self.created_resources['tenants'].remove(tenant_id)
        return success

    def test_create_transaction(self, bank_id, amount, description, category="rent"):
        """Test transaction creation"""
        success, response = self.run_test(
            "Create Transaction",
            "POST",
            "transactions",
            200,
            data={
                "bank_id": bank_id,
                "amount": amount,
                "description": description,
                "transaction_date": datetime.now(timezone.utc).isoformat(),
                "category": category
            }
        )
        if success and 'id' in response:
            self.created_resources['transactions'].append(response['id'])
            return response['id']
        return None

    def test_get_transactions(self, bank_id=None):
        """Test get transactions"""
        params = {"bank_id": bank_id} if bank_id else None
        success, response = self.run_test(
            "Get Transactions",
            "GET",
            "transactions",
            200,
            params=params
        )
        return success, response if success else []

    def test_match_transaction(self, tx_id, tenant_id):
        """Test transaction matching to tenant"""
        success, response = self.run_test(
            "Match Transaction to Tenant",
            "POST",
            f"transactions/{tx_id}/match/{tenant_id}",
            200
        )
        return success

    def test_get_payments(self, tenant_id=None):
        """Test get payments"""
        params = {"tenant_id": tenant_id} if tenant_id else None
        success, response = self.run_test(
            "Get Payments",
            "GET",
            "payments",
            200,
            params=params
        )
        return success, response if success else []

    def test_dashboard_stats(self):
        """Test dashboard stats"""
        success, response = self.run_test(
            "Get Dashboard Stats",
            "GET",
            "dashboard/stats",
            200
        )
        return success, response if success else {}

    def test_sync_notion(self):
        """Test Notion sync (expected to fail without API keys)"""
        success, response = self.run_test(
            "Sync from Notion",
            "POST",
            "tenants/sync-notion",
            400  # Expected to fail without API keys
        )
        return True  # We expect this to fail, so return True

    def test_whatsapp_notification(self, tenant_id, message):
        """Test WhatsApp notification (expected to fail without Twilio config)"""
        success, response = self.run_test(
            "Send WhatsApp Notification",
            "POST",
            "notifications/whatsapp",
            400,  # Expected to fail without Twilio config
            data={"tenant_id": tenant_id, "message": message}
        )
        return True  # We expect this to fail, so return True

    def cleanup_resources(self):
        """Clean up created resources"""
        print("\n🧹 Cleaning up test resources...")
        
        # Delete transactions
        for tx_id in self.created_resources['transactions']:
            # Transactions don't have delete endpoint, skip
            pass
        
        # Delete tenants
        for tenant_id in self.created_resources['tenants']:
            self.run_test("Cleanup Tenant", "DELETE", f"tenants/{tenant_id}", 200)
        
        # Delete banks
        for bank_id in self.created_resources['banks']:
            self.run_test("Cleanup Bank", "DELETE", f"banks/{bank_id}", 200)

def main():
    print("🚀 Starting Tenant Ledger API Tests...")
    
    # Setup
    tester = TenantLedgerAPITester()
    test_timestamp = datetime.now().strftime('%H%M%S')
    test_email = f"test_user_{test_timestamp}@example.com"
    test_password = "TestPass123!"
    test_name = f"Test User {test_timestamp}"

    try:
        # Test Authentication Flow
        print("\n📋 Testing Authentication...")
        if not tester.test_register(test_email, test_password, test_name):
            print("❌ Registration failed, trying login...")
            if not tester.test_login(test_email, test_password):
                print("❌ Both registration and login failed, stopping tests")
                return 1

        if not tester.test_get_me():
            print("❌ Get current user failed")
            return 1

        # Test Banks CRUD
        print("\n🏦 Testing Banks...")
        bank_id = tester.test_create_bank("Test Bank", "FR7612345678901234567890", 1000.0)
        if not bank_id:
            print("❌ Bank creation failed")
            return 1

        success, banks = tester.test_get_banks()
        if not success:
            print("❌ Get banks failed")
            return 1

        if not tester.test_update_bank(bank_id, name="Updated Test Bank", balance=1500.0):
            print("❌ Bank update failed")

        # Test Tenants CRUD
        print("\n🏠 Testing Tenants...")
        tenant_id = tester.test_create_tenant(
            "John Doe", 
            "123 Test Street, Paris", 
            850.0, 
            "john@example.com", 
            "+33123456789"
        )
        if not tenant_id:
            print("❌ Tenant creation failed")
            return 1

        success, tenants = tester.test_get_tenants()
        if not success:
            print("❌ Get tenants failed")
            return 1

        if not tester.test_get_tenant(tenant_id):
            print("❌ Get single tenant failed")

        if not tester.test_update_tenant(tenant_id, name="John Smith", rent_amount=900.0):
            print("❌ Tenant update failed")

        # Test Transactions
        print("\n💰 Testing Transactions...")
        tx_id = tester.test_create_transaction(bank_id, 850.0, "Rent payment from John", "rent")
        if not tx_id:
            print("❌ Transaction creation failed")
            return 1

        success, transactions = tester.test_get_transactions()
        if not success:
            print("❌ Get transactions failed")
            return 1

        success, filtered_transactions = tester.test_get_transactions(bank_id)
        if not success:
            print("❌ Get filtered transactions failed")

        # Test Transaction Matching
        if not tester.test_match_transaction(tx_id, tenant_id):
            print("❌ Transaction matching failed")

        # Test Payments
        print("\n💳 Testing Payments...")
        success, payments = tester.test_get_payments()
        if not success:
            print("❌ Get payments failed")

        success, tenant_payments = tester.test_get_payments(tenant_id)
        if not success:
            print("❌ Get tenant payments failed")

        # Test Dashboard
        print("\n📊 Testing Dashboard...")
        success, stats = tester.test_dashboard_stats()
        if not success:
            print("❌ Dashboard stats failed")
            return 1

        # Test External Integrations (expected to fail)
        print("\n🔗 Testing External Integrations...")
        tester.test_sync_notion()  # Expected to fail
        tester.test_whatsapp_notification(tenant_id, "Test message")  # Expected to fail

        # Test some delete operations
        print("\n🗑️ Testing Delete Operations...")
        # Create another tenant to delete
        temp_tenant_id = tester.test_create_tenant("Temp Tenant", "Temp Address", 500.0)
        if temp_tenant_id:
            tester.test_delete_tenant(temp_tenant_id)

        # Don't delete the main bank as it has transactions
        temp_bank_id = tester.test_create_bank("Temp Bank")
        if temp_bank_id:
            tester.test_delete_bank(temp_bank_id)

    finally:
        # Cleanup
        tester.cleanup_resources()

    # Print results
    print(f"\n📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())