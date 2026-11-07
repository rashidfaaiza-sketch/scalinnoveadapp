import os
import tempfile
from cryptography.fernet import Fernet
TEST_DIR = tempfile.TemporaryDirectory()
os.environ.update(ADMIN_PASSWORD='test-password-long-enough', ENCRYPTION_KEY=Fernet.generate_key().decode(), DATABASE_URL=f'sqlite+aiosqlite:///{TEST_DIR.name}/test.db', DATA_DIR=TEST_DIR.name, DEMO_MODE='true', GENERATION_MODE='provider', APP_ENV='development', FRONTEND_ORIGIN='http://testserver')
