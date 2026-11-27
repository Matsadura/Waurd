import type { Match } from '#lib/types/profile.ts';

export type MatchResponse = {
	id: string;
	player1_id: string;
	player2_id: string | null;
	player1_username: string;
	player2_username: string | null;
	winner_id: string | null;
	player1_elo_before: number | null;
	player1_elo_after: number | null;
	player2_elo_before: number | null;
	player2_elo_after: number | null;
	time_control_seconds: number;
	total_turns: number | null;
	ended_at: string | null;
};

export function toProfileMatch(match: MatchResponse, userId: string): Match {
    // Determine whether the current user is Player 1 or Player 2 to pick their Elo values and calculate the net change
	const isPlayer1 = match.player1_id === userId;

	const before = isPlayer1 ? match.player1_elo_before : match.player2_elo_before;
	const after = isPlayer1 ? match.player1_elo_after : match.player2_elo_after;

	const opponentElo = isPlayer1 ? match.player2_elo_before : match.player1_elo_before;

	const seconds = match.time_control_seconds;

	return {
		id: match.id,
		opponent: isPlayer1 ? (match.player2_username ?? 'Unknown opponent') : match.player1_username,
		opponentElo,
		result: match.winner_id === null ? 'draw' : match.winner_id === userId ? 'win' : 'loss',
		eloChange: before === null || after === null ? null : after - before,
		mode: seconds % 60 === 0 ? `${seconds / 60} min` : `${seconds} sec`,
		turns: match.total_turns,
		date: match.ended_at
			? new Date(match.ended_at).toLocaleDateString('en-US', {
					month: 'short',
					day: 'numeric',
					year: 'numeric'
				})
			: 'Date unavailable'
	};
}
