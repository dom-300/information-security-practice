import secrets
from cryptography.fernet import Fernet

if __name__ == "__main__":
    print(f"ENCRYPTION_KEY={Fernet.generate_key().decode()}")
    print(f"BLIND_INDEX_KEY={secrets.token_hex(32)}")
    print("\nЗбережіть ключі в .env. Втрата ключа = безповоротна втрата даних!")
