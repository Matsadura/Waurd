<script lang="ts">
	import { page } from '$app/state';
	import AuthTitle from '#lib/components/auth/AuthTitle.svelte';
	import FormField from '#lib/components/auth/FormField.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
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

<AuthTitle>Reset Password</AuthTitle>

{#if resetSuccess}
	<div class="flex flex-col items-center gap-5 text-center">
		<p class="text-lg text-success-light" role="status">
			Your password has been updated successfully!
		</p>

		<a href="/login" class="text-lg text-ash hover:text-bone hover:underline"> Back to Login </a>
	</div>
{:else if token}
	<form
		method="POST"
		action={`?/reset&token=${encodeURIComponent(token)}`}
		class="flex flex-col gap-5"
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
		/>

		<Button type="submit" size="lg" class="w-full">Change Password</Button>

		{#if form?.error}
			<Notice>{form.error}</Notice>
		{/if}
	</form>
{:else}
	{#if form?.sent}
		<p class="text-center text-lg text-success-light" role="status">
			If an account with that email exists, you will receive a password reset link shortly.
		</p>
	{:else}
		<form method="POST" action="?/request" class="flex flex-col gap-5">
			<FormField label="Email" name="email" type="email" autocomplete="email" bind:value={email} />

			<Button type="submit" size="lg" class="w-full">Reset Password</Button>

			{#if form?.error}
				<Notice>{form.error}</Notice>
			{/if}
		</form>
	{/if}
{/if}
