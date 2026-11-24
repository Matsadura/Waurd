import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './login/$types';

export const load: PageServerLoad = async ({ locals }) => {
	if (locals.user) {
		redirect(302, '/play');
	}
};
