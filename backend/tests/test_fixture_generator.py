"""Tests for AI fixture generation service."""

import json
import pytest
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
