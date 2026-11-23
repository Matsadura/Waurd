<script lang="ts">
	import FormField from '#lib/components/auth/FormField.svelte';
	import SocialLogin from '#lib/components/auth/SocialLogin.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import { PUBLIC_BACKEND_URL } from '$app/env/public';
	import type { ActionData } from './$types';

	let { form }: { form: ActionData | null } = $props();

	let email = $derived(form?.values?.email ?? '');
	let password = $state('');

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

	{#if form?.error}
		<Notice>{form.error}</Notice>
	{/if}

	<SocialLogin ongoogle={handleGoogle} />
</form>
