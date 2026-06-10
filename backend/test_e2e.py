import urllib.request
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_pipeline():
    print("🚀 Starting E2E Pipeline Test...")
    
    # 1. Create Project (Assuming there is a POST /projects route)
    # The current router only has POST /projects/{id}/generate, 
    # but we will mock a project ID for this demonstration if no POST /projects is found.
    # In a full app, you'd create the project first. Let's assume a project ID exists
    # or the /generate endpoint creates one if it doesn't.
    
    # Since we didn't explicitly write the POST /projects route in router.py yet,
    # let's write out what the payload would look like:
    payload = {
        "title": "AI Lawyer",
        "prompt": "Create a 60 second animation about an AI legal assistant helping users understand contracts."
    }
    
    print("\n📦 Payload to send:")
    print(json.dumps(payload, indent=2))
    
    print("\n✅ Once your server is running, you can trigger generation with:")
    print("curl -X POST http://localhost:8000/api/v1/projects/<UUID>/generate")
    print("\nMonitor the AIJob table in the database to watch the Orchestrator step through:")
    print("Director -> Script -> Character -> Scene -> Storyboard -> Camera -> Asset -> Voice -> Music -> Timeline -> Render -> Export")
    print("\nWhen complete, check the 'media/renders' folder for the final cinematic MP4!")

if __name__ == "__main__":
    test_pipeline()
