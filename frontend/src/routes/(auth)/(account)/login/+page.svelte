<script lang="ts">
	import FormField from '#lib/components/auth/FormField.svelte';
	import SocialLogin from '#lib/components/auth/SocialLogin.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import { PUBLIC_BACKEND_URL } from '$app/env/public';
	import type { ActionData } from './$types';
	import { page } from '$app/state';

	let { form }: { form: ActionData | null } = $props();

	let email = $derived(form?.values?.email ?? '');
	let password = $state('');

	const googleErrorMessages = new Map<string, string>([
		['cancelled', 'Google sign-in was cancelled.'],
		['invalid_state', 'That sign-in attempt expired. Please try again.'],
		['not_configured', 'Google sign-in is not available right now.'],
		['google_failed', 'Google authentication failed. Please try again.'],
		['email_not_verified', 'Your Google account does not have a verified email.'],
		['account_exists', 'An account with this email already exists.'],
		['cooldown', 'A code was sent recently. Wait a minute before trying again.']
	]);

	let googleError = $derived.by(() => {
		const code = page.url.searchParams.get('google_error');
		if (!code) return null;
		return googleErrorMessages.get(code) ?? 'Google sign-in failed. Please try again.';
	});

	// The settings page sends people here after they change their username, email or password
	let accountUpdated = $derived(page.url.searchParams.get('account_updated') === '1');

	function handleGoogle() {
		window.location.assign(`${PUBLIC_BACKEND_URL}/api/v1/auth/google`);
	}
</script>

<svelte:head>
	<title>Login</title>
</svelte:head>

<form method="POST" class="flex flex-col gap-5">
	<FormField label="Email" name="email" type="email" autocomplete="email" bind:value={email} />
	<div class="flex flex-col gap-2">
		<FormField
			label="Password"
			name="password"
			type="password"
			autocomplete="current-password"
			bind:value={password}
		/>

		<a
			href="/reset-password"
			class="self-end text-base text-ash underline-offset-4 transition-colors
			hover:text-bone hover:underline
			focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bone"
		>
			Forgot password?
		</a>
	</div>

	<Button type="submit" size="lg" class="mt-2 w-full">Login</Button>

	{#if accountUpdated && !form?.error}
		<Notice variant="success">Your account was updated. Please log in again.</Notice>
	{/if}

	{#if form?.error || googleError}
		<Notice>{form?.error ?? googleError}</Notice>
	{/if}

	<SocialLogin ongoogle={handleGoogle} />
</form>