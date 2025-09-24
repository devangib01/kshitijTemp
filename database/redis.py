


from config.config import Config
import redis.asyncio as redis_asyncio
import time
JTI_EXPIRY = getattr(Config, "JTI_EXPIRY_SECONDS", 3600)

_redis_client = None
_exception_info = None

host = getattr(Config, "REDIS_HOST", "localhost")
port = int(getattr(Config, "REDIS_PORT", 6379))
_redis_client = redis_asyncio.Redis(host=host, port=port, db=0, decode_responses=False)
_memory_blocklist: dict[str, int] = {}

async def add_jti_to_blocklist(jti: str) -> None:
    if not jti:
        return
    if _redis_client is not None:
        try:
            await _redis_client.set(name=jti, value="1", ex=JTI_EXPIRY)
            return
        except Exception:
            # fallthrough to memory fallback
            pass

    _memory_blocklist[jti] = int(time.time()) + JTI_EXPIRY

async def token_in_blocklist(jti: str) -> bool:
    if not jti:
        return False
    if _redis_client is not None:
        try:
            val = await _redis_client.get(jti)
            return val is not None
        except Exception:
            pass
    exp_ts = _memory_blocklist.get(jti)
    if exp_ts is None:
        return False
    if exp_ts < int(time.time()):
        try:
            del _memory_blocklist[jti]
        except KeyError:
            pass
        return False
    return True

# helper to surface error for debugging if needed
def get_redis_init_error() -> str | None:
    return _exception_info

# # redis.py — robust: prefer real redis, fallback to fakeredis for dev
# from config.config import Config
# import traceback, time
# _exception_info = None
# _redis_client = None

# # JTI expiry default
# JTI_EXPIRY = getattr(Config, "JTI_EXPIRY_SECONDS", 3600)

# def _init_real_redis():
#     import importlib
#     redis_asyncio = importlib.import_module("redis.asyncio")
#     host = getattr(Config, "REDIS_HOST", "localhost")
#     port = int(getattr(Config, "REDIS_PORT", 6379))
#     # decode_responses False to get bytes (consistent with previous code)
#     return redis_asyncio.Redis(host=host, port=port, db=0, decode_responses=False)

# def _init_fakeredis():
#     # fakeredis implements redis.asyncio API
#     import importlib
#     fr = importlib.import_module("fakeredis.aioredis")  # fakeredis v2+ aioredis shim
#     # create a server-backed fake client
#     return fr.FakeRedis()

# # Try real redis, else fakeredis, else fallback to None (in-memory fallback used below)
# try:
#     try:
#         _redis_client = _init_real_redis()
#         # Optional: test connection (non-blocking call may still raise on first command)
#     except Exception:
#         # try fakeredis
#         _redis_client = _init_fakeredis()
# except Exception:
#     _redis_client = None
#     _exception_info = traceback.format_exc()

# # In-memory fallback for JTI blocklist when redis not available
# _memory_blocklist: dict[str, int] = {}

# # Async helpers (same behavior as your previous file)
# async def add_jti_to_blocklist(jti: str) -> None:
#     if not jti:
#         return
#     if _redis_client is not None:
#         try:
#             # redis/fakeredis async .set
#             await _redis_client.set(name=jti, value="1", ex=JTI_EXPIRY)
#             return
#         except Exception:
#             # fall through to memory fallback
#             pass
#     _memory_blocklist[jti] = int(time.time()) + JTI_EXPIRY

# async def token_in_blocklist(jti: str) -> bool:
#     if not jti:
#         return False
#     if _redis_client is not None:
#         try:
#             val = await _redis_client.get(jti)
#             return val is not None
#         except Exception:
#             pass
#     exp_ts = _memory_blocklist.get(jti)
#     if exp_ts is None:
#         return False
#     if exp_ts < int(time.time()):
#         try:
#             del _memory_blocklist[jti]
#         except KeyError:
#             pass
#         return False
#     return True

# def get_redis_init_error() -> str | None:
#     return _exception_info
