import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from "../config/api.js";
import './AnalyticsDashboard.css';

const AnalyticsDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(30);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [isScrolledToBottom, setIsScrolledToBottom] = useState(false);
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    fetchDashboardData();
  }, [timeRange]);

  // Handle scroll events
  useEffect(() => {
    const handleScroll = (e) => {
      const element = e.target;
      const scrollTop = element.scrollTop;
      const scrollHeight = element.scrollHeight;
      const clientHeight = element.clientHeight;
      
      // Calculate scroll progress percentage
      const maxScroll = scrollHeight - clientHeight;
      const progressPercent = maxScroll > 0 ? (scrollTop / maxScroll) * 100 : 0;
      setScrollProgress(Math.min(progressPercent, 100));
      
      // Show scroll-to-top button after scrolling 200px
      setShowScrollTop(scrollTop > 200);
      
      // Check if scrolled to bottom (within 10px threshold)
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
      setIsScrolledToBottom(isAtBottom);
    };

    const dashboardElement = document.querySelector('.analytics-dashboard');
    if (dashboardElement) {
      dashboardElement.addEventListener('scroll', handleScroll);
      return () => dashboardElement.removeEventListener('scroll', handleScroll);
    }
  }, []);

  const scrollToTop = () => {
    const dashboardElement = document.querySelector('.analytics-dashboard');
    if (dashboardElement) {
      dashboardElement.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/analytics/dashboard?days=${timeRange}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('futuretec_token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data.data);
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ title, value, icon, color, subtitle }) => (
    <div className="stat-card" style={{ borderLeft: `4px solid ${color}` }}>
      <div className="stat-content">
        <div className="stat-header">
          <span className="stat-icon">{icon}</span>
          <h3 className="stat-title">{title}</h3>
        </div>
        <div className="stat-value">{value}</div>
        {subtitle && <div className="stat-subtitle">{subtitle}</div>}
      </div>
    </div>
  );

  const CategoryCard = ({ category }) => (
    <div 
      className="category-card" 
      style={{ backgroundColor: `${category.color}15`, borderColor: category.color }}
    >
      <div className="category-header">
        <span className="category-icon">{category.icon}</span>
        <div className="category-info">
          <h4 className="category-name">{category.name.replace('_', ' ').toUpperCase()}</h4>
          <p className="category-description">{category.description}</p>
        </div>
      </div>
      <div className="category-stats">
        <div className="category-count">{category.count}</div>
        <div className="category-label">Queries</div>
      </div>
    </div>
  );

  const QueryPatternCard = ({ pattern }) => (
    <div className="query-pattern-card">
      <div className="pattern-header">
        <span className="pattern-category" style={{ backgroundColor: getCategoryColor(pattern.category) }}>
          {pattern.category.replace('_', ' ')}
        </span>
        <span className="pattern-count">{pattern.count}x</span>
      </div>
      <div className="pattern-example">{pattern.example}</div>
      <div className="pattern-stats">
        <span className="pattern-time">~{pattern.avg_time}ms avg</span>
      </div>
    </div>
  );

  const getCategoryColor = (category) => {
    const colors = {
      'top_rankings': '#3B82F6',
      'sales_trends': '#10B981',
      'returns_analysis': '#F59E0B',
      'profitability': '#8B5CF6',
      'comparisons': '#EF4444',
      'growth_analysis': '#06B6D4'
    };
    return colors[category] || '#6B7280';
  };

  const renderQueryVolumeChart = () => {
    if (!dashboardData?.daily_queries || dashboardData.daily_queries.length === 0) {
      return <div className="chart-placeholder">No query data available</div>;
    }

    const maxQueries = Math.max(...dashboardData.daily_queries.map(d => d.query_count));
    
    return (
      <div className="query-volume-chart">
        <div className="chart-header">
          <h3>Query Volume Over Time</h3>
          <div className="chart-legend">
            <span className="legend-item">
              <span className="legend-color" style={{ backgroundColor: '#3B82F6' }}></span>
              Daily Queries
            </span>
          </div>
        </div>
        <div className="chart-container">
          <div className="chart-bars">
            {dashboardData.daily_queries.map((day, index) => (
              <div key={index} className="chart-bar-container">
                <div 
                  className="chart-bar"
                  style={{ 
                    height: `${(day.query_count / maxQueries) * 100}%`,
                    backgroundColor: '#3B82F6'
                  }}
                  title={`${day.date}: ${day.query_count} queries`}
                ></div>
                <div className="chart-label">
                  {new Date(day.date).getDate()}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderChartTypesDistribution = () => {
    if (!dashboardData?.chart_types) return null;

    const total = dashboardData.chart_types.reduce((sum, item) => sum + item.count, 0);
    
    return (
      <div className="chart-types-distribution">
        <h3>Chart Types Usage</h3>
        <div className="distribution-items">
          {dashboardData.chart_types.map((type, index) => {
            const percentage = ((type.count / total) * 100).toFixed(1);
            const colors = { bar: '#3B82F6', line: '#10B981', pie: '#F59E0B', table: '#8B5CF6' };
            
            return (
              <div key={index} className="distribution-item">
                <div className="distribution-header">
                  <span className="distribution-label">{type.type.toUpperCase()}</span>
                  <span className="distribution-percentage">{percentage}%</span>
                </div>
                <div className="distribution-bar">
                  <div 
                    className="distribution-fill"
                    style={{ 
                      width: `${percentage}%`,
                      backgroundColor: colors[type.type] || '#6B7280'
                    }}
                  ></div>
                </div>
                <div className="distribution-count">{type.count} queries</div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="analytics-dashboard loading">
        <div className="loading-content">
          <div className="loading-spinner"></div>
          <h2>Loading Analytics Dashboard...</h2>
          <p>Analyzing user query patterns and popular insights</p>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="analytics-dashboard error">
        <div className="error-content">
          <h2>⚠️ Unable to Load Analytics</h2>
          <p>Please check your connection and try again.</p>
          <button onClick={fetchDashboardData} className="retry-button">
            🔄 Retry
          </button>
        </div>
      </div>
    );
  }

  // Handle missing analytics tables
  if (dashboardData.tables_missing) {
    return (
      <div className="analytics-dashboard setup-needed">
        <div className="setup-content">
          <h2>📊 Analytics Setup Required</h2>
          <p>Analytics tracking is not yet configured. Follow these steps to enable analytics:</p>
          
          <div className="setup-steps">
            <div className="setup-step">
              <span className="step-number">1</span>
              <div className="step-content">
                <h3>Run Database Setup</h3>
                <div className="code-block">
                  <code>cd backend && python create_analytics_tables.py</code>
                </div>
              </div>
            </div>
            
            <div className="setup-step">
              <span className="step-number">2</span>
              <div className="step-content">
                <h3>Restart Backend Server</h3>
                <p>Restart your backend to enable analytics tracking</p>
              </div>
            </div>
            
            <div className="setup-step">
              <span className="step-number">3</span>
              <div className="step-content">
                <h3>Use Your Chatbot</h3>
                <p>Ask some questions to generate analytics data</p>
              </div>
            </div>
          </div>
          
          <div className="setup-benefits">
            <h3>🎯 What You'll Get:</h3>
            <ul>
              <li>📈 User query pattern analysis</li>
              <li>🔥 Popular insights tracking</li>
              <li>⚡ Performance monitoring</li>
              <li>📊 Usage statistics</li>
              <li>🧠 Smart query suggestions</li>
            </ul>
          </div>
          
          <button onClick={fetchDashboardData} className="retry-button">
            🔄 Check Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`analytics-dashboard ${isScrolledToBottom ? 'scrolled-to-bottom' : ''}`}>
      {/* Scroll Progress Indicator */}
      <div 
        className="scroll-progress" 
        style={{ width: `${scrollProgress}%` }}
      ></div>
      
      {/* Header */}
      <div className="dashboard-header">
        <div className="header-content">
          <h1>📊 Analytics Dashboard</h1>
          <p>User query patterns and popular insights</p>
        </div>
        <div className="header-controls">
          <select 
            value={timeRange} 
            onChange={(e) => setTimeRange(parseInt(e.target.value))}
            className="time-range-selector"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="stats-grid">
        <StatCard
          title="Total Queries"
          value={dashboardData.summary.total_queries.toLocaleString()}
          icon="💬"
          color="#3B82F6"
          subtitle={`${dashboardData.summary.active_days} active days`}
        />
        <StatCard
          title="Success Rate"
          value={`${dashboardData.summary.success_rate}%`}
          icon="✅"
          color="#10B981"
          subtitle="Query completion rate"
        />
        <StatCard
          title="Avg Response Time"
          value={`${dashboardData.summary.avg_response_time}ms`}
          icon="⚡"
          color="#F59E0B"
          subtitle="System performance"
        />
        <StatCard
          title="Popular Categories"
          value={dashboardData.popular_categories.length}
          icon="📈"
          color="#8B5CF6"
          subtitle="Query categories used"
        />
      </div>

      {/* Charts Section */}
      <div className="charts-section">
        <div className="chart-card">
          {renderQueryVolumeChart()}
        </div>
        <div className="chart-card">
          {renderChartTypesDistribution()}
        </div>
      </div>

      {/* Popular Categories */}
      <div className="section">
        <div className="section-header">
          <h2>🏆 Popular Query Categories</h2>
          <p>Most frequently used analytics categories</p>
        </div>
        <div className="categories-grid">
          {dashboardData.popular_categories?.slice(0, 6).map((category, index) => (
            <CategoryCard key={index} category={category} />
          ))}
        </div>
      </div>

      {/* Popular Insights */}
      <div className="section">
        <div className="section-header">
          <h2>🔥 Trending Query Patterns</h2>
          <p>Most popular analytics queries and patterns</p>
        </div>
        <div className="insights-grid">
          {dashboardData.popular_insights?.slice(0, 9).map((pattern, index) => (
            <QueryPatternCard key={index} pattern={pattern} />
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="section">
        <div className="section-header">
          <h2>🕒 Recent Query Activity</h2>
          <p>Latest analytics requests and their performance</p>
        </div>
        <div className="recent-queries">
          {dashboardData.recent_queries?.slice(0, 10).map((query, index) => (
            <div key={index} className="recent-query-item">
              <div className="query-content">
                <div className="query-text">{query.query}</div>
                <div className="query-meta">
                  <span className="query-category" style={{ backgroundColor: getCategoryColor(query.category) }}>
                    {query.category.replace('_', ' ')}
                  </span>
                  <span className="query-time">{query.timestamp}</span>
                  <span className="query-performance">{query.response_time}ms</span>
                  <span className={`query-status ${query.success ? 'success' : 'error'}`}>
                    {query.success ? '✅' : '❌'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Scroll to Top Button */}
      {showScrollTop && (
        <button 
          className="scroll-to-top visible" 
          onClick={scrollToTop}
          aria-label="Scroll to top"
        >
          ↑
        </button>
      )}
    </div>
  );
};

export default AnalyticsDashboard; 