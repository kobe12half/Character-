import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [currentView, setCurrentView] = useState('onboarding'); // onboarding, dashboard, camera, profile, achievements, coaching
  const [user, setUser] = useState(null);
  const [dailyStats, setDailyStats] = useState(null);
  const [userStats, setUserStats] = useState(null);
  const [weightEntries, setWeightEntries] = useState([]);
  const [foodLogs, setFoodLogs] = useState([]);
  const [achievements, setAchievements] = useState([]);
  const [badges, setBadges] = useState({});
  const [coachingTips, setCoachingTips] = useState([]);
  const [mealSuggestions, setMealSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notification, setNotification] = useState('');
  
  // Camera states
  const [cameraMode, setCameraMode] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [nutritionData, setNutritionData] = useState(null);
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);
  const streamRef = useRef(null);

  const today = new Date().toISOString().split('T')[0];

  useEffect(() => {
    const savedUser = localStorage.getItem('weightGainUser');
    if (savedUser) {
      const userData = JSON.parse(savedUser);
      setUser(userData);
      setCurrentView('dashboard');
      loadDashboardData(userData.user_id);
    }
    loadBadges();
  }, []);

  const loadBadges = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/badges`);
      if (response.ok) {
        const badgeData = await response.json();
        setBadges(badgeData);
      }
    } catch (error) {
      console.error('Error loading badges:', error);
    }
  };

  const loadDashboardData = async (userId) => {
    try {
      // Load daily stats
      const statsResponse = await fetch(`${BACKEND_URL}/api/daily-stats/${userId}/${today}`);
      if (statsResponse.ok) {
        const stats = await statsResponse.json();
        setDailyStats(stats);
        // Extract coaching tips from daily stats
        if (stats.coaching_tips) {
          setCoachingTips(stats.coaching_tips);
        }
      }

      // Load user stats
      const userStatsResponse = await fetch(`${BACKEND_URL}/api/user-stats/${userId}`);
      if (userStatsResponse.ok) {
        const userStatsData = await userStatsResponse.json();
        setUserStats(userStatsData);
      }

      // Load food logs
      const logsResponse = await fetch(`${BACKEND_URL}/api/food-logs/${userId}?date=${today}`);
      if (logsResponse.ok) {
        const logs = await logsResponse.json();
        setFoodLogs(logs);
      }

      // Load weight entries
      const weightResponse = await fetch(`${BACKEND_URL}/api/weight-entries/${userId}`);
      if (weightResponse.ok) {
        const entries = await weightResponse.json();
        setWeightEntries(entries);
      }

      // Load achievements
      const achievementsResponse = await fetch(`${BACKEND_URL}/api/achievements/${userId}`);
      if (achievementsResponse.ok) {
        const achievementsData = await achievementsResponse.json();
        setAchievements(achievementsData);
      }

      // Load coaching tips
      const coachingResponse = await fetch(`${BACKEND_URL}/api/coaching/tips/${userId}?unread_only=true`);
      if (coachingResponse.ok) {
        const coachingData = await coachingResponse.json();
        setCoachingTips(coachingData);
      }

      // Load meal suggestions
      const suggestionsResponse = await fetch(`${BACKEND_URL}/api/coaching/meal-suggestions/${userId}`);
      if (suggestionsResponse.ok) {
        const suggestionsData = await suggestionsResponse.json();
        setMealSuggestions(suggestionsData.suggestions || []);
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    }
  };

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(''), 4000);
  };

  const markTipAsRead = async (tipId) => {
    try {
      await fetch(`${BACKEND_URL}/api/coaching/tips/${tipId}/read`, {
        method: 'POST'
      });
      // Remove the tip from the list
      setCoachingTips(tips => tips.filter(tip => tip.tip_id !== tipId));
    } catch (error) {
      console.error('Error marking tip as read:', error);
    }
  };

  const generateTips = async () => {
    if (!user) return;
    
    try {
      await fetch(`${BACKEND_URL}/api/coaching/generate-tips/${user.user_id}`, {
        method: 'POST'
      });
      // Reload coaching tips
      const coachingResponse = await fetch(`${BACKEND_URL}/api/coaching/tips/${user.user_id}?unread_only=true`);
      if (coachingResponse.ok) {
        const coachingData = await coachingResponse.json();
        setCoachingTips(coachingData);
      }
      showNotification('New coaching tips generated! 🤖');
    } catch (error) {
      console.error('Error generating tips:', error);
    }
  };

  const handleOnboarding = async (formData) => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (response.ok) {
        const result = await response.json();
        setUser(result.user);
        localStorage.setItem('weightGainUser', JSON.stringify(result.user));
        setCurrentView('dashboard');
        await loadDashboardData(result.user.user_id);
        showNotification('Welcome! Your profile has been created successfully! 🎉');
      } else {
        throw new Error('Failed to create user profile');
      }
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'environment' },
        audio: false 
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraMode(true);
    } catch (error) {
      console.error('Error accessing camera:', error);
      setError('Camera access denied. Please use file upload instead.');
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    setCameraMode(false);
    setCapturedImage(null);
    setNutritionData(null);
  };

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      const context = canvas.getContext('2d');
      
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0);
      
      const imageDataUrl = canvas.toDataURL('image/jpeg', 0.8);
      setCapturedImage(imageDataUrl);
      stopCamera();
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setCapturedImage(e.target.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const analyzeFood = async () => {
    if (!capturedImage || !user) return;

    setAnalyzing(true);
    setError('');

    try {
      // Convert data URL to blob
      const response = await fetch(capturedImage);
      const blob = await response.blob();
      
      const formData = new FormData();
      formData.append('file', blob, 'food_image.jpg');
      formData.append('user_id', user.user_id);

      const analyzeResponse = await fetch(`${BACKEND_URL}/api/analyze-food`, {
        method: 'POST',
        body: formData
      });

      if (analyzeResponse.ok) {
        const result = await analyzeResponse.json();
        setNutritionData(result.nutrition_data);
      } else {
        throw new Error('Failed to analyze food image');
      }
    } catch (error) {
      setError('Failed to analyze food image: ' + error.message);
    } finally {
      setAnalyzing(false);
    }
  };

  const saveFoodLog = async (mealType = 'snack') => {
    if (!nutritionData || !user) return;

    setLoading(true);
    try {
      const logData = {
        user_id: user.user_id,
        date: today,
        meal_type: mealType,
        food_items: nutritionData.foods,
        image_base64: capturedImage ? capturedImage.split(',')[1] : null
      };

      const response = await fetch(`${BACKEND_URL}/api/food-logs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logData)
      });

      if (response.ok) {
        const result = await response.json();
        
        // Show success notification with points
        let message = `Food logged successfully! +${result.points_earned} points`;
        if (result.new_badges.length > 0) {
          message += ` • New badges earned! 🏆`;
        }
        if (result.current_streak > 1) {
          message += ` • ${result.current_streak} day streak! 🔥`;
        }
        
        showNotification(message);
        
        setCapturedImage(null);
        setNutritionData(null);
        setCurrentView('dashboard');
        await loadDashboardData(user.user_id);
      } else {
        throw new Error('Failed to save food log');
      }
    } catch (error) {
      setError('Failed to save food log: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const addWeightEntry = async (weight) => {
    if (!user || !weight) return;

    try {
      const weightData = {
        user_id: user.user_id,
        weight_kg: parseFloat(weight),
        date: today
      };

      const response = await fetch(`${BACKEND_URL}/api/weight-entries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(weightData)
      });

      if (response.ok) {
        const result = await response.json();
        showNotification(`Weight logged! +${result.points_earned} points 📊`);
        await loadDashboardData(user.user_id);
      }
    } catch (error) {
      setError('Failed to add weight entry: ' + error.message);
    }
  };

  const renderNotification = () => {
    if (!notification) return null;
    
    return (
      <div className={`notification ${notification.type}`}>
        <span>{notification.message}</span>
        <button onClick={() => setNotification('')}>×</button>
      </div>
    );
  };

  const renderOnboarding = () => (
    <div className="onboarding-container">
      <div className="onboarding-card">
        <h1 className="heading-1">Welcome to Weight Gain Tracker</h1>
        <p className="body-large">Let's set up your profile to calculate your personalized calorie targets</p>
        
        <OnboardingForm onSubmit={handleOnboarding} loading={loading} />
        
        {error && <div className="error-message">{error}</div>}
      </div>
    </div>
  );

  const renderDashboard = () => {
    if (!user || !dailyStats || !userStats) return <div className="loading">Loading dashboard...</div>;

    const calorieProgress = (dailyStats.total_calories / dailyStats.calorie_target) * 100;
    const proteinProgress = (dailyStats.total_protein / dailyStats.protein_target) * 100;

    return (
      <div className="dashboard-container">
        <header className="dashboard-header">
          <div className="user-greeting">
            <h1 className="heading-2">Hi {user.name}!</h1>
            <p className="body-medium">{today}</p>
          </div>
          <div className="gamification-summary">
            <div className="points-display">
              <span className="points-number">{userStats.total_points}</span>
              <span className="points-label">points</span>
            </div>
            <div className="streak-display">
              <span className="streak-icon">🔥</span>
              <span className="streak-number">{userStats.current_streak}</span>
            </div>
          </div>
        </header>

        {/* Coaching Tips Section */}
        {coachingTips.length > 0 && (
          <div className="coaching-tips-section">
            <div className="coaching-header">
              <h3 className="heading-4">🤖 Smart Coach</h3>
              <button className="coach-more-btn" onClick={() => setCurrentView('coaching')}>
                View All
              </button>
            </div>
            <div className="tips-preview">
              {coachingTips.slice(0, 2).map(tip => (
                <div key={tip.tip_id} className={`coaching-tip-card ${tip.priority}`}>
                  <div className="tip-header">
                    <span className="tip-title">{tip.title}</span>
                    <button 
                      className="tip-close"
                      onClick={() => markTipAsRead(tip.tip_id)}
                    >×</button>
                  </div>
                  <p className="tip-message">{tip.message}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="stats-grid">
          <div className="stat-card">
            <h3 className="heading-4">Calories</h3>
            <div className="progress-circle">
              <div className="progress-text">
                <span className="heading-3">{dailyStats.total_calories}</span>
                <span className="body-small">/ {dailyStats.calorie_target}</span>
              </div>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{width: `${Math.min(calorieProgress, 100)}%`}}></div>
            </div>
            {dailyStats.points_earned_today > 0 && (
              <div className="points-earned">+{dailyStats.points_earned_today} pts today</div>
            )}
          </div>

          <div className="stat-card">
            <h3 className="heading-4">Protein</h3>
            <div className="progress-circle">
              <div className="progress-text">
                <span className="heading-3">{Math.round(dailyStats.total_protein)}g</span>
                <span className="body-small">/ {dailyStats.protein_target}g</span>
              </div>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{width: `${Math.min(proteinProgress, 100)}%`}}></div>
            </div>
          </div>
        </div>

        <div className="macro-summary">
          <div className="macro-item">
            <span className="body-medium">Carbs: {Math.round(dailyStats.total_carbs)}g</span>
          </div>
          <div className="macro-item">
            <span className="body-medium">Fat: {Math.round(dailyStats.total_fat)}g</span>
          </div>
          <div className="macro-item">
            <span className="body-medium">Target: {Math.round(dailyStats.target_hit_percentage)}%</span>
          </div>
        </div>

        {/* Achievement Badges Display */}
        {userStats.badges_earned.length > 0 && (
          <div className="badges-preview">
            <h3 className="heading-4">Recent Badges</h3>
            <div className="badges-list">
              {userStats.badges_earned.slice(0, 3).map((badgeKey, idx) => {
                const badge = badges[badgeKey];
                return badge ? (
                  <div key={idx} className="badge-item">
                    <span className="badge-icon">{badge.icon}</span>
                    <span className="badge-name">{badge.name}</span>
                  </div>
                ) : null;
              })}
              {userStats.badges_earned.length > 3 && (
                <button 
                  className="view-all-badges" 
                  onClick={() => setCurrentView('achievements')}
                >
                  +{userStats.badges_earned.length - 3} more
                </button>
              )}
            </div>
          </div>
        )}

        <div className="action-buttons">
          <button className="btn-primary" onClick={() => setCurrentView('camera')}>
            📷 Scan Food
          </button>
          <button className="btn-secondary" onClick={() => setCurrentView('coaching')}>
            🤖 Smart Coach
          </button>
        </div>

        <div className="recent-meals">
          <h3 className="heading-4">Today's Meals</h3>
          {foodLogs.length > 0 ? (
            <div className="meals-list">
              {foodLogs.map(log => (
                <div key={log.log_id} className="meal-card">
                  <div className="meal-header">
                    <span className="meal-type">{log.meal_type}</span>
                    <div className="meal-meta">
                      <span className="meal-calories">{log.total_calories} cal</span>
                      {log.points_earned > 0 && (
                        <span className="meal-points">+{log.points_earned} pts</span>
                      )}
                    </div>
                  </div>
                  <div className="meal-foods">
                    {log.food_items.map((food, idx) => (
                      <span key={idx} className="food-name">{food.name}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="body-medium">No meals logged today. Start by scanning your first meal!</p>
          )}
        </div>

        {error && <div className="error-message">{error}</div>}
      </div>
    );
  };

  const renderCamera = () => (
    <div className="camera-container">
      <header className="camera-header">
        <button className="back-button" onClick={() => setCurrentView('dashboard')}>← Back</button>
        <h2 className="heading-3">Scan Your Food</h2>
      </header>

      {!cameraMode && !capturedImage && (
        <div className="camera-options">
          <button className="btn-primary" onClick={startCamera}>📷 Use Camera</button>
          <button className="btn-secondary" onClick={() => fileInputRef.current?.click()}>
            📁 Upload Photo
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
        </div>
      )}

      {cameraMode && (
        <div className="camera-view">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            className="camera-video"
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />
          <div className="camera-controls">
            <button className="capture-button" onClick={capturePhoto}>📷</button>
            <button className="btn-secondary" onClick={stopCamera}>Cancel</button>
          </div>
        </div>
      )}

      {capturedImage && !nutritionData && (
        <div className="image-preview">
          <img src={capturedImage} alt="Captured food" className="captured-image" />
          <div className="image-actions">
            <button 
              className="btn-primary" 
              onClick={analyzeFood}
              disabled={analyzing}
            >
              {analyzing ? 'Analyzing...' : '🔍 Analyze Food'}
            </button>
            <button className="btn-secondary" onClick={() => setCapturedImage(null)}>
              Retake
            </button>
          </div>
        </div>
      )}

      {nutritionData && (
        <div className="nutrition-results">
          <h3 className="heading-4">Nutrition Analysis</h3>
          <div className="nutrition-summary">
            <div className="nutrition-total">
              <span className="heading-3">{nutritionData.total_calories}</span>
              <span className="body-medium">calories</span>
            </div>
            <div className="nutrition-macros">
              <span className="macro">P: {Math.round(nutritionData.total_protein)}g</span>
              <span className="macro">C: {Math.round(nutritionData.total_carbs)}g</span>
              <span className="macro">F: {Math.round(nutritionData.total_fat)}g</span>
            </div>
          </div>

          <div className="food-items">
            {nutritionData.foods.map((food, idx) => (
              <div key={idx} className="food-item">
                <div className="food-name">{food.name}</div>
                <div className="food-portion">{food.portion_size}</div>
                <div className="food-calories">{food.calories} cal</div>
              </div>
            ))}
          </div>

          <div className="meal-type-selector">
            <h4 className="heading-4">Add to:</h4>
            <div className="meal-buttons">
              <button className="meal-btn" onClick={() => saveFoodLog('breakfast')}>Breakfast</button>
              <button className="meal-btn" onClick={() => saveFoodLog('lunch')}>Lunch</button>
              <button className="meal-btn" onClick={() => saveFoodLog('dinner')}>Dinner</button>
              <button className="meal-btn" onClick={() => saveFoodLog('snack')}>Snack</button>
            </div>
          </div>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}
    </div>
  );

  const renderProfile = () => (
    <div className="profile-container">
      <header className="profile-header">
        <button className="back-button" onClick={() => setCurrentView('dashboard')}>← Back</button>
        <h2 className="heading-3">Your Progress</h2>
        <button className="achievements-button" onClick={() => setCurrentView('achievements')}>
          🏆 Badges
        </button>
      </header>

      {user && userStats && (
        <div className="profile-content">
          <div className="stats-overview">
            <div className="stat-item">
              <span className="stat-number">{userStats.total_points}</span>
              <span className="stat-label">Total Points</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{userStats.current_streak}</span>
              <span className="stat-label">Current Streak</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{userStats.longest_streak}</span>
              <span className="stat-label">Best Streak</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{userStats.badges_earned.length}</span>
              <span className="stat-label">Badges</span>
            </div>
          </div>

          <div className="profile-stats">
            <h3 className="heading-4">Your Goals</h3>
            <div className="goal-item">
              <span className="label">Daily Calories:</span>
              <span className="value">{user.daily_calorie_target}</span>
            </div>
            <div className="goal-item">
              <span className="label">Target Weight:</span>
              <span className="value">{user.goal_weight_kg} kg</span>
            </div>
            <div className="goal-item">
              <span className="label">Weekly Gain:</span>
              <span className="value">{user.target_weekly_gain} kg</span>
            </div>
            <div className="goal-item">
              <span className="label">Avg Daily Calories:</span>
              <span className="value">{userStats.avg_daily_calories}</span>
            </div>
            <div className="goal-item">
              <span className="label">Goal Hit Rate:</span>
              <span className="value">{userStats.goal_completion_rate}%</span>
            </div>
          </div>

          <div className="weight-tracker">
            <h3 className="heading-4">Weight Progress</h3>
            {weightEntries.length > 0 && (
              <div className="current-weight">
                <span className="heading-2">{weightEntries[0].weight_kg} kg</span>
                <span className="body-medium">Current Weight</span>
              </div>
            )}
            
            <div className="weight-input">
              <input 
                type="number" 
                placeholder="Enter today's weight (kg)" 
                className="weight-input-field"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    addWeightEntry(e.target.value);
                    e.target.value = '';
                  }
                }}
              />
            </div>
          </div>

          <button 
            className="btn-secondary" 
            onClick={() => {
              localStorage.removeItem('weightGainUser');
              setUser(null);
              setCurrentView('onboarding');
            }}
          >
            Reset Profile
          </button>
        </div>
      )}
    </div>
  );

  const renderAchievements = () => (
    <div className="achievements-container">
      <header className="achievements-header">
        <button className="back-button" onClick={() => setCurrentView('profile')}>← Back</button>
        <h2 className="heading-3">Your Achievements</h2>
      </header>

      <div className="achievements-content">
        <div className="earned-badges">
          <h3 className="heading-4">Badges Earned ({userStats?.badges_earned.length || 0})</h3>
          <div className="badges-grid">
            {userStats?.badges_earned.map((badgeKey, idx) => {
              const badge = badges[badgeKey];
              const achievement = achievements.find(a => a.badge_type === badgeKey);
              return badge ? (
                <div key={idx} className="badge-card earned">
                  <div className="badge-icon">{badge.icon}</div>
                  <div className="badge-info">
                    <h4 className="badge-name">{badge.name}</h4>
                    <p className="badge-description">{badge.description}</p>
                    <div className="badge-points">+{badge.points} points</div>
                    {achievement && (
                      <div className="badge-date">
                        Earned: {new Date(achievement.earned_date).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                </div>
              ) : null;
            })}
          </div>
        </div>

        <div className="available-badges">
          <h3 className="heading-4">Available Badges</h3>
          <div className="badges-grid">
            {Object.entries(badges).map(([badgeKey, badge]) => {
              const isEarned = userStats?.badges_earned.includes(badgeKey);
              if (isEarned) return null;
              
              return (
                <div key={badgeKey} className="badge-card available">
                  <div className="badge-icon grayscale">{badge.icon}</div>
                  <div className="badge-info">
                    <h4 className="badge-name">{badge.name}</h4>
                    <p className="badge-description">{badge.description}</p>
                    <div className="badge-points">+{badge.points} points</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );

  const renderCoaching = () => (
    <div className="coaching-container">
      <header className="coaching-header">
        <button className="back-button" onClick={() => setCurrentView('dashboard')}>← Back</button>
        <h2 className="heading-3">🤖 Smart Coach</h2>
        <button className="generate-tips-btn" onClick={generateTips}>
          Generate Tips
        </button>
      </header>

      <div className="coaching-content">
        {/* Active Tips */}
        <div className="active-tips">
          <h3 className="heading-4">Active Tips ({coachingTips.length})</h3>
          {coachingTips.length > 0 ? (
            <div className="tips-list">
              {coachingTips.map(tip => (
                <div key={tip.tip_id} className={`coaching-tip-card full ${tip.priority}`}>
                  <div className="tip-header">
                    <div className="tip-meta">
                      <span className="tip-type">{tip.tip_type.replace('_', ' ')}</span>
                      <span className={`tip-priority ${tip.priority}`}>{tip.priority}</span>
                    </div>
                    <button 
                      className="tip-close"
                      onClick={() => markTipAsRead(tip.tip_id)}
                    >×</button>
                  </div>
                  <h4 className="tip-title">{tip.title}</h4>
                  <p className="tip-message">{tip.message}</p>
                  <div className="tip-time">
                    {new Date(tip.created_at).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="no-tips">
              <p className="body-medium">No active tips right now.</p>
              <button className="btn-secondary" onClick={generateTips}>
                Get Personalized Tips
              </button>
            </div>
          )}
        </div>

        {/* Meal Suggestions */}
        {mealSuggestions.length > 0 && (
          <div className="meal-suggestions">
            <h3 className="heading-4">Meal Suggestions</h3>
            <div className="suggestions-list">
              {mealSuggestions.map((suggestion, idx) => (
                <div key={idx} className="suggestion-card">
                  <span className="suggestion-text">{suggestion}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Coaching Stats */}
        {dailyStats && (
          <div className="coaching-stats">
            <h3 className="heading-4">Today's Progress</h3>
            <div className="progress-insights">
              <div className="insight-item">
                <span className="insight-label">Calorie Progress:</span>
                <span className="insight-value">{Math.round(dailyStats.target_hit_percentage)}%</span>
              </div>
              <div className="insight-item">
                <span className="insight-label">Protein Intake:</span>
                <span className="insight-value">{Math.round(dailyStats.total_protein)}g / {dailyStats.protein_target}g</span>
              </div>
              <div className="insight-item">
                <span className="insight-label">Current Streak:</span>
                <span className="insight-value">{userStats?.current_streak || 0} days 🔥</span>
              </div>
            </div>
            
            {dailyStats.target_hit_percentage < 80 && (
              <div className="coaching-insight">
                <h4 className="insight-title">💡 Coach Insight</h4>
                <p className="insight-text">
                  You need {dailyStats.calorie_target - dailyStats.total_calories} more calories today. 
                  Try adding a protein smoothie or healthy snack to reach your goal!
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="App">
      {renderNotification()}
      {currentView === 'onboarding' && renderOnboarding()}
      {currentView === 'dashboard' && renderDashboard()}
      {currentView === 'camera' && renderCamera()}
      {currentView === 'profile' && renderProfile()}
      {currentView === 'achievements' && renderAchievements()}
      {currentView === 'coaching' && renderCoaching()}
    </div>
  );
}

const OnboardingForm = ({ onSubmit, loading }) => {
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    height_cm: '',
    weight_kg: '',
    gender: 'male',
    activity_level: 'moderate',
    goal_weight_kg: '',
    target_weekly_gain: 0.5
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      ...formData,
      age: parseInt(formData.age),
      height_cm: parseFloat(formData.height_cm),
      weight_kg: parseFloat(formData.weight_kg),
      goal_weight_kg: parseFloat(formData.goal_weight_kg),
      target_weekly_gain: parseFloat(formData.target_weekly_gain)
    });
  };

  return (
    <form onSubmit={handleSubmit} className="onboarding-form">
      <div className="form-group">
        <label className="form-label">Name</label>
        <input
          type="text"
          className="form-input"
          value={formData.name}
          onChange={(e) => setFormData({...formData, name: e.target.value})}
          required
        />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Age</label>
          <input
            type="number"
            className="form-input"
            value={formData.age}
            onChange={(e) => setFormData({...formData, age: e.target.value})}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Gender</label>
          <select
            className="form-input"
            value={formData.gender}
            onChange={(e) => setFormData({...formData, gender: e.target.value})}
          >
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Height (cm)</label>
          <input
            type="number"
            className="form-input"
            value={formData.height_cm}
            onChange={(e) => setFormData({...formData, height_cm: e.target.value})}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Current Weight (kg)</label>
          <input
            type="number"
            step="0.1"
            className="form-input"
            value={formData.weight_kg}
            onChange={(e) => setFormData({...formData, weight_kg: e.target.value})}
            required
          />
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">Goal Weight (kg)</label>
        <input
          type="number"
          step="0.1"
          className="form-input"
          value={formData.goal_weight_kg}
          onChange={(e) => setFormData({...formData, goal_weight_kg: e.target.value})}
          required
        />
      </div>

      <div className="form-group">
        <label className="form-label">Activity Level</label>
        <select
          className="form-input"
          value={formData.activity_level}
          onChange={(e) => setFormData({...formData, activity_level: e.target.value})}
        >
          <option value="sedentary">Sedentary (little/no exercise)</option>
          <option value="light">Light (light exercise 1-3 days/week)</option>
          <option value="moderate">Moderate (moderate exercise 3-5 days/week)</option>
          <option value="active">Active (hard exercise 6-7 days/week)</option>
          <option value="very_active">Very Active (very hard exercise, physical job)</option>
        </select>
      </div>

      <div className="form-group">
        <label className="form-label">Target Weekly Gain</label>
        <select
          className="form-input"
          value={formData.target_weekly_gain}
          onChange={(e) => setFormData({...formData, target_weekly_gain: parseFloat(e.target.value)})}
        >
          <option value={0.25}>0.25 kg/week (slow & lean)</option>
          <option value={0.5}>0.5 kg/week (moderate)</option>
          <option value={1.0}>1.0 kg/week (faster)</option>
        </select>
      </div>

      <button type="submit" className="btn-primary" disabled={loading}>
        {loading ? 'Creating Profile...' : 'Start Tracking'}
      </button>
    </form>
  );
};

export default App;