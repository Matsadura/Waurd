import { error, redirect } from '@sveltejs/kit';
import { api } from '#lib/server/api.ts';
import { toProfileMatch, type MatchResponse } from '#lib/server/profile-matches.ts';
import type { PageServerLoad } from './$types';

const PAGE_SIZE = 8;

type StatsResponse = {
	matches_played: number;
	wins: number;
	losses: number;
	draws: number;
};

type MatchesResponse = {
	items: MatchResponse[];
	total: number;
	page: number;
	pages: number;
};

export const load: PageServerLoad = async ({ fetch, parent, url }) => {
	const { profile: user } = await parent();

	const requestedPage = Number(url.searchParams.get('page') ?? '1');
	const page = Number.isSafeInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;

	let statsResponse: Response;
	let matchesResponse: Response;

	try {
		[statsResponse, matchesResponse] = await Promise.all([
			fetch(api(`/users/${user.id}/stats`)),
			fetch(api(`/users/${user.id}/matches?status=FINISHED&page=${page}&size=${PAGE_SIZE}`))
		]);
	} catch {
		error(502, 'Cannot connect to the backend.');
	}

	if (statsResponse.status === 401 || matchesResponse.status === 401) {
		redirect(303, '/login');
	}

	if (!statsResponse.ok) {
		error(502, 'Could not retrieve your statistics.');
	}

	if (!matchesResponse.ok) {
		error(502, 'Could not retrieve your duels.');
	}

	const stats: StatsResponse = await statsResponse.json();
	const history: MatchesResponse = await matchesResponse.json();

	const lastPage = Math.max(1, history.pages);

	if (page > lastPage) {
		redirect(302, `/profile/history?page=${lastPage}`);
	}

	return {
		stats: {
			games: stats.matches_played,
			wins: stats.wins,
			losses: stats.losses,
			draws: stats.draws
		},
		matches: history.items.map((match) => toProfileMatch(match, user.id)),
		pagination: {
			page: history.page,
			pages: history.pages,
			total: history.total
		}
	};
};
