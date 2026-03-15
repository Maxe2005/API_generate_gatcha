"""
Tests pour le refactoring de l'historique des updates.
Valide la nouvelle architecture event-based.
"""

import pytest
from datetime import datetime, timezone
from app.services.admin_service import compute_changed_fields
from app.schemas.update_event import UpdateEvent, TimelineEvent, MonsterHistory


class TestComputeChangedFields:
    """Tests pour le calcul des champs modifiés"""

    def test_simple_field_change(self):
        """Teste les modifications simples"""
        before = {"hp": 100, "atk": 50}
        after = {"hp": 120, "atk": 50}

        result = compute_changed_fields(before, after)

        assert result["changed_fields"] == ["hp"]
        assert "hp" in result["diff_payload"]
        assert result["diff_payload"]["hp"]["before"] == 100
        assert result["diff_payload"]["hp"]["after"] == 120

    def test_nested_field_change(self):
        """Teste les modifications imbriquées"""
        before = {"stats": {"hp": 100}, "name": "Dragon"}
        after = {"stats": {"hp": 120}, "name": "Dragon"}

        result = compute_changed_fields(before, after)

        assert result["changed_fields"] == ["stats.hp"]
        assert "stats.hp" in result["diff_payload"]

    def test_no_changes(self):
        """Teste quand il n'y a pas de changements"""
        before = {"hp": 100, "atk": 50}
        after = {"hp": 100, "atk": 50}

        result = compute_changed_fields(before, after)

        assert result["changed_fields"] == []
        assert result["diff_payload"] == {}

    def test_new_field(self):
        """Teste l'ajout d'un nouveau champ"""
        before = {"hp": 100}
        after = {"hp": 100, "atk": 50}

        result = compute_changed_fields(before, after)

        assert result["changed_fields"] == ["atk"]
        assert result["diff_payload"]["atk"]["before"] is None
        assert result["diff_payload"]["atk"]["after"] == 50

    def test_removed_field(self):
        """Teste la suppression d'un champ"""
        before = {"hp": 100, "atk": 50}
        after = {"hp": 100}

        result = compute_changed_fields(before, after)

        assert result["changed_fields"] == ["atk"]
        assert result["diff_payload"]["atk"]["before"] == 50
        assert result["diff_payload"]["atk"]["after"] is None

    def test_multiple_nested_changes(self):
        """Teste plusieurs modifications imbriquées"""
        before = {"stats": {"hp": 100, "atk": 50}, "skills": [{"name": "Fireball"}]}
        after = {"stats": {"hp": 120, "atk": 60}, "skills": [{"name": "Fireball"}]}

        result = compute_changed_fields(before, after)

        assert len(result["changed_fields"]) == 2
        assert "stats.hp" in result["changed_fields"]
        assert "stats.atk" in result["changed_fields"]


class TestUpdateEventSchema:
    """Tests pour les schémas UpdateEvent et TimelineEvent"""

    def test_update_event_creation(self):
        """Teste la création d'un UpdateEvent"""
        event = UpdateEvent(
            id=1,
            monster_state_db_id=10,
            occurred_at=datetime.now(timezone.utc),
            actor_type="admin",
            actor_name="admin_user",
            actor_id="user123",
            source="admin_update_endpoint",
            reason="Test update",
            validation_before=True,
            validation_after=True,
            skip_validation=False,
            storage_mode_before="json",
            storage_mode_after="json",
            changed_fields=["stats.hp"],
            diff_payload={"stats.hp": {"before": 100, "after": 120}},
            request_context={"trace_id": "abc123"},
        )

        assert event.id == 1
        assert event.actor_name == "admin_user"
        assert len(event.changed_fields) == 1

    def test_timeline_event_state_transition(self):
        """Teste un TimelineEvent de type transition"""
        event = TimelineEvent(
            event_type="state_transition",
            happened_at=datetime.now(timezone.utc),
            actor="system",
            summary="GENERATED → PENDING_REVIEW",
            details={
                "from_state": "GENERATED",
                "to_state": "PENDING_REVIEW",
                "note": "Auto-transition",
            },
        )

        assert event.event_type == "state_transition"
        assert event.details["from_state"] == "GENERATED"

    def test_timeline_event_data_update(self):
        """Teste un TimelineEvent de type update"""
        event = TimelineEvent(
            event_type="data_update",
            happened_at=datetime.now(timezone.utc),
            actor="admin_user",
            summary="Updated 2 field(s)",
            details={
                "changed_fields": ["stats.hp", "stats.atk"],
                "validation_before": True,
                "validation_after": True,
            },
        )

        assert event.event_type == "data_update"
        assert len(event.details["changed_fields"]) == 2

    def test_monster_history_schema(self):
        """Teste le schéma MonsterHistory"""
        now = datetime.now(timezone.utc)
        history = MonsterHistory(
            monster_id="uuid-123",
            current_state="APPROVED",
            timeline=[
                TimelineEvent(
                    event_type="state_transition",
                    happened_at=now,
                    actor="system",
                    summary="GENERATED",
                    details={"to_state": "GENERATED"},
                )
            ],
        )

        assert history.monster_id == "uuid-123"
        assert history.current_state == "APPROVED"
        assert len(history.timeline) == 1


class TestTimelineOrdering:
    """Tests pour l'ordre de la timeline"""

    def test_timeline_ordering_descending(self):
        """Teste que la timeline se trie correctement en descendant"""
        now = datetime.now(timezone.utc)
        events = [
            TimelineEvent(
                event_type="state_transition",
                happened_at=now,
                actor="system",
                summary="Event 1",
                details={},
            ),
            TimelineEvent(
                event_type="data_update",
                happened_at=datetime(2026, 3, 10, 10, 0, 0, tzinfo=timezone.utc),
                actor="admin",
                summary="Event 2",
                details={},
            ),
        ]

        # Sort descending by time
        sorted_events = sorted(events, key=lambda e: e.happened_at, reverse=True)

        assert sorted_events[0].summary == "Event 1"
        assert sorted_events[1].summary == "Event 2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
