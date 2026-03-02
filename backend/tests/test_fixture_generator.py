"""Tests for AI fixture generation service."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.fixture_generator import validate_profile, validate_transactions


class TestValidateProfile:
    def test_valid_profile_passes(self):
        profile = {
            "ageYears": 34,
            "location": {"city": "Mumbai", "state": "Maharashtra", "country": "India"},
            "monthlyIncomeRange": {"min": 50000, "max": 80000, "currency": "INR"},
            "creditScore": {"score": 750, "maxScore": 900},
            "bankAccounts": [{"issuerName": "HDFC Bank"}],
            "cards": [{"issuerName": "HDFC Bank", "productName": "Regalia", "cardType": "CREDIT", "cardScheme": "VISA"}],
        }
        errors = validate_profile(profile)
        assert errors == []

    def test_missing_required_field(self):
        profile = {"ageYears": 34}
        errors = validate_profile(profile)
        assert len(errors) > 0
        assert any("location" in e for e in errors)

    def test_invalid_age_type(self):
        profile = {
            "ageYears": "thirty",
            "location": {"city": "Mumbai", "state": "Maharashtra", "country": "India"},
            "monthlyIncomeRange": {"min": 50000, "max": 80000, "currency": "INR"},
            "creditScore": {"score": 750, "maxScore": 900},
            "bankAccounts": [{"issuerName": "HDFC Bank"}],
            "cards": [{"issuerName": "HDFC Bank", "productName": "Regalia", "cardType": "CREDIT", "cardScheme": "VISA"}],
        }
        errors = validate_profile(profile)
        assert any("ageYears" in e for e in errors)

    def test_missing_location_subfield(self):
        profile = {
            "ageYears": 34,
            "location": {"city": "Mumbai"},
            "monthlyIncomeRange": {"min": 50000, "max": 80000, "currency": "INR"},
            "creditScore": {"score": 750, "maxScore": 900},
            "bankAccounts": [{"issuerName": "HDFC Bank"}],
            "cards": [{"issuerName": "HDFC Bank", "productName": "Regalia", "cardType": "CREDIT", "cardScheme": "VISA"}],
        }
        errors = validate_profile(profile)
        assert any("state" in e for e in errors)

    def test_empty_bank_accounts(self):
        profile = {
            "ageYears": 34,
            "location": {"city": "Mumbai", "state": "Maharashtra", "country": "India"},
            "monthlyIncomeRange": {"min": 50000, "max": 80000, "currency": "INR"},
            "creditScore": {"score": 750, "maxScore": 900},
            "bankAccounts": [],
            "cards": [{"issuerName": "HDFC Bank", "productName": "Regalia", "cardType": "CREDIT", "cardScheme": "VISA"}],
        }
        errors = validate_profile(profile)
        assert any("bankAccounts" in e for e in errors)


class TestValidateTransactions:
    def test_valid_transactions_pass(self):
        txs = [
            {
                "transactionId": "tx001",
                "date": "2026-01-15",
                "counterpartyName": "Spencers",
                "transactionType": "P2M",
                "merchantCategory": "Groceries and Supermarkets",
                "amount": 1037.10,
                "transactionDirection": "DEBIT",
            },
            {
                "transactionId": "tx002",
                "date": "2026-01-16",
                "counterpartyName": "Amit Verma",
                "transactionType": "P2P",
                "amount": 500.00,
                "transactionDirection": "DEBIT",
            },
        ]
        errors = validate_transactions(txs)
        assert errors == []

    def test_empty_list_fails(self):
        errors = validate_transactions([])
        assert "empty" in errors[0].lower()

    def test_not_a_list_fails(self):
        errors = validate_transactions("not a list")
        assert len(errors) > 0

    def test_missing_required_field(self):
        txs = [{"transactionId": "tx001", "date": "2026-01-15"}]
        errors = validate_transactions(txs)
        assert any("counterpartyName" in e for e in errors)

    def test_invalid_date_format(self):
        txs = [{
            "transactionId": "tx001", "date": "15-01-2026",
            "counterpartyName": "Store", "transactionType": "P2M",
            "merchantCategory": "Food", "amount": 100, "transactionDirection": "DEBIT",
        }]
        errors = validate_transactions(txs)
        assert any("date" in e for e in errors)

    def test_invalid_transaction_type(self):
        txs = [{
            "transactionId": "tx001", "date": "2026-01-15",
            "counterpartyName": "Store", "transactionType": "INVALID",
            "merchantCategory": "Food", "amount": 100, "transactionDirection": "DEBIT",
        }]
        errors = validate_transactions(txs)
        assert any("transactionType" in e for e in errors)

    def test_p2m_without_category(self):
        txs = [{
            "transactionId": "tx001", "date": "2026-01-15",
            "counterpartyName": "Store", "transactionType": "P2M",
            "amount": 100, "transactionDirection": "DEBIT",
        }]
        errors = validate_transactions(txs)
        assert any("merchantCategory" in e for e in errors)

    def test_p2p_without_category_is_ok(self):
        txs = [{
            "transactionId": "tx001", "date": "2026-01-15",
            "counterpartyName": "Amit", "transactionType": "P2P",
            "amount": 500, "transactionDirection": "DEBIT",
        }]
        errors = validate_transactions(txs)
        assert errors == []


@pytest.mark.asyncio
class TestGenerateProfile:
    async def test_returns_name_and_data(self):
        fake_profile = {
            "name": "Rajesh Kumar",
            "profile": {
                "ageYears": 34,
                "location": {"city": "Mumbai", "state": "Maharashtra", "country": "India"},
                "monthlyIncomeRange": {"min": 50000, "max": 80000, "currency": "INR"},
                "creditScore": {"score": 750, "maxScore": 900},
                "bankAccounts": [{"issuerName": "HDFC Bank"}],
                "cards": [{"issuerName": "HDFC Bank", "productName": "Regalia", "cardType": "CREDIT", "cardScheme": "VISA"}],
            },
        }
        mock_response = MagicMock()
        mock_response.text = json.dumps(fake_profile)

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("app.services.fixture_generator.get_client", return_value=mock_client):
            from app.services.fixture_generator import generate_profile
            result = await generate_profile()

        assert result["name"] == "Rajesh Kumar"
        assert result["data"]["ageYears"] == 34
        assert "location" in result["data"]

    async def test_raises_on_invalid_response(self):
        mock_response = MagicMock()
        mock_response.text = '{"name": "Bad", "profile": {"ageYears": "not a number"}}'

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("app.services.fixture_generator.get_client", return_value=mock_client):
            from app.services.fixture_generator import generate_profile
            with pytest.raises(ValueError, match="validation"):
                await generate_profile()


@pytest.mark.asyncio
class TestGenerateTransactions:
    async def test_returns_valid_transactions(self):
        fake_txs = [
            {
                "transactionId": "gen001",
                "date": "2026-01-15",
                "counterpartyName": "Spencers",
                "transactionType": "P2M",
                "merchantCategory": "Groceries and Supermarkets",
                "amount": 1037.10,
                "transactionDirection": "DEBIT",
            },
        ]
        mock_response = MagicMock()
        mock_response.text = json.dumps(fake_txs)

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("app.services.fixture_generator.get_client", return_value=mock_client):
            from app.services.fixture_generator import generate_transactions
            result = await generate_transactions(
                prompt="Generate test transactions",
                start_date="2026-01-01",
                end_date="2026-03-02",
            )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["counterpartyName"] == "Spencers"

    async def test_raises_on_invalid_response(self):
        fake_txs = [{"transactionId": "gen001", "date": "bad-date"}]
        mock_response = MagicMock()
        mock_response.text = json.dumps(fake_txs)

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("app.services.fixture_generator.get_client", return_value=mock_client):
            from app.services.fixture_generator import generate_transactions
            with pytest.raises(ValueError, match="validation"):
                await generate_transactions(
                    prompt="Generate test transactions",
                    start_date="2026-01-01",
                    end_date="2026-03-02",
                )

    async def test_passes_profile_context(self):
        fake_txs = [{
            "transactionId": "gen001", "date": "2026-01-15",
            "counterpartyName": "Store", "transactionType": "P2M",
            "merchantCategory": "Groceries", "amount": 100,
            "transactionDirection": "DEBIT",
        }]
        mock_response = MagicMock()
        mock_response.text = json.dumps(fake_txs)

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        profile = {"ageYears": 34, "location": {"city": "Mumbai"}}

        with patch("app.services.fixture_generator.get_client", return_value=mock_client):
            from app.services.fixture_generator import generate_transactions
            await generate_transactions(
                prompt="Generate transactions",
                start_date="2026-01-01",
                end_date="2026-03-02",
                profile_data=profile,
            )

        call_args = mock_client.aio.models.generate_content.call_args
        prompt_sent = call_args.kwargs.get("contents", call_args.args[0] if call_args.args else "")
        assert "Mumbai" in str(prompt_sent)


class TestGenerateProfileEndpoint:
    def test_returns_200_with_valid_profile(self, test_client):
        fake_result = {
            "name": "Priya Patel",
            "data": {
                "ageYears": 28,
                "location": {"city": "Pune", "state": "Maharashtra", "country": "India"},
                "monthlyIncomeRange": {"min": 60000, "max": 90000, "currency": "INR"},
                "creditScore": {"score": 780, "maxScore": 900},
                "bankAccounts": [{"issuerName": "SBI"}],
                "cards": [{"issuerName": "SBI", "productName": "SimplySAVE", "cardType": "CREDIT", "cardScheme": "VISA"}],
            },
        }
        with patch("app.routers.fixtures.generate_profile", new_callable=AsyncMock, return_value=fake_result):
            response = test_client.post("/api/fixtures/generate-profile")
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Priya Patel"
        assert "data" in body

    def test_returns_502_on_generation_error(self, test_client):
        with patch("app.routers.fixtures.generate_profile", new_callable=AsyncMock, side_effect=ValueError("validation failed")):
            response = test_client.post("/api/fixtures/generate-profile")
        assert response.status_code == 502


class TestGenerateTransactionsEndpoint:
    def test_returns_200_with_valid_transactions(self, test_client):
        fake_txs = [{
            "transactionId": "gen001", "date": "2026-01-15",
            "counterpartyName": "Store", "transactionType": "P2M",
            "merchantCategory": "Groceries", "amount": 100,
            "transactionDirection": "DEBIT",
        }]
        with patch("app.routers.fixtures.generate_transactions", new_callable=AsyncMock, return_value=fake_txs):
            response = test_client.post("/api/fixtures/generate-transactions", json={
                "prompt": "Generate test data",
                "start_date": "2026-01-01",
                "end_date": "2026-03-02",
            })
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert len(body["transactions"]) == 1

    def test_returns_502_on_generation_error(self, test_client):
        with patch("app.routers.fixtures.generate_transactions", new_callable=AsyncMock, side_effect=ValueError("validation failed")):
            response = test_client.post("/api/fixtures/generate-transactions", json={
                "prompt": "Generate test data",
                "start_date": "2026-01-01",
                "end_date": "2026-03-02",
            })
        assert response.status_code == 502
