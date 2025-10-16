"""
Serper API Credentials Storage
Stores API key securely using pickle (similar to Google API credentials)
"""

import pickle
import json
from pathlib import Path
from typing import Optional


class SerperCredentials:
    """Manage Serper API credentials storage."""
    
    CREDENTIALS_FILE = Path.home() / ".cloneai" / "serper_credentials.pkl"
    
    def __init__(self, api_key: str):
        """
        Initialize credentials.
        
        Args:
            api_key: Serper API key
        """
        self.api_key = api_key
    
    def save(self) -> None:
        """Save credentials to pickle file."""
        self.CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Store as simple dict to avoid unpickling issues
        data = {"api_key": self.api_key}
        with open(self.CREDENTIALS_FILE, 'wb') as f:
            pickle.dump(data, f)
        print(f"✅ Serper credentials saved to {self.CREDENTIALS_FILE}")
    
    @classmethod
    def load(cls) -> Optional['SerperCredentials']:
        """
        Load credentials from pickle file.
        
        Returns:
            SerperCredentials instance or None if not found
        """
        if not cls.CREDENTIALS_FILE.exists():
            return None
        
        try:
            with open(cls.CREDENTIALS_FILE, 'rb') as f:
                data = pickle.load(f)
                if isinstance(data, dict):
                    return cls(data["api_key"])
                elif hasattr(data, 'api_key'):
                    return data
                else:
                    return None
        except Exception as e:
            print(f"⚠️  Failed to load Serper credentials: {e}")
            return None
    
    @classmethod
    def delete(cls) -> bool:
        """
        Delete stored credentials.
        
        Returns:
            True if deleted, False if file didn't exist
        """
        if cls.CREDENTIALS_FILE.exists():
            cls.CREDENTIALS_FILE.unlink()
            print(f"✅ Serper credentials deleted from {cls.CREDENTIALS_FILE}")
            return True
        return False
    
    @classmethod
    def exists(cls) -> bool:
        """Check if credentials file exists."""
        return cls.CREDENTIALS_FILE.exists()


def setup_serper_credentials(api_key: str) -> None:
    """
    Setup and save Serper API credentials.
    
    Args:
        api_key: Serper API key from https://serper.dev
    """
    creds = SerperCredentials(api_key)
    creds.save()


def get_serper_api_key() -> Optional[str]:
    """
    Get Serper API key from stored credentials.
    
    Returns:
        API key string or None if not found
    """
    creds = SerperCredentials.load()
    if creds:
        return creds.api_key
    return None


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Serper Credentials Manager")
        print("=" * 50)
        print()
        print("Usage:")
        print("  Setup:  python -m agent.tools.serper_credentials setup <api_key>")
        print("  Check:  python -m agent.tools.serper_credentials check")
        print("  Delete: python -m agent.tools.serper_credentials delete")
        print()
        print("Get your API key at: https://serper.dev")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "setup":
        if len(sys.argv) < 3:
            print("❌ Error: API key required")
            print("Usage: python -m agent.tools.serper_credentials setup <api_key>")
            sys.exit(1)
        
        api_key = sys.argv[2]
        setup_serper_credentials(api_key)
        print()
        print("🔍 Web search is now ready!")
        print("Try: clai do \"search:web query:'Python tutorials' num_results:5\"")
    
    elif command == "check":
        if SerperCredentials.exists():
            creds = SerperCredentials.load()
            if creds:
                masked_key = creds.api_key[:8] + "..." + creds.api_key[-4:]
                print(f"✅ Serper credentials found: {masked_key}")
                print(f"📁 Location: {SerperCredentials.CREDENTIALS_FILE}")
            else:
                print("❌ Credentials file exists but failed to load")
        else:
            print("❌ No Serper credentials found")
            print("Run: python -m agent.tools.serper_credentials setup <api_key>")
    
    elif command == "delete":
        if SerperCredentials.delete():
            print("Credentials removed successfully")
        else:
            print("No credentials to delete")
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Valid commands: setup, check, delete")
        sys.exit(1)
