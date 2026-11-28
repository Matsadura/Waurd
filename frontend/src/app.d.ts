// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
		interface User {
			id: string;
			username: string;
			avatar_url: string | null;
			created_at: string;
			level: number;
			xp_into_level: number;
			xp_for_next_level: number;
		}

		interface Locals {
			user: User | null;
		}
	}
}

export {};
