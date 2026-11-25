<script lang="ts">
	import FormField from '#lib/components/auth/FormField.svelte';
	import SocialLogin from '#lib/components/auth/SocialLogin.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Checkbox from '#lib/components/ui/Checkbox.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import { PUBLIC_BACKEND_URL } from '$app/env/public';
	import type { ActionData } from './$types';

	let { form }: { form: ActionData | null } = $props();

	let username = $derived(form?.values.username ?? '');
	let email = $derived(form?.values.email ?? '');
	let password = $state('');
	let confirmPassword = $state('');
	let termsAccepted = $state(false);

	function handleGoogle() {
		window.location.assign(`${PUBLIC_BACKEND_URL}/api/v1/auth/google`);
	}
</script>

<svelte:head>
	<title>Register</title>
</svelte:head>

<form method="POST" class="flex flex-col gap-5">
	<FormField
		label="Username"
		name="username"
		type="text"
		autocomplete="username"
		bind:value={username}
	/>
	<FormField label="Email" name="email" type="email" autocomplete="email" bind:value={email} />
	<FormField
		label="Password"
		name="password"
		type="password"
		autocomplete="new-password"
		bind:value={password}
	/>
	<FormField
		label="Confirm Password"
		name="confirm-password"
		type="password"
		autocomplete="new-password"
		bind:value={confirmPassword}
	/>

	<Checkbox name="terms" required bind:checked={termsAccepted}>
		I agree to the
		<a
			href="/terms"
			target="_blank"
			rel="noopener noreferrer"
			class="text-primary-light underline underline-offset-4 transition-colors hover:text-bone"
		>
			Terms of Service
		</a>
	</Checkbox>

	<Button type="submit" size="lg" class="mt-2 w-full">Register</Button>

	{#if form?.error}
		<Notice>{form.error}</Notice>
	{/if}

	<SocialLogin ongoogle={handleGoogle} />
</form>
