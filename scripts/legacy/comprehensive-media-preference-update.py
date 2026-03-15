#!/usr/bin/env python3
"""
Comprehensive Media Preference Update
Updates preferred media outlets for multiple locations based on EPD/WBB preferences
"""

import pymysql
import logging
from datetime import datetime

DB_CONFIG = {
    'host': 'permtrak.com',
    'user': 'permtrak2_crm',
    'password': 'xX-6x8-Wcx6y8-9hjJFe44VhA-Xx',
    'database': 'permtrak2_crm'
}

LOG_FILE = '/var/log/media-preference-update.log'

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])
logger = logging.getLogger(__name__)

def comprehensive_media_update():
    """Update media preferences for multiple locations"""
    
    logger.info("=" * 80)
    logger.info("🎯 COMPREHENSIVE MEDIA PREFERENCE UPDATE")
    logger.info("Purpose: Update preferred outlets for EPD/WBB client locations")
    logger.info("=" * 80)
    
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Media preference updates
    updates = [
        # Orange County - Mass update (361 ZIP codes)
        {
            'description': 'Orange County - LA Times + Daily Pilot',
            'query': 'UPDATE zip_to_media SET news_id = %s, local_id = %s WHERE county LIKE %s AND deleted = 0',
            'params': ('4a2a36eea7e4fcb08', '5143173368939b6d0', '%Orange%'),
            'type': 'county'
        },
        
        # San Francisco County - Bay Area Reporter
        {
            'description': 'San Francisco County - Bay Area Reporter (Local)',
            'query': 'UPDATE zip_to_media SET local_id = %s WHERE county LIKE %s AND state = %s AND deleted = 0',
            'params': ('15da7b4ad44ebbba0', '%San Francisco%', 'CA'),
            'type': 'county'
        },
        
        # Albany County, NY - Troy Record + WGNA-FM
        {
            'description': 'Albany County, NY - Troy Record + WGNA-FM',
            'query': 'UPDATE zip_to_media SET local_id = %s, radio_id = %s WHERE county LIKE %s AND state = %s AND deleted = 0',
            'params': ('68fb6e82b3699565d', '23bbe39ee3955543e', '%Albany%', 'NY'),
            'type': 'county'
        },
        
        # Westlake Village, CA - The Acorn
        {
            'description': 'Westlake Village, CA - The Acorn (Local)',
            'query': 'UPDATE zip_to_media SET local_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('bb0dbcfd3ea68651b', '%Westlake%', 'CA'),
            'type': 'city'
        },
        
        # Carlsbad, CA - The Coast News + San Diego Reader + KYXY-FM
        {
            'description': 'Carlsbad, CA - The Coast News + San Diego Reader + KYXY-FM',
            'query': 'UPDATE zip_to_media SET local_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('ea5b3f02352528302', '%Carlsbad%', 'CA'),
            'type': 'city'
        },
        {
            'description': 'San Diego area - San Diego Reader (Local)',
            'query': 'UPDATE zip_to_media SET local_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('641d0439a633d58a3', '%San Diego%', 'CA'),
            'type': 'city'
        },
        {
            'description': 'San Diego area - KYXY-FM (Radio)',
            'query': 'UPDATE zip_to_media SET radio_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('66db4260f2e54daab', '%San Diego%', 'CA'),
            'type': 'city'
        },
        
        # New York City, NY - AM New York + New York Post
        {
            'description': 'New York City - AM New York (Local)',
            'query': 'UPDATE zip_to_media SET local_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('51bfc189b5feab437', '%New York%', 'NY'),
            'type': 'city'
        },
        {
            'description': 'New York City - New York Post (News)',
            'query': 'UPDATE zip_to_media SET news_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('4bed7757e82431c2d', '%New York%', 'NY'),
            'type': 'city'
        },
        
        # Austin, TX - Austin Chronicle + KAMX
        {
            'description': 'Austin, TX - Austin Chronicle (Local)',
            'query': 'UPDATE zip_to_media SET local_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('b2596a00b857a3020', '%Austin%', 'TX'),
            'type': 'city'
        },
        {
            'description': 'Austin, TX - KAMX (Radio)',
            'query': 'UPDATE zip_to_media SET radio_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('102471474f77e542b', '%Austin%', 'TX'),
            'type': 'city'
        },
        
        # Middleton, WI - Wisconsin State Journal + Badgerland News Dane + WMHX
        {
            'description': 'Middleton, WI - Wisconsin State Journal (News)',
            'query': 'UPDATE zip_to_media SET news_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('7c9926e24fced0e63', '%Middleton%', 'WI'),
            'type': 'city'
        },
        {
            'description': 'Middleton, WI - Badgerland News Dane (Local)',
            'query': 'UPDATE zip_to_media SET local_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('129bf9b17d7e7fe83', '%Middleton%', 'WI'),
            'type': 'city'
        },
        {
            'description': 'Middleton, WI - WMHX (Radio)',
            'query': 'UPDATE zip_to_media SET radio_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('d383c208fedffe247', '%Middleton%', 'WI'),
            'type': 'city'
        },
        
        # Playa Vista, CA - LA Times + Daily Pilot + KTWV
        {
            'description': 'Playa Vista, CA - Los Angeles Times (News)',
            'query': 'UPDATE zip_to_media SET news_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('4a2a36eea7e4fcb08', '%Playa Vista%', 'CA'),
            'type': 'city'
        },
        {
            'description': 'Playa Vista, CA - Daily Pilot (Local)',
            'query': 'UPDATE zip_to_media SET local_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('5143173368939b6d0', '%Playa Vista%', 'CA'),
            'type': 'city'
        },
        {
            'description': 'Playa Vista, CA - KTWV (Radio)',
            'query': 'UPDATE zip_to_media SET radio_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('fd890e17806403499', '%Playa Vista%', 'CA'),
            'type': 'city'
        },
        
        # Woodland Hills, CA - LA Times + Daily Pilot + KTWV
        {
            'description': 'Woodland Hills, CA - Los Angeles Times (News)',
            'query': 'UPDATE zip_to_media SET news_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('4a2a36eea7e4fcb08', '%Woodland Hills%', 'CA'),
            'type': 'city'
        },
        {
            'description': 'Woodland Hills, CA - Daily Pilot (Local)',
            'query': 'UPDATE zip_to_media SET local_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('5143173368939b6d0', '%Woodland Hills%', 'CA'),
            'type': 'city'
        },
        {
            'description': 'Woodland Hills, CA - KTWV (Radio)',
            'query': 'UPDATE zip_to_media SET radio_id = %s WHERE city LIKE %s AND state = %s AND deleted = 0',
            'params': ('fd890e17806403499', '%Woodland Hills%', 'CA'),
            'type': 'city'
        }
    ]
    
    total_updated = 0
    
    for update in updates:
        logger.info(f"🔄 {update['description']}")
        
        # Check how many records will be affected
        check_query = update['query'].replace('UPDATE zip_to_media SET', 'SELECT COUNT(*) FROM zip_to_media WHERE').split('SET')[1].split('WHERE')[1]
        check_params = update['params'][2:] if len(update['params']) > 2 else update['params'][1:]
        
        cursor.execute(f"SELECT COUNT(*) FROM zip_to_media WHERE {check_query}", check_params)
        affected_count = cursor.fetchone()[0]
        
        if affected_count > 0:
            logger.info(f"   📊 Will update {affected_count} ZIP code(s)")
            
            # Execute the update
            cursor.execute(update['query'], update['params'])
            updated = cursor.rowcount
            
            logger.info(f"   ✅ Updated {updated} ZIP code(s)")
            total_updated += updated
        else:
            logger.info(f"   📭 No ZIP codes found for {update['description']}")
    
    # Commit all changes
    conn.commit()
    
    logger.info("=" * 80)
    logger.info(f"📊 COMPREHENSIVE MEDIA UPDATE COMPLETE")
    logger.info(f"✅ Total ZIP codes updated: {total_updated}")
    logger.info("✅ Preferred media outlets applied to all EPD/WBB locations")
    logger.info("=" * 80)
    
    conn.close()

def main():
    """Main comprehensive media update function"""
    logger.info("🚀 Comprehensive Media Preference Update")
    logger.info("Integration: EPD/WBB preferred outlets for all client locations")
    logger.info("")
    
    try:
        comprehensive_media_update()
    except Exception as e:
        logger.error(f"❌ Media update error: {e}")

if __name__ == '__main__':
    main()
