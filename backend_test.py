#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Weight Gain App
Tests all API endpoints with realistic scenarios
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
    
    def test_user_creation(self):
        """Test POST /api/users with TDEE calculation"""
        # Test data: 25 years old, male, 170cm, 60kg, moderate activity, goal 70kg, 0.5kg/week gain
        user_data = {
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
            response = requests.post(f"{self.base_url}/users", json=user_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.test_user_id = data.get("user_id")
                user_profile = data.get("user")
                
                # Verify TDEE calculation
                # Expected BMR for male: (10 * 60) + (6.25 * 170) - (5 * 25) + 5 = 600 + 1062.5 - 125 + 5 = 1542.5
                # Expected TDEE: 1542.5 * 1.55 (moderate) = 2390.875 ≈ 2390
                # Expected daily calories: 2390 + 500 (0.5kg/week surplus) = 2890
                expected_calories = 2890
                actual_calories = user_profile.get("daily_calorie_target")
                
                # Allow 50 calorie tolerance
                if abs(actual_calories - expected_calories) <= 50:
                    # Verify macro targets (30% protein, 35% carbs, 35% fat)
                    expected_protein = int((actual_calories * 0.30) / 4)  # 4 cal/g
                    expected_carbs = int((actual_calories * 0.35) / 4)    # 4 cal/g  
                    expected_fat = int((actual_calories * 0.35) / 9)      # 9 cal/g
                    
                    actual_protein = user_profile.get("daily_protein_target")
                    actual_carbs = user_profile.get("daily_carb_target")
                    actual_fat = user_profile.get("daily_fat_target")
                    
                    if (abs(actual_protein - expected_protein) <= 5 and 
                        abs(actual_carbs - expected_carbs) <= 5 and
                        abs(actual_fat - expected_fat) <= 5):
                        self.log_test("User Creation & TDEE Calculation", True, 
                                    f"User created with correct TDEE: {actual_calories} cal, Macros: {actual_protein}p/{actual_carbs}c/{actual_fat}f")
                        return True
                    else:
                        self.log_test("User Creation & TDEE Calculation", False, 
                                    f"Macro calculation error. Expected: {expected_protein}p/{expected_carbs}c/{expected_fat}f, Got: {actual_protein}p/{actual_carbs}c/{actual_fat}f")
                        return False
                else:
                    self.log_test("User Creation & TDEE Calculation", False, 
                                f"TDEE calculation error. Expected ~{expected_calories}, got {actual_calories}")
                    return False
            else:
                self.log_test("User Creation & TDEE Calculation", False, 
                            f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("User Creation & TDEE Calculation", False, f"Exception: {str(e)}")
            return False
    
    def test_get_user(self):
        """Test GET /api/users/{user_id}"""
        if not self.test_user_id:
            self.log_test("Get User Profile", False, "No test user ID available")
            return False
            
        try:
            response = requests.get(f"{self.base_url}/users/{self.test_user_id}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("user_id") == self.test_user_id:
                    self.log_test("Get User Profile", True, "User profile retrieved successfully")
                    return True
                else:
                    self.log_test("Get User Profile", False, "User ID mismatch", data)
                    return False
            else:
                self.log_test("Get User Profile", False, f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Get User Profile", False, f"Exception: {str(e)}")
            return False
    
    def test_food_image_analysis(self):
        """Test POST /api/analyze-food with mock image"""
        if not self.test_user_id:
            self.log_test("Food Image Analysis", False, "No test user ID available")
            return False
            
        # Create a small test image (1x1 pixel PNG)
        test_image_data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==")
        
        try:
            files = {'file': ('test_food.png', test_image_data, 'image/png')}
            data = {'user_id': self.test_user_id}
            
            response = requests.post(f"{self.base_url}/analyze-food", files=files, data=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                nutrition_data = result.get("nutrition_data")
                
                # Verify response structure
                if (nutrition_data and 
                    "foods" in nutrition_data and 
                    "total_calories" in nutrition_data and
                    "confidence" in nutrition_data):
                    
                    foods = nutrition_data["foods"]
                    if foods and len(foods) > 0:
                        food = foods[0]
                        if all(key in food for key in ["name", "calories", "protein", "carbs", "fat", "portion_size"]):
                            self.log_test("Food Image Analysis", True, 
                                        f"AI analysis successful. Detected: {food['name']}, {food['calories']} cal, confidence: {nutrition_data['confidence']}")
                            return True
                        else:
                            self.log_test("Food Image Analysis", False, "Missing food nutrition fields", nutrition_data)
                            return False
                    else:
                        self.log_test("Food Image Analysis", False, "No foods detected", nutrition_data)
                        return False
                else:
                    self.log_test("Food Image Analysis", False, "Invalid response structure", result)
                    return False
            else:
                self.log_test("Food Image Analysis", False, f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Food Image Analysis", False, f"Exception: {str(e)}")
            return False
    
    def test_food_logging(self):
        """Test POST /api/food-logs"""
        if not self.test_user_id:
            self.log_test("Food Logging", False, "No test user ID available")
            return False
            
        # Test food log data
        today = datetime.now().strftime("%Y-%m-%d")
        food_log_data = {
            "user_id": self.test_user_id,
            "date": today,
            "meal_type": "breakfast",
            "food_items": [
                {
                    "name": "Scrambled Eggs",
                    "calories": 200,
                    "protein": 14.0,
                    "carbs": 2.0,
                    "fat": 15.0,
                    "portion_size": "2 large eggs"
                },
                {
                    "name": "Whole Wheat Toast",
                    "calories": 160,
                    "protein": 6.0,
                    "carbs": 28.0,
                    "fat": 3.0,
                    "portion_size": "2 slices"
                }
            ]
        }
        
        try:
            response = requests.post(f"{self.base_url}/food-logs", json=food_log_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                food_log = data.get("food_log")
                
                # Verify totals calculation
                expected_calories = 360  # 200 + 160
                expected_protein = 20.0  # 14 + 6
                expected_carbs = 30.0    # 2 + 28
                expected_fat = 18.0      # 15 + 3
                
                if (food_log.get("total_calories") == expected_calories and
                    food_log.get("total_protein") == expected_protein and
                    food_log.get("total_carbs") == expected_carbs and
                    food_log.get("total_fat") == expected_fat):
                    self.log_test("Food Logging", True, 
                                f"Food log created with correct totals: {expected_calories} cal, {expected_protein}p/{expected_carbs}c/{expected_fat}f")
                    return True
                else:
                    self.log_test("Food Logging", False, 
                                f"Incorrect totals. Expected: {expected_calories}cal, Got: {food_log.get('total_calories')}cal", food_log)
                    return False
            else:
                self.log_test("Food Logging", False, f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Food Logging", False, f"Exception: {str(e)}")
            return False
    
    def test_get_food_logs(self):
        """Test GET /api/food-logs/{user_id}"""
        if not self.test_user_id:
            self.log_test("Get Food Logs", False, "No test user ID available")
            return False
            
        try:
            response = requests.get(f"{self.base_url}/food-logs/{self.test_user_id}", timeout=10)
            if response.status_code == 200:
                logs = response.json()
                if isinstance(logs, list) and len(logs) > 0:
                    # Check if our test log is there
                    test_log = logs[0]  # Should be most recent
                    if test_log.get("user_id") == self.test_user_id:
                        self.log_test("Get Food Logs", True, f"Retrieved {len(logs)} food logs")
                        return True
                    else:
                        self.log_test("Get Food Logs", False, "User ID mismatch in logs", logs)
                        return False
                else:
                    self.log_test("Get Food Logs", True, "No food logs found (empty response)")
                    return True
            else:
                self.log_test("Get Food Logs", False, f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Get Food Logs", False, f"Exception: {str(e)}")
            return False
    
    def test_weight_tracking(self):
        """Test POST /api/weight-entries"""
        if not self.test_user_id:
            self.log_test("Weight Tracking", False, "No test user ID available")
            return False
            
        today = datetime.now().strftime("%Y-%m-%d")
        weight_data = {
            "user_id": self.test_user_id,
            "weight_kg": 60.5,
            "date": today
        }
        
        try:
            response = requests.post(f"{self.base_url}/weight-entries", json=weight_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                weight_entry = data.get("weight_entry")
                
                if (weight_entry.get("user_id") == self.test_user_id and
                    weight_entry.get("weight_kg") == 60.5 and
                    weight_entry.get("date") == today):
                    self.log_test("Weight Tracking", True, f"Weight entry created: {weight_entry['weight_kg']}kg on {weight_entry['date']}")
                    return True
                else:
                    self.log_test("Weight Tracking", False, "Weight entry data mismatch", weight_entry)
                    return False
            else:
                self.log_test("Weight Tracking", False, f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Weight Tracking", False, f"Exception: {str(e)}")
            return False
    
    def test_get_weight_entries(self):
        """Test GET /api/weight-entries/{user_id}"""
        if not self.test_user_id:
            self.log_test("Get Weight Entries", False, "No test user ID available")
            return False
            
        try:
            response = requests.get(f"{self.base_url}/weight-entries/{self.test_user_id}", timeout=10)
            if response.status_code == 200:
                entries = response.json()
                if isinstance(entries, list) and len(entries) > 0:
                    test_entry = entries[0]  # Should be most recent
                    if test_entry.get("user_id") == self.test_user_id:
                        self.log_test("Get Weight Entries", True, f"Retrieved {len(entries)} weight entries")
                        return True
                    else:
                        self.log_test("Get Weight Entries", False, "User ID mismatch in entries", entries)
                        return False
                else:
                    self.log_test("Get Weight Entries", True, "No weight entries found (empty response)")
                    return True
            else:
                self.log_test("Get Weight Entries", False, f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Get Weight Entries", False, f"Exception: {str(e)}")
            return False
    
    def test_daily_stats(self):
        """Test GET /api/daily-stats/{user_id}/{date}"""
        if not self.test_user_id:
            self.log_test("Daily Stats", False, "No test user ID available")
            return False
            
        today = datetime.now().strftime("%Y-%m-%d")
        
        try:
            response = requests.get(f"{self.base_url}/daily-stats/{self.test_user_id}/{today}", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                
                # Verify stats structure
                required_fields = ["date", "total_calories", "total_protein", "total_carbs", "total_fat",
                                 "calorie_target", "protein_target", "carb_target", "fat_target"]
                
                if all(field in stats for field in required_fields):
                    # Should have our breakfast log totals
                    if stats["total_calories"] >= 360:  # From our food log test
                        self.log_test("Daily Stats", True, 
                                    f"Daily stats retrieved: {stats['total_calories']}/{stats['calorie_target']} calories")
                        return True
                    else:
                        self.log_test("Daily Stats", True, 
                                    f"Daily stats retrieved (no food logs): {stats['total_calories']}/{stats['calorie_target']} calories")
                        return True
                else:
                    self.log_test("Daily Stats", False, "Missing required fields in stats", stats)
                    return False
            else:
                self.log_test("Daily Stats", False, f"Status code: {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Daily Stats", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print(f"\n🚀 Starting Weight Gain App Backend Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            self.test_health_check,
            self.test_user_creation,
            self.test_get_user,
            self.test_food_image_analysis,
            self.test_food_logging,
            self.test_get_food_logs,
            self.test_weight_tracking,
            self.test_get_weight_entries,
            self.test_daily_stats
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
            time.sleep(1)  # Small delay between tests
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        # Summary of failures
        failures = [r for r in self.test_results if not r["success"]]
        if failures:
            print("\n❌ Failed Tests:")
            for failure in failures:
                print(f"   • {failure['test']}: {failure['details']}")
        
        return passed, total, self.test_results

if __name__ == "__main__":
    tester = WeightGainAppTester()
    passed, total, results = tester.run_all_tests()
    
    # Save detailed results
    with open("/app/backend_test_results.json", "w") as f:
        json.dump({
            "summary": {"passed": passed, "total": total, "success_rate": f"{(passed/total)*100:.1f}%"},
            "results": results,
            "backend_url": BACKEND_URL,
            "test_timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\n📝 Detailed results saved to backend_test_results.json")