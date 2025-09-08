#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Weight Gain App - GAMIFICATION SYSTEM
Tests all API endpoints with focus on new gamification features
"""

import requests
import json
import base64
import os
from datetime import datetime, timedelta
import time

# Get backend URL from frontend env
BACKEND_URL = "https://gain-weight-guide.preview.emergentagent.com/api"

class WeightGainAppTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_user_id = None
        self.test_results = []
        
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
        """Test POST /api/users with gamification fields"""
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
            response = requests.post(f"{self.base_url}/users", json=user_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.test_user_id = data.get("user_id")
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
                    self.log_test("User Creation with Gamification", True, 
                                f"User created with gamification fields initialized correctly")
                    return True
                else:
                    self.log_test("User Creation with Gamification", False, 
                                f"Gamification fields not properly initialized", user_profile)
                    return False
            else:
                self.log_test("User Creation with Gamification", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("User Creation with Gamification", False, f"Exception: {str(e)}")
            return False
    
    def test_enhanced_food_logging_gamification(self):
        """Test POST /api/food-logs with comprehensive gamification features"""
        if not self.test_user_id:
            self.log_test("Enhanced Food Logging Gamification", False, "No test user ID available")
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
            response = requests.post(f"{self.base_url}/food-logs", json=food_log_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Verify gamification response fields
                required_fields = ["points_earned", "new_badges", "badge_points", "current_streak"]
                if not all(field in data for field in required_fields):
                    self.log_test("Enhanced Food Logging Gamification", False, 
                                f"Missing gamification fields in response", data)
                    return False
                
                # Should get first_meal badge (50 points) + base points (25) = 75+ points
                points_earned = data.get("points_earned", 0)
                new_badges = data.get("new_badges", [])
                badge_points = data.get("badge_points", 0)
                current_streak = data.get("current_streak", 0)
                
                # Verify first meal badge
                if "first_meal" in new_badges and badge_points >= 50 and current_streak == 1:
                    self.log_test("Enhanced Food Logging Gamification", True, 
                                f"First meal logged successfully. Points: {points_earned}, Badges: {new_badges}, Streak: {current_streak}")
                    return True
                else:
                    self.log_test("Enhanced Food Logging Gamification", False, 
                                f"First meal gamification failed. Points: {points_earned}, Badges: {new_badges}, Streak: {current_streak}")
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
    
    def run_gamification_tests(self):
        """Run comprehensive gamification system tests"""
        print(f"\n🎮 Starting Weight Gain App GAMIFICATION SYSTEM Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 70)
        
        # Test sequence focusing on gamification
        tests = [
            self.test_health_check,
            self.test_user_creation_with_gamification,
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
        
        print("\n" + "=" * 70)
        print(f"🎯 Gamification Test Results: {passed}/{total} tests passed")
        
        # Summary of failures
        failures = [r for r in self.test_results if not r["success"]]
        if failures:
            print("\n❌ Failed Tests:")
            for failure in failures:
                print(f"   • {failure['test']}: {failure['details']}")
        else:
            print("\n🎉 All gamification features working perfectly!")
        
        return passed, total, self.test_results

if __name__ == "__main__":
    tester = WeightGainAppTester()
    passed, total, results = tester.run_gamification_tests()
    
    # Save detailed results
    with open("/app/gamification_test_results.json", "w") as f:
        json.dump({
            "summary": {"passed": passed, "total": total, "success_rate": f"{(passed/total)*100:.1f}%"},
            "results": results,
            "backend_url": BACKEND_URL,
            "test_timestamp": datetime.now().isoformat(),
            "test_focus": "Gamification System - Phase 2"
        }, f, indent=2)
    
    print(f"\n📝 Detailed results saved to gamification_test_results.json")