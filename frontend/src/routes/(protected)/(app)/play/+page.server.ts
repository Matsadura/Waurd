import { fail, redirect } from '@sveltejs/kit';
import { PUBLIC_BACKEND_URL } from '$app/env/public';
import type { Actions, PageServerLoad } from './$types';

async function errorText(res: Response): Promise<string> {
	const text = await res.text();
	let message = `Request failed (HTTP ${res.status})`;

	if (text) {
		try {
			const body = JSON.parse(text);
			if (typeof body?.detail === 'string') {
				message = body.detail;
			}
		} catch {
			message = text;
		}
	}

	return message;
}

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/status`);
	let statusError: string | null = null;

	if (res.ok) {
		const ticket = await res.json();

		if (ticket.status === 'QUEUED' || ticket.status === 'CLAIMING') {
			redirect(302, '/play/online');
		} else if (ticket.status === 'WAITING') {
			redirect(302, '/play/friend');
		} else if (
			(ticket.status === 'MATCHED' || ticket.status === 'ACTIVE') &&
			ticket.matched_match_id
		) {
			redirect(302, '/battle/arena');
		}
	} else if (res.status !== 404) {
		statusError = await errorText(res);
	}

	return { statusError };
};

export const actions: Actions = {
	queue: async ({ request, fetch }) => {
		const formData = await request.formData();
		const seconds = Number(formData.get('time_control_seconds') ?? 300);

		const res = await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/queue`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ time_control_seconds: seconds })
		});

		if (!res.ok) {
			return fail(res.status, { error: await errorText(res) });
		} else {
			const ticket = await res.json();

			if (ticket.matched_match_id) {
				redirect(303, '/battle/arena');
			} else {
				redirect(303, '/play/online');
			}
		}
	},

	private: async ({ request, fetch }) => {
		const formData = await request.formData();
		const seconds = Number(formData.get('time_control_seconds') ?? 300);

		const res = await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/matches/custom`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ time_control_seconds: seconds })
		});

		if (!res.ok) {
			return fail(res.status, { error: await errorText(res) });
		} else {
			redirect(303, '/play/friend');
		}
	},

	join: async ({ request, fetch }) => {
		const formData = await request.formData();
		const code = String(formData.get('invite_code') ?? '')
			.trim()
			.toUpperCase();

		const res = await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/matches/join`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ invite_code: code })
		});

		if (!res.ok) {
			return fail(res.status, { error: 'Join code: ' + (await errorText(res)) });
		} else {
			const match = await res.json();

			if (match.id) {
				redirect(303, '/battle/arena');
			} else {
				redirect(303, '/play');
			}
		}
	}
};
