#!/usr/bin/env python3
"""
Script to update all endpoints to use organization_id filtering
"""
import re

def update_server_py():
    with open('/app/backend/server.py', 'r') as f:
        content = f.read()
    
    # Pattern 1: {"user_id": current_user["id"]} -> get_filter_for_user(current_user)
    pattern1 = r'\{"user_id"\s*:\s*current_user\["id"\]\}'
    replacement1 = 'get_filter_for_user(current_user)'
    content = re.sub(pattern1, replacement1, content)
    
    # Pattern 2: user_id = current_user["id"] in dict creation for insert
    # We need to use prepare_document_for_insert
    # This is more complex, so we'll do it manually for critical endpoints
    
    with open('/app/backend/server.py', 'w') as f:
        f.write(content)
    
    print("✅ Updated server.py with organization filtering")

if __name__ == "__main__":
    update_server_py()
