import { redirect } from '@sveltejs/kit';
import { SESSION_COOKIE, TWO_FACTOR_COOKIE } from '#lib/server/api.ts';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = ({ url, cookies }) => {
	const needsTwoFactor = url.searchParams.get('two_factor') === 'required';

	if (needsTwoFactor) {
		if (!cookies.get(TWO_FACTOR_COOKIE)) {
			redirect(303, '/login');
		}

		redirect(303, '/verify-2fa');
	}

	if (!cookies.get(SESSION_COOKIE)) {
		redirect(303, '/login');
	}

	redirect(303, '/play');
};
