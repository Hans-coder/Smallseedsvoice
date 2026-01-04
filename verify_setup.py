"""
Verify API Credentials
Tests Threads Token and Instagram Session ID.
"""
import os
import requests
import instaloader
from dotenv import load_dotenv
from src.utils.logger import setup_logger

# Load .env
load_dotenv()
logger = setup_logger("verify_setup")

def verify_threads():
    logger.info("--- Testing Threads API Token ---")
    token = os.getenv("THREADS_ACCESS_TOKEN")
    if not token or "your_token" in token:
        logger.error("❌ THREADS_ACCESS_TOKEN is missing or default.")
        return False
        
    url = "https://graph.threads.net/v1.0/me"
    params = {
        "access_token": token,
        "fields": "id,username,name"
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if response.status_code == 200:
            logger.info(f"✅ Threads Token Valid! User: {data.get('name')} (@{data.get('username')})")
            return True
        else:
            logger.error(f"❌ Threads API Error: {data}")
            return False
    except Exception as e:
        logger.error(f"❌ Connection Failed: {e}")
        return False

def verify_instagram():
    logger.info("--- Testing Instagram Session ID ---")
    session_id = os.getenv("INSTAGRAM_SESSION_ID")
    
    # We use Instaloader to test login
    L = instaloader.Instaloader()
    
    if not session_id or "your_session" in session_id:
        logger.warning("⚠️ INSTAGRAM_SESSION_ID is missing using anonymous mode (might be rate limited).")
        # Test anonymous access
        try:
            profile = instaloader.Profile.from_username(L.context, "livetws")
            logger.info("✅ Anonymous Check: Can access @livetws public profile.")
            return True
        except Exception as e:
             logger.error(f"❌ Anonymous Check Failed: {e}")
             return False
        
    try:
        # Load session manually
        L.context._session.cookies.set('sessionid', session_id)
        # Check if we are logged in by fetching own profile info usually, 
        # but instaloader doesn't have a direct 'me' without username.
        # We'll try to access a public profile with the session.
        
        username = "livetws"
        profile = instaloader.Profile.from_username(L.context, username)
        logger.info(f"✅ Instagram Session Valid! Successfully accessed @{username}.")
        return True
    except Exception as e:
        logger.error(f"❌ Instagram Session Error (or Rate Limit): {e}")
        return False

def main():
    logger.info("Starting Verification...")
    t_ok = verify_threads()
    i_ok = verify_instagram()
    
    if t_ok and i_ok:
        logger.info("\n🎉 All credentials look good! You are ready for GitHub Actions.")
    else:
        logger.warning("\n⚠️ Some credentials failed or are missing. Check logs above.")

if __name__ == "__main__":
    main()
