import { fail, redirect } from '@sveltejs/kit';
import * as v from 'valibot';
import { loginSchema } from '#lib/schemas/login.ts';
import {
	api,
	jsonPost,
	errorMessage,
	forwardCookies,
	SESSION_COOKIE,
	CSRF_COOKIE,
	TWO_FACTOR_COOKIE
} from '#lib/server/api.ts';
import type { Actions } from './$types';

export const actions = {
	default: async ({ request, fetch, cookies }) => {
		const data = await request.formData();

		const email = String(data.get('email') ?? '');
		const password = String(data.get('password') ?? '');
		const values = { email };

		const result = v.safeParse(loginSchema, { email, password });

		if (!result.success) {
			return fail(400, {
				error: result.issues[0].message,
				values
			});
		}

		let response: Response;

		try {
			response = await fetch(api('/auth/login'), jsonPost(result.output));
		} catch {
			return fail(502, {
				error: 'Cannot connect to the server. Please try again.',
				values
			});
		}

		if (!response.ok) {
			return fail(response.status, {
				error: await errorMessage(response, 'Login failed. Please try again.'),
				values
			});
		}

		if (response.status === 202) {
			if (!forwardCookies(response, cookies, [TWO_FACTOR_COOKIE])) {
				return fail(502, {
					error: 'Could not start two-factor verification. Please try again.',
					values
				});
			}

			redirect(303, '/verify-2fa');
		}

		if (response.status !== 200) {
			return fail(502, {
				error: 'Unexpected login response. Please try again.',
				values
			});
		}

		if (!forwardCookies(response, cookies, [SESSION_COOKIE, CSRF_COOKIE])) {
			return fail(502, {
				error: 'Could not establish your session. Please try again.',
				values
			});
		}

		redirect(303, '/play');
	}
} satisfies Actions;
