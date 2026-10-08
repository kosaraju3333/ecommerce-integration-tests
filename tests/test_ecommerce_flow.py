import os

import httpx
import pytest

BASE_URL = os.getenv(
    "BASE_URL",
    "https://api-dev.spontansolutions.com"
)

TEST_PRODUCT_SKU = os.getenv(
    "TEST_PRODUCT_SKU",
    "INTEGRATION-TEST-001"
)

AUTH_URL = BASE_URL
PRODUCT_URL = BASE_URL
CART_URL = BASE_URL
ORDER_URL = BASE_URL

# TEST_PRODUCT_SKU = "DELL-Pro"


def get_test_product():

    response = httpx.get(
        f"{PRODUCT_URL}/api/products/"
    )

    assert response.status_code == 200

    products = response.json()

    product = next(
        (
            product
            for product in products
            if product["sku"] == TEST_PRODUCT_SKU
        ),
        None
    )

    assert product is not None, (
        f"Integration test product "
        f"{TEST_PRODUCT_SKU} does not exist"
    )

    return product


@pytest.fixture
def clean_customer_cart(customer_token):

    headers = {
        "Authorization": f"Bearer {customer_token}"
    }

    # Clean cart BEFORE test
    response = httpx.delete(
        f"{CART_URL}/api/cart/",
        headers=headers
    )

    assert response.status_code == 200

    yield headers

    # Clean cart AFTER test
    response = httpx.delete(
        f"{CART_URL}/api/cart/",
        headers=headers
    )

    assert response.status_code == 200

# ============================================================
# FIXTURE - LOGIN CUSTOMER AND RETURN JWT TOKEN
# ============================================================

@pytest.fixture
def customer_token():

    username = os.environ["TEST_CUSTOMER_USERNAME"]
    password = os.environ["TEST_CUSTOMER_PASSWORD"]

    response = httpx.post(
        f"{AUTH_URL}/api/auth/login",
        json={
            "username": username,
            "password": password
        }
    )

    assert response.status_code == 200

    return response.json()["access_token"]


# ============================================================
# HEALTH CHECK TESTS
# ============================================================

