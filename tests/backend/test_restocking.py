"""
Tests for restocking API endpoints.
"""
import pytest
from mock_data import restock_orders


@pytest.fixture(autouse=True)
def clear_restock_orders():
    """Reset in-memory restock orders before each test so tests stay independent."""
    restock_orders.clear()
    yield
    restock_orders.clear()


class TestRestockingRecommendations:
    """Test suite for GET /api/restocking/recommendations."""

    def test_recommendations_response_structure(self, client):
        """Test that recommendations response has the expected shape."""
        response = client.get("/api/restocking/recommendations?budget=50000")
        assert response.status_code == 200

        data = response.json()
        assert "budget" in data
        assert "total_cost" in data
        assert "remaining_budget" in data
        assert "lead_time_days" in data
        assert "items" in data
        assert isinstance(data["items"], list)

        if data["items"]:
            item = data["items"][0]
            for field in ("item_sku", "item_name", "forecasted_demand", "quantity_on_hand",
                          "shortfall", "trend", "unit_cost", "lead_time_days",
                          "recommended_qty", "line_cost"):
                assert field in item

    def test_recommendations_respects_budget(self, client):
        """Test that total_cost never exceeds the requested budget."""
        for budget in (5000, 25000, 100000, 250000):
            response = client.get(f"/api/restocking/recommendations?budget={budget}")
            assert response.status_code == 200
            data = response.json()
            assert data["total_cost"] <= budget
            assert abs(data["total_cost"] + data["remaining_budget"] - budget) < 0.01

    def test_recommendations_ranks_increasing_trend_first(self, client):
        """Test that items with 'increasing' trend appear before other trends."""
        response = client.get("/api/restocking/recommendations?budget=250000")
        assert response.status_code == 200
        items = response.json()["items"]

        seen_non_increasing = False
        for item in items:
            if item["trend"] != "increasing":
                seen_non_increasing = True
            else:
                assert not seen_non_increasing, "increasing-trend item appeared after non-increasing"

    def test_recommendations_partial_fills_within_budget(self, client):
        """Test that a tiny budget yields a partial allocation, not zero or overflow."""
        response = client.get("/api/restocking/recommendations?budget=5000")
        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            assert item["recommended_qty"] > 0
            assert item["recommended_qty"] <= item["shortfall"]
            assert abs(item["line_cost"] - item["recommended_qty"] * item["unit_cost"]) < 0.01

    def test_recommendations_lead_time_is_max_of_items(self, client):
        """Test that overall lead_time_days equals the max across allocated items."""
        response = client.get("/api/restocking/recommendations?budget=250000")
        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            expected = max(i["lead_time_days"] for i in data["items"])
            assert data["lead_time_days"] == expected
        else:
            assert data["lead_time_days"] == 0


class TestRestockingOrders:
    """Test suite for POST/GET /api/restocking/orders."""

    def _sample_payload(self):
        return {
            "budget": 50000,
            "items": [
                {"item_sku": "WDG-001", "item_name": "Industrial Widget Type A",
                 "quantity": 100, "unit_cost": 18.5, "lead_time_days": 6},
                {"item_sku": "MTR-304", "item_name": "Electric Motor 5HP",
                 "quantity": 5, "unit_cost": 320.0, "lead_time_days": 18},
            ],
        }

    def test_create_restock_order_returns_201_and_appears_in_list(self, client):
        """Test that POST creates an order and GET lists it."""
        response = client.post("/api/restocking/orders", json=self._sample_payload())
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"].startswith("RST-")
        assert order["status"] == "Submitted"
        assert len(order["items"]) == 2

        list_response = client.get("/api/restocking/orders")
        assert list_response.status_code == 200
        listed = list_response.json()
        assert len(listed) == 1
        assert listed[0]["id"] == order["id"]

    def test_restock_order_lead_time_is_max_of_lines(self, client):
        """Test that order lead_time_days = max(line.lead_time_days)."""
        response = client.post("/api/restocking/orders", json=self._sample_payload())
        assert response.status_code == 201
        order = response.json()
        assert order["lead_time_days"] == 18

    def test_restock_order_total_cost_calculation(self, client):
        """Test that total_cost = sum(qty * unit_cost)."""
        response = client.post("/api/restocking/orders", json=self._sample_payload())
        order = response.json()
        expected = 100 * 18.5 + 5 * 320.0
        assert abs(order["total_cost"] - expected) < 0.01

    def test_create_restock_order_rejects_empty_items(self, client):
        """Test that an empty items list is rejected with 400."""
        response = client.post("/api/restocking/orders", json={"budget": 10000, "items": []})
        assert response.status_code == 400
        assert "at least one item" in response.json()["detail"].lower()
