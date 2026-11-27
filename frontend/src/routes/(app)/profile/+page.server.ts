import { error, redirect } from '@sveltejs/kit';
import { api } from '#lib/server/api.ts';
import type { PageServerLoad } from './$types';

type StatsResponse = {
	matches_played: number;
	wins: number;
	losses: number;
	draws: number;
	rating_elo: number;
};

export const load: PageServerLoad = async ({ fetch, parent }) => {
	// Get the user already fetched in +layout.server.ts instead of requesting /users/me again
	const { user } = await parent();

	let statsResponse: Response;
	let friendsResponse: Response;

	try {
		[statsResponse, friendsResponse] = await Promise.all([
			fetch(api(`/users/${user.id}/stats`)),
			fetch(api('/friends?page=1&size=1'))
		]);
	} catch {
		error(502, 'Cannot connect to the backend.');
	}

	if (statsResponse.status === 401 || friendsResponse.status === 401) {
		redirect(303, '/login');
	}

	if (!statsResponse.ok) {
		error(502, 'Could not retrieve your statistics.');
	}

	if (!friendsResponse.ok) {
		error(502, 'Could not retrieve your friends.');
	}

	const stats: StatsResponse = await statsResponse.json();
	const friends: { total: number } = await friendsResponse.json();

	return {
		stats: {
			elo: stats.rating_elo,
			games: stats.matches_played,
			wins: stats.wins,
			losses: stats.losses,
			draws: stats.draws
		},
		friendCount: friends.total
	};
};
