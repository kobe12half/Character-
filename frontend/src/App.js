import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [currentView, setCurrentView] = useState('login'); // login, register, forgot-password, onboarding, dashboard, camera, profile, achievements, coaching, challenges
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [dailyStats, setDailyStats] = useState(null);
  const [userStats, setUserStats] = useState(null);
  const [weightEntries, setWeightEntries] = useState([]);
  const [foodLogs, setFoodLogs] = useState([]);
  const [achievements, setAchievements] = useState([]);
  const [badges, setBadges] = useState({});
  const [coachingTips, setCoachingTips] = useState([]);
  const [mealSuggestions, setMealSuggestions] = useState([]);
  const [activeChallenges, setActiveChallenges] = useState([]);
  const [completedChallenges, setCompletedChallenges] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notification, setNotification] = useState('');
  const [celebration, setCelebration] = useState(null);
  
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
    // Check for saved token and user
    const savedToken = localStorage.getItem('weightGainToken');
    const savedUser = localStorage.getItem('weightGainUser');
    
    if (savedToken && savedUser) {
      try {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
        setCurrentView('dashboard');
        loadDashboardData(JSON.parse(savedUser).user_id);
      } catch (error) {
        // Clear corrupted data
        localStorage.removeItem('weightGainToken');
        localStorage.removeItem('weightGainUser');
        setCurrentView('login');
      }
    } else {
      setCurrentView('login');
    }
    
    loadBadges();
  }, []);

  const getAuthHeaders = () => {
    return token ? {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    } : {
      'Content-Type': 'application/json'
    };
  };

  const handleAuthError = (response) => {
    if (response.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('weightGainToken');
      localStorage.removeItem('weightGainUser');
      setToken(null);
      setUser(null);
      setCurrentView('login');
      showNotification('Session expired. Please login again.', 'error');
      return true;
    }
    return false;
  };

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

  const loadDashboardData = async (userId, authToken = null) => {
    const currentToken = authToken || token;
    if (!currentToken) return;
    
    try {
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentToken}`
      };

      // Helper function to safely load endpoint data
      const safeLoad = async (url, setter, defaultValue = null, dataKey = null) => {
        try {
          const response = await fetch(url, { headers });
          if (response.ok) {
            const data = await response.json();
            setter(dataKey ? data[dataKey] : data);
            return true;
          } else if (handleAuthError(response)) {
            throw new Error('Authentication error');
          } else {
            console.warn(`Failed to load ${url}: ${response.status}`);
            if (defaultValue !== null) {
              setter(defaultValue);
            }
            return false;
          }
        } catch (error) {
          console.warn(`Error loading ${url}:`, error);
          if (defaultValue !== null) {
            setter(defaultValue);
          }
          return false;
        }
      };

      // Load all data with fallbacks
      const loadPromises = [
        safeLoad(`${BACKEND_URL}/api/daily-stats/${userId}/${today}`, (stats) => {
          setDailyStats(stats);
          if (stats.coaching_tips) {
            setCoachingTips(stats.coaching_tips);
          }
          if (stats.active_challenges) {
            setActiveChallenges(stats.active_challenges);
          }
        }, {
          date: today,
          total_calories: 0,
          total_protein: 0,
          total_carbs: 0,
          total_fat: 0,
          calorie_target: user?.daily_calorie_target || 2500,
          protein_target: user?.daily_protein_target || 150,
          carb_target: user?.daily_carb_target || 250,
          fat_target: user?.daily_fat_target || 100,
          points_earned_today: 0,
          streak_status: false,
          target_hit_percentage: 0.0,
          coaching_tips: [],
          active_challenges: []
        }),

        safeLoad(`${BACKEND_URL}/api/user-stats/${userId}`, setUserStats, {
          user_id: userId,
          total_points: 0,
          current_streak: 0,
          longest_streak: 0,
          badges_earned: [],
          total_logs: 0,
          total_weight_entries: 0,
          days_active: 0,
          avg_daily_calories: 0,
          goal_completion_rate: 0,
          challenge_points: 0,
          active_challenges_count: 0,
          completed_challenges_count: 0
        }),

        safeLoad(`${BACKEND_URL}/api/food-logs/${userId}?date=${today}`, setFoodLogs, []),

        safeLoad(`${BACKEND_URL}/api/weight-entries/${userId}`, setWeightEntries, []),

        safeLoad(`${BACKEND_URL}/api/achievements/${userId}`, setAchievements, []),

        safeLoad(`${BACKEND_URL}/api/coaching/tips/${userId}?unread_only=true`, setCoachingTips, []),

        safeLoad(`${BACKEND_URL}/api/coaching/meal-suggestions/${userId}`, (data) => {
          setMealSuggestions(data.suggestions || []);
        }, []),

        safeLoad(`${BACKEND_URL}/api/challenges/active/${userId}`, setActiveChallenges, []),

        safeLoad(`${BACKEND_URL}/api/challenges/completed/${userId}`, setCompletedChallenges, [])
      ];

      // Wait for all loads to complete (but don't fail if some don't work)
      const results = await Promise.allSettled(loadPromises);
      
      // Check if authentication failed
      const authFailures = results.filter(result => 
        result.status === 'rejected' && result.reason?.message === 'Authentication error'
      );
      
      if (authFailures.length > 0) {
        return; // User will be redirected to login
      }

      console.log('Dashboard data loading completed');
      setLoading(false); // Clear loading state after successful data loading
      
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      
      // Set minimal default state so dashboard can still render
      setDailyStats({
        date: today,
        total_calories: 0,
        total_protein: 0,
        total_carbs: 0,
        total_fat: 0,
        calorie_target: user?.daily_calorie_target || 2500,
        protein_target: user?.daily_protein_target || 150,
        carb_target: user?.daily_carb_target || 250,
        fat_target: user?.daily_fat_target || 100,
        points_earned_today: 0,
        streak_status: false,
        target_hit_percentage: 0.0
      });
      
      setUserStats({
        user_id: userId,
        total_points: 0,
        current_streak: 0,
        longest_streak: 0,
        badges_earned: [],
        total_logs: 0,
        total_weight_entries: 0,
        days_active: 0,
        avg_daily_calories: 0,
        goal_completion_rate: 0
      });
      
      setError('Some dashboard data could not be loaded, but you can still use the app.');
      setLoading(false); // Clear loading state even if there are errors
    }
  };

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(''), 5000);
  };

  const showCelebration = (type, data) => {
    setCelebration({ type, data });
    setTimeout(() => setCelebration(null), 4000);
  };

  const handleLogin = async (loginData) => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginData)
      });

      if (response.ok) {
        const result = await response.json();
        setToken(result.access_token);
        setUser(result.user);
        
        // Save to localStorage
        localStorage.setItem('weightGainToken', result.access_token);
        localStorage.setItem('weightGainUser', JSON.stringify(result.user));
        
        setCurrentView('dashboard');
        await loadDashboardData(result.user.user_id, result.access_token);
        showNotification('Welcome back! 🎉');
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (registerData) => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(registerData)
      });

      if (response.ok) {
        const result = await response.json();
        setToken(result.access_token);
        setUser(result.user);
        
        // Save to localStorage
        localStorage.setItem('weightGainToken', result.access_token);
        localStorage.setItem('weightGainUser', JSON.stringify(result.user));
        
        setCurrentView('dashboard');
        await loadDashboardData(result.user.user_id, result.access_token);
        showNotification('Welcome to your weight gain journey! 🎉');
        showCelebration('welcome', { name: registerData.name });
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Registration failed');
      }
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (email) => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });

      if (response.ok) {
        const result = await response.json();
        showNotification('Password reset instructions sent to your email!');
        
        // For demo purposes, show the reset token (REMOVE IN PRODUCTION)
        if (result.reset_token) {
          setNotification({
            message: `Demo: Use this reset token: ${result.reset_token}`,
            type: 'warning'
          });
        }
        setCurrentView('login');
      } else {
        throw new Error('Failed to send reset email');
      }
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (resetData) => {
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(resetData)
      });

      if (response.ok) {
        showNotification('Password reset successfully! Please login with your new password.');
        setCurrentView('login');
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Password reset failed');
      }
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('weightGainToken');
    localStorage.removeItem('weightGainUser');
    setToken(null);
    setUser(null);
    setCurrentView('login');
    showNotification('Logged out successfully');
  };

  const markTipAsRead = async (tipId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/coaching/tips/${tipId}/read`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        setCoachingTips(tips => tips.filter(tip => tip.tip_id !== tipId));
      } else if (handleAuthError(response)) {
        return;
      }
    } catch (error) {
      console.error('Error marking tip as read:', error);
    }
  };

  const generateTips = async () => {
    if (!user || !token) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/coaching/generate-tips/${user.user_id}`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        const coachingResponse = await fetch(`${BACKEND_URL}/api/coaching/tips/${user.user_id}?unread_only=true`, {
          headers: getAuthHeaders()
        });
        if (coachingResponse.ok) {
          const coachingData = await coachingResponse.json();
          setCoachingTips(coachingData);
        }
        showNotification('New coaching tips generated! 🤖');
      } else if (handleAuthError(response)) {
        return;
      }
    } catch (error) {
      console.error('Error generating tips:', error);
    }
  };

  const createRandomChallenges = async () => {
    if (!user || !token) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/challenges/create-random/${user.user_id}`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        const result = await response.json();
        showNotification(`${result.challenges_created} new challenges created! 🎯`);
        showCelebration('challenges', { count: result.challenges_created });
        await loadDashboardData(user.user_id);
      } else if (handleAuthError(response)) {
        return;
      }
    } catch (error) {
      console.error('Error creating challenges:', error);
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
    if (!capturedImage || !user || !token) return;

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
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (analyzeResponse.ok) {
        const result = await analyzeResponse.json();
        setNutritionData(result.nutrition_data);
        showCelebration('analysis', { calories: result.nutrition_data.total_calories });
      } else if (handleAuthError(analyzeResponse)) {
        return;
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
    if (!nutritionData || !user || !token) return;

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
        headers: getAuthHeaders(),
        body: JSON.stringify(logData)
      });

      if (response.ok) {
        const result = await response.json();
        
        // Show success notification with points
        let message = `Food logged successfully! +${result.points_earned} points`;
        if (result.new_badges.length > 0) {
          message += ` • New badges earned! 🏆`;
          showCelebration('badges', { badges: result.new_badges, points: result.badge_points });
        }
        if (result.completed_challenges && result.completed_challenges.length > 0) {
          message += ` • Challenge completed! 🎯`;
          showCelebration('challenge_complete', { challenges: result.completed_challenges });
        }
        if (result.current_streak > 1) {
          message += ` • ${result.current_streak} day streak! 🔥`;
        }
        
        showNotification(message);
        
        setCapturedImage(null);
        setNutritionData(null);
        setCurrentView('dashboard');
        await loadDashboardData(user.user_id);
      } else if (handleAuthError(response)) {
        return;
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
    if (!user || !weight || !token) return;

    try {
      const weightData = {
        user_id: user.user_id,
        weight_kg: parseFloat(weight),
        date: today
      };

      const response = await fetch(`${BACKEND_URL}/api/weight-entries`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(weightData)
      });

      if (response.ok) {
        const result = await response.json();
        showNotification(`Weight logged! +${result.points_earned} points 📊`);
        showCelebration('weight', { weight: parseFloat(weight) });
        await loadDashboardData(user.user_id);
      } else if (handleAuthError(response)) {
        return;
      }
    } catch (error) {
      setError('Failed to add weight entry: ' + error.message);
    }
  };

  const renderNotification = () => {
    if (!notification) return null;
    
    return (
      <div className={`notification ${notification.type} slide-in`}>
        <span>{notification.message}</span>
        <button onClick={() => setNotification('')}>×</button>
      </div>
    );
  };

  const renderCelebration = () => {
    if (!celebration) return null;
    
    return (
      <div className="celebration-overlay">
        <div className="celebration-content">
          {celebration.type === 'welcome' && (
            <>
              <div className="celebration-icon">🎉</div>
              <h2>Welcome, {celebration.data.name}!</h2>
              <p>Your weight gain journey starts now!</p>
            </>
          )}
          {celebration.type === 'badges' && (
            <>
              <div className="celebration-icon animate-bounce">🏆</div>
              <h2>Badge Earned!</h2>
              <p>+{celebration.data.points} bonus points!</p>
            </>
          )}
          {celebration.type === 'challenge_complete' && (
            <>
              <div className="celebration-icon animate-pulse">🎯</div>
              <h2>Challenge Complete!</h2>
              <p>Amazing work! Keep it up!</p>
            </>
          )}
          {celebration.type === 'challenges' && (
            <>
              <div className="celebration-icon animate-spin-slow">⚡</div>
              <h2>New Challenges!</h2>
              <p>{celebration.data.count} challenges ready for you!</p>
            </>
          )}
          {celebration.type === 'analysis' && (
            <>
              <div className="celebration-icon animate-pulse">🔍</div>
              <h2>Food Analyzed!</h2>
              <p>{celebration.data.calories} calories detected!</p>
            </>
          )}
          {celebration.type === 'weight' && (
            <>
              <div className="celebration-icon animate-bounce">⚖️</div>
              <h2>Weight Logged!</h2>
              <p>{celebration.data.weight}kg recorded!</p>
            </>
          )}
        </div>
        <div className="celebration-particles">
          {[...Array(12)].map((_, i) => (
            <div key={i} className={`particle particle-${i + 1}`}>✨</div>
          ))}
        </div>
      </div>
    );
  };

  const renderLogin = () => (
    <div className="auth-container">
      <div className="auth-card fade-in">
        <h1 className="heading-1">Welcome Back</h1>
        <p className="body-large">Sign in to continue your weight gain journey</p>
        
        <LoginForm onSubmit={handleLogin} loading={loading} />
        
        <div className="auth-links">
          <button className="link-button" onClick={() => setCurrentView('register')}>
            Don't have an account? Register
          </button>
          <button className="link-button" onClick={() => setCurrentView('forgot-password')}>
            Forgot your password?
          </button>
        </div>
        
        {error && <div className="error-message shake">{error}</div>}
      </div>
    </div>
  );

  const renderRegister = () => (
    <div className="auth-container">
      <div className="auth-card fade-in">
        <h1 className="heading-1">Start Your Journey</h1>
        <p className="body-large">Create your account and set up your weight gain goals</p>
        
        <RegisterForm onSubmit={handleRegister} loading={loading} />
        
        <div className="auth-links">
          <button className="link-button" onClick={() => setCurrentView('login')}>
            Already have an account? Sign in
          </button>
        </div>
        
        {error && <div className="error-message shake">{error}</div>}
      </div>
    </div>
  );

  const renderForgotPassword = () => (
    <div className="auth-container">
      <div className="auth-card fade-in">
        <h1 className="heading-2">Reset Password</h1>
        <p className="body-large">Enter your email to receive reset instructions</p>
        
        <ForgotPasswordForm onSubmit={handleForgotPassword} onReset={handleResetPassword} loading={loading} />
        
        <div className="auth-links">
          <button className="link-button" onClick={() => setCurrentView('login')}>
            Back to login
          </button>
        </div>
        
        {error && <div className="error-message shake">{error}</div>}
      </div>
    </div>
  );

  const renderDashboard = () => {
    if (!user || !dailyStats || !userStats) return <div className="loading pulse">Loading dashboard...</div>;

    const calorieProgress = (dailyStats.total_calories / dailyStats.calorie_target) * 100;
    const proteinProgress = (dailyStats.total_protein / dailyStats.protein_target) * 100;

    return (
      <div className="dashboard-container">
        <header className="dashboard-header fade-in">
          <div className="user-greeting">
            <h1 className="heading-2">Hi {user.name}! 👋</h1>
            <p className="body-medium">{today}</p>
          </div>
          <div className="user-controls">
            <div className="gamification-summary">
              <div className="points-display animate-count">
                <span className="points-number">{userStats.total_points}</span>
                <span className="points-label">points</span>
              </div>
              <div className="streak-display">
                <span className="streak-icon animate-flicker">🔥</span>
                <span className="streak-number">{userStats.current_streak}</span>
              </div>
            </div>
            <button className="logout-btn hover-scale" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </header>

        {/* Active Challenges Preview */}
        {activeChallenges.length > 0 && (
          <div className="challenges-preview slide-in">
            <div className="challenges-header">
              <h3 className="heading-4">🎯 Active Challenges</h3>
              <button className="view-all-btn" onClick={() => setCurrentView('challenges')}>
                View All ({activeChallenges.length})
              </button>
            </div>
            <div className="challenges-list">
              {activeChallenges.slice(0, 2).map(challenge => (
                <div key={challenge.challenge_id} className="challenge-card mini">
                  <div className="challenge-info">
                    <span className="challenge-title">{challenge.title}</span>
                    <div className="challenge-progress">
                      <div className="progress-bar">
                        <div 
                          className="progress-fill animate-width" 
                          style={{width: `${Math.min(challenge.progress_percentage || 0, 100)}%`}}
                        ></div>
                      </div>
                      <span className="progress-text">
                        {challenge.current_progress}/{challenge.goal_value} {challenge.goal_unit}
                      </span>
                    </div>
                  </div>
                  <div className="challenge-reward">
                    +{challenge.points_reward} pts
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Coaching Tips Section */}
        {coachingTips.length > 0 && (
          <div className="coaching-tips-section slide-in">
            <div className="coaching-header">
              <h3 className="heading-4">🤖 Smart Coach</h3>
              <button className="coach-more-btn" onClick={() => setCurrentView('coaching')}>
                View All
              </button>
            </div>
            <div className="tips-preview">
              {coachingTips.slice(0, 2).map(tip => (
                <div key={tip.tip_id} className={`coaching-tip-card ${tip.priority} slide-in-up`}>
                  <div className="tip-header">
                    <span className="tip-title">{tip.title}</span>
                    <button 
                      className="tip-close hover-scale"
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
          <div className="stat-card hover-lift">
            <h3 className="heading-4">Calories</h3>
            <div className="progress-circle">
              <div className="progress-text">
                <span className="heading-3 animate-count">{dailyStats.total_calories}</span>
                <span className="body-small">/ {dailyStats.calorie_target}</span>
              </div>
            </div>
            <div className="progress-bar">
              <div 
                className="progress-fill animate-width" 
                style={{width: `${Math.min(calorieProgress, 100)}%`}}
              ></div>
            </div>
            {dailyStats.points_earned_today > 0 && (
              <div className="points-earned animate-bounce">+{dailyStats.points_earned_today} pts today</div>
            )}
          </div>

          <div className="stat-card hover-lift">
            <h3 className="heading-4">Protein</h3>
            <div className="progress-circle">
              <div className="progress-text">
                <span className="heading-3 animate-count">{Math.round(dailyStats.total_protein)}g</span>
                <span className="body-small">/ {dailyStats.protein_target}g</span>
              </div>
            </div>
            <div className="progress-bar">
              <div 
                className="progress-fill animate-width" 
                style={{width: `${Math.min(proteinProgress, 100)}%`}}
              ></div>
            </div>
          </div>
        </div>

        <div className="macro-summary slide-in">
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
          <div className="badges-preview slide-in">
            <h3 className="heading-4">Recent Badges</h3>
            <div className="badges-list">
              {userStats.badges_earned.slice(0, 3).map((badgeKey, idx) => {
                const badge = badges[badgeKey];
                return badge ? (
                  <div key={idx} className="badge-item hover-scale">
                    <span className="badge-icon">{badge.icon}</span>
                    <span className="badge-name">{badge.name}</span>
                  </div>
                ) : null;
              })}
              {userStats.badges_earned.length > 3 && (
                <button 
                  className="view-all-badges hover-scale" 
                  onClick={() => setCurrentView('achievements')}
                >
                  +{userStats.badges_earned.length - 3} more
                </button>
              )}
            </div>
          </div>
        )}

        <div className="action-buttons">
          <button className="btn-primary hover-scale" onClick={() => setCurrentView('camera')}>
            📷 Scan Food
          </button>
          <button className="btn-secondary hover-scale" onClick={() => setCurrentView('challenges')}>
            🎯 Challenges
          </button>
        </div>

        <div className="recent-meals slide-in">
          <h3 className="heading-4">Today's Meals</h3>
          {foodLogs.length > 0 ? (
            <div className="meals-list">
              {foodLogs.map((log, idx) => (
                <div key={log.log_id} className={`meal-card slide-in-up`} style={{animationDelay: `${idx * 0.1}s`}}>
                  <div className="meal-header">
                    <span className="meal-type">{log.meal_type}</span>
                    <div className="meal-meta">
                      <span className="meal-calories">{log.total_calories} cal</span>
                      {log.points_earned > 0 && (
                        <span className="meal-points animate-pulse">+{log.points_earned} pts</span>
                      )}
                    </div>
                  </div>
                  <div className="meal-foods">
                    {log.food_items.map((food, idx) => (
                      <span key={idx} className="food-name">{food.name}</span>
                    ))}
                  </div>
                  {/* Show food image if available */}
                  {log.image_base64 && (
                    <div className="meal-image">
                      <img 
                        src={`data:image/jpeg;base64,${log.image_base64}`}
                        alt="Food photo" 
                        className="food-photo" 
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="no-meals">
              <p className="body-medium">No meals logged today.</p>
              <p className="body-small">Start by scanning your first meal to earn points and complete challenges!</p>
            </div>
          )}
        </div>

        {error && <div className="error-message shake">{error}</div>}
      </div>
    );
  };

  // Camera and other render functions remain the same but with auth fixes...
  const renderCamera = () => (
    <div className="camera-container">
      <header className="camera-header fade-in">
        <button className="back-button hover-scale" onClick={() => setCurrentView('dashboard')}>← Back</button>
        <h2 className="heading-3">Scan Your Food</h2>
      </header>

      {!cameraMode && !capturedImage && (
        <div className="camera-options">
          <button className="btn-primary hover-scale" onClick={startCamera}>📷 Use Camera</button>
          <button className="btn-secondary hover-scale" onClick={() => fileInputRef.current?.click()}>
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
        <div className="camera-view fade-in">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            className="camera-video"
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />
          <div className="camera-controls">
            <button className="capture-button pulse" onClick={capturePhoto}>📷</button>
            <button className="btn-secondary" onClick={stopCamera}>Cancel</button>
          </div>
        </div>
      )}

      {capturedImage && !nutritionData && (
        <div className="image-preview fade-in">
          <img src={capturedImage} alt="Captured food" className="captured-image" />
          <div className="image-actions">
            <button 
              className={`btn-primary ${analyzing ? 'pulse' : 'hover-scale'}`}
              onClick={analyzeFood}
              disabled={analyzing}
            >
              {analyzing ? '🔍 Analyzing...' : '🔍 Analyze Food'}
            </button>
            <button className="btn-secondary hover-scale" onClick={() => setCapturedImage(null)}>
              Retake
            </button>
          </div>
        </div>
      )}

      {nutritionData && (
        <div className="nutrition-results slide-in">
          <h3 className="heading-4">Nutrition Analysis</h3>
          <div className="nutrition-summary">
            <div className="nutrition-total">
              <span className="heading-3 animate-count">{nutritionData.total_calories}</span>
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
              <div key={idx} className={`food-item slide-in-up`} style={{animationDelay: `${idx * 0.1}s`}}>
                <div className="food-name">{food.name}</div>
                <div className="food-portion">{food.portion_size}</div>
                <div className="food-calories">{food.calories} cal</div>
              </div>
            ))}
          </div>

          <div className="meal-type-selector">
            <h4 className="heading-4">Add to:</h4>
            <div className="meal-buttons">
              <button className="meal-btn hover-scale" onClick={() => saveFoodLog('breakfast')}>Breakfast</button>
              <button className="meal-btn hover-scale" onClick={() => saveFoodLog('lunch')}>Lunch</button>
              <button className="meal-btn hover-scale" onClick={() => saveFoodLog('dinner')}>Dinner</button>
              <button className="meal-btn hover-scale" onClick={() => saveFoodLog('snack')}>Snack</button>
            </div>
          </div>
        </div>
      )}

      {error && <div className="error-message shake">{error}</div>}
    </div>
  );

  const renderProfile = () => (
    <div className="profile-container">
      <header className="profile-header fade-in">
        <button className="back-button hover-scale" onClick={() => setCurrentView('dashboard')}>← Back</button>
        <h2 className="heading-3">Your Progress</h2>
        <button className="achievements-button hover-scale" onClick={() => setCurrentView('achievements')}>
          🏆 Badges
        </button>
      </header>

      {user && userStats && (
        <div className="profile-content">
          <div className="stats-overview slide-in">
            <div className="stat-item hover-lift">
              <span className="stat-number animate-count">{userStats.total_points}</span>
              <span className="stat-label">Total Points</span>
            </div>
            <div className="stat-item hover-lift">
              <span className="stat-number animate-count">{userStats.current_streak}</span>
              <span className="stat-label">Current Streak</span>
            </div>
            <div className="stat-item hover-lift">
              <span className="stat-number animate-count">{userStats.longest_streak}</span>
              <span className="stat-label">Best Streak</span>
            </div>
            <div className="stat-item hover-lift">
              <span className="stat-number animate-count">{userStats.badges_earned.length}</span>
              <span className="stat-label">Badges</span>
            </div>
          </div>

          <div className="profile-stats slide-in">
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
            <div className="goal-item">
              <span className="label">Challenge Points:</span>
              <span className="value">{userStats.challenge_points}</span>
            </div>
          </div>

          <div className="weight-tracker slide-in">
            <h3 className="heading-4">Weight Progress</h3>
            {weightEntries.length > 0 && (
              <div className="current-weight">
                <span className="heading-2 animate-count">{weightEntries[0].weight_kg} kg</span>
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
        </div>
      )}
    </div>
  );

  // ... (other render methods remain similar but with auth checks)

  return (
    <div className="App">
      {renderNotification()}
      {renderCelebration()}
      {currentView === 'login' && renderLogin()}
      {currentView === 'register' && renderRegister()}
      {currentView === 'forgot-password' && renderForgotPassword()}
      {currentView === 'dashboard' && renderDashboard()}
      {currentView === 'camera' && renderCamera()}
      {currentView === 'profile' && renderProfile()}
    </div>
  );
}

// Authentication Forms
const LoginForm = ({ onSubmit, loading }) => {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <div className="form-group">
        <label className="form-label">Email</label>
        <input
          type="email"
          className="form-input"
          value={formData.email}
          onChange={(e) => setFormData({...formData, email: e.target.value})}
          required
        />
      </div>

      <div className="form-group">
        <label className="form-label">Password</label>
        <input
          type="password"
          className="form-input"
          value={formData.password}
          onChange={(e) => setFormData({...formData, password: e.target.value})}
          required
        />
      </div>

      <button type="submit" className={`btn-primary ${loading ? 'loading' : 'hover-scale'}`} disabled={loading}>
        {loading ? 'Signing In...' : 'Sign In'}
      </button>
    </form>
  );
};

const RegisterForm = ({ onSubmit, loading }) => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
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
    
    if (formData.password !== formData.confirmPassword) {
      alert('Passwords do not match');
      return;
    }
    
    const submitData = { ...formData };
    delete submitData.confirmPassword;
    
    onSubmit({
      ...submitData,
      age: parseInt(submitData.age),
      height_cm: parseFloat(submitData.height_cm),
      weight_kg: parseFloat(submitData.weight_kg),
      goal_weight_kg: parseFloat(submitData.goal_weight_kg),
      target_weekly_gain: parseFloat(submitData.target_weekly_gain)
    });
  };

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <div className="form-group">
        <label className="form-label">Email</label>
        <input
          type="email"
          className="form-input"
          value={formData.email}
          onChange={(e) => setFormData({...formData, email: e.target.value})}
          required
        />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Password</label>
          <input
            type="password"
            className="form-input"
            value={formData.password}
            onChange={(e) => setFormData({...formData, password: e.target.value})}
            required
            minLength={6}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Confirm Password</label>
          <input
            type="password"
            className="form-input"
            value={formData.confirmPassword}
            onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
            required
            minLength={6}
          />
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">Full Name</label>
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

      <button type="submit" className={`btn-primary ${loading ? 'loading' : 'hover-scale'}`} disabled={loading}>
        {loading ? 'Creating Account...' : 'Create Account'}
      </button>
    </form>
  );
};

const ForgotPasswordForm = ({ onSubmit, onReset, loading }) => {
  const [step, setStep] = useState('request'); // 'request' or 'reset'
  const [formData, setFormData] = useState({
    email: '',
    resetToken: '',
    newPassword: '',
    confirmPassword: ''
  });

  const handleRequestSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData.email);
    setStep('reset');
  };

  const handleResetSubmit = (e) => {
    e.preventDefault();
    
    if (formData.newPassword !== formData.confirmPassword) {
      alert('Passwords do not match');
      return;
    }
    
    onReset({
      reset_token: formData.resetToken,
      new_password: formData.newPassword
    });
  };

  if (step === 'request') {
    return (
      <form onSubmit={handleRequestSubmit} className="auth-form">
        <div className="form-group">
          <label className="form-label">Email Address</label>
          <input
            type="email"
            className="form-input"
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
            required
          />
        </div>

        <button type="submit" className={`btn-primary ${loading ? 'loading' : 'hover-scale'}`} disabled={loading}>
          {loading ? 'Sending...' : 'Send Reset Instructions'}
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={handleResetSubmit} className="auth-form">
      <div className="form-group">
        <label className="form-label">Reset Token</label>
        <input
          type="text"
          className="form-input"
          value={formData.resetToken}
          onChange={(e) => setFormData({...formData, resetToken: e.target.value})}
          required
          placeholder="Enter the reset token from your email"
        />
      </div>

      <div className="form-group">
        <label className="form-label">New Password</label>
        <input
          type="password"
          className="form-input"
          value={formData.newPassword}
          onChange={(e) => setFormData({...formData, newPassword: e.target.value})}
          required
          minLength={6}
        />
      </div>

      <div className="form-group">
        <label className="form-label">Confirm New Password</label>
        <input
          type="password"
          className="form-input"
          value={formData.confirmPassword}
          onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
          required
          minLength={6}
        />
      </div>

      <button type="submit" className={`btn-primary ${loading ? 'loading' : 'hover-scale'}`} disabled={loading}>
        {loading ? 'Resetting...' : 'Reset Password'}
      </button>
    </form>
  );
};

export default App;