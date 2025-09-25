from config.config import Config
import redis.asyncio as redis_asyncio
import time
JTI_EXPIRY = getattr(Config, "JTI_EXPIRY_SECONDS", 3600)

_redis_client = None
_exception_info = None

host = getattr(Config, "REDIS_HOST", "localhost")
port = int(getattr(Config, "REDIS_PORT", 6379))
_redis_client = redis_asyncio.Redis(host=host, port=port, db=0, decode_responses=True)
_memory_blocklist: dict[str, int] = {}

async def add_jti_to_blocklist(jti: str) -> None:
    if not jti:
        return
    if _redis_client is not None:
        try:
            await _redis_client.set(name=jti, value="1", ex=JTI_EXPIRY)
            return
        except Exception:
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


def get_redis_init_error() -> str | None:
    return _exception_info

