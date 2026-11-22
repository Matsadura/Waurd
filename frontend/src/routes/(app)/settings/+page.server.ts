import { BACKEND_URL } from '$app/env/private';
import { error, fail, redirect } from '@sveltejs/kit';
import * as v from 'valibot';
import { twoFactorCodeSchema } from '#lib/schemas/two-factor.ts';
import type { Actions, PageServerLoad } from './$types';


export const load: PageServerLoad = async ({ cookies, fetch }) => {
	const sessionId = cookies.get('session_id');

	if (!sessionId) {
		redirect(303, '/login');
	}

	let response: Response;

	try {
		response = await fetch(`${BACKEND_URL}/api/v1/auth/2fa`, {
			headers: {
				Cookie: `session_id=${sessionId}`
			}
		});
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

function authHeaders(sessionId: string, csrfToken: string) {
	return {
		'Content-Type': 'application/json',
		Cookie: `session_id=${sessionId}; csrf_token=${csrfToken}`,
		'X-CSRF-Token': csrfToken
	};
}

async function extractError(response: Response): Promise<string> {
	const json = await response.json().catch(() => null);

	if (
		typeof json === 'object' &&
		json !== null &&
		'detail' in json &&
		typeof json.detail === 'string'
	) {
		return json.detail;
	}

	return 'Something went wrong. Please try again.';
}

export const actions = {
	requestCode: async ({ request, fetch, cookies }) => {
		const sessionId = cookies.get('session_id');
		const csrfToken = cookies.get('csrf_token');

		if (!sessionId) redirect(303, '/login');

		if (!csrfToken) {
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
			response = await fetch(`${BACKEND_URL}/api/v1/auth/2fa/code`, {
				method: 'POST',
				headers: authHeaders(sessionId, csrfToken),
				body: JSON.stringify({ action })
			});
		} catch {
			return fail(502, {
				step: null,
				action,
				error: 'Cannot connect to the server. Please try again.'
			});
		}

		if (response.status === 401) redirect(303, '/login');

		if (!response.ok) {
			return fail(response.status, {
				step: null,
				action,
				error: await extractError(response)
			});
		}

		return {
			step: 'code',
			action,
			error: null
		};
	},

	confirmCode: async ({ request, fetch, cookies }) => {
		const sessionId = cookies.get('session_id');
		const csrfToken = cookies.get('csrf_token');

		if (!sessionId) redirect(303, '/login');

		if (!csrfToken) {
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
			response = await fetch(`${BACKEND_URL}/api/v1/auth/2fa/${action}`, {
				method: 'POST',
				headers: authHeaders(sessionId, csrfToken),
				body: JSON.stringify(result.output)
			});
		} catch {
			return fail(502, {
				step: 'code',
				action,
				error: 'Cannot connect to the server. Please try again.'
			});
		}

		if (response.status === 401) redirect(303, '/login');

		if (!response.ok) {
			return fail(response.status, {
				step: 'code',
				action,
				error: await extractError(response)
			});
		}

		redirect(303, '/settings?two_factor_updated=1');
	}
} satisfies Actions;