# quick script (python REPL)
from utils.utils import create_access_token
user_payload = {"user_id": 1, "username": "admin", "global_role": {"role_id": 1, "role_name": "superadmin"}}
token = create_access_token(user_payload)
print(token)
