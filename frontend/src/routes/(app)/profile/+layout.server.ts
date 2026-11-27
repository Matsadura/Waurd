import { PUBLIC_BACKEND_URL } from '$app/env/public';
import { error, redirect } from '@sveltejs/kit';
import { api, SESSION_COOKIE } from '#lib/server/api.ts';
import type { LayoutServerLoad } from './$types';

type UserResponse = {
	id: string;
	username: string;
	avatar_url: string | null;
	level: number;
	created_at: string;
	xp_into_level: number;
	xp_for_next_level: number;
};

export const load: LayoutServerLoad = async ({ cookies, fetch }) => {
	if (!cookies.get(SESSION_COOKIE)) {
		redirect(303, '/login');
	}

	let response: Response;

	try {
		response = await fetch(api('/users/me'));
	} catch {
		error(502, 'Cannot connect to the backend.');
	}

	if (response.status === 401) {
		redirect(303, '/login');
	}

	if (!response.ok) {
		error(502, 'Could not retrieve your profile.');
	}

	const me: UserResponse = await response.json();

	return {
		user: {
			id: me.id,
			username: me.username,
			level: me.level,
			avatarUrl: me.avatar_url?.startsWith('/')
				? `${PUBLIC_BACKEND_URL}${me.avatar_url}`
				: me.avatar_url,

			xpIntoLevel: me.xp_into_level,
			xpForNextLevel: me.xp_for_next_level,
			joined: new Date(me.created_at).toLocaleDateString('en-US', {
				month: 'short',
				day: 'numeric',
				year: 'numeric'
			})
		}
	};
};
