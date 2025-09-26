
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
print(pwd_context.hash("H@nnib@l924802"))  


"""
INSERT INTO users (user_id, username, email, password_hash, global_role_id)
VALUES (
    1,
    'root',
    'root@system.local',
    '$2b$12$3W5HSTbHhghVB18gPW34QuQvkUhtgBMeM67W5daQ4WqQgMGjIWKiu',
    1
);

"""