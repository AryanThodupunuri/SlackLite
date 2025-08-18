#!/usr/bin/env python3

import requests
import sys
import json
import time
from datetime import datetime
import uuid

class SlackLiteAPITester:
    def __init__(self, base_url="https://quickmsg-35.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.username = None
        self.tests_run = 0
        self.tests_passed = 0
        
        # Test data
        self.test_user_1 = {
            "username": f"testuser1_{int(time.time())}",
            "email": f"test1_{int(time.time())}@example.com",
            "password": "TestPass123!"
        }
        
        self.test_user_2 = {
            "username": f"testuser2_{int(time.time())}",
            "email": f"test2_{int(time.time())}@example.com", 
            "password": "TestPass123!"
        }
        
        self.test_channel = {
            "name": f"test_channel_{int(time.time())}",
            "description": "Test channel for API testing",
            "is_public": True
        }

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
    def make_request(self, method, endpoint, data=None, files=None, expected_status=200):
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
            
        if files:
            # Remove content-type for file uploads
            headers.pop('Content-Type', None)
            
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, headers=headers, files=files)
                else:
                    response = requests.post(url, headers=headers, json=data)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            else:
                return False, f"Unsupported method: {method}"
                
            success = response.status_code == expected_status
            
            if success:
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                try:
                    error_detail = response.json().get('detail', response.text)
                except:
                    error_detail = response.text
                return False, f"Status {response.status_code}: {error_detail}"
                
        except Exception as e:
            return False, f"Request failed: {str(e)}"

    def test_health_check(self):
        """Test health endpoint"""
        success, response = self.make_request('GET', '/api/health')
        self.log_test("Health Check", success, "" if success else response)
        return success

    def test_user_registration(self):
        """Test user registration"""
        success, response = self.make_request('POST', '/api/auth/register', self.test_user_1)
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            self.username = response['user']['username']
            self.log_test("User Registration", True)
            return True
        else:
            self.log_test("User Registration", False, response)
            return False

    def test_user_login(self):
        """Test user login"""
        login_data = {
            "username": self.test_user_1["username"],
            "password": self.test_user_1["password"]
        }
        
        success, response = self.make_request('POST', '/api/auth/login', login_data)
        
        if success and 'access_token' in response:
            self.log_test("User Login", True)
            return True
        else:
            self.log_test("User Login", False, response)
            return False

    def test_get_current_user(self):
        """Test get current user endpoint"""
        success, response = self.make_request('GET', '/api/auth/me')
        
        if success and 'username' in response:
            self.log_test("Get Current User", True)
            return True
        else:
            self.log_test("Get Current User", False, response)
            return False

    def test_create_second_user(self):
        """Create second user for testing interactions"""
        success, response = self.make_request('POST', '/api/auth/register', self.test_user_2)
        
        if success and 'access_token' in response:
            self.log_test("Create Second User", True)
            return response['user']['id']
        else:
            self.log_test("Create Second User", False, response)
            return None

    def test_get_users(self):
        """Test get all users endpoint"""
        success, response = self.make_request('GET', '/api/users')
        
        if success and isinstance(response, list):
            self.log_test("Get Users List", True)
            return True
        else:
            self.log_test("Get Users List", False, response)
            return False

    def test_create_channel(self):
        """Test channel creation"""
        success, response = self.make_request('POST', '/api/channels', self.test_channel)
        
        if success and 'id' in response:
            self.log_test("Create Channel", True)
            return response['id']
        else:
            self.log_test("Create Channel", False, response)
            return None

    def test_get_channels(self):
        """Test get channels endpoint"""
        success, response = self.make_request('GET', '/api/channels')
        
        if success and isinstance(response, list):
            self.log_test("Get Channels List", True)
            return True
        else:
            self.log_test("Get Channels List", False, response)
            return False

    def test_join_channel(self, channel_id):
        """Test joining a channel"""
        success, response = self.make_request('POST', f'/api/channels/{channel_id}/join')
        
        if success:
            self.log_test("Join Channel", True)
            return True
        else:
            self.log_test("Join Channel", False, response)
            return False

    def test_send_channel_message(self, channel_id):
        """Test sending message to channel"""
        message_data = {
            "content": f"Test message from {self.username} at {datetime.now().isoformat()}",
            "channel_id": channel_id
        }
        
        success, response = self.make_request('POST', '/api/messages', message_data)
        
        if success and 'id' in response:
            self.log_test("Send Channel Message", True)
            return response['id']
        else:
            self.log_test("Send Channel Message", False, response)
            return None

    def test_send_direct_message(self, recipient_id):
        """Test sending direct message"""
        message_data = {
            "content": f"Direct message from {self.username} at {datetime.now().isoformat()}",
            "recipient_id": recipient_id
        }
        
        success, response = self.make_request('POST', '/api/messages', message_data)
        
        if success and 'id' in response:
            self.log_test("Send Direct Message", True)
            return response['id']
        else:
            self.log_test("Send Direct Message", False, response)
            return None

    def test_get_channel_messages(self, channel_id):
        """Test getting channel messages"""
        success, response = self.make_request('GET', f'/api/messages/channel/{channel_id}')
        
        if success and isinstance(response, list):
            self.log_test("Get Channel Messages", True)
            return True
        else:
            self.log_test("Get Channel Messages", False, response)
            return False

    def test_get_direct_messages(self, user_id):
        """Test getting direct messages"""
        success, response = self.make_request('GET', f'/api/messages/direct/{user_id}')
        
        if success and isinstance(response, list):
            self.log_test("Get Direct Messages", True)
            return True
        else:
            self.log_test("Get Direct Messages", False, response)
            return False

    def test_edit_message(self, message_id):
        """Test editing a message"""
        edit_data = {
            "content": f"Edited message at {datetime.now().isoformat()}"
        }
        
        success, response = self.make_request('PUT', f'/api/messages/{message_id}', edit_data)
        
        if success and 'content' in response:
            self.log_test("Edit Message", True)
            return True
        else:
            self.log_test("Edit Message", False, response)
            return False

    def test_add_reaction(self, message_id):
        """Test adding reaction to message"""
        reaction_data = {
            "emoji": "👍"
        }
        
        success, response = self.make_request('POST', f'/api/messages/{message_id}/reactions', reaction_data)
        
        if success:
            self.log_test("Add Reaction", True)
            return True
        else:
            self.log_test("Add Reaction", False, response)
            return False

    def test_file_upload(self):
        """Test file upload functionality"""
        # Create a simple test file
        test_content = b"This is a test file for SlackLite API testing"
        files = {'file': ('test.txt', test_content, 'text/plain')}
        
        success, response = self.make_request('POST', '/api/upload', files=files)
        
        if success and 'file_url' in response:
            self.log_test("File Upload", True)
            return response['file_url']
        else:
            self.log_test("File Upload", False, response)
            return None

    def test_leave_channel(self, channel_id):
        """Test leaving a channel"""
        success, response = self.make_request('POST', f'/api/channels/{channel_id}/leave')
        
        if success:
            self.log_test("Leave Channel", True)
            return True
        else:
            self.log_test("Leave Channel", False, response)
            return False

    def run_all_tests(self):
        """Run comprehensive API test suite"""
        print("🚀 Starting SlackLite API Test Suite")
        print(f"📡 Testing endpoint: {self.base_url}")
        print("=" * 60)
        
        # Health check
        if not self.test_health_check():
            print("❌ Health check failed - stopping tests")
            return False
            
        # Authentication tests
        if not self.test_user_registration():
            print("❌ User registration failed - stopping tests")
            return False
            
        if not self.test_user_login():
            print("❌ User login failed - stopping tests")
            return False
            
        if not self.test_get_current_user():
            print("❌ Get current user failed - stopping tests")
            return False
        
        # Create second user for interaction tests
        second_user_id = self.test_create_second_user()
        if not second_user_id:
            print("⚠️  Second user creation failed - skipping interaction tests")
        
        # User management tests
        self.test_get_users()
        
        # Channel tests
        channel_id = self.test_create_channel()
        if channel_id:
            self.test_get_channels()
            self.test_join_channel(channel_id)
            
            # Message tests
            message_id = self.test_send_channel_message(channel_id)
            if message_id:
                self.test_get_channel_messages(channel_id)
                self.test_edit_message(message_id)
                self.test_add_reaction(message_id)
            
            # Direct message tests
            if second_user_id:
                dm_message_id = self.test_send_direct_message(second_user_id)
                if dm_message_id:
                    self.test_get_direct_messages(second_user_id)
            
            # File upload test
            self.test_file_upload()
            
            # Leave channel test
            self.test_leave_channel(channel_id)
        
        # Print results
        print("=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed! Backend API is working correctly.")
            return True
        else:
            failed_tests = self.tests_run - self.tests_passed
            print(f"⚠️  {failed_tests} test(s) failed. Backend needs attention.")
            return False

def main():
    """Main test execution"""
    tester = SlackLiteAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())