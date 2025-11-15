#!/usr/bin/env python3
"""
Benchmark Ollama response times: subprocess vs persistent server
"""

import time
import subprocess
import json
import urllib.request
import urllib.error

def benchmark_subprocess_ollama(model="qwen3:4b-instruct", prompt="Hello", runs=3):
    """Current approach - spawn subprocess each time"""
    print(f"\n📊 Benchmarking subprocess approach ({runs} runs)...")
    times = []
    
    for i in range(runs):
        start = time.time()
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            timeout=30
        )
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.2f}s (first token)")
    
    avg = sum(times) / len(times)
    print(f"  Average: {avg:.2f}s")
    return avg

def benchmark_persistent_ollama(model="qwen3:4b-instruct", prompt="Hello", runs=3):
    """Using persistent Ollama HTTP API server"""
    print(f"\n📊 Benchmarking persistent API approach ({runs} runs)...")
    
    # Check if Ollama server is running
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status != 200:
                print("  ⚠️  Ollama server not running. Start it with: ollama serve")
                return None
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
        print("  ⚠️  Ollama server not running. Start it with: ollama serve")
        return None
    
    times = []
    
    for i in range(runs):
        start = time.time()
        
        # Use streaming API to get time to first token
        data = json.dumps({"model": model, "prompt": prompt, "stream": True}).encode('utf-8')
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                # Read first line to get time to first token
                first_line = response.readline()
                if first_line:
                    elapsed = time.time() - start
                    times.append(elapsed)
                    print(f"  Run {i+1}: {elapsed:.2f}s (first token)")
        except Exception as e:
            print(f"  Run {i+1}: Failed - {e}")
            continue
    
    if not times:
        return None
        
    avg = sum(times) / len(times)
    print(f"  Average: {avg:.2f}s")
    return avg

def check_model_loaded(model="qwen3:4b-instruct"):
    """Check if model is already loaded in memory"""
    try:
        req = urllib.request.Request("http://localhost:11434/api/ps")
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode('utf-8'))
            models = data.get("models", [])
            loaded = any(m.get("name", "").startswith(model.split(":")[0]) for m in models)
            return loaded
    except:
        return False
    return False

if __name__ == "__main__":
    print("🚀 Ollama Latency Benchmark")
    print("=" * 50)
    
    model = "qwen3:4b-instruct"
    
    # Check model status
    if check_model_loaded(model):
        print(f"✅ Model {model} is already loaded in memory")
    else:
        print(f"⚠️  Model {model} is NOT loaded (first request will be slower)")
    
    # Benchmark current approach
    subprocess_avg = benchmark_subprocess_ollama(model=model, runs=3)
    
    # Benchmark persistent approach
    persistent_avg = benchmark_persistent_ollama(model=model, runs=3)
    
    # Summary
    print("\n" + "=" * 50)
    print("📈 RESULTS:")
    print(f"  Subprocess approach: {subprocess_avg:.2f}s avg")
    if persistent_avg:
        print(f"  Persistent API:      {persistent_avg:.2f}s avg")
        speedup = subprocess_avg / persistent_avg
        time_saved = subprocess_avg - persistent_avg
        print(f"  Speedup:            {speedup:.1f}x faster ({time_saved:.2f}s saved)")
        print(f"\n💡 Switching to persistent API could reduce latency by ~{time_saved:.1f}s per request!")
    else:
        print(f"  Persistent API:      Not available (server not running)")
        print(f"\n💡 Start Ollama server with: ollama serve")
        print(f"   Then model stays loaded and subsequent requests are much faster!")
