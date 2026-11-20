// The REST helper: CSRF header, errors.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from './api.ts';

function respond(status: number, body: unknown) {
	const fetch = vi
		.fn()
		.mockResolvedValue(
			new Response(body === null ? null : JSON.stringify(body), { status, statusText: 'Status' })
		);
	vi.stubGlobal('fetch', fetch);
	return fetch;
}

afterEach(() => vi.unstubAllGlobals());

describe('api', () => {
	it('sends JSON with the CSRF token from the cookie', async () => {
		vi.stubGlobal('document', { cookie: 'session_id=x; csrf_token=abc%3D' });
		const fetch = respond(201, { id: '1' });

		const result = await api('/matchmaking/queue', {
			method: 'POST',
			body: { time_control_seconds: 300 }
		});

		expect(result).toEqual({ id: '1' });
		const [url, init] = fetch.mock.calls[0];
		expect(url).toBe('/api/v1/matchmaking/queue');
		expect(init.headers).toEqual({ 'Content-Type': 'application/json', 'X-CSRF-Token': 'abc=' });
		expect(init.body).toBe('{"time_control_seconds":300}');
	});

	it('does not send a CSRF token on GET', async () => {
		vi.stubGlobal('document', { cookie: 'csrf_token=abc' });
		const fetch = respond(200, {});

		await api('/users/me');

		expect(fetch.mock.calls[0][1].headers).toEqual({});
	});

	it('throws the server’s message', async () => {
		vi.stubGlobal('document', { cookie: '' });
		respond(400, { detail: 'Please leave the matchmaking queue first.' });

		const error = (await api('/x', { method: 'POST' }).catch((e: unknown) => e)) as ApiError;

		expect(error).toBeInstanceOf(ApiError);
		expect(error.status).toBe(400);
		expect(error.message).toBe('Please leave the matchmaking queue first.');
	});

	it('handles an empty 204', async () => {
		vi.stubGlobal('document', { cookie: '' });
		respond(204, null);

		expect(await api('/auth/logout', { method: 'POST' })).toBeNull();
	});
});
