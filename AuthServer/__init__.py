import os
from dotenv import load_dotenv

load_dotenv("../lenden.env")

print(os.getenv('CACHE_FOLDER'))