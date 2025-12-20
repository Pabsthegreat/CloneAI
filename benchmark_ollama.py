#!/usr/bin/env python3
"""
Benchmark Ollama response times: subprocess vs persistent server
Tests with both small and large inputs to measure prompt processing overhead.
"""

import time
import subprocess
import json
import urllib.request
import urllib.error

# Large input simulation - typical email/document context
LARGE_PROMPT = """Analyze this email thread and provide a brief summary:

From: john@example.com
To: team@example.com
Subject: Q4 Planning Meeting

Hi team,

I wanted to follow up on our discussion from last week regarding the Q4 planning initiative. Here are the key points we covered:

1. Budget allocation for the new marketing campaign
2. Timeline for the product launch
3. Resource planning for the engineering team
4. Customer feedback integration
5. Competitive analysis updates

Please review the attached documents and provide your feedback by Friday. We need to finalize the budget numbers before the board meeting next Tuesday.

Key metrics from Q3:
- Revenue: $2.5M (up 15% YoY)
- Customer acquisition: 1,200 new customers
- Churn rate: 3.2% (down from 4.1%)
- NPS score: 72

Action items from the last meeting:
- Sarah: Complete competitive analysis
- Mike: Finalize engineering roadmap
- Lisa: Prepare customer survey results
- Tom: Update financial projections

Let me know if you have any questions.

Best,
John

---
Reply from Sarah:

Thanks John, I'll have the competitive analysis ready by Thursday. Quick question - should we include the new entrant (TechCorp) in the analysis?

---
Reply from Mike:

The engineering roadmap is 80% complete. We're still waiting on final requirements for the mobile app features.

Provide a 2-sentence summary of the key action items and deadlines."""

def benchmark_subprocess_ollama(model="qwen3:4b-instruct", prompt="Hello", runs=3, label="small"):
    """Current approach - spawn subprocess each time"""
    print(f"\n📊 Benchmarking subprocess approach - {label} input ({runs} runs)...")
    times = []
    
    for i in range(runs):
        start = time.time()
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            timeout=60
        )
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.2f}s (first token)")
    
    avg = sum(times) / len(times)
    print(f"  Average: {avg:.2f}s")
    return avg

def benchmark_persistent_ollama(model="qwen3:4b-instruct", prompt="Hello", runs=3, label="small", options=None):
    """Using persistent Ollama HTTP API server"""
    print(f"\n📊 Benchmarking persistent API approach - {label} input ({runs} runs)...")
    
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
        
        payload = {"model": model, "prompt": prompt, "stream": True}
        if options:
            payload["options"] = options
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
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

def keep_model_alive(model="qwen3:4b-instruct", keep_alive="30m"):
    """Send a keep-alive request to prevent model unloading"""
    try:
        payload = {"model": model, "prompt": "", "keep_alive": keep_alive}
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except:
        return False

if __name__ == "__main__":
    print("🚀 Ollama Latency Benchmark (Small vs Large Inputs)")
    print("=" * 60)
    
    model = "qwen3:4b-instruct"
    small_prompt = "Hello"
    large_prompt = LARGE_PROMPT
    
    print(f"\n📏 Input sizes:")
    print(f"   Small: {len(small_prompt)} chars")
    print(f"   Large: {len(large_prompt)} chars (~{len(large_prompt)//4} tokens)")
    
    # Check model status
    if check_model_loaded(model):
        print(f"\n✅ Model {model} is already loaded in memory")
    else:
        print(f"\n⚠️  Model {model} is NOT loaded (first request will be slower)")
    
    # Keep model alive
    print("\n🔥 Sending keep-alive request...")
    keep_model_alive(model, "30m")
    
    # Optimized options for faster prefill
    fast_options = {
        "num_ctx": 4096,      # Smaller context = faster
        "num_batch": 512,     # Larger batch = faster prefill
        "num_gpu": 99,        # All layers on GPU
    }
    
    print("\n" + "=" * 60)
    print("📊 SMALL INPUT TESTS")
    print("=" * 60)
    
    # Small input - subprocess
    subprocess_small = benchmark_subprocess_ollama(model=model, prompt=small_prompt, runs=3, label="small")
    
    # Small input - persistent API
    persistent_small = benchmark_persistent_ollama(model=model, prompt=small_prompt, runs=3, label="small")
    
    # Small input - persistent with optimization
    persistent_small_opt = benchmark_persistent_ollama(model=model, prompt=small_prompt, runs=3, label="small+optimized", options=fast_options)
    
    print("\n" + "=" * 60)
    print("📊 LARGE INPUT TESTS")
    print("=" * 60)
    
    # Large input - subprocess
    subprocess_large = benchmark_subprocess_ollama(model=model, prompt=large_prompt, runs=3, label="large")
    
    # Large input - persistent API
    persistent_large = benchmark_persistent_ollama(model=model, prompt=large_prompt, runs=3, label="large")
    
    # Large input - persistent with optimization
    persistent_large_opt = benchmark_persistent_ollama(model=model, prompt=large_prompt, runs=3, label="large+optimized", options=fast_options)
    
    # Summary
    print("\n" + "=" * 60)
    print("📈 RESULTS SUMMARY:")
    print("=" * 60)
    print("\n  SMALL INPUT (baseline):")
    print(f"    Subprocess:            {subprocess_small:.2f}s")
    if persistent_small:
        print(f"    Persistent API:        {persistent_small:.2f}s")
    if persistent_small_opt:
        print(f"    Persistent + Optimized: {persistent_small_opt:.2f}s")
    
    print("\n  LARGE INPUT:")
    print(f"    Subprocess:            {subprocess_large:.2f}s")
    if persistent_large:
        print(f"    Persistent API:        {persistent_large:.2f}s")
    if persistent_large_opt:
        print(f"    Persistent + Optimized: {persistent_large_opt:.2f}s")
        improvement = subprocess_large - persistent_large_opt
        speedup = subprocess_large / persistent_large_opt if persistent_large_opt > 0 else 0
        print(f"\n  🎯 Best improvement: {speedup:.1f}x faster ({improvement:.2f}s saved)")
    
    print("\n💡 RECOMMENDATIONS:")
    print("   1. Set OLLAMA_USE_HTTP=1 to use persistent API")
    print("   2. Keep model warm with keep_alive requests")
    print("   3. Use num_ctx appropriate to your actual needs (smaller = faster)")
    print("   4. Ensure num_gpu=99 to use GPU for all layers")
    print("   5. Consider a smaller/faster model for classification tasks")
