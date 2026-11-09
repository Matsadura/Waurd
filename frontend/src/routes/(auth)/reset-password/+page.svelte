<script lang="ts">
	import FormField from '#lib/components/auth/FormField.svelte';
	import AuthButton from '#lib/components/auth/AuthButton.svelte';

	type ResetStatus = 'ready' | 'loading' | 'success';

	let status = $state<ResetStatus>('ready');
	let email = $state('');

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();

		status = 'loading';

		await new Promise<void>((resolve) => {
			setTimeout(resolve, 1200);
		});

		status = 'success';
	}

	// function handleSubmit(event: SubmitEvent) {
	//     event.preventDefault();
	//     // TODO: reset-password API
	// }
</script>

<svelte:head>
	<title>Reset Password</title>
</svelte:head>

<form class="flex w-full flex-col items-center" onsubmit={handleSubmit}>
	{#if status !== 'success'}
		<div class="flex w-full flex-col items-center" class:loading={status === 'loading'}>
			<FormField label="Email" name="email" type="email" autocomplete="email" bind:value={email} />

			<AuthButton class="mt-12 mb-2" disabled={status === 'loading'}>Reset Password</AuthButton>
		</div>

		{#if status === 'loading'}
			<div class="mt-4 flex justify-center sm:mt-6" role="status">
				<div class="spinner"></div>
				<span class="sr-only">Sending password reset request...</span>
			</div>
		{/if}
	{:else}
		<p class="mt-8 text-center text-base font-bold text-[#00d66b] sm:text-lg" role="status">
			*If your email address exists in our database, you will receive a password recovery link at
			your email address in a few minutes.
		</p>
	{/if}
</form>

<style>
	.spinner {
		width: 32px;
		height: 32px;
		border: 4px solid rgba(255, 255, 255, 0.25);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
