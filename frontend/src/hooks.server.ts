import type { Handle, HandleFetch } from '@sveltejs/kit/hooks';
import { BACKEND_URL } from '$app/env/private';
import { PUBLIC_BACKEND_URL } from '$app/env/public';
import { CSRF_COOKIE } from '#lib/server/api.ts';

const backendOrigin = new URL(BACKEND_URL).origin;
const safeMethods = ['GET', 'HEAD', 'OPTIONS', 'TRACE'];

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
	if (request.url.startsWith(PUBLIC_BACKEND_URL)) {
		request = new Request(request.url.replace(PUBLIC_BACKEND_URL, BACKEND_URL), request);
	}

	const target = new URL(request.url);

	if (target.origin !== backendOrigin || !target.pathname.startsWith('/api/v1/')) {
		return fetch(request);
	}

	const browserCookies = event.request.headers.get('cookie');
	if (browserCookies) {
		request.headers.set('cookie', browserCookies);
	}

	if (!safeMethods.includes(request.method.toUpperCase())) {
		const csrfToken = event.cookies.get(CSRF_COOKIE);
		if (csrfToken) {
			request.headers.set('X-CSRF-Token', csrfToken);
		}
	}

	return fetch(request);
};

/** Hook to handle user auth */
export const handle: Handle = async ({ event, resolve }) => {
	// Skip the backend call if the browser sent no cookies at all
	if (!event.request.headers.get('cookie')) {
		event.locals.user = null;
		return resolve(event);
	}

	const res = await event.fetch(`${PUBLIC_BACKEND_URL}/api/v1/users/me`);
	event.locals.user = res.ok ? await res.json() : null;

	return resolve(event);
};
