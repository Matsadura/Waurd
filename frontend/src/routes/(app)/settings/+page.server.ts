import { error, fail, redirect } from '@sveltejs/kit';
import * as v from 'valibot';
import { twoFactorCodeSchema } from '#lib/schemas/two-factor.ts';
import { api, jsonPost, errorMessage, SESSION_COOKIE, CSRF_COOKIE } from '#lib/server/api.ts';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ cookies, fetch }) => {
	if (!cookies.get(SESSION_COOKIE)) {
		redirect(303, '/login');
	}

	let response: Response;

	try {
		response = await fetch(api('/auth/2fa'));
	} catch {
		error(502, 'Cannot connect to the backend.');
	}

	if (response.status === 401) {
		redirect(303, '/login');
	}

	if (!response.ok) {
		error(502, 'Could not retrieve two-factor authentication status.');
	}

	const result: { enabled: boolean } = await response.json();

	return {
		twoFactorEnabled: result.enabled
	};
};

type TwoFactorAction = 'enable' | 'disable';

function getAction(data: FormData): TwoFactorAction | null {
	const action = data.get('action');

	return action === 'enable' || action === 'disable' ? action : null;
}

export const actions = {
	requestCode: async ({ request, fetch, cookies }) => {
		if (!cookies.get(SESSION_COOKIE)) {
			redirect(303, '/login');
		}

		if (!cookies.get(CSRF_COOKIE)) {
			return fail(403, {
				step: null,
				action: null,
				error: 'CSRF token missing. Please log in again.'
			});
		}

		const data = await request.formData();
		const action = getAction(data);

		if (!action) {
			return fail(400, {
				step: null,
				action: null,
				error: 'Invalid two-factor authentication action.'
			});
		}

		let response: Response;

		try {
			response = await fetch(api('/auth/2fa/code'), jsonPost({ action }));
		} catch {
			return fail(502, {
				step: null,
				action,
				error: 'Cannot connect to the server. Please try again.'
			});
		}

		if (response.status === 401) {
			redirect(303, '/login');
		}

		if (!response.ok) {
			return fail(response.status, {
				step: null,
				action,
				error: await errorMessage(response, 'Something went wrong. Please try again.')
			});
		}

		return {
			step: 'code',
			action,
			error: null
		};
	},

	confirmCode: async ({ request, fetch, cookies }) => {
		if (!cookies.get(SESSION_COOKIE)) {
			redirect(303, '/login');
		}

		if (!cookies.get(CSRF_COOKIE)) {
			return fail(403, {
				step: null,
				action: null,
				error: 'CSRF token missing. Please log in again.'
			});
		}

		const data = await request.formData();
		const action = getAction(data);

		if (!action) {
			return fail(400, {
				step: null,
				action: null,
				error: 'Invalid two-factor authentication action.'
			});
		}

		const code = String(data.get('code') ?? '');
		const result = v.safeParse(twoFactorCodeSchema, { code });

		if (!result.success) {
			return fail(400, {
				step: 'code',
				action,
				error: result.issues[0].message
			});
		}

		let response: Response;

		try {
			response = await fetch(api(`/auth/2fa/${action}`), jsonPost(result.output));
		} catch {
			return fail(502, {
				step: 'code',
				action,
				error: 'Cannot connect to the server. Please try again.'
			});
		}

		if (response.status === 401) {
			redirect(303, '/login');
		}

		if (!response.ok) {
			return fail(response.status, {
				step: 'code',
				action,
				error: await errorMessage(response, 'Something went wrong. Please try again.')
			});
		}

		redirect(303, '/settings?two_factor_updated=1');
	}
} satisfies Actions;
