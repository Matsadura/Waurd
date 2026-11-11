<script lang="ts">
	import FormField from '#lib/components/auth/FormField.svelte';
	import AuthButton from '#lib/components/auth/AuthButton.svelte';
	import SocialLogin from '#lib/components/auth/SocialLogin.svelte';
	import type { ActionData } from './$types';

	let { form }: { form: ActionData | null } = $props();

	let email = $derived(form?.values?.email ?? '');
	let password = $state('');

	function handleGoogle() {
		// TODO: google sign-in
	}
</script>

<svelte:head>
	<title>Login</title>
</svelte:head>

<form method="POST" class="flex w-full flex-col items-center">
	<FormField label="Email" name="email" type="email" autocomplete="email" bind:value={email} />

	<FormField
		label="Password"
		name="password"
		type="password"
		autocomplete="current-password"
		bind:value={password}
		class="mt-3 sm:mt-5"
	/>

	<AuthButton class="mt-12 mb-2">LOGIN</AuthButton>

	<p class="mt-2 min-h-5 text-center text-base text-[#ff0000] sm:mt-3 sm:text-lg" role="alert">
		{#if form?.error}
			*{form.error}
		{/if}
	</p>

	<SocialLogin ongoogle={handleGoogle} />
</form>
