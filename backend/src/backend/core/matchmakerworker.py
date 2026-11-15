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

        if not raw_user_ids:
            return

        candidates: list[dict] = []
        dead_uids: list[str] = []

        for raw_uid in raw_user_ids:
            uid_str = raw_uid.decode("utf-8") if isinstance(raw_uid, bytes) else raw_uid
            ticket = await self.queue_store.get_user_ticket(uid_str)

            if (
                ticket
                and ticket.get("status") == "QUEUED"
                and ticket.get("time_control_seconds") == time_control
            ):
                candidates.append(ticket)
            elif not ticket or ticket.get("time_control_seconds") != time_control:
                dead_uids.append(uid_str)

        # Evict expired tickets or users who switched to another time-control queue
        for dead_uid in dead_uids:
            await self.queue_store.redis.lrem(queue_key, 0, dead_uid)

        if len(candidates) < 2:
            return

        # Sort candidate pool ascending by Elo rating
        candidates.sort(key=lambda p: p.get("elo", 1000))

        # Pair adjacent players (0 & 1, 2 & 3, etc.)
        for index in range(0, len(candidates) - 1, 2):
            player_a = candidates[index]
            player_b = candidates[index + 1]

            if (
                abs(player_a.get("elo", 1000) - player_b.get("elo", 1000))
                > MAX_ALLOWED_ELO_DIFF
            ):
                continue

            match_id = str(uuid.uuid4())
            p1_id = player_a["user_id"]
            p2_id = player_b["user_id"]

            # 1. Atomically lock both candidates in Redis for 10s
            claimed = await self.queue_store.claim_pair(p1_id, p2_id, time_control)
            if not claimed:
                continue

            # 2. Persist match in MySQL, then immediately delete Redis queue state
            try:
                async with self.session_factory() as db:
                    match_repo = MatchRepository(db)
                    await match_repo.create_pvp_match(
                        match_id_str=match_id,
                        player1_id_str=p1_id,
                        player2_id_str=p2_id,
                        time_control_seconds=time_control,
                    )
                    await db.commit()

                await self.queue_store.finalize_matched_pair(
                    p1_id, p2_id, time_control, match_id=match_id
                )
            except Exception as e:
                logger.error(
                    f"Failed to persist PvP match {match_id} for {p1_id} vs {p2_id}: {e}"
                )

    async def start_loop(self) -> None:
        """Runs continuous queue sweeps every second."""
        while True:
            try:
                for time_control in self.time_controls:
                    await self.process_queue_for_time_control(time_control)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Matchmaker worker error: {e}")

            await asyncio.sleep(1)
