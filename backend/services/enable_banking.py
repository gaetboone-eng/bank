import jwt as pyjwt
from datetime import datetime, timezone
from fastapi import HTTPException
from ..core.config import ENABLE_BANKING_APP_ID, ENABLE_BANKING_PRIVATE_KEY


def create_enable_banking_jwt() -> str:
    if not ENABLE_BANKING_APP_ID or not ENABLE_BANKING_PRIVATE_KEY:
        raise HTTPException(status_code=400, detail="Enable Banking not configured")

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    iat = int(datetime.now(timezone.utc).timestamp())
    jwt_body = {
        "iss": "enablebanking.com",
        "aud": "api.enablebanking.com",
        "iat": iat,
        "exp": iat + 3600,
    }

    try:
        if ENABLE_BANKING_PRIVATE_KEY.startswith("/") or ENABLE_BANKING_PRIVATE_KEY.endswith(".pem"):
            with open(ENABLE_BANKING_PRIVATE_KEY, 'rb') as f:
                key_data = f.read()
        else:
            key_data = ENABLE_BANKING_PRIVATE_KEY.encode('utf-8')

        private_key = serialization.load_pem_private_key(key_data, password=None, backend=default_backend())
        return pyjwt.encode(jwt_body, private_key, algorithm="RS256", headers={"kid": ENABLE_BANKING_APP_ID})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating JWT: {str(e)}")
