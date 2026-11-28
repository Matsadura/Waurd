import { error, redirect } from '@sveltejs/kit';
import { api } from '#lib/server/api.ts';
import type { PageServerLoad } from './$types';
import { toProfileMatch, type MatchResponse } from '#lib/server/profile-matches.ts';

type StatsResponse = {
	matches_played: number;
	wins: number;
	losses: number;
	draws: number;
	rating_elo: number;
	win_streak: number;
	best_win_streak: number;
};

type MatchesResponse = {
	items: MatchResponse[];
	total: number;
};

export const load: PageServerLoad = async ({ fetch, parent }) => {
	// Get the user already fetched in +layout.server.ts instead of requesting /users/me again
	const { profile: user } = await parent();

	let statsResponse: Response;
	let friendsResponse: Response;
	let matchesResponse: Response;

	try {
		[statsResponse, friendsResponse, matchesResponse] = await Promise.all([
			fetch(api(`/users/${user.id}/stats`)),
			fetch(api('/friends?page=1&size=1')),
			fetch(api(`/users/${user.id}/matches?status=FINISHED&page=1&size=4`))
		]);
	} catch {
		error(502, 'Cannot connect to the backend.');
	}

	if (
		statsResponse.status === 401 ||
		friendsResponse.status === 401 ||
		matchesResponse.status === 401
	) {
		redirect(303, '/login');
	}

	if (!statsResponse.ok) {
		error(502, 'Could not retrieve your statistics.');
	}

	if (!friendsResponse.ok) {
		error(502, 'Could not retrieve your friends.');
	}

	if (!matchesResponse.ok) {
		error(502, 'Could not retrieve your recent duels.');
	}

	const stats: StatsResponse = await statsResponse.json();
	const friends: { total: number } = await friendsResponse.json();
	const matches: MatchesResponse = await matchesResponse.json();

	return {
		stats: {
			elo: stats.rating_elo,
			games: stats.matches_played,
			wins: stats.wins,
			losses: stats.losses,
			draws: stats.draws,
			winStreak: stats.win_streak,
			bestWinStreak: stats.best_win_streak
		},
		friendCount: friends.total,
		recentMatches: matches.items.map((match) => toProfileMatch(match, user.id))
	};
};
