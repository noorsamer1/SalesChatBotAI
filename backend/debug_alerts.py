#!/usr/bin/env python3
"""Debug script for Business Intelligence Alert System"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.db import engine
from sqlalchemy import text
from app.services.prompt_builder import get_real_time_business_alerts

def test_database_connection():
    """Test basic database connectivity"""
    print("🔍 Testing database connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM sales_data")).fetchone()
            print(f"✅ Database connected. Total records: {result[0]:,}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_data_availability():
    """Test data availability by year"""
    print("\n🔍 Testing data availability by year...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT yy, COUNT(*) as records, 
                       ROUND(SUM(sales_value), 0) as total_sales
                FROM sales_data 
                GROUP BY yy 
                ORDER BY yy
            """)).fetchall()
            
            for row in result:
                print(f"  {row[0]}: {row[1]:,} records, {row[2]:,.0f} KWD total sales")
            return True
    except Exception as e:
        print(f"❌ Data availability test failed: {e}")
        return False

def test_performance_drops():
    """Test for actual performance drops that should trigger alerts"""
    print("\n🔍 Testing for performance drops (2024 vs 2023)...")
    try:
        with engine.connect() as conn:
            query = """
            WITH performance_comparison AS (
                SELECT 
                    salesman_name_e,
                    ROUND(SUM(CASE WHEN yy = 2024 THEN sales_value ELSE 0 END), 3) as sales_2024,
                    ROUND(SUM(CASE WHEN yy = 2023 THEN sales_value ELSE 0 END), 3) as sales_2023
                FROM sales_data 
                WHERE yy IN (2023, 2024)
                GROUP BY salesman_name_e
                HAVING SUM(CASE WHEN yy = 2023 THEN sales_value ELSE 0 END) > 50000
            )
            SELECT salesman_name_e, sales_2024, sales_2023,
                   ROUND(((sales_2024 - sales_2023) / NULLIF(sales_2023, 0)) * 100, 1) as performance_change
            FROM performance_comparison 
            WHERE sales_2024 < sales_2023 * 0.7
            ORDER BY performance_change ASC LIMIT 5
            """
            
            result = conn.execute(text(query)).fetchall()
            print(f"  Found {len(result)} salespeople with 30%+ performance drops:")
            
            for row in result:
                print(f"    🔴 {row[0]}: {row[3]}% change ({row[2]:,.0f} → {row[1]:,.0f})")
                
            return len(result) > 0
            
    except Exception as e:
        print(f"❌ Performance drop test failed: {e}")
        return False

def test_recent_trends():
    """Test for recent trends (2025 YTD vs 2024 same period)"""
    print("\n🔍 Testing for recent trends (2025 YTD vs 2024 Jan-May)...")
    try:
        with engine.connect() as conn:
            query = """
            WITH recent_comparison AS (
                SELECT 
                    salesman_name_e,
                    ROUND(SUM(CASE WHEN yy = 2025 THEN sales_value ELSE 0 END), 3) as sales_2025_ytd,
                    ROUND(SUM(CASE WHEN yy = 2024 AND mm <= 5 THEN sales_value ELSE 0 END), 3) as sales_2024_same_period
                FROM sales_data 
                WHERE (yy = 2025) OR (yy = 2024 AND mm <= 5)
                GROUP BY salesman_name_e
                HAVING SUM(CASE WHEN yy = 2024 AND mm <= 5 THEN sales_value ELSE 0 END) > 20000
            )
            SELECT salesman_name_e, sales_2025_ytd, sales_2024_same_period,
                   ROUND(((sales_2025_ytd - sales_2024_same_period) / NULLIF(sales_2024_same_period, 0)) * 100, 1) as recent_change
            FROM recent_comparison 
            WHERE sales_2025_ytd < sales_2024_same_period * 0.6
            ORDER BY recent_change ASC LIMIT 3
            """
            
            result = conn.execute(text(query)).fetchall()
            print(f"  Found {len(result)} salespeople with 40%+ recent decline:")
            
            for row in result:
                print(f"    🔴 {row[0]}: {row[3]}% recent change ({row[2]:,.0f} → {row[1]:,.0f})")
                
            return len(result) > 0
            
    except Exception as e:
        print(f"❌ Recent trends test failed: {e}")
        return False

def test_alert_system():
    """Test the actual alert system function"""
    print("\n🔍 Testing Business Intelligence Alert System...")
    try:
        alerts = get_real_time_business_alerts("top salespeople performance")
        
        print(f"  Alert count: {alerts['alert_count']}")
        print(f"  Performance alerts: {len(alerts['performance_alerts'])}")
        print(f"  Quality alerts: {len(alerts['quality_alerts'])}")
        print(f"  Growth opportunities: {len(alerts['opportunity_alerts'])}")
        print(f"  Risk indicators: {len(alerts['risk_indicators'])}")
        
        if alerts['alert_count'] > 0:
            print("\n  🚨 Active Alerts:")
            for alert in alerts['performance_alerts']:
                print(f"    {alert}")
            for alert in alerts['quality_alerts']:
                print(f"    {alert}")
            for alert in alerts['opportunity_alerts']:
                print(f"    {alert}")
            for alert in alerts['risk_indicators']:
                print(f"    {alert}")
        else:
            print("  ⚠️ No alerts generated")
        
        return alerts['alert_count'] > 0
        
    except Exception as e:
        print(f"❌ Alert system test failed: {e}")
        return False

def main():
    """Run all debug tests"""
    print("🔧 BUSINESS INTELLIGENCE ALERT SYSTEM DEBUG")
    print("=" * 50)
    
    # Run all tests
    tests = [
        ("Database Connection", test_database_connection),
        ("Data Availability", test_data_availability),
        ("Performance Drops", test_performance_drops),
        ("Recent Trends", test_recent_trends),
        ("Alert System", test_alert_system),
    ]
    
    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()
    
    print("\n" + "=" * 50)
    print("🏁 DEBUG SUMMARY:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    if not results["Alert System"]:
        print("\n💡 RECOMMENDATION:")
        if not results["Performance Drops"] and not results["Recent Trends"]:
            print("  - No significant performance drops found in data")
            print("  - Consider lowering alert thresholds for testing")
            print("  - Or add test data with performance drops")
        else:
            print("  - Data exists but alert system isn't processing it correctly")
            print("  - Check alert system logic and SQL queries")

if __name__ == "__main__":
    main() 