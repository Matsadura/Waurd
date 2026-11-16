<script lang="ts">
	import { page } from '$app/state';
	import FormField from '#lib/components/auth/FormField.svelte';
	import AuthButton from '#lib/components/auth/AuthButton.svelte';
	import type { ActionData } from './$types';

	let { form }: { form: ActionData | null } = $props();

	let email = $derived(form?.values?.email ?? '');

	let newPassword = $state('');
	let confirmPassword = $state('');

	let token = $derived(page.url.searchParams.get('token') ?? '');
	let resetSuccess = $derived(page.url.searchParams.get('success') === '1');
</script>

<svelte:head>
	<title>Reset Password</title>
</svelte:head>

{#if resetSuccess}
	<div class="flex w-full flex-col items-center gap-5 text-center">
		<p class="mt-8 text-base font-bold text-[#00d66b] sm:text-lg" role="status">
			*Your password has been updated successfully!
		</p>

		<a href="/login" class="text-lg font-bold text-accent-action hover:underline">
			BACK TO LOGIN
		</a>
	</div>

{:else if token}
	<form
		method="POST"
		action={`?/reset&token=${encodeURIComponent(token)}`}
		class="flex w-full flex-col items-center"
	>
		<FormField
			label="New Password"
			name="newPassword"
			type="password"
			autocomplete="new-password"
			bind:value={newPassword}
		/>

		<FormField
			label="Confirm Password"
			name="confirmPassword"
			type="password"
			autocomplete="new-password"
			bind:value={confirmPassword}
			class="mt-3 sm:mt-5"
		/>

		<AuthButton class="mt-12 mb-2">CHANGE PASSWORD</AuthButton>

		<p
			class="mt-2 min-h-5 text-center text-base text-[#ff0000] sm:mt-3 sm:text-lg"
			role="alert"
		>
			{#if form?.error}
				*{form.error}
			{/if}
		</p>
	</form>

{:else}
	<form method="POST" action="?/request" class="flex w-full flex-col items-center">
		{#if form?.sent}
			<p class="mt-8 text-center text-base font-bold text-[#00d66b] sm:text-lg" role="status">
				*If your email address exists in our database, you will receive a password
				recovery link at your email address in a few minutes.
			</p>
		{:else}
			<FormField
				label="Email"
				name="email"
				type="email"
				autocomplete="email"
				bind:value={email}
			/>

			<AuthButton class="mt-12 mb-2">Reset Password</AuthButton>

			<p
				class="mt-2 min-h-5 text-center text-base text-[#ff0000] sm:mt-3 sm:text-lg"
				role="alert"
			>
				{#if form?.error}
					*{form.error}
				{/if}
			</p>
		{/if}
	</form>
{/if}