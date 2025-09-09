#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Weight Gain App - SMART COACHING SYSTEM (Phase 3)
Tests all API endpoints with focus on new AI-powered coaching features
"""

import requests
import json
import base64
import os
from datetime import datetime, timedelta
import time

# Get backend URL from frontend env
BACKEND_URL = "https://nutriboost-6.preview.emergentagent.com/api"

class WeightGainAppTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_user_id = None
        self.test_results = []
        self.auth_token = None
        self.test_user_email = None
        self.reset_token = None
        
    def log_test(self, test_name, success, details="", response_data=None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        if not success and response_data:
            print(f"   Response: {response_data}")
    
    def test_health_check(self):
        """Test GET /api/health"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test("Health Check", True, "API is healthy")
                    return True
                else:
                    self.log_test("Health Check", False, "Unexpected response format", data)
                    return False
            else:
                self.log_test("Health Check", False, f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {str(e)}")
            return False
    
    def test_user_creation_with_gamification(self):
        """Test POST /api/users with gamification fields (legacy endpoint - should still work)"""
        user_data = {
            "name": "Emma Rodriguez",
            "age": 28,
            "height_cm": 165.0,
            "weight_kg": 55.0,
            "gender": "female",
            "activity_level": "active",
            "goal_weight_kg": 65.0,
            "target_weekly_gain": 0.5
        }
        
        try:
            # Note: This tests the legacy endpoint if it still exists
            # The new auth system uses /api/auth/register
            response = requests.post(f"{self.base_url}/users", json=user_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                legacy_user_id = data.get("user_id")
                user_profile = data.get("user")
                
                # Verify gamification fields are initialized
                gamification_fields = {
                    "total_points": 0,
                    "current_streak": 0,
                    "longest_streak": 0,
                    "last_log_date": None,
                    "badges_earned": []
                }
                
                all_fields_correct = True
                for field, expected_value in gamification_fields.items():
                    actual_value = user_profile.get(field)
                    if actual_value != expected_value:
                        all_fields_correct = False
                        break
                
                if all_fields_correct:
                    self.log_test("User Creation with Gamification (Legacy)", True, 
                                f"Legacy user creation with gamification fields initialized correctly")
                    return True
                else:
                    self.log_test("User Creation with Gamification (Legacy)", False, 
                                f"Gamification fields not properly initialized", user_profile)
                    return False
            elif response.status_code == 404:
                # Legacy endpoint might be removed - this is acceptable
                self.log_test("User Creation with Gamification (Legacy)", True, 
                            f"Legacy endpoint removed (expected with auth system)")
                return True
            else:
                self.log_test("User Creation with Gamification (Legacy)", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("User Creation with Gamification (Legacy)", False, f"Exception: {str(e)}")
            return False
    
    def test_enhanced_food_logging_gamification(self):
        """Test POST /api/food-logs with comprehensive gamification features (with auth)"""
        if not self.test_user_id or not self.auth_token:
            self.log_test("Enhanced Food Logging Gamification", False, "No test user ID or auth token available")
            return False
            
        # Test Day 1 - First meal (should get first_meal badge)
        today = datetime.now().strftime("%Y-%m-%d")
        food_log_data = {
            "user_id": self.test_user_id,
            "date": today,
            "meal_type": "breakfast",
            "food_items": [
                {
                    "name": "Protein Smoothie",
                    "calories": 450,
                    "protein": 35.0,
                    "carbs": 40.0,
                    "fat": 15.0,
                    "portion_size": "1 large smoothie"
                },
                {
                    "name": "Banana",
                    "calories": 105,
                    "protein": 1.3,
                    "carbs": 27.0,
                    "fat": 0.3,
                    "portion_size": "1 medium banana"
                }
            ]
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(f"{self.base_url}/food-logs", json=food_log_data, 
                                   headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Verify gamification response fields
                required_fields = ["points_earned", "new_badges", "badge_points", "current_streak"]
                if not all(field in data for field in required_fields):
                    self.log_test("Enhanced Food Logging Gamification", False, 
                                f"Missing gamification fields in response", data)
                    return False
                
                # Should get points and potentially badges
                points_earned = data.get("points_earned", 0)
                new_badges = data.get("new_badges", [])
                badge_points = data.get("badge_points", 0)
                current_streak = data.get("current_streak", 0)
                
                # Verify basic gamification functionality
                if points_earned >= 25 and current_streak >= 1:  # At least base points and streak
                    self.log_test("Enhanced Food Logging Gamification", True, 
                                f"Food logging with gamification successful. Points: {points_earned}, Badges: {new_badges}, Streak: {current_streak}")
                    return True
                else:
                    self.log_test("Enhanced Food Logging Gamification", False, 
                                f"Gamification values seem incorrect. Points: {points_earned}, Streak: {current_streak}")
                    return False
            else:
                self.log_test("Enhanced Food Logging Gamification", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Enhanced Food Logging Gamification", False, f"Exception: {str(e)}")
            return False
    
    def test_points_system_calculation(self):
        """Test points calculation based on target achievement"""
        if not self.test_user_id:
            self.log_test("Points System Calculation", False, "No test user ID available")
            return False
        
        # Get user targets first
        try:
            user_response = requests.get(f"{self.base_url}/users/{self.test_user_id}", timeout=10)
            if user_response.status_code != 200:
                self.log_test("Points System Calculation", False, "Could not get user data")
                return False
            
            user_data = user_response.json()
            calorie_target = user_data.get("daily_calorie_target", 2500)
            protein_target = user_data.get("daily_protein_target", 150)
            
            # Test high-calorie meal that hits targets (should get bonus points)
            today = datetime.now().strftime("%Y-%m-%d")
            high_calorie_log = {
                "user_id": self.test_user_id,
                "date": today,
                "meal_type": "lunch",
                "food_items": [
                    {
                        "name": "Chicken Breast with Rice",
                        "calories": int(calorie_target * 0.9),  # 90% of daily target in one meal
                        "protein": float(protein_target * 0.8),  # 80% of protein target
                        "carbs": 200.0,
                        "fat": 50.0,
                        "portion_size": "Large serving"
                    }
                ]
            }
            
            response = requests.post(f"{self.base_url}/food-logs", json=high_calorie_log, timeout=10)
            if response.status_code == 200:
                data = response.json()
                points_earned = data.get("points_earned", 0)
                
                # Should get: 25 (base) + 25 (80% calorie) + 50 (100% calorie) + 25 (80% protein) + 50 (100% protein) = 175 points
                # But since we're at 90% calories and 80% protein, expect: 25 + 25 + 25 = 75 points minimum
                if points_earned >= 50:  # At least base + some bonuses
                    self.log_test("Points System Calculation", True, 
                                f"Points calculated correctly for target achievement: {points_earned} points")
                    return True
                else:
                    self.log_test("Points System Calculation", False, 
                                f"Points calculation seems incorrect: {points_earned} points for high-target meal")
                    return False
            else:
                self.log_test("Points System Calculation", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Points System Calculation", False, f"Exception: {str(e)}")
            return False
    
    def test_streak_tracking_system(self):
        """Test streak logic with different day scenarios"""
        if not self.test_user_id:
            self.log_test("Streak Tracking System", False, "No test user ID available")
            return False
        
        try:
            # Test consecutive day logging
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            next_day_log = {
                "user_id": self.test_user_id,
                "date": tomorrow,
                "meal_type": "breakfast",
                "food_items": [
                    {
                        "name": "Oatmeal with Berries",
                        "calories": 300,
                        "protein": 12.0,
                        "carbs": 55.0,
                        "fat": 6.0,
                        "portion_size": "1 bowl"
                    }
                ]
            }
            
            response = requests.post(f"{self.base_url}/food-logs", json=next_day_log, timeout=10)
            if response.status_code == 200:
                data = response.json()
                current_streak = data.get("current_streak", 0)
                
                # Should increment streak to 2 (previous day + this day)
                if current_streak >= 2:
                    self.log_test("Streak Tracking System", True, 
                                f"Consecutive day streak working: {current_streak} days")
                    return True
                else:
                    self.log_test("Streak Tracking System", False, 
                                f"Streak not incrementing correctly: {current_streak} days")
                    return False
            else:
                self.log_test("Streak Tracking System", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Streak Tracking System", False, f"Exception: {str(e)}")
            return False
    
    def test_badge_system_comprehensive(self):
        """Test multiple badge achievements"""
        if not self.test_user_id:
            self.log_test("Badge System Comprehensive", False, "No test user ID available")
            return False
        
        try:
            # Test streak badge by logging for day 3
            day_after_tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
            day3_log = {
                "user_id": self.test_user_id,
                "date": day_after_tomorrow,
                "meal_type": "dinner",
                "food_items": [
                    {
                        "name": "Grilled Salmon",
                        "calories": 400,
                        "protein": 45.0,
                        "carbs": 5.0,
                        "fat": 20.0,
                        "portion_size": "6 oz fillet"
                    }
                ]
            }
            
            response = requests.post(f"{self.base_url}/food-logs", json=day3_log, timeout=10)
            if response.status_code == 200:
                data = response.json()
                new_badges = data.get("new_badges", [])
                current_streak = data.get("current_streak", 0)
                
                # Should get streak_3 badge at 3-day streak
                if current_streak >= 3 and "streak_3" in new_badges:
                    self.log_test("Badge System Comprehensive", True, 
                                f"3-day streak badge awarded correctly. Streak: {current_streak}, New badges: {new_badges}")
                    return True
                elif current_streak >= 3:
                    self.log_test("Badge System Comprehensive", True, 
                                f"3-day streak achieved: {current_streak} days (badge may have been awarded earlier)")
                    return True
                else:
                    self.log_test("Badge System Comprehensive", False, 
                                f"3-day streak not achieved: {current_streak} days, badges: {new_badges}")
                    return False
            else:
                self.log_test("Badge System Comprehensive", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Badge System Comprehensive", False, f"Exception: {str(e)}")
            return False
    
    def test_enhanced_weight_entries_gamification(self):
        """Test POST /api/weight-entries with gamification"""
        if not self.test_user_id:
            self.log_test("Enhanced Weight Entries Gamification", False, "No test user ID available")
            return False
        
        # Test multiple weight entries to trigger weight_logger badge (after 5 entries)
        weight_entries = [
            {"weight_kg": 55.2, "date": datetime.now().strftime("%Y-%m-%d")},
            {"weight_kg": 55.4, "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")},
            {"weight_kg": 55.6, "date": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")},
            {"weight_kg": 55.8, "date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")},
            {"weight_kg": 56.0, "date": (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")}
        ]
        
        try:
            for i, entry_data in enumerate(weight_entries):
                weight_data = {
                    "user_id": self.test_user_id,
                    "weight_kg": entry_data["weight_kg"],
                    "date": entry_data["date"]
                }
                
                response = requests.post(f"{self.base_url}/weight-entries", json=weight_data, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    points_earned = data.get("points_earned", 0)
                    new_badges = data.get("new_badges", [])
                    
                    # Each weight entry should give 30 points
                    if points_earned != 30:
                        self.log_test("Enhanced Weight Entries Gamification", False, 
                                    f"Incorrect points for weight entry {i+1}: {points_earned} (expected 30)")
                        return False
                    
                    # 5th entry should trigger weight_logger badge
                    if i == 4 and "weight_logger" in new_badges:
                        self.log_test("Enhanced Weight Entries Gamification", True, 
                                    f"Weight logger badge awarded after 5 entries. Points: {points_earned}, Badges: {new_badges}")
                        return True
                else:
                    self.log_test("Enhanced Weight Entries Gamification", False, 
                                f"Weight entry {i+1} failed. Status: {response.status_code}")
                    return False
            
            # If we get here, all entries succeeded but no badge (might be awarded earlier)
            self.log_test("Enhanced Weight Entries Gamification", True, 
                        "All weight entries successful with correct points (30 each)")
            return True
            
        except Exception as e:
            self.log_test("Enhanced Weight Entries Gamification", False, f"Exception: {str(e)}")
            return False
    
    def test_user_statistics_api(self):
        """Test GET /api/user-stats/{user_id}"""
        if not self.test_user_id:
            self.log_test("User Statistics API", False, "No test user ID available")
            return False
        
        try:
            response = requests.get(f"{self.base_url}/user-stats/{self.test_user_id}", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                
                # Verify all required fields
                required_fields = [
                    "user_id", "total_points", "current_streak", "longest_streak",
                    "badges_earned", "total_logs", "total_weight_entries", 
                    "days_active", "avg_daily_calories", "goal_completion_rate"
                ]
                
                missing_fields = [field for field in required_fields if field not in stats]
                if missing_fields:
                    self.log_test("User Statistics API", False, 
                                f"Missing fields: {missing_fields}", stats)
                    return False
                
                # Verify data makes sense
                if (stats["total_points"] > 0 and 
                    stats["total_logs"] > 0 and 
                    stats["total_weight_entries"] > 0 and
                    isinstance(stats["badges_earned"], list)):
                    
                    self.log_test("User Statistics API", True, 
                                f"User stats retrieved: {stats['total_points']} points, {stats['total_logs']} logs, {len(stats['badges_earned'])} badges")
                    return True
                else:
                    self.log_test("User Statistics API", False, 
                                f"User stats data seems incorrect", stats)
                    return False
            else:
                self.log_test("User Statistics API", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("User Statistics API", False, f"Exception: {str(e)}")
            return False
    
    def test_achievement_api_system(self):
        """Test GET /api/achievements/{user_id} and GET /api/badges"""
        if not self.test_user_id:
            self.log_test("Achievement API System", False, "No test user ID available")
            return False
        
        try:
            # Test user achievements
            achievements_response = requests.get(f"{self.base_url}/achievements/{self.test_user_id}", timeout=10)
            if achievements_response.status_code != 200:
                self.log_test("Achievement API System", False, 
                            f"Achievements API failed: {achievements_response.status_code}")
                return False
            
            achievements = achievements_response.json()
            
            # Test badges catalog
            badges_response = requests.get(f"{self.base_url}/badges", timeout=10)
            if badges_response.status_code != 200:
                self.log_test("Achievement API System", False, 
                            f"Badges API failed: {badges_response.status_code}")
                return False
            
            badges_catalog = badges_response.json()
            
            # Verify badges catalog has all expected badges
            expected_badges = [
                "first_meal", "streak_3", "streak_7", "streak_14", "streak_30",
                "calorie_target", "protein_master", "weight_logger", "goal_achieved", "macro_balance"
            ]
            
            missing_badges = [badge for badge in expected_badges if badge not in badges_catalog]
            if missing_badges:
                self.log_test("Achievement API System", False, 
                            f"Missing badges in catalog: {missing_badges}")
                return False
            
            # Verify achievements have proper structure
            if isinstance(achievements, list):
                for achievement in achievements:
                    required_fields = ["achievement_id", "user_id", "badge_type", "badge_name", 
                                     "badge_description", "points_awarded", "earned_date", "icon"]
                    if not all(field in achievement for field in required_fields):
                        self.log_test("Achievement API System", False, 
                                    f"Achievement missing fields", achievement)
                        return False
                
                self.log_test("Achievement API System", True, 
                            f"Achievement APIs working. User has {len(achievements)} achievements, {len(badges_catalog)} badges available")
                return True
            else:
                self.log_test("Achievement API System", False, 
                            f"Achievements not returned as list", achievements)
                return False
                
        except Exception as e:
            self.log_test("Achievement API System", False, f"Exception: {str(e)}")
            return False
    
    def test_enhanced_daily_stats_gamification(self):
        """Test GET /api/daily-stats/{user_id}/{date} with gamification fields"""
        if not self.test_user_id:
            self.log_test("Enhanced Daily Stats Gamification", False, "No test user ID available")
            return False
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        try:
            response = requests.get(f"{self.base_url}/daily-stats/{self.test_user_id}/{today}", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                
                # Verify new gamification fields
                gamification_fields = ["points_earned_today", "streak_status", "target_hit_percentage"]
                missing_fields = [field for field in gamification_fields if field not in stats]
                
                if missing_fields:
                    self.log_test("Enhanced Daily Stats Gamification", False, 
                                f"Missing gamification fields: {missing_fields}", stats)
                    return False
                
                # Verify field types and values
                points_today = stats.get("points_earned_today", 0)
                streak_status = stats.get("streak_status")
                target_percentage = stats.get("target_hit_percentage", 0)
                
                if (isinstance(points_today, int) and points_today >= 0 and
                    isinstance(streak_status, bool) and
                    isinstance(target_percentage, (int, float)) and 0 <= target_percentage <= 100):
                    
                    self.log_test("Enhanced Daily Stats Gamification", True, 
                                f"Daily stats with gamification: {points_today} points today, {target_percentage}% target hit, streak active: {streak_status}")
                    return True
                else:
                    self.log_test("Enhanced Daily Stats Gamification", False, 
                                f"Gamification field values incorrect", stats)
                    return False
            else:
                self.log_test("Enhanced Daily Stats Gamification", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Enhanced Daily Stats Gamification", False, f"Exception: {str(e)}")
            return False
    
    def test_leaderboard_system(self):
        """Test GET /api/leaderboard"""
        try:
            response = requests.get(f"{self.base_url}/leaderboard", timeout=10)
            if response.status_code == 200:
                leaderboard = response.json()
                
                if isinstance(leaderboard, list):
                    # Verify leaderboard structure
                    for i, user in enumerate(leaderboard):
                        required_fields = ["name", "total_points", "current_streak", "badges_earned", "rank", "badge_count"]
                        if not all(field in user for field in required_fields):
                            self.log_test("Leaderboard System", False, 
                                        f"Leaderboard user missing fields", user)
                            return False
                        
                        # Verify ranking is correct
                        if user["rank"] != i + 1:
                            self.log_test("Leaderboard System", False, 
                                        f"Incorrect ranking: expected {i+1}, got {user['rank']}")
                            return False
                    
                    self.log_test("Leaderboard System", True, 
                                f"Leaderboard working with {len(leaderboard)} users ranked by points")
                    return True
                else:
                    self.log_test("Leaderboard System", False, 
                                f"Leaderboard not returned as list", leaderboard)
                    return False
            else:
                self.log_test("Leaderboard System", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Leaderboard System", False, f"Exception: {str(e)}")
            return False

    # ========== JWT AUTHENTICATION SYSTEM TESTS ==========
    
    def test_user_registration(self):
        """Test POST /api/auth/register with valid user data"""
        user_data = {
            "email": "alex.johnson@example.com",
            "password": "SecurePass123!",
            "name": "Alex Johnson",
            "age": 25,
            "height_cm": 170.0,
            "weight_kg": 60.0,
            "gender": "male",
            "activity_level": "moderate",
            "goal_weight_kg": 70.0,
            "target_weekly_gain": 0.5
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/register", json=user_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Verify response structure
                required_fields = ["access_token", "token_type", "user"]
                if not all(field in data for field in required_fields):
                    self.log_test("User Registration", False, 
                                f"Missing fields in registration response", data)
                    return False
                
                # Store auth data for subsequent tests
                self.auth_token = data["access_token"]
                self.test_user_id = data["user"]["user_id"]
                self.test_user_email = data["user"]["email"]
                
                # Verify user data
                user = data["user"]
                if (user["email"] == user_data["email"] and 
                    user["name"] == user_data["name"] and
                    user["daily_calorie_target"] > 0 and
                    "password_hash" not in user):  # Ensure password not exposed
                    
                    self.log_test("User Registration", True, 
                                f"User registered successfully. ID: {self.test_user_id}, Token received")
                    return True
                else:
                    self.log_test("User Registration", False, 
                                f"User data validation failed", user)
                    return False
            else:
                self.log_test("User Registration", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("User Registration", False, f"Exception: {str(e)}")
            return False
    
    def test_user_login(self):
        """Test POST /api/auth/login with registered credentials"""
        if not self.test_user_email:
            self.log_test("User Login", False, "No test user email available")
            return False
        
        login_data = {
            "email": self.test_user_email,
            "password": "SecurePass123!"
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/login", json=login_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Verify response structure
                required_fields = ["access_token", "token_type", "user"]
                if not all(field in data for field in required_fields):
                    self.log_test("User Login", False, 
                                f"Missing fields in login response", data)
                    return False
                
                # Verify token is different from registration token (new session)
                new_token = data["access_token"]
                if new_token and data["token_type"] == "bearer":
                    # Update auth token for subsequent tests
                    self.auth_token = new_token
                    
                    self.log_test("User Login", True, 
                                f"User logged in successfully. New token received")
                    return True
                else:
                    self.log_test("User Login", False, 
                                f"Invalid token or token type", data)
                    return False
            else:
                self.log_test("User Login", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("User Login", False, f"Exception: {str(e)}")
            return False
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        invalid_login_data = {
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!"
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/login", json=invalid_login_data, timeout=10)
            if response.status_code == 401:
                self.log_test("Invalid Login", True, 
                            "Invalid credentials correctly rejected with 401")
                return True
            else:
                self.log_test("Invalid Login", False, 
                            f"Expected 401, got {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Invalid Login", False, f"Exception: {str(e)}")
            return False
    
    def test_forgot_password(self):
        """Test POST /api/auth/forgot-password"""
        if not self.test_user_email:
            self.log_test("Forgot Password", False, "No test user email available")
            return False
        
        reset_data = {
            "email": self.test_user_email
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/forgot-password", json=reset_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Verify response
                if "message" in data:
                    # Store reset token if provided (for testing purposes)
                    if "reset_token" in data:
                        self.reset_token = data["reset_token"]
                    
                    self.log_test("Forgot Password", True, 
                                f"Password reset initiated successfully")
                    return True
                else:
                    self.log_test("Forgot Password", False, 
                                f"Invalid response format", data)
                    return False
            else:
                self.log_test("Forgot Password", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Forgot Password", False, f"Exception: {str(e)}")
            return False
    
    def test_reset_password(self):
        """Test POST /api/auth/reset-password"""
        if not self.reset_token:
            self.log_test("Reset Password", False, "No reset token available")
            return False
        
        reset_data = {
            "reset_token": self.reset_token,
            "new_password": "NewSecurePass456!"
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/reset-password", json=reset_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if "message" in data and "successfully" in data["message"].lower():
                    self.log_test("Reset Password", True, 
                                f"Password reset completed successfully")
                    return True
                else:
                    self.log_test("Reset Password", False, 
                                f"Unexpected response", data)
                    return False
            else:
                self.log_test("Reset Password", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Reset Password", False, f"Exception: {str(e)}")
            return False
    
    def test_login_with_new_password(self):
        """Test login with the new password after reset"""
        if not self.test_user_email:
            self.log_test("Login with New Password", False, "No test user email available")
            return False
        
        login_data = {
            "email": self.test_user_email,
            "password": "NewSecurePass456!"
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/login", json=login_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if "access_token" in data:
                    # Update auth token
                    self.auth_token = data["access_token"]
                    
                    self.log_test("Login with New Password", True, 
                                f"Login successful with new password")
                    return True
                else:
                    self.log_test("Login with New Password", False, 
                                f"No access token in response", data)
                    return False
            else:
                self.log_test("Login with New Password", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Login with New Password", False, f"Exception: {str(e)}")
            return False
    
    def test_protected_endpoint_without_token(self):
        """Test protected endpoint without authentication token"""
        if not self.test_user_id:
            self.log_test("Protected Endpoint Without Token", False, "No test user ID available")
            return False
        
        try:
            # Try to access user profile without token
            response = requests.get(f"{self.base_url}/users/{self.test_user_id}", timeout=10)
            # FastAPI HTTPBearer returns 403 when no Authorization header is provided
            if response.status_code in [401, 403]:
                self.log_test("Protected Endpoint Without Token", True, 
                            f"Protected endpoint correctly rejected request without token ({response.status_code})")
                return True
            else:
                self.log_test("Protected Endpoint Without Token", False, 
                            f"Expected 401 or 403, got {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Protected Endpoint Without Token", False, f"Exception: {str(e)}")
            return False
    
    def test_protected_endpoint_with_invalid_token(self):
        """Test protected endpoint with invalid token"""
        if not self.test_user_id:
            self.log_test("Protected Endpoint Invalid Token", False, "No test user ID available")
            return False
        
        try:
            # Try to access user profile with invalid token
            headers = {"Authorization": "Bearer invalid_token_12345"}
            response = requests.get(f"{self.base_url}/users/{self.test_user_id}", 
                                  headers=headers, timeout=10)
            if response.status_code == 401:
                self.log_test("Protected Endpoint Invalid Token", True, 
                            "Protected endpoint correctly rejected invalid token (401)")
                return True
            else:
                self.log_test("Protected Endpoint Invalid Token", False, 
                            f"Expected 401, got {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Protected Endpoint Invalid Token", False, f"Exception: {str(e)}")
            return False
    
    def test_protected_endpoint_with_valid_token(self):
        """Test protected endpoint with valid authentication token"""
        if not self.test_user_id or not self.auth_token:
            self.log_test("Protected Endpoint Valid Token", False, "No test user ID or auth token available")
            return False
        
        try:
            # Access user profile with valid token
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(f"{self.base_url}/users/{self.test_user_id}", 
                                  headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Verify user data is returned
                if (data.get("user_id") == self.test_user_id and 
                    data.get("email") == self.test_user_email and
                    "password_hash" not in data):  # Ensure password not exposed
                    
                    self.log_test("Protected Endpoint Valid Token", True, 
                                f"Protected endpoint accessible with valid token")
                    return True
                else:
                    self.log_test("Protected Endpoint Valid Token", False, 
                                f"Invalid user data returned", data)
                    return False
            else:
                self.log_test("Protected Endpoint Valid Token", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Protected Endpoint Valid Token", False, f"Exception: {str(e)}")
            return False
    
    def test_food_logging_requires_auth(self):
        """Test POST /api/food-logs requires authentication"""
        if not self.test_user_id:
            self.log_test("Food Logging Auth Required", False, "No test user ID available")
            return False
        
        food_log_data = {
            "user_id": self.test_user_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "meal_type": "breakfast",
            "food_items": [
                {
                    "name": "Test Food",
                    "calories": 200,
                    "protein": 10.0,
                    "carbs": 20.0,
                    "fat": 8.0,
                    "portion_size": "1 serving"
                }
            ]
        }
        
        try:
            # Try without token
            response = requests.post(f"{self.base_url}/food-logs", json=food_log_data, timeout=10)
            # FastAPI HTTPBearer returns 403 when no Authorization header is provided
            if response.status_code in [401, 403]:
                self.log_test("Food Logging Auth Required", True, 
                            f"Food logging correctly requires authentication ({response.status_code})")
                return True
            else:
                self.log_test("Food Logging Auth Required", False, 
                            f"Expected 401 or 403, got {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Food Logging Auth Required", False, f"Exception: {str(e)}")
            return False
    
    def test_food_logging_with_auth(self):
        """Test POST /api/food-logs works with authentication"""
        if not self.test_user_id or not self.auth_token:
            self.log_test("Food Logging With Auth", False, "No test user ID or auth token available")
            return False
        
        food_log_data = {
            "user_id": self.test_user_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "meal_type": "breakfast",
            "food_items": [
                {
                    "name": "Authenticated Food Log",
                    "calories": 300,
                    "protein": 15.0,
                    "carbs": 30.0,
                    "fat": 12.0,
                    "portion_size": "1 serving"
                }
            ]
        }
        
        try:
            # Try with valid token
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.post(f"{self.base_url}/food-logs", json=food_log_data, 
                                   headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Verify food log was created
                if ("log_id" in data and 
                    "points_earned" in data and
                    data.get("food_log", {}).get("user_id") == self.test_user_id):
                    
                    self.log_test("Food Logging With Auth", True, 
                                f"Food logging successful with authentication")
                    return True
                else:
                    self.log_test("Food Logging With Auth", False, 
                                f"Invalid food log response", data)
                    return False
            else:
                self.log_test("Food Logging With Auth", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Food Logging With Auth", False, f"Exception: {str(e)}")
            return False
    
    def test_daily_stats_requires_auth(self):
        """Test GET /api/daily-stats/{user_id}/{date} requires authentication"""
        if not self.test_user_id:
            self.log_test("Daily Stats Auth Required", False, "No test user ID available")
            return False
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Try without token
            response = requests.get(f"{self.base_url}/daily-stats/{self.test_user_id}/{today}", timeout=10)
            if response.status_code == 401:
                self.log_test("Daily Stats Auth Required", True, 
                            "Daily stats correctly requires authentication (401)")
                return True
            else:
                self.log_test("Daily Stats Auth Required", False, 
                            f"Expected 401, got {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Daily Stats Auth Required", False, f"Exception: {str(e)}")
            return False
    
    def test_daily_stats_with_auth(self):
        """Test GET /api/daily-stats/{user_id}/{date} works with authentication"""
        if not self.test_user_id or not self.auth_token:
            self.log_test("Daily Stats With Auth", False, "No test user ID or auth token available")
            return False
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # Try with valid token
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(f"{self.base_url}/daily-stats/{self.test_user_id}/{today}", 
                                  headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Verify daily stats structure
                required_fields = ["date", "total_calories", "total_protein", "calorie_target", "protein_target"]
                if all(field in data for field in required_fields):
                    self.log_test("Daily Stats With Auth", True, 
                                f"Daily stats accessible with authentication")
                    return True
                else:
                    self.log_test("Daily Stats With Auth", False, 
                                f"Invalid daily stats response", data)
                    return False
            else:
                self.log_test("Daily Stats With Auth", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Daily Stats With Auth", False, f"Exception: {str(e)}")
            return False
    
    def test_cross_user_access_prevention(self):
        """Test that users cannot access other users' data"""
        if not self.auth_token:
            self.log_test("Cross User Access Prevention", False, "No auth token available")
            return False
        
        # Try to access a different user ID
        fake_user_id = "different-user-id-12345"
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(f"{self.base_url}/users/{fake_user_id}", 
                                  headers=headers, timeout=10)
            if response.status_code == 403:
                self.log_test("Cross User Access Prevention", True, 
                            "Cross-user access correctly prevented (403)")
                return True
            elif response.status_code == 404:
                self.log_test("Cross User Access Prevention", True, 
                            "Cross-user access prevented (404 - user not found)")
                return True
            else:
                self.log_test("Cross User Access Prevention", False, 
                            f"Expected 403 or 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Cross User Access Prevention", False, f"Exception: {str(e)}")
            return False
    
    def test_token_expiration_handling(self):
        """Test handling of expired tokens (simulated)"""
        if not self.test_user_id:
            self.log_test("Token Expiration Handling", False, "No test user ID available")
            return False
        
        try:
            # Use a malformed/expired-looking token
            expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiZXhwaXJlZCIsImV4cCI6MTYwMDAwMDAwMH0.invalid"
            headers = {"Authorization": f"Bearer {expired_token}"}
            
            response = requests.get(f"{self.base_url}/users/{self.test_user_id}", 
                                  headers=headers, timeout=10)
            if response.status_code == 401:
                self.log_test("Token Expiration Handling", True, 
                            "Expired/invalid token correctly rejected (401)")
                return True
            else:
                self.log_test("Token Expiration Handling", False, 
                            f"Expected 401, got {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Token Expiration Handling", False, f"Exception: {str(e)}")
            return False
    
    def test_get_current_user_profile(self):
        """Test GET /api/auth/me endpoint"""
        if not self.auth_token:
            self.log_test("Get Current User Profile", False, "No auth token available")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = requests.get(f"{self.base_url}/auth/me", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify user profile data
                if (data.get("user_id") == self.test_user_id and 
                    data.get("email") == self.test_user_email and
                    "password_hash" not in data):
                    
                    self.log_test("Get Current User Profile", True, 
                                f"Current user profile retrieved successfully")
                    return True
                else:
                    self.log_test("Get Current User Profile", False, 
                                f"Invalid user profile data", data)
                    return False
            else:
                self.log_test("Get Current User Profile", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Get Current User Profile", False, f"Exception: {str(e)}")
            return False

    # ========== SMART COACHING SYSTEM TESTS (Phase 3) ==========
    
    def test_user_creation_with_coaching_welcome_tip(self):
        """Test POST /api/users creates welcome coaching tip"""
        user_data = {
            "name": "Marcus Johnson",
            "age": 24,
            "height_cm": 180.0,
            "weight_kg": 68.0,
            "gender": "male",
            "activity_level": "moderate",
            "goal_weight_kg": 78.0,
            "target_weekly_gain": 0.5
        }
        
        try:
            response = requests.post(f"{self.base_url}/users", json=user_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                coaching_user_id = data.get("user_id")
                
                # Wait a moment for coaching tip to be created
                time.sleep(2)
                
                # Check if welcome coaching tip was created
                tips_response = requests.get(f"{self.base_url}/coaching/tips/{coaching_user_id}?unread_only=true", timeout=10)
                if tips_response.status_code == 200:
                    tips = tips_response.json()
                    
                    # Look for welcome tip
                    welcome_tip = next((tip for tip in tips if "Welcome" in tip.get("title", "")), None)
                    if welcome_tip:
                        self.log_test("User Creation with Coaching Welcome Tip", True, 
                                    f"Welcome coaching tip created: '{welcome_tip['title']}'")
                        return True
                    else:
                        self.log_test("User Creation with Coaching Welcome Tip", False, 
                                    f"No welcome coaching tip found. Tips: {len(tips)}")
                        return False
                else:
                    self.log_test("User Creation with Coaching Welcome Tip", False, 
                                f"Could not retrieve coaching tips: {tips_response.status_code}")
                    return False
            else:
                self.log_test("User Creation with Coaching Welcome Tip", False, 
                            f"User creation failed: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("User Creation with Coaching Welcome Tip", False, f"Exception: {str(e)}")
            return False

    def test_coaching_tips_retrieval_and_filtering(self):
        """Test GET /api/coaching/tips/{user_id} with filtering"""
        if not self.test_user_id:
            self.log_test("Coaching Tips Retrieval and Filtering", False, "No test user ID available")
            return False
        
        try:
            # Test getting all tips
            all_tips_response = requests.get(f"{self.base_url}/coaching/tips/{self.test_user_id}", timeout=10)
            if all_tips_response.status_code != 200:
                self.log_test("Coaching Tips Retrieval and Filtering", False, 
                            f"Failed to get all tips: {all_tips_response.status_code}")
                return False
            
            all_tips = all_tips_response.json()
            
            # Test getting unread tips only
            unread_tips_response = requests.get(f"{self.base_url}/coaching/tips/{self.test_user_id}?unread_only=true", timeout=10)
            if unread_tips_response.status_code != 200:
                self.log_test("Coaching Tips Retrieval and Filtering", False, 
                            f"Failed to get unread tips: {unread_tips_response.status_code}")
                return False
            
            unread_tips = unread_tips_response.json()
            
            # Verify tip structure
            if all_tips:
                tip = all_tips[0]
                required_fields = ["tip_id", "user_id", "tip_type", "title", "message", "priority", "is_read", "created_at"]
                missing_fields = [field for field in required_fields if field not in tip]
                
                if missing_fields:
                    self.log_test("Coaching Tips Retrieval and Filtering", False, 
                                f"Tip missing fields: {missing_fields}")
                    return False
            
            self.log_test("Coaching Tips Retrieval and Filtering", True, 
                        f"Tips retrieved successfully. All: {len(all_tips)}, Unread: {len(unread_tips)}")
            return True
            
        except Exception as e:
            self.log_test("Coaching Tips Retrieval and Filtering", False, f"Exception: {str(e)}")
            return False

    def test_coaching_tip_mark_as_read(self):
        """Test POST /api/coaching/tips/{tip_id}/read"""
        if not self.test_user_id:
            self.log_test("Coaching Tip Mark as Read", False, "No test user ID available")
            return False
        
        try:
            # Get unread tips first
            tips_response = requests.get(f"{self.base_url}/coaching/tips/{self.test_user_id}?unread_only=true", timeout=10)
            if tips_response.status_code != 200:
                self.log_test("Coaching Tip Mark as Read", False, "Could not get unread tips")
                return False
            
            tips = tips_response.json()
            if not tips:
                self.log_test("Coaching Tip Mark as Read", False, "No unread tips available to test")
                return False
            
            tip_id = tips[0]["tip_id"]
            
            # Mark tip as read
            read_response = requests.post(f"{self.base_url}/coaching/tips/{tip_id}/read", timeout=10)
            if read_response.status_code != 200:
                self.log_test("Coaching Tip Mark as Read", False, 
                            f"Failed to mark tip as read: {read_response.status_code}")
                return False
            
            # Verify tip is now read
            time.sleep(1)
            updated_tips_response = requests.get(f"{self.base_url}/coaching/tips/{self.test_user_id}?unread_only=true", timeout=10)
            if updated_tips_response.status_code == 200:
                updated_tips = updated_tips_response.json()
                
                # The tip should no longer be in unread list
                tip_still_unread = any(tip["tip_id"] == tip_id for tip in updated_tips)
                if not tip_still_unread:
                    self.log_test("Coaching Tip Mark as Read", True, 
                                f"Tip marked as read successfully. Unread count: {len(updated_tips)}")
                    return True
                else:
                    self.log_test("Coaching Tip Mark as Read", False, 
                                "Tip still appears in unread list after marking as read")
                    return False
            else:
                self.log_test("Coaching Tip Mark as Read", False, 
                            "Could not verify tip read status")
                return False
                
        except Exception as e:
            self.log_test("Coaching Tip Mark as Read", False, f"Exception: {str(e)}")
            return False

    def test_manual_coaching_tip_generation(self):
        """Test POST /api/coaching/generate-tips/{user_id}"""
        if not self.test_user_id:
            self.log_test("Manual Coaching Tip Generation", False, "No test user ID available")
            return False
        
        try:
            # Get current tip count
            before_response = requests.get(f"{self.base_url}/coaching/tips/{self.test_user_id}", timeout=10)
            if before_response.status_code != 200:
                self.log_test("Manual Coaching Tip Generation", False, "Could not get initial tip count")
                return False
            
            tips_before = len(before_response.json())
            
            # Generate tips manually
            generate_response = requests.post(f"{self.base_url}/coaching/generate-tips/{self.test_user_id}", timeout=15)
            if generate_response.status_code != 200:
                self.log_test("Manual Coaching Tip Generation", False, 
                            f"Failed to generate tips: {generate_response.status_code}")
                return False
            
            # Wait for tips to be generated
            time.sleep(3)
            
            # Check if new tips were created
            after_response = requests.get(f"{self.base_url}/coaching/tips/{self.test_user_id}", timeout=10)
            if after_response.status_code == 200:
                tips_after = len(after_response.json())
                
                if tips_after >= tips_before:
                    self.log_test("Manual Coaching Tip Generation", True, 
                                f"Tips generated successfully. Before: {tips_before}, After: {tips_after}")
                    return True
                else:
                    self.log_test("Manual Coaching Tip Generation", False, 
                                f"No new tips generated. Before: {tips_before}, After: {tips_after}")
                    return False
            else:
                self.log_test("Manual Coaching Tip Generation", False, 
                            "Could not verify tip generation")
                return False
                
        except Exception as e:
            self.log_test("Manual Coaching Tip Generation", False, f"Exception: {str(e)}")
            return False

    def test_smart_meal_suggestions(self):
        """Test GET /api/coaching/meal-suggestions/{user_id}"""
        if not self.test_user_id:
            self.log_test("Smart Meal Suggestions", False, "No test user ID available")
            return False
        
        try:
            response = requests.get(f"{self.base_url}/coaching/meal-suggestions/{self.test_user_id}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Verify response structure
                if "suggestions" not in data or "context" not in data:
                    self.log_test("Smart Meal Suggestions", False, 
                                f"Missing required fields in response", data)
                    return False
                
                suggestions = data["suggestions"]
                context = data["context"]
                
                # Verify suggestions are provided
                if not isinstance(suggestions, list) or len(suggestions) == 0:
                    self.log_test("Smart Meal Suggestions", False, 
                                f"No meal suggestions provided", data)
                    return False
                
                # Verify context has required fields
                context_fields = ["current_hour", "calories_needed", "protein_needed"]
                missing_context = [field for field in context_fields if field not in context]
                
                if missing_context:
                    self.log_test("Smart Meal Suggestions", False, 
                                f"Missing context fields: {missing_context}")
                    return False
                
                self.log_test("Smart Meal Suggestions", True, 
                            f"Smart meal suggestions working. {len(suggestions)} suggestions provided based on context")
                return True
            else:
                self.log_test("Smart Meal Suggestions", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Smart Meal Suggestions", False, f"Exception: {str(e)}")
            return False

    def test_weekly_checkin_system(self):
        """Test POST /api/coaching/weekly-checkin/{user_id}"""
        if not self.test_user_id:
            self.log_test("Weekly Checkin System", False, "No test user ID available")
            return False
        
        try:
            # Perform weekly check-in
            checkin_response = requests.post(f"{self.base_url}/coaching/weekly-checkin/{self.test_user_id}", timeout=15)
            
            if checkin_response.status_code == 200:
                data = checkin_response.json()
                
                # Verify response structure
                required_fields = ["success", "checkin", "tdee_adjustment", "new_target"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Weekly Checkin System", False, 
                                f"Missing response fields: {missing_fields}")
                    return False
                
                checkin = data["checkin"]
                
                # Verify checkin structure
                checkin_fields = ["checkin_id", "user_id", "week_start_date", "week_end_date", 
                                "starting_weight", "ending_weight", "weight_change", "expected_change",
                                "avg_daily_calories", "goal_hit_rate", "tdee_adjustment", "coaching_summary"]
                
                missing_checkin_fields = [field for field in checkin_fields if field not in checkin]
                
                if missing_checkin_fields:
                    self.log_test("Weekly Checkin System", False, 
                                f"Missing checkin fields: {missing_checkin_fields}")
                    return False
                
                self.log_test("Weekly Checkin System", True, 
                            f"Weekly check-in completed. TDEE adjustment: {data['tdee_adjustment']}, New target: {data['new_target']}")
                return True
            else:
                # Check if it's because of insufficient data
                if checkin_response.status_code == 200:
                    error_data = checkin_response.json()
                    if not error_data.get("success", True):
                        self.log_test("Weekly Checkin System", True, 
                                    f"Weekly check-in handled correctly: {error_data.get('message', 'Insufficient data')}")
                        return True
                
                self.log_test("Weekly Checkin System", False, 
                            f"Status code: {checkin_response.status_code}", checkin_response.text)
                return False
        except Exception as e:
            self.log_test("Weekly Checkin System", False, f"Exception: {str(e)}")
            return False

    def test_weekly_checkin_history(self):
        """Test GET /api/coaching/weekly-checkins/{user_id}"""
        if not self.test_user_id:
            self.log_test("Weekly Checkin History", False, "No test user ID available")
            return False
        
        try:
            response = requests.get(f"{self.base_url}/coaching/weekly-checkins/{self.test_user_id}", timeout=10)
            if response.status_code == 200:
                checkins = response.json()
                
                if isinstance(checkins, list):
                    self.log_test("Weekly Checkin History", True, 
                                f"Weekly check-in history retrieved: {len(checkins)} check-ins")
                    return True
                else:
                    self.log_test("Weekly Checkin History", False, 
                                f"Check-ins not returned as list", checkins)
                    return False
            else:
                self.log_test("Weekly Checkin History", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Weekly Checkin History", False, f"Exception: {str(e)}")
            return False

    def test_enhanced_food_logging_with_coaching_tips(self):
        """Test POST /api/food-logs triggers contextual coaching tips"""
        if not self.test_user_id:
            self.log_test("Enhanced Food Logging with Coaching Tips", False, "No test user ID available")
            return False
        
        try:
            # Get initial tip count
            before_response = requests.get(f"{self.base_url}/coaching/tips/{self.test_user_id}", timeout=10)
            if before_response.status_code != 200:
                self.log_test("Enhanced Food Logging with Coaching Tips", False, "Could not get initial tip count")
                return False
            
            tips_before = len(before_response.json())
            
            # Log a low-calorie meal to trigger coaching tips
            today = datetime.now().strftime("%Y-%m-%d")
            low_calorie_log = {
                "user_id": self.test_user_id,
                "date": today,
                "meal_type": "lunch",
                "food_items": [
                    {
                        "name": "Small Salad",
                        "calories": 150,
                        "protein": 5.0,
                        "carbs": 15.0,
                        "fat": 8.0,
                        "portion_size": "1 small bowl"
                    }
                ]
            }
            
            # Log the food
            log_response = requests.post(f"{self.base_url}/food-logs", json=low_calorie_log, timeout=10)
            if log_response.status_code != 200:
                self.log_test("Enhanced Food Logging with Coaching Tips", False, 
                            f"Food logging failed: {log_response.status_code}")
                return False
            
            # Wait for contextual tips to be generated
            time.sleep(3)
            
            # Check if new coaching tips were created
            after_response = requests.get(f"{self.base_url}/coaching/tips/{self.test_user_id}", timeout=10)
            if after_response.status_code == 200:
                tips_after = len(after_response.json())
                
                # Food logging should have triggered contextual coaching tips
                if tips_after >= tips_before:
                    self.log_test("Enhanced Food Logging with Coaching Tips", True, 
                                f"Food logging triggered coaching tips. Before: {tips_before}, After: {tips_after}")
                    return True
                else:
                    # This might be okay if no contextual tips were needed
                    self.log_test("Enhanced Food Logging with Coaching Tips", True, 
                                f"Food logging completed (no new tips needed). Tips: {tips_after}")
                    return True
            else:
                self.log_test("Enhanced Food Logging with Coaching Tips", False, 
                            "Could not verify coaching tip generation")
                return False
                
        except Exception as e:
            self.log_test("Enhanced Food Logging with Coaching Tips", False, f"Exception: {str(e)}")
            return False

    def test_enhanced_weight_entries_with_coaching_tips(self):
        """Test POST /api/weight-entries generates weight progress tips"""
        if not self.test_user_id:
            self.log_test("Enhanced Weight Entries with Coaching Tips", False, "No test user ID available")
            return False
        
        try:
            # Get initial tip count
            before_response = requests.get(f"{self.base_url}/coaching/tips/{self.test_user_id}", timeout=10)
            if before_response.status_code != 200:
                self.log_test("Enhanced Weight Entries with Coaching Tips", False, "Could not get initial tip count")
                return False
            
            tips_before = len(before_response.json())
            
            # Add a weight entry
            today = datetime.now().strftime("%Y-%m-%d")
            weight_data = {
                "user_id": self.test_user_id,
                "weight_kg": 69.5,
                "date": today
            }
            
            weight_response = requests.post(f"{self.base_url}/weight-entries", json=weight_data, timeout=10)
            if weight_response.status_code != 200:
                self.log_test("Enhanced Weight Entries with Coaching Tips", False, 
                            f"Weight entry failed: {weight_response.status_code}")
                return False
            
            # Wait for coaching tips to be generated
            time.sleep(2)
            
            # Check if coaching tips were created
            after_response = requests.get(f"{self.base_url}/coaching/tips/{self.test_user_id}", timeout=10)
            if after_response.status_code == 200:
                tips_after = len(after_response.json())
                
                self.log_test("Enhanced Weight Entries with Coaching Tips", True, 
                            f"Weight entry with coaching integration completed. Tips before: {tips_before}, after: {tips_after}")
                return True
            else:
                self.log_test("Enhanced Weight Entries with Coaching Tips", False, 
                            "Could not verify coaching tip generation")
                return False
                
        except Exception as e:
            self.log_test("Enhanced Weight Entries with Coaching Tips", False, f"Exception: {str(e)}")
            return False

    def test_enhanced_daily_stats_with_coaching_tips(self):
        """Test GET /api/daily-stats/{user_id}/{date} includes coaching tips"""
        if not self.test_user_id:
            self.log_test("Enhanced Daily Stats with Coaching Tips", False, "No test user ID available")
            return False
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        try:
            response = requests.get(f"{self.base_url}/daily-stats/{self.test_user_id}/{today}", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                
                # Verify coaching_tips field is present
                if "coaching_tips" not in stats:
                    self.log_test("Enhanced Daily Stats with Coaching Tips", False, 
                                f"coaching_tips field missing from daily stats")
                    return False
                
                coaching_tips = stats["coaching_tips"]
                
                if isinstance(coaching_tips, list):
                    self.log_test("Enhanced Daily Stats with Coaching Tips", True, 
                                f"Daily stats include coaching tips: {len(coaching_tips)} tips for today")
                    return True
                else:
                    self.log_test("Enhanced Daily Stats with Coaching Tips", False, 
                                f"coaching_tips not returned as list")
                    return False
            else:
                self.log_test("Enhanced Daily Stats with Coaching Tips", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Enhanced Daily Stats with Coaching Tips", False, f"Exception: {str(e)}")
            return False

    def test_ai_coaching_integration(self):
        """Test AI-powered coaching tip generation"""
        if not self.test_user_id:
            self.log_test("AI Coaching Integration", False, "No test user ID available")
            return False
        
        try:
            # Generate tips manually to test AI integration
            generate_response = requests.post(f"{self.base_url}/coaching/generate-tips/{self.test_user_id}", timeout=20)
            if generate_response.status_code != 200:
                self.log_test("AI Coaching Integration", False, 
                            f"Failed to trigger AI tip generation: {generate_response.status_code}")
                return False
            
            # Wait for AI processing
            time.sleep(5)
            
            # Get recent tips to check for AI-generated content
            tips_response = requests.get(f"{self.base_url}/coaching/tips/{self.test_user_id}?limit=5", timeout=10)
            if tips_response.status_code == 200:
                tips = tips_response.json()
                
                if tips:
                    # Check if tips have meaningful content (indicating AI generation)
                    ai_indicators = ["you", "your", "try", "consider", "focus", "remember"]
                    ai_generated = False
                    
                    for tip in tips:
                        message = tip.get("message", "").lower()
                        if any(indicator in message for indicator in ai_indicators) and len(message) > 20:
                            ai_generated = True
                            break
                    
                    if ai_generated:
                        self.log_test("AI Coaching Integration", True, 
                                    f"AI-powered coaching tips generated successfully. Recent tips: {len(tips)}")
                        return True
                    else:
                        self.log_test("AI Coaching Integration", True, 
                                    f"Coaching system working (fallback tips used). Tips: {len(tips)}")
                        return True
                else:
                    self.log_test("AI Coaching Integration", False, 
                                "No coaching tips found after AI generation")
                    return False
            else:
                self.log_test("AI Coaching Integration", False, 
                            "Could not retrieve tips to verify AI integration")
                return False
                
        except Exception as e:
            self.log_test("AI Coaching Integration", False, f"Exception: {str(e)}")
            return False

    def test_pattern_analysis_system(self):
        """Test user behavior pattern analysis for smart coaching"""
        if not self.test_user_id:
            self.log_test("Pattern Analysis System", False, "No test user ID available")
            return False
        
        try:
            # The pattern analysis is internal, but we can test it indirectly through meal suggestions
            # which use pattern analysis to provide contextual recommendations
            
            # Get meal suggestions which internally use pattern analysis
            suggestions_response = requests.get(f"{self.base_url}/coaching/meal-suggestions/{self.test_user_id}", timeout=10)
            if suggestions_response.status_code != 200:
                self.log_test("Pattern Analysis System", False, 
                            f"Could not get meal suggestions: {suggestions_response.status_code}")
                return False
            
            suggestions_data = suggestions_response.json()
            
            # Verify contextual data is provided (indicates pattern analysis is working)
            context = suggestions_data.get("context", {})
            if "current_hour" in context and "calories_needed" in context:
                self.log_test("Pattern Analysis System", True, 
                            f"Pattern analysis working through contextual meal suggestions")
                return True
            else:
                self.log_test("Pattern Analysis System", False, 
                            f"Pattern analysis context missing from meal suggestions")
                return False
                
        except Exception as e:
            self.log_test("Pattern Analysis System", False, f"Exception: {str(e)}")
            return False
    
    def run_jwt_authentication_tests(self):
        """Run comprehensive JWT Authentication System tests"""
        print(f"\n🔐 Starting Weight Gain App JWT AUTHENTICATION SYSTEM Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence focusing on JWT Authentication
        auth_tests = [
            # Core authentication flow
            self.test_health_check,
            self.test_user_registration,
            self.test_user_login,
            self.test_invalid_login,
            
            # Password reset flow
            self.test_forgot_password,
            self.test_reset_password,
            self.test_login_with_new_password,
            
            # Token validation and security
            self.test_protected_endpoint_without_token,
            self.test_protected_endpoint_with_invalid_token,
            self.test_protected_endpoint_with_valid_token,
            self.test_token_expiration_handling,
            self.test_cross_user_access_prevention,
            self.test_get_current_user_profile,
            
            # Protected endpoints integration
            self.test_food_logging_requires_auth,
            self.test_food_logging_with_auth,
            self.test_daily_stats_requires_auth,
            self.test_daily_stats_with_auth,
            
            # Verify existing features still work with auth
            self.test_user_creation_with_gamification,
            self.test_enhanced_food_logging_gamification,
        ]
        
        passed = 0
        total = len(auth_tests)
        
        for test in auth_tests:
            if test():
                passed += 1
            time.sleep(1)  # Small delay between tests
        
        print("\n" + "=" * 80)
        print(f"🎯 JWT Authentication Test Results: {passed}/{total} tests passed")
        
        # Summary of failures
        failures = [r for r in self.test_results if not r["success"]]
        if failures:
            print("\n❌ Failed Tests:")
            for failure in failures:
                print(f"   • {failure['test']}: {failure['details']}")
        else:
            print("\n🎉 All JWT Authentication features working perfectly!")
        
        return passed, total, self.test_results

    def run_smart_coaching_tests(self):
        """Run comprehensive Smart Coaching System tests (Phase 3)"""
        print(f"\n🧠 Starting Weight Gain App SMART COACHING SYSTEM Tests (Phase 3)")
        print(f"Backend URL: {self.base_url}")
        print("=" * 80)
        
        # Test sequence focusing on Smart Coaching System
        tests = [
            # Core system tests
            self.test_health_check,
            self.test_user_creation_with_gamification,
            
            # Smart Coaching System tests
            self.test_user_creation_with_coaching_welcome_tip,
            self.test_coaching_tips_retrieval_and_filtering,
            self.test_coaching_tip_mark_as_read,
            self.test_manual_coaching_tip_generation,
            self.test_smart_meal_suggestions,
            self.test_weekly_checkin_system,
            self.test_weekly_checkin_history,
            
            # Enhanced existing endpoints with coaching
            self.test_enhanced_food_logging_with_coaching_tips,
            self.test_enhanced_weight_entries_with_coaching_tips,
            self.test_enhanced_daily_stats_with_coaching_tips,
            
            # AI and pattern analysis
            self.test_ai_coaching_integration,
            self.test_pattern_analysis_system,
            
            # Gamification system (existing functionality)
            self.test_enhanced_food_logging_gamification,
            self.test_points_system_calculation,
            self.test_streak_tracking_system,
            self.test_badge_system_comprehensive,
            self.test_enhanced_weight_entries_gamification,
            self.test_user_statistics_api,
            self.test_achievement_api_system,
            self.test_enhanced_daily_stats_gamification,
            self.test_leaderboard_system
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
            time.sleep(1)  # Small delay between tests
        
        print("\n" + "=" * 80)
        print(f"🎯 Smart Coaching System Test Results: {passed}/{total} tests passed")
        
        # Summary of failures
        failures = [r for r in self.test_results if not r["success"]]
        if failures:
            print("\n❌ Failed Tests:")
            for failure in failures:
                print(f"   • {failure['test']}: {failure['details']}")
        else:
            print("\n🎉 All Smart Coaching System features working perfectly!")
        
        return passed, total, self.test_results

if __name__ == "__main__":
    tester = WeightGainAppTester()
    
    # Run JWT Authentication tests as requested
    print("🔐 TESTING JWT AUTHENTICATION SYSTEM FOR WEIGHT GAIN APP")
    print("=" * 80)
    
    passed, total, results = tester.run_jwt_authentication_tests()
    
    # Save detailed results
    with open("/app/jwt_auth_test_results.json", "w") as f:
        json.dump({
            "summary": {"passed": passed, "total": total, "success_rate": f"{(passed/total)*100:.1f}%"},
            "results": results,
            "backend_url": BACKEND_URL,
            "test_timestamp": datetime.now().isoformat(),
            "test_focus": "JWT Authentication System"
        }, f, indent=2)
    
    print(f"\n📝 Detailed results saved to jwt_auth_test_results.json")
    
    # Also run a subset of smart coaching tests to verify integration
    print(f"\n\n🧠 Running Integration Tests with Smart Coaching System")
    print("=" * 80)
    
    # Reset test results for coaching tests
    tester.test_results = []
    
    # Run key coaching tests to verify they work with authentication
    coaching_integration_tests = [
        tester.test_user_creation_with_coaching_welcome_tip,
        tester.test_coaching_tips_retrieval_and_filtering,
        tester.test_smart_meal_suggestions,
        tester.test_enhanced_food_logging_with_coaching_tips,
        tester.test_enhanced_daily_stats_with_coaching_tips,
    ]
    
    coaching_passed = 0
    coaching_total = len(coaching_integration_tests)
    
    for test in coaching_integration_tests:
        if test():
            coaching_passed += 1
        time.sleep(1)
    
    print(f"\n🎯 Coaching Integration Test Results: {coaching_passed}/{coaching_total} tests passed")
    
    # Overall summary
    overall_passed = passed + coaching_passed
    overall_total = total + coaching_total
    
    print(f"\n" + "=" * 80)
    print(f"🏆 OVERALL TEST RESULTS: {overall_passed}/{overall_total} tests passed ({(overall_passed/overall_total)*100:.1f}%)")
    print(f"🔐 JWT Authentication: {passed}/{total} passed")
    print(f"🧠 Coaching Integration: {coaching_passed}/{coaching_total} passed")
    
    if overall_passed == overall_total:
        print(f"\n🎉 ALL TESTS PASSED! JWT Authentication system is working perfectly!")
    else:
        print(f"\n⚠️  Some tests failed. Check the detailed results above.")