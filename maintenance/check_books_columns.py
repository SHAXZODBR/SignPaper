# List columns of books table
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
res = c.table('books').select('*').limit(1).execute()
if res.data:
    print("Columns in 'books' table:")
    print(list(res.data[0].keys()))
else:
    print("No data in books table")
