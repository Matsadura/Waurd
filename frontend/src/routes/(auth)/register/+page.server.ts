import { BACKEND_URL } from '$app/env/private';
import { fail, redirect } from '@sveltejs/kit';
import * as v from 'valibot';
import { registerSchema } from '#lib/schemas/register.ts';
import type { Actions } from './$types';

function extractError(json: unknown): string {
	if (
		typeof json === 'object' &&
		json !== null &&
		'detail' in json &&
		typeof json.detail === 'string'
	) {
		return json.detail;
	}

	return 'Registration failed. Please try again.';
}

export const actions = {
	default: async ({ request, fetch }) => {
		const data = await request.formData();

		const username = String(data.get('username') ?? '');
		const email = String(data.get('email') ?? '');
		const password = String(data.get('password') ?? '');
		const confirmPassword = String(data.get('confirm-password') ?? '');
		const termsAccepted = data.get('terms') === 'on';

		const values = { username, email };

		const result = v.safeParse(registerSchema, {
			username,
			email,
			password,
			confirmPassword,
			termsAccepted
		});

		if (!result.success) {
			return fail(400, {
				error: result.issues[0].message,
				values
			});
		}

		let response: Response;
		try {
			response = await fetch(`${BACKEND_URL}/api/v1/auth/register`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					username: result.output.username,
					email: result.output.email,
					password: result.output.password
				})
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
