import { error, redirect } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$app/env/public';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
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
			return { ticket };
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
			const res = await fetch(
				`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/matches/${matchId}/abandon`,
				{
					method: 'DELETE'
				}
			);

			// TODO(Ali): Are we sure that this request never fails? if the the other player 
			// abandoned the game first, this call will always fail!
			redirect(303, '/play');
		}
	}
};
