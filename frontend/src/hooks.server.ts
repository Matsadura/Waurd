import { BACKEND_URL } from '$app/env/private';
import type { HandleFetch } from '@sveltejs/kit/hooks';
import { CSRF_COOKIE } from '#lib/server/api.ts';

const backendOrigin = new URL(BACKEND_URL).origin;
const safeMethods = ['GET', 'HEAD', 'OPTIONS', 'TRACE'];

export const handleFetch: HandleFetch = ({ event, request, fetch }) => {
	const target = new URL(request.url);

	if (target.origin !== backendOrigin || !target.pathname.startsWith('/api/v1/')) {
		return fetch(request);//If this request isn't going to the Waurd API, leave it alone
	}

	const browserCookies = event.request.headers.get('cookie');//the incoming browser cookies

	if (browserCookies) {
		request.headers.set('cookie', browserCookies);//the headers of the outgoing FastAPI request
	}

	if (!safeMethods.includes(request.method)) {
		const csrfToken = event.cookies.get(CSRF_COOKIE);

		if (csrfToken) {
			request.headers.set('X-CSRF-Token', csrfToken);
		}
	}

	return fetch(request);//Now send this request to its destination
};
