import { fail, redirect } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$app/env/public';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/status`);

	if (!res.ok) {
		redirect(302, '/play');
	} else {
		const ticket = await res.json();

		if (ticket.status === 'QUEUED' || ticket.status === 'CLAIMING') {
			redirect(302, '/play/online');
		} else if (
			(ticket.status === 'MATCHED' || ticket.status === 'ACTIVE') &&
			ticket.matched_match_id
		) {
			redirect(302, '/battle/arena');
		} else if (ticket.status !== 'WAITING') {
			redirect(302, '/play');
		} else {
			const matchRes = await fetch(
				`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/matches/${ticket.ticket_id}`
			);

			if (!matchRes.ok) {
				redirect(302, '/play');
			} else {
				const match = await matchRes.json();
				return { match };
			}
		}
	}
};

export const actions: Actions = {
	cancel: async ({ request, fetch }) => {
		const formData = await request.formData();
		const matchId = String(formData.get('match_id') ?? '');

		const res = await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/matches/${matchId}`, {
			method: 'DELETE'
		});

		if (!res.ok && res.status !== 404) {
			return fail(res.status, { error: `Could not cancel game (HTTP ${res.status}).` });
		} else {
			redirect(303, '/play');
		}
	}
};
