import { enhancedImages } from '@sveltejs/enhanced-img';
import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-auto';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

// Node's process, without needing @types/node.
const env = (globalThis as { process?: { env: Record<string, string | undefined> } }).process?.env;
const backendUrl = env?.BACKEND_URL ?? 'http://localhost:8000';

export default defineConfig({
	plugins: [
		enhancedImages(),
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// adapter-auto only supports some environments, see https://svelte.dev/docs/kit/adapter-auto for a list.
			// If your environment is not supported, or you settled on a specific environment, switch out the adapter.
			// See https://svelte.dev/docs/kit/adapters for more information about adapters.
			adapter: adapter()
		})
	],
	test: {
		include: ['src/**/*.test.ts']
	},
	server: {
		// The browser talks to the backend through Vite, on the same origin, so the
		// session cookie and the match socket just work. Docker sets BACKEND_URL.
		proxy: {
			'/api': {
				target: backendUrl,
				ws: true
			}
		}
	}
});
