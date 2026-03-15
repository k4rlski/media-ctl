#!/usr/bin/env python3
"""
Google Maps URL Generation System for ZIP Codes
Geo-Intelligence Integration for PERM-Ads.com

This script generates Google Maps URLs for all ZIP codes with:
- ZIP code boundaries
- CBSA/MSA region highlighting  
- Nearest city context
- No API authentication required (public Google Maps URLs)

Author: AI Assistant
Date: September 2025
"""

import mysql.connector
import urllib.parse
import sys
import time
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': 'permtrak.com',
    'user': 'permtrak2_prod', 
    'password': 'xX-6x8-Wcx6y8-9hjJFe44VhA-Xx',
    'database': 'permtrak2_prod'
}

def create_google_maps_url(zipcode, city, state, cbsa_name=None, county=None):
    """
    Create a comprehensive Google Maps URL for a ZIP code with enhanced features
    
    Features:
    - ZIP code search with boundaries
    - CBSA/MSA context in search
    - Nearest city for navigation
    - Satellite view for geographic context
    - No authentication required
    """
    
    # Base Google Maps URL
    base_url = "https://www.google.com/maps/search/"
    
    # Create search query with multiple context layers
    search_components = []
    
    # Primary: ZIP code with boundaries
    search_components.append(f"{zipcode} ZIP code boundaries")
    
    # Secondary: City and state context
    if city and state:
        search_components.append(f"{city}, {state}")
    
    # Tertiary: CBSA/MSA context for regional understanding
    if cbsa_name and cbsa_name != 'Non-Metropolitan Area' and cbsa_name != 'Unknown':
        # Clean CBSA name for URL
        cbsa_clean = cbsa_name.replace(' Metro Area', '').replace(' Metropolitan Statistical Area', '')
        search_components.append(f"{cbsa_clean} region")
    
    # Quaternary: County context
    if county and county != city:
        search_components.append(f"{county} County, {state}")
    
    # Join components with OR operator for comprehensive search
    search_query = " OR ".join(search_components)
    
    # URL encode the search query
    encoded_query = urllib.parse.quote_plus(search_query)
    
    # Add parameters for enhanced mapping
    params = {
        'api': '1',  # Use Google Maps API format
        'query': search_query,
        'zoom': '12',  # Good balance for ZIP code level
        'maptype': 'roadmap'  # Start with roadmap, user can switch to satellite
    }
    
    # Build final URL
    param_string = "&".join([f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in params.items()])
    final_url = f"{base_url}?{param_string}"
    
    # Ensure URL is under 255 characters (database limit)
    if len(final_url) > 250:
        # Fallback to simpler URL
        simple_query = f"{zipcode} {city} {state}"
        encoded_simple = urllib.parse.quote_plus(simple_query)
        final_url = f"https://www.google.com/maps/search/{encoded_simple}"
    
    return final_url

def get_zip_data():
    """Get all ZIP code data from database"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT 
            name as zipcode,
            city,
            state, 
            county,
            cbsaname,
            msaname,
            gmapurl
        FROM zip_to_media 
        WHERE deleted = 0 
        AND name IS NOT NULL
        ORDER BY state, county, city, name
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return results
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return []

def update_google_maps_url(zipcode, gmap_url):
    """Update the gmapurl field for a specific ZIP code"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        update_query = """
        UPDATE zip_to_media 
        SET gmapurl = %s,
            modified_at = NOW()
        WHERE name = %s 
        AND deleted = 0
        """
        
        cursor.execute(update_query, (gmap_url, zipcode))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        return True
        
    except mysql.connector.Error as e:
        print(f"Database update error for {zipcode}: {e}")
        return False

def process_state_batch(state_code, batch_size=100):
    """Process ZIP codes for a specific state in batches"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        
        # Get ZIP codes for the state that need URL generation
        query = """
        SELECT 
            name as zipcode,
            city,
            state, 
            county,
            cbsaname,
            msaname,
            gmapurl
        FROM zip_to_media 
        WHERE deleted = 0 
        AND name IS NOT NULL
        AND state = %s
        AND (gmapurl IS NULL OR gmapurl = '')
        ORDER BY county, city, name
        LIMIT %s
        """
        
        cursor.execute(query, (state_code, batch_size))
        zip_codes = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        if not zip_codes:
            print(f"✅ {state_code}: No ZIP codes need URL generation")
            return 0
        
        print(f"🗺️ {state_code}: Processing {len(zip_codes)} ZIP codes...")
        
        success_count = 0
        for i, zip_data in enumerate(zip_codes, 1):
            zipcode = zip_data['zipcode']
            city = zip_data['city']
            state = zip_data['state']
            county = zip_data['county']
            cbsa_name = zip_data['cbsaname']
            
            # Generate Google Maps URL
            gmap_url = create_google_maps_url(
                zipcode=zipcode,
                city=city, 
                state=state,
                cbsa_name=cbsa_name,
                county=county
            )
            
            # Update database
            if update_google_maps_url(zipcode, gmap_url):
                success_count += 1
                if i % 10 == 0:  # Progress update every 10 records
                    print(f"   📍 Processed {i}/{len(zip_codes)} ZIP codes...")
            else:
                print(f"   ❌ Failed to update {zipcode}")
            
            # Small delay to be respectful
            time.sleep(0.1)
        
        print(f"✅ {state_code}: Successfully updated {success_count}/{len(zip_codes)} ZIP codes")
        return success_count
        
    except mysql.connector.Error as e:
        print(f"❌ {state_code}: Database error: {e}")
        return 0

