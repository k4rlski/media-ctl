#!/usr/bin/env python3
"""
Simple test script for Google Maps URL generation
Tests the system with a few sample ZIP codes
"""

import sys
import os

# Add current directory to path to import the generate_google_maps_urls module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from generate_google_maps_urls import create_google_maps_url, DB_CONFIG
    import mysql.connector
    print("✅ Successfully imported required modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure mysql-connector-python is installed:")
    print("   pip3 install mysql-connector-python")
    sys.exit(1)

def test_url_generation():
    """Test URL generation with sample data"""
    print("\n🧪 TESTING GOOGLE MAPS URL GENERATION")
    print("=" * 50)
    
    test_cases = [
        {
            'zipcode': '33106',
            'city': 'Miami',
            'state': 'FL',
            'county': 'Miami-Dade',
            'cbsa_name': 'Miami-Fort Lauderdale-Pompano Beach, FL'
        },
        {
            'zipcode': '77001',
            'city': 'Houston',
            'state': 'TX',
            'county': 'Harris',
            'cbsa_name': 'Houston-The Woodlands-Sugar Land, TX'
        },
        {
            'zipcode': '10001',
            'city': 'New York',
            'state': 'NY',
            'county': 'New York',
            'cbsa_name': 'New York-Newark-Jersey City, NY-NJ-PA'
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📍 Test {i}: {test['zipcode']} ({test['city']}, {test['state']})")
        
        try:
            url = create_google_maps_url(**test)
            print(f"   🔗 URL: {url}")
            print(f"   📏 Length: {len(url)} characters")
            
            # Validate URL
            if url.startswith('https://www.google.com/maps'):
                print(f"   ✅ Valid Google Maps URL")
            else:
                print(f"   ❌ Invalid URL format")
                
        except Exception as e:
            print(f"   ❌ Error generating URL: {e}")

def test_database_connection():
    """Test database connection"""
    print("\n🔌 TESTING DATABASE CONNECTION")
    print("=" * 40)
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Test query
        cursor.execute("SELECT COUNT(*) FROM zip_to_media WHERE deleted = 0")
        total_zips = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM zip_to_media WHERE deleted = 0 AND gmapurl IS NOT NULL AND gmapurl != ''")
        with_urls = cursor.fetchone()[0]
        
        cursor.close()
        connection.close()
        
        print(f"✅ Database connection successful")
        print(f"📊 Total ZIP codes: {total_zips:,}")
        print(f"🔗 With Google Maps URLs: {with_urls:,}")
        print(f"📍 Missing URLs: {total_zips - with_urls:,}")
        print(f"📈 Progress: {(with_urls/total_zips*100):.1f}%")
        
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Database connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 GOOGLE MAPS URL SYSTEM TESTS")
    print("=" * 60)
    
    # Test database connection first
    if not test_database_connection():
        print("\n❌ Database connection failed - cannot proceed with other tests")
        return False
    
    # Test URL generation
    test_url_generation()
    
    print("\n" + "=" * 60)
    print("🏆 TESTS COMPLETE")
    print("\n💡 To process states, run:")
    print("   python3 generate_google_maps_urls.py state FL 50")
    print("   python3 process_remaining_states.py")
    
    return True

if __name__ == "__main__":
    main()
