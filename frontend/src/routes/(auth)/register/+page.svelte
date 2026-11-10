<script lang="ts">
	import FormField from '#lib/components/auth/FormField.svelte';
	import AuthButton from '#lib/components/auth/AuthButton.svelte';
	import SocialLogin from '#lib/components/auth/SocialLogin.svelte';
	import type { ActionData } from './$types';

	let { form }: { form: ActionData | null } = $props();

	let username = $derived(form?.values.username ?? '');
	let email = $derived(form?.values.email ?? '');
	let password = $state('');
	let confirmPassword = $state('');
	let termsAccepted = $state(false);

	function handleGoogle() {
		// TODO: google sign-in
	}
</script>

<svelte:head>
	<title>Register</title>
</svelte:head>

<form method="POST" class="flex w-full flex-col items-center">
	<FormField
		label="Username"
		name="username"
		type="text"
		autocomplete="username"
		bind:value={username}
	/>

	<FormField
		label="Email"
		name="email"
		type="email"
		autocomplete="email"
		bind:value={email}
		class="mt-3 sm:mt-5"
	/>

	<FormField
		label="Password"
		name="password"
		type="password"
		autocomplete="new-password"
		bind:value={password}
		class="mt-3 sm:mt-5"
	/>

	<FormField
		label="Confirm Password"
		name="confirm-password"
		type="password"
		autocomplete="new-password"
		bind:value={confirmPassword}
		class="mt-3 sm:mt-5"
	/>

	<!-- Terms of Service -->
	<div class="mt-6 flex items-center justify-center gap-2 text-sm">
		<input
			id="terms"
			name="terms"
			type="checkbox"
			bind:checked={termsAccepted}
			class="size-5 cursor-pointer accent-accent-action"
		/>

		<label for="terms" class="cursor-pointer text-white">
			I agree to all
			<a
				href="/terms"
				target="_blank"
				rel="noopener noreferrer"
				class="font-bold underline"
				onclick={(event) => event.stopPropagation()}
			>
				Terms of Service
			</a>
		</label>
	</div>

	<AuthButton class="mt-12 mb-2">REGISTER</AuthButton>

	<p class="mt-2 mb-2 min-h-5 text-center text-base text-[#ff0000] sm:mt-3 sm:text-lg" role="alert">
		{#if form?.error}
			*{form?.error}
		{/if}
	</p>

	<SocialLogin ongoogle={handleGoogle} />
</form>