def generate_sample_urls():
    """Generate sample URLs to test the system"""
    print("🧪 TESTING GOOGLE MAPS URL GENERATION:")
    print("=" * 60)
    
    test_cases = [
        {
            'zipcode': '90210',
            'city': 'Beverly Hills', 
            'state': 'CA',
            'county': 'Los Angeles',
            'cbsa_name': 'Los Angeles-Long Beach-Anaheim, CA'
        },
        {
            'zipcode': '33106',
            'city': 'Miami',
            'state': 'FL', 
            'county': 'Miami-Dade',
            'cbsa_name': 'Miami-Fort Lauderdale-Pompano Beach, FL'
        },
        {
            'zipcode': '10001',
            'city': 'New York',
            'state': 'NY',
            'county': 'New York',
            'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA'
        },
        {
            'zipcode': '95221',
            'city': 'Stockton',
            'state': 'CA',
            'county': 'San Joaquin', 
            'cbsa_name': 'Stockton, CA'
        }
    ]
    
    for test in test_cases:
        url = create_google_maps_url(**test)
        print(f"📍 {test['zipcode']} ({test['city']}, {test['state']}):")
        print(f"   🔗 {url}")
        print(f"   📏 Length: {len(url)} characters")
        print()

def main():
    """Main execution function"""
    print("🗺️ GOOGLE MAPS URL GENERATION SYSTEM")
    print("=" * 50)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            generate_sample_urls()
            return
        elif sys.argv[1] == 'state' and len(sys.argv) > 2:
            state_code = sys.argv[2].upper()
            batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 100
            
            print(f"🎯 Processing state: {state_code}")
            print(f"📦 Batch size: {batch_size}")
            print()
            
            success_count = process_state_batch(state_code, batch_size)
            print()
            print(f"🏆 COMPLETED: {success_count} ZIP codes updated with Google Maps URLs")
            return
    
    # Default: Show available options
    print("📋 AVAILABLE OPTIONS:")
    print()
    print("🧪 Test URL Generation:")
    print("   python3 generate_google_maps_urls.py test")
    print()
    print("🗺️ Process Specific State:")
    print("   python3 generate_google_maps_urls.py state CA 50")
    print("   python3 generate_google_maps_urls.py state FL 100")
    print()
    print("📊 Current Database Status:")
    
    # Show current status
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Count total ZIP codes
        cursor.execute("SELECT COUNT(*) FROM zip_to_media WHERE deleted = 0 AND name IS NOT NULL")
        total_zips = cursor.fetchone()[0]
        
        # Count ZIP codes with Google Maps URLs
        cursor.execute("SELECT COUNT(*) FROM zip_to_media WHERE deleted = 0 AND name IS NOT NULL AND gmapurl IS NOT NULL AND gmapurl != ''")
        with_urls = cursor.fetchone()[0]
        
        # Count by state
        cursor.execute("""
        SELECT 
            state,
            COUNT(*) as total,
            COUNT(CASE WHEN gmapurl IS NOT NULL AND gmapurl != '' THEN 1 END) as with_urls
        FROM zip_to_media 
        WHERE deleted = 0 AND name IS NOT NULL
        GROUP BY state 
        ORDER BY state
        """)
        
        state_stats = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        print(f"   📊 Total ZIP codes: {total_zips:,}")
        print(f"   🔗 With Google Maps URLs: {with_urls:,} ({with_urls/total_zips*100:.1f}%)")
        print(f"   📍 Missing URLs: {total_zips-with_urls:,}")
        print()
        
        if state_stats:
            print("📈 BY STATE STATUS:")
            for state, total, urls in state_stats[:10]:  # Show first 10 states
                pct = (urls/total*100) if total > 0 else 0
                print(f"   {state}: {urls:,}/{total:,} ({pct:.1f}%)")
        
    except mysql.connector.Error as e:
        print(f"   ❌ Database connection error: {e}")

if __name__ == "__main__":
    main()
