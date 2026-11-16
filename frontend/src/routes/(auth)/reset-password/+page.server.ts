import { BACKEND_URL } from '$app/env/private';
import { fail, redirect } from '@sveltejs/kit';
import * as v from 'valibot';
import { forgotPasswordSchema, resetPasswordSchema } from '#lib/schemas/password-reset.ts';
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

	return 'Could not request password reset. Please try again.';
}

export const actions = {
	request: async ({ request, fetch }) => {
		const data = await request.formData();
		const email = String(data.get('email') ?? '');
		const values = { email };

		const result = v.safeParse(forgotPasswordSchema, { email });

		if (!result.success) {
			return fail(400, {
				sent: false,
				error: result.issues[0].message,
				values
			});
		}

		let response: Response;

		try {
			response = await fetch(`${BACKEND_URL}/api/v1/auth/password/forgot`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(result.output)
			});
		} catch {
			return fail(502, {
				sent: false,
				error: 'Cannot connect to the server. Please try again.',
				values
			});
		}

		if (!response.ok) {
			const json = await response.json().catch(() => null);

			return fail(response.status, {
				sent: false,
				error: extractError(json),
				values
			});
		}

		return {
			sent: true,
			error: null,
			values: { email: result.output.email }
		};
	},

	reset: async ({ request, fetch, url }) => {
		const token = url.searchParams.get('token') ?? '';

		if (!token || token.length > 256) {
			return fail(400, {
				sent: false,
				error: 'Invalid reset link. Request a new one.',
				values: { email: '' }
			});
		}

		const data = await request.formData();

		const newPassword = String(data.get('newPassword') ?? '');
		const confirmPassword = String(data.get('confirmPassword') ?? '');

		const result = v.safeParse(resetPasswordSchema, {
			newPassword,
			confirmPassword
		});

		if (!result.success) {
			return fail(400, {
				sent: false,
				error: result.issues[0].message,
				values: { email: '' }
			});
		}

		let response: Response;

		try {
			response = await fetch(`${BACKEND_URL}/api/v1/auth/password/reset`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					token,
					new_password: result.output.newPassword
				})
			});
		} catch {
			return fail(502, {
				sent: false,
				error: 'Cannot connect to the server. Please try again.',
				values: { email: '' }
			});
		}

		if (!response.ok) {
			const json = await response.json().catch(() => null);

			return fail(response.status, {
				sent: false,
				error: extractError(json),
				values: { email: '' }
			});
		}

		redirect(303, '/reset-password?success=1');
	}
} satisfies Actions;
