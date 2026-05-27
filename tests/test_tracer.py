import asyncio, pytest
from asynctrace import install, traced

def test_traced_decorator_reraises():
    @traced
    async def fail(): raise ValueError("boom")
    with pytest.raises(ValueError, match="boom"):
        asyncio.run(fail())

def test_install_doesnt_crash():
    install()   # patches policy
    async def ok(): return 42
    assert asyncio.run(ok()) == 42
