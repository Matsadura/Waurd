<script lang="ts">
	import { enhance, type SubmitFunction } from '$app/forms';
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import { fade } from 'svelte/transition';

	let { data, form } = $props();
	let pending = $state<string | null>(null);

	const timeControls = [
		{ seconds: 180, label: '3 min', pace: 'Blitz' },
		{ seconds: 300, label: '5 min', pace: 'Standard' },
		{ seconds: 600, label: '10 min', pace: 'Relaxed' }
	];

	function submit(key: string): SubmitFunction {
		return () => {
			pending = key;
			return async ({ update }) => {
				try {
					await update();
				} finally {
					pending = null;
				}
			};
		};
	}
</script>

<svelte:head>
	<title>Play</title>
</svelte:head>

<div class="mx-auto w-full max-w-5xl px-3 py-6 font-body text-bone sm:px-4">
	<Frame>
		<header>
			<h1 class="font-display text-3xl sm:text-4xl">Enter the Arena</h1>
		</header>

		{#if data.statusError}
			<div in:fade>
				<Notice variant="danger" class="mt-4">{data.statusError}</Notice>
			</div>
		{:else if form?.error}
			<div in:fade>
				<Notice variant="danger" class="mt-4">{form.error}</Notice>
			</div>
		{/if}

		<Divider class="my-6" />

		<div class="grid items-start gap-8 lg:grid-cols-[1fr_20rem]">
			<div>
				<section>
					<h2 id="quick-match" class="font-display text-2xl">Quick Match</h2>
					<p class="mt-1 text-base text-lg text-secondary-light">
						Join the queue to play a random opponent
					</p>

					<div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
						{#each timeControls as tc (tc.seconds)}
							<form method="POST" action="?/queue" use:enhance={submit(`queue-${tc.seconds}`)}>
								<input type="hidden" name="time_control_seconds" value={tc.seconds} />
								<Button
									type="submit"
									variant="primary"
									outline
									size="lg"
									loading={pending === `queue-${tc.seconds}`}
									disabled={pending !== null}
									class="flex h-36 w-full flex-col items-center justify-center gap-1"
								>
									<span class="font-display text-3xl text-bone">{tc.label}</span>
									<span class="text-sm tracking-widest uppercase">{tc.pace}</span>
								</Button>
							</form>
						{/each}
					</div>
				</section>

				<Divider class="my-6" />

				<section>
					<h2 id="private-game" class="font-display text-2xl">Private Game</h2>
					<p class="mt-1 text-base text-lg text-secondary-light">
						Create a private game and share the invite code with your friend
					</p>

					<div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
						{#each timeControls as tc (tc.seconds)}
							<form method="POST" action="?/private" use:enhance={submit(`private-${tc.seconds}`)}>
								<input type="hidden" name="time_control_seconds" value={tc.seconds} />
								<Button
									type="submit"
									variant="secondary"
									outline
									size="lg"
									loading={pending === `private-${tc.seconds}`}
									disabled={pending !== null}
									class="flex h-36 w-full flex-col items-center justify-center gap-1"
								>
									<span class="font-display text-3xl text-bone">{tc.label}</span>
									<span class="text-sm tracking-widest uppercase">{tc.pace}</span>
								</Button>
							</form>
						{/each}
					</div>
				</section>
			</div>

			<Frame variant="double-border" as="aside">
				<Frame variant="border" class="font-display text-lg">
					<h2 id="join-private">Join by Code</h2>
				</Frame>

				<form method="POST" action="?/join" use:enhance={submit('join')} class="mt-5 space-y-6">
					<div>
						<label for="invite-code" class="field-label mb-2 block">Invite code</label>
						<input
							id="invite-code"
							type="text"
							name="invite_code"
							placeholder="TCA999"
							maxlength="6"
							required
							class="field font-mono tracking-widest uppercase placeholder:tracking-normal placeholder:normal-case"
						/>
					</div>

					<Button
						type="submit"
						variant="primary"
						size="lg"
						loading={pending === 'join'}
						disabled={pending !== null}
						class="mt-4 w-full"
					>
						Join Private Game
					</Button>
				</form>
			</Frame>
		</div>
	</Frame>
</div>
