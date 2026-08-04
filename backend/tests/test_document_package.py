"""
Tests for the universal document package.

Two things matter here. First, that a document is reported workable only when
its inputs actually exist -- a package that says "ready" for a document nobody
can start is worse than no package. Second, that documents which do not apply
to the deal are EXCLUDED rather than counted incomplete, because the second
behaviour silently understates every percentage on the frontend.
"""
import pytest

from services.document_package import (
    DOCUMENT_CATALOGUE, SILO_IDS, DocumentPackageError, build_package,
    silo_package,
)

BASE = {
    "par_amount": 92_000_000, "capital_stack": True, "project_budget": True,
    "revenue_mechanism": "special_tax", "project_description": True,
    "site_control": True, "org_structure": True, "readiness_submissions": True,
    "market_data": True,
}


def _ids(pkg):
    return {d["id"] for s in pkg["silos"] for d in s["documents"]}


class TestCatalogue:

    def test_every_document_belongs_to_a_known_silo(self):
        assert {d["silo"] for d in DOCUMENT_CATALOGUE} <= set(SILO_IDS)

    def test_document_ids_are_unique(self):
        ids = [d["id"] for d in DOCUMENT_CATALOGUE]
        assert len(ids) == len(set(ids))

    def test_silos_are_returned_in_sequence(self):
        seqs = [s["seq"] for s in build_package(BASE)["silos"]]
        assert seqs == sorted(seqs)


class TestConditionalDocuments:

    def test_taxable_deal_excludes_tax_exempt_documents(self):
        ids = _ids(build_package({**BASE, "tax_exempt": False}))
        assert "form_8038" not in ids
        assert "tax_opinion" not in ids
        assert "tax_regulatory_agreement" not in ids

    def test_tax_exempt_deal_includes_them(self):
        ids = _ids(build_package({**BASE, "tax_exempt": True}))
        assert {"form_8038", "tax_opinion", "tax_regulatory_agreement"} <= ids

    def test_private_placement_excludes_public_offering_documents(self):
        ids = _ids(build_package(
            {**BASE, "distribution_method": "private_placement"}))
        assert "blue_sky_filings" not in ids
        assert "emma_filing" not in ids
        assert "roadshow_deck" not in ids

    def test_unrated_deal_excludes_the_rating_silo_documents(self):
        ids = _ids(build_package(BASE))
        assert "indicative_rating_letter" not in ids

    def test_excluded_documents_are_counted_not_hidden(self):
        """
        The count of inapplicable documents is reported, so a low document
        total is explainable rather than mysterious.
        """
        pkg = build_package({**BASE, "distribution_method": "private_placement"})
        assert pkg["totals"]["excluded_as_inapplicable"] > 0
        assert (pkg["totals"]["documents"]
                + pkg["totals"]["excluded_as_inapplicable"]
                == len(DOCUMENT_CATALOGUE))

    def test_inapplicable_silo_is_not_applicable_not_locked(self):
        """An unenhanced deal has no enhancement work pending -- it has none."""
        pkg = build_package(BASE)
        enh = next(s for s in pkg["silos"] if s["id"] == "enhancement")
        assert enh["document_count"] == 0
        assert enh["gate_state"] == "NOT_APPLICABLE"
        assert enh["rag"] == "GREY"


class TestBlocking:

    def test_document_is_blocked_until_its_input_exists(self):
        pkg = build_package(BASE)
        indenture = next(d for s in pkg["silos"] for d in s["documents"]
                         if d["id"] == "trust_indenture")
        assert indenture["state"] == "BLOCKED"
        assert "bond_counsel_engaged" in indenture["blocked_by"]

    def test_engaging_counsel_unblocks_it(self):
        pkg = build_package({**BASE, "bond_counsel_engaged": True})
        indenture = next(d for s in pkg["silos"] for d in s["documents"]
                         if d["id"] == "trust_indenture")
        assert indenture["state"] == "READY"
        assert indenture["blocked_by"] == []

    def test_an_upstream_document_can_satisfy_a_downstream_input(self):
        """
        The supplemental indenture needs the trust indenture -- which is a
        document, not a deal fact. Accepting it must unblock the dependent.
        """
        deal = {**BASE, "bond_counsel_engaged": True}
        before = build_package(deal)
        after = build_package(deal, {"trust_indenture": "accepted"})

        def state(pkg):
            return next(d["state"] for s in pkg["silos"] for d in s["documents"]
                        if d["id"] == "supplemental_indenture")

        assert state(before) == "BLOCKED"
        assert state(after) == "READY"

    def test_silo_gate_locks_until_prerequisites_clear(self):
        pkg = build_package(BASE)
        doc_silo = next(s for s in pkg["silos"] if s["id"] == "documentation")
        assert doc_silo["gate_state"] == "LOCKED"
        assert "bond_counsel_engaged" in doc_silo["gate_blocked_by"]

    def test_current_silo_is_the_first_open_one(self):
        assert build_package(BASE)["current_silo"] == "intake"

    def test_current_silo_advances_when_a_silo_completes(self):
        done = {d["id"]: "accepted" for d in DOCUMENT_CATALOGUE
                if d["silo"] == "intake"}
        assert build_package(BASE, done)["current_silo"] == "structuring"


