import time
import requests
import statistics
import os
import sqlite3

BASE_URL = "http://127.0.0.1:5000"
DB_PATH = os.path.join(os.path.dirname(__file__), "lablink.db")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT id FROM equipment WHERE code = 'GPU-CS-4090A'")
row = c.fetchone()
eq_id = row[0] if row else 491
conn.close()

endpoints = [
    ("Root Redirect", f"{BASE_URL}/"),
    ("Student Dashboard", f"{BASE_URL}/student/dashboard"),
    ("Equipment Catalogue", f"{BASE_URL}/student/equipment"),
    ("Slots Availability API", f"{BASE_URL}/api/equipment/{eq_id}/slots?date=2026-11-24"),
    ("Equipment Detail API", f"{BASE_URL}/api/equipment/{eq_id}"),
    ("Analytics API", f"{BASE_URL}/analytics/api/summary"),
    ("Faculty Dashboard", f"{BASE_URL}/faculty/dashboard"),
    ("AI Conflict Center", f"{BASE_URL}/faculty/conflicts"),
    ("Resource Analytics HTML", f"{BASE_URL}/analytics/")
]

session = requests.Session()
# Switch to faculty for benchmarking so all routes accessible
session.get(f"{BASE_URL}/switch-role/faculty")

print("=" * 75)
print(f"   LabLink Latency & Performance Benchmark (30 iterations per route)")
print("=" * 75)

summary = []

for name, url in endpoints:
    latencies = []
    # Warmup
    session.get(url)
    
    for _ in range(30):
        t0 = time.perf_counter()
        r = session.get(url)
        t1 = time.perf_counter()
        if r.status_code == 200:
            latencies.append((t1 - t0) * 1000.0)
            
    if latencies:
        mean_lat = statistics.mean(latencies)
        med_lat = statistics.median(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        p95_lat = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max_lat
        
        summary.append({
            "name": name,
            "mean": mean_lat,
            "med": med_lat,
            "min": min_lat,
            "max": max_lat,
            "p95": p95_lat
        })
        print(f"{name:<25} | Mean: {mean_lat:6.2f}ms | Median: {med_lat:6.2f}ms | Min: {min_lat:5.2f}ms | P95: {p95_lat:6.2f}ms")
    else:
        print(f"{name:<25} | FAILED")

print("=" * 75)
