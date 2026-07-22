import asyncio
import os
import secrets
from pathlib import Path

import aiofiles


async def write_text_atomic(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        async with aiofiles.open(temporary, "w") as file:
            await file.write(content)
        await asyncio.to_thread(os.replace, temporary, path)
    finally:
        await asyncio.to_thread(temporary.unlink, missing_ok=True)
