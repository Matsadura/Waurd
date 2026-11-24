import { redirect } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$app/env/public';
import type { Actions, PageServerLoad } from './$types';
import type { Ticket } from '../+page.server';

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/status`);

	if (!res.ok) {
		redirect(302, '/play');
	}

	const ticket: Ticket = await res.json();
	if (ticket.matched_match_id) {
		redirect(302, `/match/${ticket.matched_match_id}`);
	}

	return { ticket };
};

export const actions: Actions = {
	default: async ({ request, fetch }) => {
		const formData = await request.formData();
		const seconds = Number(formData.get('time_control_seconds'));

		await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/queue`, {
			method: 'DELETE',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ time_control_seconds: seconds })
		});

		// Redirecting to /play re-runs /play's load check: if a match was found right as
		// the player clicked cancel, /play will automatically forward them into the match.
		redirect(303, '/play');
	}
};
