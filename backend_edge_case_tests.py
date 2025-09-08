#!/usr/bin/env python3
"""
Edge Case Testing for Weight Gain App Backend
Tests error handling and edge cases
"""

import requests
import json
from datetime import datetime

BACKEND_URL = "https://gain-weight-guide.preview.emergentagent.com/api"

def test_invalid_user_id():
    """Test GET endpoints with invalid user ID"""
    print("Testing invalid user ID...")
    
    # Test get user with invalid ID
    response = requests.get(f"{BACKEND_URL}/users/invalid-id")
    if response.status_code == 404:
        print("✅ Get user with invalid ID returns 404")
    else:
        print(f"❌ Expected 404, got {response.status_code}")
    
    # Test get food logs with invalid ID
    response = requests.get(f"{BACKEND_URL}/food-logs/invalid-id")
    if response.status_code == 200 and response.json() == []:
        print("✅ Get food logs with invalid ID returns empty array")
    else:
        print(f"❌ Unexpected response for invalid user food logs: {response.status_code}")
    
    # Test get weight entries with invalid ID
    response = requests.get(f"{BACKEND_URL}/weight-entries/invalid-id")
    if response.status_code == 200 and response.json() == []:
        print("✅ Get weight entries with invalid ID returns empty array")
    else:
        print(f"❌ Unexpected response for invalid user weight entries: {response.status_code}")
    
    # Test daily stats with invalid ID
    response = requests.get(f"{BACKEND_URL}/daily-stats/invalid-id/2025-09-08")
    if response.status_code == 404:
        print("✅ Daily stats with invalid ID returns 404")
    else:
        print(f"❌ Expected 404 for daily stats, got {response.status_code}")

def test_invalid_data():
    """Test POST endpoints with invalid data"""
    print("\nTesting invalid data...")
    
    # Test user creation with missing fields
    response = requests.post(f"{BACKEND_URL}/users", json={"name": "Test"})
    if response.status_code in [400, 422, 500]:
        print("✅ User creation with missing fields returns error")
    else:
        print(f"❌ Expected error for incomplete user data, got {response.status_code}")
    
    # Test food log with missing fields
    response = requests.post(f"{BACKEND_URL}/food-logs", json={"user_id": "test"})
    if response.status_code in [400, 422, 500]:
        print("✅ Food log creation with missing fields returns error")
    else:
        print(f"❌ Expected error for incomplete food log data, got {response.status_code}")
    
    # Test weight entry with missing fields
    response = requests.post(f"{BACKEND_URL}/weight-entries", json={"user_id": "test"})
    if response.status_code in [400, 422, 500]:
        print("✅ Weight entry creation with missing fields returns error")
    else:
        print(f"❌ Expected error for incomplete weight entry data, got {response.status_code}")

def test_tdee_calculations():
    """Test TDEE calculations with different parameters"""
    print("\nTesting TDEE calculations...")
    
    # Test female user
    female_user = {
        "name": "Jane Doe",
        "age": 30,
        "height_cm": 165.0,
        "weight_kg": 55.0,
        "gender": "female",
        "activity_level": "light",
        "goal_weight_kg": 65.0,
        "target_weekly_gain": 0.25
    }
    
    response = requests.post(f"{BACKEND_URL}/users", json=female_user)
    if response.status_code == 200:
        data = response.json()
        user = data["user"]
        # Female BMR: (10 * 55) + (6.25 * 165) - (5 * 30) - 161 = 550 + 1031.25 - 150 - 161 = 1270.25
        # TDEE: 1270.25 * 1.375 (light) = 1746.59 ≈ 1746
        # With 0.25kg/week surplus: 1746 + 250 = 1996
        expected_calories = 1996
        actual_calories = user["daily_calorie_target"]
        
        if abs(actual_calories - expected_calories) <= 50:
            print(f"✅ Female TDEE calculation correct: {actual_calories} cal (expected ~{expected_calories})")
        else:
            print(f"❌ Female TDEE calculation error: got {actual_calories}, expected ~{expected_calories}")
    else:
        print(f"❌ Failed to create female user: {response.status_code}")
    
    # Test very active male
    active_male = {
        "name": "John Strong",
        "age": 22,
        "height_cm": 180.0,
        "weight_kg": 75.0,
        "gender": "male",
        "activity_level": "very_active",
        "goal_weight_kg": 85.0,
        "target_weekly_gain": 1.0
    }
    
    response = requests.post(f"{BACKEND_URL}/users", json=active_male)
    if response.status_code == 200:
        data = response.json()
        user = data["user"]
        # Male BMR: (10 * 75) + (6.25 * 180) - (5 * 22) + 5 = 750 + 1125 - 110 + 5 = 1770
        # TDEE: 1770 * 1.9 (very_active) = 3363
        # With 1.0kg/week surplus: 3363 + 750 = 4113
        expected_calories = 4113
        actual_calories = user["daily_calorie_target"]
        
        if abs(actual_calories - expected_calories) <= 50:
            print(f"✅ Very active male TDEE calculation correct: {actual_calories} cal (expected ~{expected_calories})")
        else:
            print(f"❌ Very active male TDEE calculation error: got {actual_calories}, expected ~{expected_calories}")
    else:
        print(f"❌ Failed to create very active male user: {response.status_code}")

def test_date_filtering():
    """Test date filtering for food logs"""
    print("\nTesting date filtering...")
    
    # Create a test user first
    user_data = {
        "name": "Test User",
        "age": 25,
        "height_cm": 170.0,
        "weight_kg": 60.0,
        "gender": "male",
        "activity_level": "moderate",
        "goal_weight_kg": 70.0,
        "target_weekly_gain": 0.5
    }
    
    response = requests.post(f"{BACKEND_URL}/users", json=user_data)
    if response.status_code == 200:
        user_id = response.json()["user_id"]
        
        # Create food logs for different dates
        yesterday = "2025-09-07"
        today = "2025-09-08"
        
        # Log for yesterday
        food_log_yesterday = {
            "user_id": user_id,
            "date": yesterday,
            "meal_type": "lunch",
            "food_items": [{"name": "Sandwich", "calories": 400, "protein": 20.0, "carbs": 40.0, "fat": 15.0, "portion_size": "1 sandwich"}]
        }
        
        # Log for today
        food_log_today = {
            "user_id": user_id,
            "date": today,
            "meal_type": "dinner",
            "food_items": [{"name": "Pasta", "calories": 500, "protein": 15.0, "carbs": 80.0, "fat": 10.0, "portion_size": "1 bowl"}]
        }
        
        # Create both logs
        requests.post(f"{BACKEND_URL}/food-logs", json=food_log_yesterday)
        requests.post(f"{BACKEND_URL}/food-logs", json=food_log_today)
        
        # Test filtering by date
        response = requests.get(f"{BACKEND_URL}/food-logs/{user_id}?date={yesterday}")
        if response.status_code == 200:
            logs = response.json()
            if len(logs) == 1 and logs[0]["date"] == yesterday:
                print("✅ Date filtering works correctly")
            else:
                print(f"❌ Date filtering failed: expected 1 log for {yesterday}, got {len(logs)}")
        else:
            print(f"❌ Failed to get filtered food logs: {response.status_code}")
    else:
        print(f"❌ Failed to create test user for date filtering: {response.status_code}")

if __name__ == "__main__":
    print("🧪 Running Edge Case Tests for Weight Gain App Backend")
    print("=" * 60)
    
    test_invalid_user_id()
    test_invalid_data()
    test_tdee_calculations()
    test_date_filtering()
    
    print("\n" + "=" * 60)
    print("🏁 Edge case testing completed")