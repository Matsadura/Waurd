import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	BACKEND_URL: {},
	PUBLIC_BACKEND_URL: { public: true }
});