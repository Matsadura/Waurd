import { fail, redirect } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$app/env/public';
import type { Actions, PageServerLoad } from './$types';

export type Ticket = {
	status: string;
	matched_match_id?: string;
	time_control_seconds: number;
};

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/status`);

	if (res.ok) {
		const ticket: Ticket = await res.json();
		if (ticket.matched_match_id) {
			redirect(302, `/match/${ticket.matched_match_id}`);
		}
		redirect(302, '/play/online');
	}

	if (res.status !== 404) {
		return { statusError: `Server error (HTTP ${res.status})` };
	}

	return { statusError: null };
};

export const actions: Actions = {
	default: async ({ request, fetch }) => {
		const formData = await request.formData();
		const seconds = Number(formData.get('time_control_seconds') ?? 300);

		const res = await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/queue`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ time_control_seconds: seconds })
		});

		if (!res.ok) {
			const body = await res.json().catch(() => null);
			const detail =
				typeof body?.detail === 'string' ? body.detail : `Request failed (HTTP ${res.status})`;
			return fail(res.status, { error: detail });
		}

		// If paired immediately on join, skip /queue and go straight to the match
		const ticket: Ticket | null = await res.json().catch(() => null);
		if (ticket?.matched_match_id) {
			redirect(303, `/match/${ticket.matched_match_id}`);
		}

		redirect(303, '/play/online');
	}
};
