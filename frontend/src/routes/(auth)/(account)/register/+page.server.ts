import { fail, redirect } from '@sveltejs/kit';
import { api, jsonPost, errorMessage } from '#lib/server/api.ts';
import * as v from 'valibot';
import { registerSchema } from '#lib/schemas/register.ts';
import type { Actions } from './$types';

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
			response = await fetch(
				api('/auth/register'),
				jsonPost({
					username: result.output.username,
					email: result.output.email,
					password: result.output.password
				})
			);
		} catch {
			return fail(502, {
				error: 'Cannot connect to the server. Please try again.',
				values
			});
		}

		if (!response.ok) {
			return fail(response.status, {
				error: await errorMessage(response, 'Registration failed. Please try again.'),
				values
			});
		}

		redirect(303, '/login');
	}
} satisfies Actions;
