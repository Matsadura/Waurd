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
			return { ticket };
		} else if (ticket.status === 'WAITING') {
			redirect(302, '/play/friend');
		} else if (
			(ticket.status === 'MATCHED' || ticket.status === 'ACTIVE') &&
			ticket.matched_match_id
		) {
			redirect(302, '/battle/arena');
		} else {
			redirect(302, '/play');
		}
	}
};

export const actions: Actions = {
	default: async ({ request, fetch }) => {
		const formData = await request.formData();
		const seconds = Number(formData.get('time_control_seconds'));

		const res = await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/queue`, {
			method: 'DELETE',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ time_control_seconds: seconds })
		});

		if (!res.ok && res.status !== 404) {
			return fail(res.status, { error: `Could not leave queue (HTTP ${res.status}).` });
		} else {
			redirect(303, '/play');
		}
	}
};
