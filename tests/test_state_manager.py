"""
Tests unitaires pour la state machine du cycle de vie des monstres
(app.services.state_manager.MonsterStateManager).

Ne nécessite ni base de données ni services externes : `transition()` (et
tout ce qui est testé ici) est pure, seule `perform_transition()` touche les
repositories (non testée ici).
"""

from datetime import datetime, timezone

import pytest

from app.core.constants import MonsterStateEnum
from app.schemas.metadata import MonsterMetadata
from app.services.state_manager import MonsterStateManager, StateTransitionError


def make_metadata(state: MonsterStateEnum, monster_id: str = "m-1") -> MonsterMetadata:
    now = datetime.now(timezone.utc)
    return MonsterMetadata(
        monster_id=monster_id,
        state=state,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def manager():
    # Ni state_repository ni transition_repository ne sont utilisés par les
    # méthodes testées ici (can_transition/transition/get_next_states/...).
    return MonsterStateManager(state_repository=None, transition_repository=None)


class TestValidTransitionsTable:
    """Verrouille le contrat documenté du cycle de vie (CLAUDE.md) :
    GENERATED -> PENDING_REVIEW/DEFECTIVE, DEFECTIVE -> PENDING_REVIEW/REJECTED,
    PENDING_REVIEW -> APPROVED/REJECTED, APPROVED -> TRANSMITTED/PENDING_REVIEW,
    TRANSMITTED -> TRANSMITTED (retransmission), REJECTED terminal.
    """

    @pytest.mark.parametrize(
        "from_state,to_state",
        [
            (MonsterStateEnum.GENERATED, MonsterStateEnum.PENDING_REVIEW),
            (MonsterStateEnum.GENERATED, MonsterStateEnum.DEFECTIVE),
            (MonsterStateEnum.DEFECTIVE, MonsterStateEnum.PENDING_REVIEW),
            (MonsterStateEnum.DEFECTIVE, MonsterStateEnum.REJECTED),
            (MonsterStateEnum.PENDING_REVIEW, MonsterStateEnum.APPROVED),
            (MonsterStateEnum.PENDING_REVIEW, MonsterStateEnum.REJECTED),
            (MonsterStateEnum.APPROVED, MonsterStateEnum.TRANSMITTED),
            (MonsterStateEnum.APPROVED, MonsterStateEnum.PENDING_REVIEW),
            (MonsterStateEnum.TRANSMITTED, MonsterStateEnum.TRANSMITTED),
        ],
    )
    def test_allowed_transition(self, manager, from_state, to_state):
        assert manager.can_transition(from_state, to_state) is True

    @pytest.mark.parametrize(
        "from_state,to_state",
        [
            # Bug historique (admin_service.py, corrigé en P0) : le bulk
            # process mettait state=DEFECTIVE avant d'appeler
            # perform_transition(-> DEFECTIVE), ce qui suppose à tort que
            # DEFECTIVE -> DEFECTIVE est une transition valide.
            (MonsterStateEnum.DEFECTIVE, MonsterStateEnum.DEFECTIVE),
            (MonsterStateEnum.GENERATED, MonsterStateEnum.GENERATED),
            (MonsterStateEnum.GENERATED, MonsterStateEnum.APPROVED),
            (MonsterStateEnum.GENERATED, MonsterStateEnum.TRANSMITTED),
            (MonsterStateEnum.PENDING_REVIEW, MonsterStateEnum.GENERATED),
            (MonsterStateEnum.PENDING_REVIEW, MonsterStateEnum.DEFECTIVE),
            (MonsterStateEnum.APPROVED, MonsterStateEnum.REJECTED),
            (MonsterStateEnum.APPROVED, MonsterStateEnum.GENERATED),
            (MonsterStateEnum.TRANSMITTED, MonsterStateEnum.APPROVED),
            (MonsterStateEnum.TRANSMITTED, MonsterStateEnum.PENDING_REVIEW),
            (MonsterStateEnum.REJECTED, MonsterStateEnum.PENDING_REVIEW),
            (MonsterStateEnum.REJECTED, MonsterStateEnum.GENERATED),
        ],
    )
    def test_forbidden_transition(self, manager, from_state, to_state):
        assert manager.can_transition(from_state, to_state) is False

    def test_rejected_is_a_final_state(self, manager):
        assert manager.is_final_state(MonsterStateEnum.REJECTED) is True
        assert manager.get_next_states(MonsterStateEnum.REJECTED) == []

    @pytest.mark.parametrize(
        "state",
        [
            MonsterStateEnum.GENERATED,
            MonsterStateEnum.DEFECTIVE,
            MonsterStateEnum.PENDING_REVIEW,
            MonsterStateEnum.APPROVED,
            MonsterStateEnum.TRANSMITTED,
        ],
    )
    def test_non_rejected_states_are_not_final(self, manager, state):
        assert manager.is_final_state(state) is False


class TestTransition:
    def test_valid_transition_updates_state_and_history(self, manager):
        metadata = make_metadata(MonsterStateEnum.GENERATED)

        updated = manager.transition(
            metadata, MonsterStateEnum.PENDING_REVIEW, actor="alice", note="ok"
        )

        assert updated.state == MonsterStateEnum.PENDING_REVIEW
        assert len(updated.history) == 1
        entry = updated.history[0]
        assert entry.from_state == MonsterStateEnum.GENERATED
        assert entry.to_state == MonsterStateEnum.PENDING_REVIEW
        assert entry.actor == "alice"
        assert entry.note == "ok"

    def test_invalid_transition_raises_and_leaves_state_untouched(self, manager):
        metadata = make_metadata(MonsterStateEnum.REJECTED)

        with pytest.raises(StateTransitionError):
            manager.transition(metadata, MonsterStateEnum.PENDING_REVIEW)

        # L'état n'a pas bougé et aucune entrée d'historique n'a été ajoutée.
        assert metadata.state == MonsterStateEnum.REJECTED
        assert metadata.history == []

    def test_defective_to_defective_is_rejected(self, manager):
        """Régression directe du bug corrigé en P0 (admin_service.py)."""
        metadata = make_metadata(MonsterStateEnum.DEFECTIVE)

        with pytest.raises(StateTransitionError):
            manager.transition(metadata, MonsterStateEnum.DEFECTIVE)

    def test_history_accumulates_across_multiple_transitions(self, manager):
        metadata = make_metadata(MonsterStateEnum.GENERATED)

        manager.transition(metadata, MonsterStateEnum.PENDING_REVIEW, actor="system")
        manager.transition(metadata, MonsterStateEnum.APPROVED, actor="alice")
        manager.transition(metadata, MonsterStateEnum.TRANSMITTED, actor="system")

        assert [e.to_state for e in metadata.history] == [
            MonsterStateEnum.PENDING_REVIEW,
            MonsterStateEnum.APPROVED,
            MonsterStateEnum.TRANSMITTED,
        ]
        assert metadata.state == MonsterStateEnum.TRANSMITTED


class TestDataShapeHelpers:
    @pytest.mark.parametrize("state", [MonsterStateEnum.GENERATED, MonsterStateEnum.DEFECTIVE])
    def test_json_states_require_json_data(self, manager, state):
        assert manager.requires_json_data(state) is True
        assert manager.requires_structured_data(state) is False

    @pytest.mark.parametrize(
        "state",
        [
            MonsterStateEnum.PENDING_REVIEW,
            MonsterStateEnum.APPROVED,
            MonsterStateEnum.TRANSMITTED,
            MonsterStateEnum.REJECTED,
        ],
    )
    def test_structured_states_require_structured_data(self, manager, state):
        assert manager.requires_structured_data(state) is True
        assert manager.requires_json_data(state) is False
