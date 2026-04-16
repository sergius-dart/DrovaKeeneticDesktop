import pytest
import pytest_asyncio

from drova_desktop_keenetic.common.drova import DrovaService, FakeDrova, ProductInfo, SessionsEntity

FAKE_AUTH_TOKEN = "test"


@pytest_asyncio.fixture
async def fake_drova():
    server = FakeDrova()
    await server.start()
    yield server
    await server.close()


@pytest.mark.asyncio
async def test_DrovaServiceWithFake(fake_drova: FakeDrova):  # pylint: disable=C0103,W0621
    service = DrovaService(fake_drova.faked_host)

    session: SessionsEntity = await service.get_latest_session("", FAKE_AUTH_TOKEN)
    assert session
    assert session.client_id

    product: ProductInfo = await service.get_product_info("test", FAKE_AUTH_TOKEN)
    assert product
    assert product.product_id
