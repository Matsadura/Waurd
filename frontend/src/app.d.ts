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
			// add other public fields returned by /api/v1/users/me
		}

		interface Locals {
			user: User | null;
		}
	}
}

export {};
