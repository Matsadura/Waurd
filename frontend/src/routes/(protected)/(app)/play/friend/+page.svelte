<script lang="ts">
	import { goto } from '$app/navigation';
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import { APIFetch } from '#lib/utils/APIFetch.js';
	import Spinner from '#lib/components/ui/Spinner.svelte';
	import { enhance, type SubmitFunction } from '$app/forms';

	let { data, form } = $props();
	let pollError = $state('');

	$effect(() => {
		let cancelled = false;

		async function poll() {
			try {
				const res = await APIFetch('GET', `/matchmaking/matches/${data.match.id}`);

				if (!cancelled) {
					if (!res.ok) {
						await goto('/play');
					} else {
						pollError = '';
						const match = await res.json();

						if (match.status === 'ACTIVE') {
							await goto('/battle/arena');
						} else if (match.status !== 'WAITING') {
							await goto('/play');
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
	<title>Private Game</title>
</svelte:head>

<div class="mx-auto w-full max-w-md px-3 py-10 font-body text-bone sm:px-4">
	<Frame class="text-center">
		<h1 class="font-display text-3xl">Private Game</h1>
		<p class="mt-2 text-lg text-ash">Share this code with your friend...</p>

		<Frame variant="double-border" class="mx-auto mt-6 inline-block px-8 py-4">
			<span class="font-mono text-4xl tracking-[0.3em] text-bone">
				{data.match.invite_code}
			</span>
		</Frame>

		<p class="mt-4 font-body text-lg">
			<span class="font-bold text-success"
				>{Math.floor(data.match.time_control_seconds / 60)} min
			</span> &middot; Waiting for opponent...
		</p>

		<Spinner size="lg" disabled={panding} class="mt-6 border-primary-light" />

		{#if form?.error}
			<Notice variant="danger" class="mt-4 text-left">{form.error}</Notice>
		{:else if pollError}
			<Notice variant="warning" class="mt-4 text-left">{pollError}</Notice>
		{/if}

		<Divider class="my-6" />

		<form method="POST" action="?/cancel" use:enhance={submit()}>
			<input type="hidden" name="match_id" value={data.match.id} />
			<Button variant="danger" outline loading={panding} type="submit" class="w-full">
				Cancel Game
			</Button>
		</form>
	</Frame>
</div>
