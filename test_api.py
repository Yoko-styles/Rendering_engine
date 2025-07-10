import json
import requests
import time
from pathlib import Path

# API configuration
API_BASE_URL = "http://localhost:8000"
PATTERN_FILE = "assets/Patterns/dress_pencil_specification.json"

def load_pattern_json():
    """Load the pattern JSON file"""
    pattern_path = Path(PATTERN_FILE)
    if not pattern_path.exists():
        print(f"❌ Pattern file not found: {pattern_path}")
        return None
    
    try:
        with open(pattern_path, 'r') as f:
            pattern_data = json.load(f)
        print(f"✅ Successfully loaded pattern from: {pattern_path}")
        print(f"📋 Pattern contains: {list(pattern_data.keys())}")
        if 'pattern' in pattern_data:
            print(f"📐 Pattern panels: {list(pattern_data['pattern']['panels'].keys())}")
        return pattern_data
    except Exception as e:
        print(f"❌ Error loading pattern file: {str(e)}")
        return None

def test_api_health():
    """Test if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ API is healthy and running!")
            return True
        else:
            print(f"⚠️ API health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to API: {str(e)}")
        print("💡 Make sure your API server is running on http://localhost:8000")
        return False

def main():
    """Main test function with user choice"""
    print("🚀 STARTING API TEST SUITE")
    print("🔗 API Base URL:", API_BASE_URL)
    print("📁 Pattern File:", PATTERN_FILE)
    print("="*60)
    
    # Step 1: Load pattern data
    pattern_data = load_pattern_json()
    if not pattern_data:
        print("❌ Cannot proceed without pattern data")
        return
    
    # Step 2: Check API health
    if not test_api_health():
        print("❌ Cannot proceed - API is not responding")
        return
    
    # Step 3: Ask user what to test
    print("\n🎯 CHOOSE WHAT TO TEST:")
    print("1️⃣  SVG Generation only")
    print("2️⃣  3D Generation only") 
    print("3️⃣  Combined Generation (SVG + 3D)")
    print("4️⃣  Test All (SVG, 3D, Combined)")
    
    try:
        choice = input("\n👉 Enter your choice (1-4): ").strip()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        return
    
    session_ids = []
    
    if choice == "1":
        print("\n🎨 Testing SVG Generation only...")
        svg_session = test_svg_generation_simple(pattern_data)
        session_ids.append(svg_session)
        
    elif choice == "2":
        print("\n🎯 Testing 3D Generation only...")
        model_3d_session = test_3d_generation_simple(pattern_data)
        session_ids.append(model_3d_session)
        
    elif choice == "3":
        print("\n🔄 Testing Combined Generation only...")
        combined_session = test_combined_generation_simple(pattern_data)
        session_ids.append(combined_session)
        
    elif choice == "4":
        print("\n🚀 Testing All endpoints...")
        # Test SVG generation
        svg_session = test_svg_generation_simple(pattern_data)
        session_ids.append(svg_session)
        
        # Test 3D generation
        model_3d_session = test_3d_generation_simple(pattern_data)
        session_ids.append(model_3d_session)
        
        # Test combined generation
        combined_session = test_combined_generation_simple(pattern_data)
        session_ids.append(combined_session)
    else:
        print("❌ Invalid choice. Please run again and choose 1-4.")
        return
    
    # Summary
    print("\n" + "="*60)
    print("🎉 TEST COMPLETED!")
    print("="*60)
    
    successful_tests = [s for s in session_ids if s is not None]
    total_tests = len(session_ids)
    print(f"✅ Successful tests: {len(successful_tests)}/{total_tests}")
    
    if len(successful_tests) == total_tests and total_tests > 0:
        print("🎊 All tests passed! Your API is working perfectly!")
    elif len(successful_tests) > 0:
        print("⚠️  Some tests passed, some failed. Check the logs above for details.")
    else:
        print("❌ All tests failed. Check the API server and logs.")

def test_svg_generation_simple(pattern_data):
    """Test SVG generation endpoint - simplified without downloads"""
    print("\n" + "="*60)
    print("� TESTING SVG GENERATION")
    print("="*60)
    
    # Prepare request payload - SEND FULL JSON STRUCTURE
    payload = {
        "pattern_specification": pattern_data,  # Send the complete JSON with all keys
        "pattern_name": "test_dress_svg",
        "with_text": False,
        "view_ids": False,
        "with_printable": False
    }
    
    # Debug: Print what we're sending
    print(f"🔍 Request payload structure: {list(payload.keys())}")
    print(f"🔍 Pattern specification keys: {list(payload['pattern_specification'].keys())}")
    
    try:
        print("🚀 Sending SVG generation request...")
        response = requests.post(
            f"{API_BASE_URL}/generate_svg",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SVG generation successful!")
            print(f"🆔 Session ID: {result['session_id']}")
            print(f"📄 SVG File: {result['svg_file_path']}")
            print(f"🖼️  PNG File: {result['png_file_path']}")
            print(f"📁 Output Directory: {result['output_dir']}")
            return result['session_id']
        else:
            print(f"❌ SVG generation failed: {response.status_code}")
            print(f"📝 Error details: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
        return None

def test_3d_generation_simple(pattern_data):
    """Test 3D generation endpoint - simplified without downloads"""
    print("\n" + "="*60)
    print("🎯 TESTING 3D MODEL GENERATION")
    print("="*60)
    
    # Prepare request payload - SEND FULL JSON STRUCTURE
    payload = {
        "pattern_specification": pattern_data,  # Send the complete JSON with all keys
        "pattern_name": "test_dress_3d"
    }
    
    # Debug: Print what we're sending
    print(f"🔍 Request payload structure: {list(payload.keys())}")
    print(f"🔍 Pattern specification keys: {list(payload['pattern_specification'].keys())}")
    
    try:
        print("🚀 Sending 3D generation request...")
        response = requests.post(
            f"{API_BASE_URL}/generate_3d",
            json=payload,
            timeout=120  # 3D generation takes longer
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 3D model generation successful!")
            print(f"🆔 Session ID: {result['session_id']}")
            print(f"� GLB File: {result['glb_file_path']}")
            print(f"📁 Output Directory: {result['output_dir']}")
            return result['session_id']
        else:
            print(f"❌ 3D generation failed: {response.status_code}")
            print(f"📝 Error details: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
        return None

def test_combined_generation_simple(pattern_data):
    """Test combined generation endpoint - simplified without downloads"""
    print("\n" + "="*60)
    print("🔄 TESTING COMBINED GENERATION (SVG + 3D)")
    print("="*60)
    
    # Prepare request payload - SEND FULL JSON STRUCTURE
    payload = {
        "pattern_specification": pattern_data,  # Send the complete JSON with all keys
        "pattern_name": "test_dress_combined",
        "with_text": False,
        "view_ids": False,
        "with_printable": False
    }
    
    # Debug: Print what we're sending
    print(f"🔍 Request payload structure: {list(payload.keys())}")
    print(f"🔍 Pattern specification keys: {list(payload['pattern_specification'].keys())}")
    
    try:
        print("🚀 Sending combined generation request...")
        response = requests.post(
            f"{API_BASE_URL}/generate_both",
            json=payload,
            timeout=180  # Combined generation takes longest
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Combined generation successful!")
            print(f"🆔 Session ID: {result['session_id']}")
            print(f"🔍 Response keys: {list(result.keys())}")
            
            # SVG results
            if 'svg_result' in result:
                svg_result = result['svg_result']
                print(f"📄 SVG Status: {svg_result.get('status', 'unknown')}")
                if svg_result.get('status') == 'success':
                    print(f"📄 SVG Files: {svg_result.get('svg_file', 'N/A')}, {svg_result.get('png_file', 'N/A')}")
            else:
                print("⚠️ No svg_result in response")
            
            # 3D results
            if 'model_3d_result' in result:
                model_3d_result = result['model_3d_result']
                print(f"🎯 3D Status: {model_3d_result.get('status', 'unknown')}")
                if model_3d_result.get('status') == 'success':
                    print(f"🎯 3D File: {model_3d_result.get('glb_file', 'N/A')}")
            else:
                print("⚠️ No model_3d_result in response")
            
            return result['session_id']
        else:
            print(f"❌ Combined generation failed: {response.status_code}")
            print(f"📝 Error details: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
        return None

if __name__ == "__main__":
    main()
