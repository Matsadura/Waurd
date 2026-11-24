<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import { PUBLIC_BACKEND_URL } from '$app/env/public';
	import Button from '#lib/components/ui/Button.svelte';

	let { data } = $props();
	let pollError = $state('');
	let leaving = $state(false);

	$effect(() => {
		let cancelled = false;

		async function poll() {
			try {
				const res = await fetch(`${PUBLIC_BACKEND_URL}/api/v1/matchmaking/status`, {
					credentials: 'include'
				});

				if (cancelled) return;

				if (res.status === 404) {
					await goto('/play');
					return;
				}

				if (!res.ok) {
					pollError = `Connection issue (HTTP ${res.status})`;
					return;
				}

				pollError = '';
				const ticket = await res.json();
				if (ticket.matched_match_id) {
					await goto(`/match/${ticket.matched_match_id}`);
				}
			} catch {
				if (!cancelled) pollError = 'Cannot reach the server. Retrying...';
			}
		}

		const interval = setInterval(poll, 1000);
		return () => {
			cancelled = true;
			clearInterval(interval);
		};
	});
</script>

<p>Searching for an opponent ({data.ticket.time_control_seconds}s)...</p>

{#if pollError}
	<p class="text-red-400">{pollError}</p>
{/if}

<form
	method="POST"
	use:enhance={() => {
		leaving = true;
		return async ({ update }) => {
			leaving = false;
			await update();
		};
	}}
>
	<input type="hidden" name="time_control_seconds" value={data.ticket.time_control_seconds} />
	<Button variant="danger" type="submit" disabled={leaving}>
		{leaving ? 'Leaving...' : 'Leave Queue'}
	</Button>
</form>
