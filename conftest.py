import os
import pytest
import httpx

BASE_URL = os.getenv(
    "BASE_URL",
    "https://api-dev.spontansolutions.com"
)

AUTH_URL = BASE_URL


@pytest.fixture
def customer_token():
    username = os.environ["TEST_CUSTOMER_USERNAME"]
    password = os.environ["TEST_CUSTOMER_PASSWORD"]

    response = httpx.post(
        f"{AUTH_URL}/api/auth/login",
        json={
            "username": username,
            "password": password
        },
        timeout=15
    )

    assert response.status_code == 200, response.text

    return response.json()["access_token"]


#### ADMIN 

@pytest.fixture
def prepare_test_inventory():
    admin_username = os.environ["TEST_ADMIN_USERNAME"]
    admin_password = os.environ["TEST_ADMIN_PASSWORD"]
    test_sku = os.getenv("TEST_PRODUCT_SKU", "INTEGRATION-TEST-001")

    login_response = httpx.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "username": admin_username,
            "password": admin_password
        },
        timeout=15
    )

    assert login_response.status_code == 200, login_response.text

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    products_response = httpx.get(
        f"{BASE_URL}/api/products/",
        timeout=15
    )
    assert products_response.status_code == 200, products_response.text

    product = next(
        (p for p in products_response.json() if p["sku"] == test_sku),
        None
    )
    assert product is not None, f"Missing test product: {test_sku}"

    # Replenish only when inventory is low.
    if product["stock_quantity"] < 10:

        update_payload = {
            "name": product["name"],
            "price": product["price"],
            "sku": product["sku"],
            "category": product["category"],
            "stock_quantity": 100
        }

        update_response = httpx.put(
            f"{BASE_URL}/api/products/{product['id']}",
            headers=headers,
            json=update_payload,
            timeout=15
        )

        assert update_response.status_code == 200, update_response.text

        print(
            f"Test inventory replenished: "
            f"{product['name']} → 100 units"
        )

    # if product["stock_quantity"] < 10:
    #     update_response = httpx.put(
    #         f"{BASE_URL}/api/products/{product['id']}",
    #         headers=headers,
    #         json={"stock_quantity": 100},
    #         timeout=15
    #     )
    #     assert update_response.status_code == 200, update_response.text

    # yield