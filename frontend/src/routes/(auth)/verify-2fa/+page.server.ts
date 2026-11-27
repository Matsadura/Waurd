import { fail, redirect } from '@sveltejs/kit';
import * as v from 'valibot';
import { twoFactorCodeSchema } from '#lib/schemas/two-factor.ts';
import {
	api,
	jsonPost,
	errorMessage,
	forwardCookies,
	SESSION_COOKIE,
	CSRF_COOKIE,
	TWO_FACTOR_COOKIE
} from '#lib/server/api.ts';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = ({ cookies }) => {
	if (!cookies.get(TWO_FACTOR_COOKIE)) {
		redirect(303, '/login');
	}
};

export const actions = {
	default: async ({ request, fetch, cookies }) => {
		if (!cookies.get(TWO_FACTOR_COOKIE)) {
			redirect(303, '/login');
		}

		const data = await request.formData();
		const code = String(data.get('code') ?? '');

		const result = v.safeParse(twoFactorCodeSchema, { code });

		if (!result.success) {
			return fail(400, {
				error: result.issues[0].message
			});
		}

		let response: Response;

		try {
			response = await fetch(api('/auth/2fa/verify'), jsonPost(result.output));
		} catch {
			return fail(502, {
				error: 'Cannot connect to the server. Please try again.'
			});
		}

		if (!response.ok) {
			return fail(response.status, {
				error: await errorMessage(response, 'Verification failed. Please try again.')
			});
		}

		if (response.status !== 200) {
			return fail(502, {
				error: 'Unexpected verification response. Please try again.'
			});
		}

		if (!forwardCookies(response, cookies, [SESSION_COOKIE, CSRF_COOKIE])) {
			return fail(502, {
				error: 'Could not establish your session. Please try again.'
			});
		}

		redirect(303, '/play');
	}
} satisfies Actions;