class TestStatusAndProgress:

    def test_accepted_documents_count_complete(self):
        pkg = build_package(BASE, {"data_room": "accepted"})
        intake = next(s for s in pkg["silos"] if s["id"] == "intake")
        assert intake["documents_complete"] == 1

    def test_waived_counts_complete_too(self):
        pkg = build_package(BASE, {"data_room": "waived"})
        intake = next(s for s in pkg["silos"] if s["id"] == "intake")
        assert intake["documents_complete"] == 1

    def test_delivered_is_not_yet_complete(self):
        """Delivered is not accepted. The client still has to sign off."""
        pkg = build_package(BASE, {"data_room": "delivered"})
        intake = next(s for s in pkg["silos"] if s["id"] == "intake")
        assert intake["documents_complete"] == 0

    def test_fully_accepted_silo_reads_complete(self):
        done = {d["id"]: "accepted" for d in DOCUMENT_CATALOGUE
                if d["silo"] == "intake"}
        pkg = build_package(BASE, done)
        intake = next(s for s in pkg["silos"] if s["id"] == "intake")
        assert intake["gate_state"] == "COMPLETE"
        assert intake["rag"] == "GREEN"

    def test_unknown_status_is_rejected(self):
        with pytest.raises(DocumentPackageError):
            build_package(BASE, {"data_room": "sort_of_done"})

    def test_unknown_silo_is_rejected(self):
        with pytest.raises(DocumentPackageError):
            silo_package("kitchen", BASE)


class TestPOMComposite:

    def _pom(self, pkg):
        return next(d for s in pkg["silos"] for d in s["documents"]
                    if d["id"] == "preliminary_official_statement")

    def test_pom_carries_section_level_detail(self):
        """
        The POM is the largest block of NEST hours in the engagement. Tracking
        it as one line item hides where it actually stands.
        """
        pom = self._pom(build_package(BASE))
        assert pom["composite"] == "pom"
        d = pom["composite_detail"]
        assert d["section_count"] > 1
        assert d["sections_blocked"] > 0
        assert d["nest_hours"] > 0

    def test_pom_detail_responds_to_the_deal(self):
        blocked = self._pom(build_package(BASE))["composite_detail"]
        better = self._pom(build_package(
            {**BASE, "bond_counsel_engaged": True, "feasibility_study": True}
        ))["composite_detail"]
        assert better["sections_blocked"] < blocked["sections_blocked"]

    def test_no_other_document_claims_to_be_composite(self):
        composites = [d["id"] for d in DOCUMENT_CATALOGUE if d.get("composite")]
        assert composites == ["preliminary_official_statement"]


class TestRoutes:

    def test_package_over_http(self, client):
        r = client.post("/api/gate-fees/documents/package", json={"deal": BASE})
        assert r.status_code == 200
        d = r.get_json()["data"]
        assert len(d["silos"]) == len(SILO_IDS)

    def test_silo_drilldown_over_http(self, client):
        r = client.post("/api/gate-fees/documents/silo/intake",
                        json={"deal": BASE})
        assert r.status_code == 200
        assert r.get_json()["data"]["id"] == "intake"

    def test_unknown_silo_is_400_not_500(self, client):
        r = client.post("/api/gate-fees/documents/silo/kitchen",
                        json={"deal": BASE})
        assert r.status_code == 400

    def test_bad_status_is_400(self, client):
        r = client.post("/api/gate-fees/documents/package",
                        json={"deal": BASE, "statuses": {"data_room": "nope"}})
        assert r.status_code == 400

    def test_catalogue_is_readable(self, client):
        r = client.get("/api/gate-fees/documents/catalogue")
        assert r.status_code == 200
        d = r.get_json()["data"]
        assert len(d["documents"]) == len(DOCUMENT_CATALOGUE)
        assert len(d["silos"]) == len(SILO_IDS)