def test_auth_service_health():

    response = httpx.get(
        f"{AUTH_URL}/health"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_product_service_health():

    response = httpx.get(
        f"{PRODUCT_URL}/health"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_cart_service_health():

    response = httpx.get(
        f"{CART_URL}/health"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_order_service_health():

    response = httpx.get(
        f"{ORDER_URL}/health"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "UP"


# ============================================================
# AUTH SERVICE
# ============================================================

import os

def test_customer_login():

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

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == username
    assert data["user"]["role"] == "CUSTOMER"

# ============================================================
# PRODUCT SERVICE
# ============================================================

def test_get_products():

    response = httpx.get(
        f"{PRODUCT_URL}/api/products/"
    )

    assert response.status_code == 200

    products = response.json()

    assert isinstance(products, list)
    assert len(products) > 0

    product = products[0]

    assert "id" in product
    assert "name" in product
    assert "price" in product
    assert "sku" in product
    assert "stock_quantity" in product


# ============================================================
# CART SERVICE
# ============================================================

def test_customer_can_get_cart(customer_token):

    headers = {
        "Authorization": f"Bearer {customer_token}"
    }

    response = httpx.get(
        f"{CART_URL}/api/cart/",
        headers=headers
    )

    assert response.status_code == 200

    cart = response.json()

    assert "items" in cart
    assert "total" in cart

    assert isinstance(cart["items"], list)


def test_cart_rejects_request_without_token():

    response = httpx.get(
        f"{CART_URL}/api/cart/"
    )

    assert response.status_code in (401, 403)

def test_customer_add_product_to_cart(clean_customer_cart):

    headers = clean_customer_cart

    # -------------------------------------------------
    # 1. Get available products from Product Service
    # -------------------------------------------------

    product_response = httpx.get(
        f"{PRODUCT_URL}/api/products/"
    )

    assert product_response.status_code == 200

    products = product_response.json()

    assert len(products) > 0

    # product = products[0]
    product = get_test_product()

    product_id = product["id"]

    print(
        f"\nTesting product: "
        f"{product['name']} "
        f"(ID: {product_id})"
    )


    # -------------------------------------------------
    # 2. Add product to Cart Service
    # -------------------------------------------------

    # headers = {
    #     "Authorization": f"Bearer {customer_token}"
    # }

    add_response = httpx.post(
        f"{CART_URL}/api/cart/items",
        headers=headers,
        json={
            "product_id": product_id,
            "quantity": 1
        }
    )

    assert add_response.status_code == 200


    # -------------------------------------------------
    # 3. Get customer's cart
    # -------------------------------------------------

    cart_response = httpx.get(
        f"{CART_URL}/api/cart/",
        headers=headers
    )

    assert cart_response.status_code == 200

    cart = cart_response.json()

    assert "items" in cart
    assert len(cart["items"]) > 0


    # -------------------------------------------------
    # 4. Verify product exists in cart
    # -------------------------------------------------

    cart_product = next(
        (
            item
            for item in cart["items"]
            if item["product_id"] == product_id
        ),
        None
    )

    assert cart_product is not None

    assert cart_product["product_id"] == product_id

    assert cart_product["name"] == product["name"]

    assert cart_product["quantity"] >= 1

def test_complete_checkout_flow(
    prepare_test_inventory,
    clean_customer_cart
):

    headers = clean_customer_cart

    # ==================================================
    # 1. Get a product
    # ==================================================

    product = get_test_product()

    product_id = product["id"]

    stock_before = product["stock_quantity"]

    assert stock_before >= 1, (
        f"Insufficient stock for integration testing. "
        f"Product: {product['name']}, "
        f"Available stock: {stock_before}"
    )
    # assert stock_before > 0
    
    # ==================================================
    # 2. Add ONE product to cart
    # ==================================================

    add_response = httpx.post(
        f"{CART_URL}/api/cart/items",
        headers=headers,
        json={
            "product_id": product_id,
            "quantity": 1
        }
    )

    assert add_response.status_code == 200


    # ==================================================
    # 3. Verify product is in cart
    # ==================================================

    cart_response = httpx.get(
        f"{CART_URL}/api/cart/",
        headers=headers
    )

    assert cart_response.status_code == 200

    cart = cart_response.json()

    assert len(cart["items"]) == 1
    assert cart["items"][0]["product_id"] == product_id
    assert cart["items"][0]["quantity"] == 1


    # ==================================================
    # 4. Checkout
    # ==================================================

    checkout_response = httpx.post(
        f"{ORDER_URL}/api/orders/checkout",
        headers=headers,
        json={}
    )

    assert checkout_response.status_code == 200

    order = checkout_response.json()


    # ==================================================
    # 5. Verify created order
    # ==================================================

    assert "id" in order

    order_id = order["id"]

    assert order["status"] == "PLACED"

    assert len(order["items"]) == 1

    order_item = order["items"][0]

    assert order_item["product_id"] == product_id
    assert order_item["quantity"] == 1
    assert order_item["product_name"] == product["name"]


    # ==================================================
    # 6. Verify order through GET endpoint
    # ==================================================

    order_response = httpx.get(
        f"{ORDER_URL}/api/orders/{order_id}",
        headers=headers
    )

    assert order_response.status_code == 200

    saved_order = order_response.json()

    assert saved_order["id"] == order_id
    assert saved_order["status"] == "PLACED"


    # ==================================================
    # 7. Verify Product Service reduced stock
    # ==================================================

    updated_product_response = httpx.get(
        f"{PRODUCT_URL}/api/products/{product_id}"
    )

    assert updated_product_response.status_code == 200

    updated_product = updated_product_response.json()

    stock_after = updated_product["stock_quantity"]

    assert stock_after == stock_before - 1


    # ==================================================
    # 8. Verify Cart Service cleared cart
    # ==================================================

    cart_after_response = httpx.get(
        f"{CART_URL}/api/cart/",
        headers=headers
    )

    assert cart_after_response.status_code == 200

    cart_after = cart_after_response.json()

    assert cart_after["items"] == []
    assert cart_after["total"] == 0