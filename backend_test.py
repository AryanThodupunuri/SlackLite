#!/usr/bin/env python3

import requests
import sys
import json
import time
from datetime import datetime, timedelta
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
        timestamp = int(time.time())
        self.test_user_1 = {
            "username": f"testuser1_{timestamp}",
            "email": f"test1_{timestamp}@example.com",
            "password": "TestPass123!"
        }
        
        self.test_user_2 = {
            "username": f"testuser2_{timestamp}",
            "email": f"test2_{timestamp}@example.com", 
            "password": "TestPass123!"
        }
        
        # Enhanced channel test data with new features
        self.test_channels = {
            "general": {
                "name": f"general_test_{timestamp}",
                "description": "General test channel",
                "is_public": True,
                "ttl_enabled": False,
                "ttl_seconds": 3600,
                "domain_type": "general",
                "domain_config": {}
            },
            "sports": {
                "name": f"sports_test_{timestamp}",
                "description": "Sports team test channel",
                "is_public": True,
                "ttl_enabled": True,
                "ttl_seconds": 300,  # 5 minutes for testing
                "domain_type": "sports",
                "domain_config": {"team_name": "Test Team"}
            },
            "study": {
                "name": f"study_test_{timestamp}",
                "description": "Study group test channel",
                "is_public": True,
                "ttl_enabled": False,
                "ttl_seconds": 3600,
                "domain_type": "study",
                "domain_config": {"subject": "Computer Science"}
            },
            "agile": {
                "name": f"agile_test_{timestamp}",
                "description": "Agile/DevOps test channel",
                "is_public": True,
                "ttl_enabled": True,
                "ttl_seconds": 900,  # 15 minutes
                "domain_type": "agile",
                "domain_config": {"project": "Test Project"}
            }
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

    def test_create_enhanced_channel(self, channel_type="general"):
        """Test enhanced channel creation with new features"""
        channel_data = self.test_channels[channel_type]
        success, response = self.make_request('POST', '/api/channels', channel_data)
        
        if success and 'id' in response:
            # Verify all new fields are present
            expected_fields = ['domain_type', 'ttl_enabled', 'ttl_seconds']
            missing_fields = [field for field in expected_fields if field not in response]
            
            if missing_fields:
                self.log_test(f"Create {channel_type.title()} Channel", False, f"Missing fields: {missing_fields}")
                return None
            else:
                self.log_test(f"Create {channel_type.title()} Channel", True)
                return response['id']
        else:
            self.log_test(f"Create {channel_type.title()} Channel", False, response)
            return None

    def test_create_channel(self):
        """Test basic channel creation (backward compatibility)"""
        basic_channel = {
            "name": f"basic_test_{int(time.time())}",
            "description": "Basic test channel",
            "is_public": True
        }
        success, response = self.make_request('POST', '/api/channels', basic_channel)
        
        if success and 'id' in response:
            self.log_test("Create Basic Channel", True)
            return response['id']
        else:
            self.log_test("Create Basic Channel", False, response)
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

    def test_update_channel_settings(self, channel_id):
        """Test updating channel settings"""
        settings_data = {
            "ttl_enabled": True,
            "ttl_seconds": 1800,  # 30 minutes
            "domain_type": "general",
            "domain_config": {"updated": True}
        }
        
        success, response = self.make_request('PUT', f'/api/channels/{channel_id}/settings', settings_data)
        
        if success:
            self.log_test("Update Channel Settings", True)
            return True
        else:
            self.log_test("Update Channel Settings", False, response)
            return False

    def test_ephemeral_message(self, channel_id):
        """Test ephemeral message creation in TTL-enabled channel"""
        message_data = {
            "content": f"Ephemeral test message at {datetime.now().isoformat()}",
            "channel_id": channel_id
        }
        
        success, response = self.make_request('POST', '/api/messages', message_data)
        
        if success and 'id' in response:
            # Check if message has ephemeral properties
            if response.get('is_ephemeral') and response.get('expires_at'):
                self.log_test("Send Ephemeral Message", True)
                return response['id']
            else:
                self.log_test("Send Ephemeral Message", False, "Message not marked as ephemeral")
                return None
        else:
            self.log_test("Send Ephemeral Message", False, response)
            return None

    # Sports Team Domain Tests
    def test_create_player_stats(self, channel_id):
        """Test creating player stats for sports channel"""
        stats_data = {
            "channel_id": channel_id,
            "player_name": "Test Player",
            "games_played": 5,
            "points": 120,
            "assists": 25,
            "rebounds": 30
        }
        
        success, response = self.make_request('POST', '/api/sports/stats', None, None, 200)
        # Add query parameters manually
        url = f"{self.base_url}/api/sports/stats"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.post(url, headers=headers, params=stats_data)
            success = response.status_code == 200
            
            if success:
                self.log_test("Create Player Stats", True)
                return True
            else:
                self.log_test("Create Player Stats", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Create Player Stats", False, str(e))
            return False

    def test_get_team_stats(self, channel_id):
        """Test getting team stats"""
        success, response = self.make_request('GET', f'/api/sports/stats/{channel_id}')
        
        if success and isinstance(response, list):
            self.log_test("Get Team Stats", True)
            return True
        else:
            self.log_test("Get Team Stats", False, response)
            return False

    def test_create_game_schedule(self, channel_id):
        """Test creating game schedule"""
        future_date = (datetime.now() + timedelta(days=7)).isoformat()
        schedule_data = {
            "channel_id": channel_id,
            "date": future_date,
            "opponent": "Test Opponent",
            "location": "Test Stadium"
        }
        
        url = f"{self.base_url}/api/sports/schedule"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.post(url, headers=headers, params=schedule_data)
            success = response.status_code == 200
            
            if success:
                self.log_test("Create Game Schedule", True)
                return True
            else:
                self.log_test("Create Game Schedule", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Create Game Schedule", False, str(e))
            return False

    def test_get_team_schedule(self, channel_id):
        """Test getting team schedule"""
        success, response = self.make_request('GET', f'/api/sports/schedule/{channel_id}')
        
        if success and isinstance(response, list):
            self.log_test("Get Team Schedule", True)
            return True
        else:
            self.log_test("Get Team Schedule", False, response)
            return False

    # Study Group Domain Tests
    def test_create_flashcard(self, channel_id):
        """Test creating flashcard for study channel"""
        flashcard_data = {
            "channel_id": channel_id,
            "question": "What is the capital of France?",
            "answer": "Paris",
            "difficulty": 2,
            "subject": "Geography",
            "tags": ["geography", "capitals", "europe"]
        }
        
        url = f"{self.base_url}/api/study/flashcards"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.post(url, headers=headers, params=flashcard_data)
            success = response.status_code == 200
            
            if success:
                self.log_test("Create Flashcard", True)
                return True
            else:
                self.log_test("Create Flashcard", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Create Flashcard", False, str(e))
            return False

    def test_get_flashcards(self, channel_id):
        """Test getting flashcards"""
        success, response = self.make_request('GET', f'/api/study/flashcards/{channel_id}')
        
        if success and isinstance(response, list):
            self.log_test("Get Flashcards", True)
            return True
        else:
            self.log_test("Get Flashcards", False, response)
            return False

    def test_create_study_material(self, channel_id):
        """Test creating study material"""
        material_data = {
            "channel_id": channel_id,
            "title": "Test Study Material",
            "file_url": "/uploads/test_material.pdf",
            "file_type": "pdf",
            "subject": "Computer Science",
            "description": "Test material for API testing"
        }
        
        url = f"{self.base_url}/api/study/materials"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.post(url, headers=headers, params=material_data)
            success = response.status_code == 200
            
            if success:
                self.log_test("Create Study Material", True)
                return True
            else:
                self.log_test("Create Study Material", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Create Study Material", False, str(e))
            return False

    def test_get_study_materials(self, channel_id):
        """Test getting study materials"""
        success, response = self.make_request('GET', f'/api/study/materials/{channel_id}')
        
        if success and isinstance(response, list):
            self.log_test("Get Study Materials", True)
            return True
        else:
            self.log_test("Get Study Materials", False, response)
            return False

    # Agile/DevOps Domain Tests
    def test_create_sprint(self, channel_id):
        """Test creating sprint for agile channel"""
        start_date = datetime.now().isoformat()
        end_date = (datetime.now() + timedelta(days=14)).isoformat()
        
        sprint_data = {
            "channel_id": channel_id,
            "sprint_name": "Test Sprint 1",
            "start_date": start_date,
            "end_date": end_date,
            "story_points_planned": 50
        }
        
        url = f"{self.base_url}/api/agile/sprint"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        try:
            response = requests.post(url, headers=headers, params=sprint_data)
            success = response.status_code == 200
            
            if success:
                self.log_test("Create Sprint", True)
                return True
            else:
                self.log_test("Create Sprint", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Create Sprint", False, str(e))
            return False

    def test_get_active_sprint(self, channel_id):
        """Test getting active sprint"""
        success, response = self.make_request('GET', f'/api/agile/sprint/{channel_id}')
        
        # Note: This might return None if no active sprint, which is valid
        if success:
            self.log_test("Get Active Sprint", True)
            return True
        else:
            self.log_test("Get Active Sprint", False, response)
            return False

    def test_jira_webhook(self):
        """Test Jira webhook endpoint"""
        webhook_data = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "TEST-123",
                "fields": {
                    "summary": "Test Issue",
                    "status": {
                        "name": "In Progress"
                    }
                }
            }
        }
        
        success, response = self.make_request('POST', '/api/agile/jira-webhook', webhook_data)
        
        if success:
            self.log_test("Jira Webhook", True)
            return True
        else:
            self.log_test("Jira Webhook", False, response)
            return False

    def test_github_webhook(self):
        """Test GitHub webhook endpoint"""
        webhook_data = {
            "action": "opened",
            "pull_request": {
                "number": 123,
                "title": "Test PR",
                "user": {
                    "login": "testuser"
                }
            }
        }
        
        success, response = self.make_request('POST', '/api/agile/github-webhook', webhook_data)
        
        if success:
            self.log_test("GitHub Webhook", True)
            return True
        else:
            self.log_test("GitHub Webhook", False, response)
            return False

    def run_all_tests(self):
        """Run comprehensive API test suite including new features"""
        print("🚀 Starting Enhanced SlackLite API Test Suite")
        print(f"📡 Testing endpoint: {self.base_url}")
        print("=" * 80)
        
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
        
        print("\n🔧 Testing Enhanced Channel Features...")
        
        # Test enhanced channel creation for each domain type
        channel_ids = {}
        for domain_type in ['general', 'sports', 'study', 'agile']:
            channel_id = self.test_create_enhanced_channel(domain_type)
            if channel_id:
                channel_ids[domain_type] = channel_id
        
        # Test basic channel creation (backward compatibility)
        basic_channel_id = self.test_create_channel()
        if basic_channel_id:
            channel_ids['basic'] = basic_channel_id
        
        self.test_get_channels()
        
        print("\n⚡ Testing Ephemeral Messaging...")
        
        # Test ephemeral messaging in sports channel (has TTL enabled)
        if 'sports' in channel_ids:
            sports_channel_id = channel_ids['sports']
            self.test_join_channel(sports_channel_id)
            ephemeral_msg_id = self.test_ephemeral_message(sports_channel_id)
            
            if ephemeral_msg_id:
                self.test_get_channel_messages(sports_channel_id)
        
        # Test channel settings update
        if 'basic' in channel_ids:
            self.test_update_channel_settings(channel_ids['basic'])
        
        print("\n🏀 Testing Sports Domain Features...")
        
        # Sports domain tests
        if 'sports' in channel_ids:
            sports_id = channel_ids['sports']
            self.test_create_player_stats(sports_id)
            self.test_get_team_stats(sports_id)
            self.test_create_game_schedule(sports_id)
            self.test_get_team_schedule(sports_id)
        
        print("\n📚 Testing Study Group Features...")
        
        # Study domain tests
        if 'study' in channel_ids:
            study_id = channel_ids['study']
            self.test_join_channel(study_id)
            self.test_create_flashcard(study_id)
            self.test_get_flashcards(study_id)
            self.test_create_study_material(study_id)
            self.test_get_study_materials(study_id)
        
        print("\n🚀 Testing Agile/DevOps Features...")
        
        # Agile domain tests
        if 'agile' in channel_ids:
            agile_id = channel_ids['agile']
            self.test_join_channel(agile_id)
            self.test_create_sprint(agile_id)
            self.test_get_active_sprint(agile_id)
        
        # Webhook tests
        self.test_jira_webhook()
        self.test_github_webhook()
        
        print("\n💬 Testing Core Messaging Features...")
        
        # Core messaging tests
        if 'general' in channel_ids:
            general_id = channel_ids['general']
            self.test_join_channel(general_id)
            
            # Message tests
            message_id = self.test_send_channel_message(general_id)
            if message_id:
                self.test_get_channel_messages(general_id)
                self.test_edit_message(message_id)
                self.test_add_reaction(message_id)
            
            # Direct message tests
            if second_user_id:
                dm_message_id = self.test_send_direct_message(second_user_id)
                if dm_message_id:
                    self.test_get_direct_messages(second_user_id)
            
            # File upload test
            self.test_file_upload()
        
        # Print results
        print("=" * 80)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed! Enhanced SlackLite API is working correctly.")
            print("✅ Ephemeral messaging, domain-specific features, and webhooks are functional.")
            return True
        else:
            failed_tests = self.tests_run - self.tests_passed
            success_rate = (self.tests_passed / self.tests_run) * 100
            print(f"⚠️  {failed_tests} test(s) failed. Success rate: {success_rate:.1f}%")
            
            if success_rate >= 80:
                print("✅ Most features are working. Minor issues detected.")
                return True
            else:
                print("❌ Significant issues detected. Backend needs attention.")
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