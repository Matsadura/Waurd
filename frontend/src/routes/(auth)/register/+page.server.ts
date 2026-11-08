import { BACKEND_URL } from '$app/env/private';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';

function extractError(json: any): string {
	const detail = json?.detail;
	if (typeof detail === 'string') return detail;
	if (Array.isArray(detail)) return detail.map((d) => d.msg).join(' ');
	return 'Registration failed. Please try again.';
}

export const actions = {
	default: async ({ request, fetch }) => {
		const data = await request.formData();

		const username = String(data.get('username') ?? '').trim();
		const email = String(data.get('email') ?? '').trim();
		const password = String(data.get('password') ?? '');
		const termsAccepted = data.get('terms') === 'on';

		const values = { username, email };

		if (!termsAccepted) {
			return fail(400, { error: 'You must accept the terms.', values });
		}

		let response: Response;
		try {
			response = await fetch(`${BACKEND_URL}/api/v1/auth/register`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ username, email, password })
			});
		} catch {
			return fail(502, {
				error: 'Cannot connect to the server. Please try again.',
				values
			});
		}

		if (!response.ok) {
			const json = await response.json().catch(() => null);
			return fail(response.status, { error: extractError(json), values });
		}

		redirect(303, '/login');
	}
} satisfies Actions;
