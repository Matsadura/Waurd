import { error, redirect } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$app/env/public';
import type { Actions, PageServerLoad } from './$types';

type MatchPlayer = {
	id: string;
	username: string;
	avatar_url: string | null;
};

function resolveAvatar(avatarUrl: string | null | undefined): string | undefined {
	let resolved: string | undefined = undefined;
	if (avatarUrl) {
		if (avatarUrl.startsWith('/')) {
			resolved = `${PUBLIC_BACKEND_URL}${avatarUrl}`;
		} else {
			resolved = avatarUrl;
		}
	}
	return resolved;
}

export const load: PageServerLoad = async ({ fetch, locals }) => {
	const res = await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/status`);

	if (res.status === 404) {
		redirect(302, '/play');
	} else if (!res.ok) {
		error(res.status, `Could not check match status (HTTP ${res.status}).`);
	} else {
		const ticket = await res.json();

		if (ticket.status === 'QUEUED' || ticket.status === 'CLAIMING') {
			redirect(302, '/play/online');
		} else if (ticket.status === 'WAITING') {
			redirect(302, '/play/friend');
		} else if (
			(ticket.status === 'MATCHED' || ticket.status === 'ACTIVE') &&
			ticket.matched_match_id
		) {
			const matchRes = await fetch(
				`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/matches/${ticket.matched_match_id}`
			);

			if (!matchRes.ok) {
				error(matchRes.status, `Could not load battle details (HTTP ${matchRes.status}).`);
			} else {
				const match = (await matchRes.json()) as {
					time_control_seconds: number;
					player1: MatchPlayer;
					player2: MatchPlayer | null;
				};
				const isPlayer1 = match.player1.id === locals.user?.id;
				const rawMe = isPlayer1 ? match.player1 : match.player2;
				const rawOpponent = isPlayer1 ? match.player2 : match.player1;

				return {
					ticket,
					timeControlSeconds: match.time_control_seconds,
					players: {
						me: {
							name: rawMe?.username ?? locals.user?.username ?? 'You',
							avatar: resolveAvatar(rawMe?.avatar_url)
						},
						opponent: {
							name: rawOpponent?.username ?? 'Opponent',
							avatar: resolveAvatar(rawOpponent?.avatar_url)
						}
					}
				};
			}
		} else {
			redirect(302, '/play');
		}
	}
};

export const actions: Actions = {
	default: async ({ request, fetch }) => {
		const formData = await request.formData();
		const matchId = String(formData.get('match_id') ?? '');

		if (!matchId) {
			redirect(303, '/play');
		} else {
			await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/matches/${matchId}/abandon`, {
				method: 'DELETE'
			});

			// TODO(Ali): Are we sure that this request never fails? if the the other player
			// abandoned the game first, this call will always fail!
			redirect(303, '/play');
		}
	}
};
