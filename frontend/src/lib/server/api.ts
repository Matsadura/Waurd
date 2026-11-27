import { BACKEND_URL } from '$app/env/private';
import type { Cookies } from '@sveltejs/kit';

// Cookie names shared with FastAPI
export const SESSION_COOKIE = 'session_id';
export const CSRF_COOKIE = 'csrf_token';
export const TWO_FACTOR_COOKIE = 'two_factor_token';

// Build a URL to our FastAPI backend
export function api(path: string): string {
	return `${BACKEND_URL}/api/v1${path}`;
}

// Prepare a JSON POST request
export function jsonPost(body: unknown): RequestInit {
	return {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	};
}

// Prepare a JSON PATCH request
export function jsonPatch(body: unknown): RequestInit {
	return {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	};
}

// Extract FastAPI's error message
export async function errorMessage(response: Response, fallback: string): Promise<string> {
	const json: unknown = await response.json().catch(() => null);

	if (
		typeof json === 'object' &&
		json !== null &&
		'detail' in json &&
		typeof json.detail === 'string'
	) {
		return json.detail;
	}

	return fallback;
}

// Apply FastAPI's Set-Cookie headers to the browser response
export function forwardCookies(
	response: Response,
	cookies: Cookies,
	requiredNames: string[] = []
): boolean {
	const setCookieHeaders = response.headers.getSetCookie();
	const parsed = setCookieHeaders.map((rawCookie) => cookies.parse(rawCookie));
	//const parsed = response.headers.getSetCookie().map((header) => cookies.parse(header)); //.map goes through every element, transforms it, and returns a NEW array.

	const valid = requiredNames.every(
		(name) => parsed.some((cookie) => cookie.name === name && Boolean(cookie.value)) //check that the response includes the required cookies with nonempty values
	);

	if (!valid) return false;

	for (const { name, value, ...options } of parsed) {
		cookies.set(name, value ?? '', {
			...options,
			httpOnly: options.httpOnly ?? false,
			secure: options.secure ?? false,
			encode: (cookieValue) => cookieValue
		});
	}

	return true;
}
