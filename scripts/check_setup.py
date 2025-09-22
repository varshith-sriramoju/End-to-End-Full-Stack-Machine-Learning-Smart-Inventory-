#!/usr/bin/env python3
"""
Setup verification script for SmartInventory
"""

import os
import sys
import requests
import time
from urllib.parse import urljoin

def check_service(name, url, timeout=30):
    """Check if a service is responding"""
    print(f"Checking {name} at {url}...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name} is running")
                return True
        except requests.exceptions.RequestException:
            pass

        time.sleep(2)

    print(f"❌ {name} is not responding")
    return False

def check_static_files():
    """Check if static files are accessible"""
    static_urls = [
        "http://localhost:8000/static/css/main.css",
        "http://localhost:8000/static/js/main.js",
        "http://localhost:8000/static/js/api.js"
    ]

    for url in static_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ Static file accessible: {url}")
            else:
                print(f"❌ Static file not found: {url}")
                return False
        except requests.exceptions.RequestException:
            print(f"❌ Cannot access static file: {url}")
            return False

    return True

def check_api_endpoints():
    """Check if API endpoints are working"""
    endpoints = [
        ("Health Check", "http://localhost:8000/health/"),
        ("API Docs", "http://localhost:8000/docs/"),
        ("Dashboard Stats", "http://localhost:8000/api/dashboard/stats/")
    ]

    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code in [200, 401]:  # 401 is OK for protected endpoints
                print(f"✅ {name} endpoint working")
            else:
                print(f"❌ {name} endpoint failed: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ {name} endpoint error: {e}")
            return False

    return True

def main():
    """Main setup verification"""
    print("🔍 SmartInventory Setup Verification")
    print("=" * 40)

    # Check main services
    services = [
        ("Django Web Server", "http://localhost:8000/"),
        ("MySQL Database", "http://localhost:8000/health/"),
        ("Redis Cache", "http://localhost:8000/health/")
    ]

    all_good = True

    # Check services
    for name, url in services:
        if not check_service(name, url):
            all_good = False

    # Check static files
    print("\n📁 Checking Static Files...")
    if not check_static_files():
        all_good = False

    # Check API endpoints
    print("\n🔌 Checking API Endpoints...")
    if not check_api_endpoints():
        all_good = False

    print("\n" + "=" * 40)
    if all_good:
        print("🎉 All checks passed! SmartInventory is ready to use.")
        print("🌐 Access the application at: http://localhost:8000")
        print("📚 API Documentation at: http://localhost:8000/docs/")
    else:
        print("❌ Some checks failed. Please review the errors above.")
        print("📖 Check SETUP.md for troubleshooting steps.")
        sys.exit(1)

if __name__ == "__main__":
    main()