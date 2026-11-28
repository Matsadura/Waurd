import { PUBLIC_BACKEND_URL } from '$app/env/public';
import { redirect } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = ({ locals }) => {
	if (!locals.user) {
		redirect(303, '/login');
	}

	const me = locals.user;

	return {
		profile: {
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
