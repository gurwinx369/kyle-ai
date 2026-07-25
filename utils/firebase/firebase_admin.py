import logging
import firebase_admin
from firebase_admin import auth, credentials

from core.config import FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY, FIREBASE_PROJECT_ID

logger = logging.getLogger(__name__)

if not firebase_admin._apps:
    if FIREBASE_PROJECT_ID and FIREBASE_CLIENT_EMAIL and FIREBASE_PRIVATE_KEY:
        _cred = credentials.Certificate(
            {
                "type": "service_account",
                "project_id": FIREBASE_PROJECT_ID,
                "client_email": FIREBASE_CLIENT_EMAIL,
                "private_key": FIREBASE_PRIVATE_KEY,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )
        firebase_admin.initialize_app(_cred)
    else:
        logger.warning(
            "Firebase credentials incomplete or missing. Set FIREBASE_PROJECT_ID, "
            "FIREBASE_CLIENT_EMAIL, and FIREBASE_PRIVATE_KEY in environment variables."
        )

# Export the auth singleton — everything imports from here.
firebase_auth = auth

