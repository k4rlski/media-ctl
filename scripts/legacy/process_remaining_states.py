#!/usr/bin/env python3
"""
Batch process remaining states for Google Maps URL generation
This script processes the major states that still need Google Maps URLs
"""

import subprocess
import sys
import time
from datetime import datetime

def run_state_processing(state_code, batch_size=100):
    """Run the Google Maps URL generation for a specific state"""
    try:
        print(f"🗺️ Processing {state_code}...")
        
        # Run the generate_google_maps_urls.py script
        cmd = [
            'python3', 
            'generate_google_maps_urls.py', 
            'state', 
            state_code, 
            str(batch_size)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            print(f"✅ {state_code}: Success")
            print(result.stdout)
        else:
            print(f"❌ {state_code}: Error")
            print(result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ {state_code}: Exception - {e}")
        return False

def main():
    """Process major states in priority order"""
    print("🚀 BATCH PROCESSING GOOGLE MAPS URLs")
    print("=" * 50)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Priority states to process (CA already complete)
    priority_states = [
        ('FL', 100),  # Florida
        ('TX', 100),  # Texas  
        ('NY', 100),  # New York
        ('PA', 100),  # Pennsylvania
        ('IL', 100),  # Illinois
        ('OH', 100),  # Ohio
        ('GA', 100),  # Georgia
        ('NC', 100),  # North Carolina
        ('MI', 100),  # Michigan
        ('NJ', 100),  # New Jersey
        ('VA', 100),  # Virginia
        ('WA', 100),  # Washington
        ('AZ', 100),  # Arizona
        ('MA', 100),  # Massachusetts
        ('TN', 100),  # Tennessee
        ('IN', 100),  # Indiana
        ('MO', 100),  # Missouri
        ('MD', 100),  # Maryland
        ('WI', 100),  # Wisconsin
        ('CO', 100),  # Colorado
    ]
    
    success_count = 0
    total_states = len(priority_states)
    
    for state_code, batch_size in priority_states:
        print(f"\n📍 Processing {state_code} (batch size: {batch_size})")
        
        if run_state_processing(state_code, batch_size):
            success_count += 1
        
        # Small delay between states
        time.sleep(2)
    
    print("\n" + "=" * 50)
    print(f"🏆 BATCH PROCESSING COMPLETE")
    print(f"✅ Successfully processed: {success_count}/{total_states} states")
    print(f"⏰ Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success_count < total_states:
        print(f"⚠️  {total_states - success_count} states had errors - check logs above")

if __name__ == "__main__":
    main()
