from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import os
from app.config import settings

security = HTTPBearer()


def verify_admin_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return credentials.credentials


class Encryptor:
    def __init__(self, key: str):
        # Decode base64 key or use raw bytes
        try:
            key_bytes = base64.b64decode(key)
        except:
            key_bytes = key.encode('utf-8')
        
        # Ensure 32 bytes for AES-256
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b'\0')
        else:
            key_bytes = key_bytes[:32]
        
        self.aesgcm = AESGCM(key_bytes)
    
    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        return base64.b64encode(nonce + ciphertext).decode('utf-8')
    
    def decrypt(self, encrypted: str) -> str:
        data = base64.b64decode(encrypted)
        nonce = data[:12]
        ciphertext = data[12:]
        plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')


encryptor = Encryptor(settings.app_encryption_key)








