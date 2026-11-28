<script lang="ts">
	import { goto } from '$app/navigation';
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import { enhance, type SubmitFunction } from '$app/forms';
	import Spinner from '#lib/components/ui/Spinner.svelte';
	import { APIFetch } from '#lib/utils/APIFetch.js';

	let { data, form } = $props();
	let pollError = $state('');

	$effect(() => {
		let cancelled = false;

		async function poll() {
			try {
				const res = await APIFetch('GET', '/matchmaking/status');

				if (!cancelled) {
					if (res.status === 404) {
						await goto('/play');
					} else if (!res.ok) {
						pollError = `Connection issue (HTTP ${res.status})`;
					} else {
						pollError = '';
						const ticket = await res.json();

						if (
							(ticket.status === 'MATCHED' || ticket.status === 'ACTIVE') &&
							ticket.matched_match_id
						) {
							await goto('/battle/arena');
						} else if (ticket.status === 'WAITING') {
							await goto('/play/friend');
						}
					}
				}
			} catch {
				if (!cancelled) {
					pollError = 'Cannot reach the server. Retrying...';
				}
			}
		}

		const interval = setInterval(poll, 2000);
		return () => {
			cancelled = true;
			clearInterval(interval);
		};
	});

	let panding = $state(false);
	function submit(): SubmitFunction {
		return () => {
			panding = true;
			return async ({ update }) => {
				await update();
			};
		};
	}
</script>

<svelte:head>
	<title>Searching for Opponent</title>
</svelte:head>

<div class="mx-auto w-full max-w-md px-3 py-10 font-body text-bone sm:px-4">
	<Frame class="fade-in text-center">
		<h1 class="font-display text-3xl">Searching for opponent...</h1>
		<p class="mt-4 font-body text-lg">
			<span class="font-bold text-success"
				>{Math.floor(data.ticket.time_control_seconds / 60)} min
			</span> &middot; Finding an opponent...
		</p>

		<Spinner disabled={panding} size="lg" class="mt-6 border-primary-light" />

		{#if form?.error}
			<Notice variant="danger" class="mt-4 text-left">{form.error}</Notice>
		{:else if pollError}
			<Notice variant="warning" class="mt-4 text-left">{pollError}</Notice>
		{/if}

		<Divider class="my-6" />

		<form method="POST" use:enhance={submit()}>
			<input type="hidden" name="time_control_seconds" value={data.ticket.time_control_seconds} />
			<Button variant="danger" loading={panding} outline type="submit" class="w-full">
				Leave Queue
			</Button>
		</form>
	</Frame>
</div>
