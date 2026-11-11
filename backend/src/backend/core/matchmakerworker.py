import asyncio
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.matchmaking_store import MatchmakingQueueStore
from backend.repositories.match import MatchRepository

logger = logging.getLogger(__name__)

MAX_ALLOWED_ELO_DIFF = 200


class MatchmakerWorker:
    def __init__(
        self,
        queue_store: MatchmakingQueueStore,
        session_factory: async_sessionmaker[AsyncSession],
        time_controls: list[int] | None = None,
    ):
        self.queue_store = queue_store
        self.session_factory = session_factory
        self.time_controls = time_controls or [60, 180, 300]

    async def process_queue_for_time_control(self, time_control: int) -> None:
        queue_key = self.queue_store._queue_key(time_control)
        raw_user_ids = await self.queue_store.redis.lrange(queue_key, 0, 99)

        if not raw_user_ids or len(raw_user_ids) < 2:
            return

        candidates: list[dict] = []
        dead_uids: list[str] = []

        for raw_uid in raw_user_ids:
            # Safely decode bytes if redis response isn't auto-decoded
            uid_str = raw_uid.decode("utf-8") if isinstance(raw_uid, bytes) else raw_uid

            # Pass time_control to get_user_ticket
            ticket = await self.queue_store.get_user_ticket(
                user_id_str=uid_str, 
                time_control=time_control,
            )

            if ticket and ticket.get("status") == "QUEUED":
                candidates.append(ticket)
            else:
                # Mark expired/cancelled ticket IDs for list cleanup
                dead_uids.append(uid_str)

        # Evict dead/expired tickets from the Redis queue list
        for dead_uid in dead_uids:
            await self.queue_store.redis.lrem(queue_key, 0, dead_uid)

        if len(candidates) < 2:
            return

        # Sort candidate pool ascending by Elo rating
        candidates.sort(key=lambda p: p.get("elo", 1000))

        # Pair adjacent players (0 & 1, 2 & 3, etc.)
        for i in range(0, len(candidates) - 1, 2):
            player_a = candidates[i]
            player_b = candidates[i + 1]

            if (
                abs(player_a.get("elo", 1000) - player_b.get("elo", 1000))
                > MAX_ALLOWED_ELO_DIFF
            ):
                continue

            match_id = str(uuid.uuid4())

            # Pass time_control to claim_candidate
            ticket_a = await self.queue_store.claim_candidate(
                candidate_id_str=player_a["user_id"],
                time_control=time_control,
                match_id_str=match_id,
            )
            ticket_b = await self.queue_store.claim_candidate(
                candidate_id_str=player_b["user_id"],
                time_control=time_control,
                match_id_str=match_id,
            )

            if ticket_a and ticket_b:
                async with self.session_factory() as db:
                    match_repo = MatchRepository(db)
                    await match_repo.create_pvp_match(
                        match_id_str=match_id,
                        player1_id_str=player_a["user_id"],
                        player2_id_str=player_b["user_id"],
                        time_control_seconds=time_control,
                    )
                    await db.commit()

                # Remove matched players from the Redis queue list
                await self.queue_store.redis.lrem(queue_key, 0, player_a["user_id"])
                await self.queue_store.redis.lrem(queue_key, 0, player_b["user_id"])

    async def start_loop(self) -> None:
        """Runs continuous queue sweeps every second."""
        while True:
            try:
                for tc in self.time_controls:
                    await self.process_queue_for_time_control(tc)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Matchmaker worker error: {e}")

            await asyncio.sleep(1)