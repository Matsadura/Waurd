import { fail, redirect } from '@sveltejs/kit';
import * as v from 'valibot';
import { forgotPasswordSchema, resetPasswordSchema } from '#lib/schemas/password-reset.ts';
import { api, jsonPost, errorMessage } from '#lib/server/api.ts';
import type { Actions } from './$types';

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
			response = await fetch(api('/auth/password/forgot'), jsonPost(result.output));
		} catch {
			return fail(502, {
				sent: false,
				error: 'Cannot connect to the server. Please try again.',
				values
			});
		}

		if (!response.ok) {
			return fail(response.status, {
				sent: false,
				error: await errorMessage(response, 'Could not request password reset. Please try again.'),
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
			response = await fetch(
				api('/auth/password/reset'),
				jsonPost({
					token,
					new_password: result.output.newPassword
				})
			);
		} catch {
			return fail(502, {
				sent: false,
				error: 'Cannot connect to the server. Please try again.',
				values: { email: '' }
			});
		}

		if (!response.ok) {
			return fail(response.status, {
				sent: false,
				error: await errorMessage(response, 'Could not reset password. Please try again.'),
				values: { email: '' }
			});
		}

		redirect(303, '/reset-password?success=1');
	}
} satisfies Actions;
