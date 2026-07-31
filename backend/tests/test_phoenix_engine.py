"""Tests for PhoenixEngine — Ticket 8 (partial): create_deal/update_deal
must write through to Supabase when configured, same as get_deal/list_deals
already do, instead of only ever touching the local in-memory fixture.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.phoenix_engine as phoenix_engine_module
from services.phoenix_engine import PhoenixEngine


class _FakeDB:
    """Minimal in-memory stand-in for services.database.DatabaseService."""

    def __init__(self, configured: bool):
        self.configured = configured
        self.inserted = []
        self.updated = []
        self.rows = {}

    def select(self, table, params=None, single=False):
        if not self.configured:
            return None
        if params and "id" in params:
            deal_id = params["id"].replace("eq.", "")
            row = self.rows.get(deal_id)
            return [row] if row else []
        return list(self.rows.values())

    def insert(self, table, data):
        if not self.configured:
            return None
        self.inserted.append(data)
        self.rows[data["id"]] = data
        return [data]

    def update(self, table, match, data):
        if not self.configured:
            return None
        self.updated.append((match, data))
        deal_id = match["id"].replace("eq.", "")
        if deal_id in self.rows:
            self.rows[deal_id].update(data)
        return [self.rows.get(deal_id, data)]


class TestCreateDealWritesThroughWhenConfigured:
    def test_create_deal_calls_db_insert_when_configured(self, monkeypatch):
        fake_db = _FakeDB(configured=True)
        monkeypatch.setattr(phoenix_engine_module, "_db", fake_db)
        engine = PhoenixEngine()

        deal = engine.create_deal({"name": "Test Deal"})

        assert len(fake_db.inserted) == 1
        assert fake_db.inserted[0]["name"] == "Test Deal"
        assert deal["name"] == "Test Deal"

    def test_create_deal_does_not_call_db_when_not_configured(self, monkeypatch):
        fake_db = _FakeDB(configured=False)
        monkeypatch.setattr(phoenix_engine_module, "_db", fake_db)
        engine = PhoenixEngine()

        deal = engine.create_deal({"name": "Test Deal"})

        assert fake_db.inserted == []
        assert deal["name"] == "Test Deal"
        assert engine.get_deal(deal["id"]) == deal


class TestUpdateDealWritesThroughWhenConfigured:
    def test_update_deal_calls_db_update_when_configured(self, monkeypatch):
        fake_db = _FakeDB(configured=True)
        monkeypatch.setattr(phoenix_engine_module, "_db", fake_db)
        engine = PhoenixEngine()
        existing_id = next(iter(engine._deals))

        result = engine.update_deal(existing_id, {"stage": "closed"})

        assert result["stage"] == "closed"
        assert len(fake_db.updated) == 1
        match, data = fake_db.updated[0]
        assert match == {"id": f"eq.{existing_id}"}
        assert data == {"stage": "closed"}

    def test_update_deal_unknown_id_returns_none(self, monkeypatch):
        fake_db = _FakeDB(configured=True)
        monkeypatch.setattr(phoenix_engine_module, "_db", fake_db)
        engine = PhoenixEngine()

        assert engine.update_deal("does-not-exist", {"stage": "closed"}) is None
        assert fake_db.updated == []


class TestCreatedDealVisibleInListDeals:
    """The core bug: a deal created locally must not disappear from
    list_deals() when Supabase isn't configured."""

    def test_locally_created_deal_appears_in_list_deals(self, monkeypatch):
        fake_db = _FakeDB(configured=False)
        monkeypatch.setattr(phoenix_engine_module, "_db", fake_db)
        engine = PhoenixEngine()

        deal = engine.create_deal({"name": "New Sourced Deal"})
        listed_ids = {d["id"] for d in engine.list_deals()}

        assert deal["id"] in listed_ids

    def test_seed_fixtures_not_duplicated_in_list_deals(self, monkeypatch):
        fake_db = _FakeDB(configured=False)
        monkeypatch.setattr(phoenix_engine_module, "_db", fake_db)
        engine = PhoenixEngine()

        listed_ids = [d["id"] for d in engine.list_deals()]
        assert len(listed_ids) == len(set(listed_ids))
