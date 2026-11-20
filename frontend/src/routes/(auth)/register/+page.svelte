<script lang="ts">
	import FormField from '#lib/components/auth/FormField.svelte';
	import AuthButton from '#lib/components/auth/AuthButton.svelte';
	import SocialLogin from '#lib/components/auth/SocialLogin.svelte';
	import { goto } from '$app/navigation';
	import { api } from '#lib/api.ts';
	import { loadUser } from '#lib/session.svelte.ts';

	let username = $state('');
	let email = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let termsAccepted = $state(false);
	let showTermsError = $state(false);
	let error = $state('');
	let busy = $state(false);

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		error = '';

		if (!termsAccepted) {
			showTermsError = true;
			return;
		}
		showTermsError = false;
		if (password !== confirmPassword) {
			error = "The passwords don't match.";
			return;
		}
		busy = true;
		try {
			await api('/auth/register', { method: 'POST', body: { username, email, password } });
			await api('/auth/login', { method: 'POST', body: { email, password } });
			await loadUser();
			await goto('/play');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Registration failed.';
		} finally {
			busy = false;
		}
	}

	function handleGoogle() {
		location.href = '/api/v1/auth/google';
	}
</script>

<svelte:head>
	<title>Register</title>
</svelte:head>

<form class="flex w-full flex-col items-center" onsubmit={handleSubmit}>
	<FormField label="Username" name="username" autocomplete="username" bind:value={username} />

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
			onchange={() => {
				if (termsAccepted) {
					showTermsError = false;
				}
			}}
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

	<AuthButton class="mt-12 mb-2" disabled={busy}>REGISTER</AuthButton>

	<p class="mt-2 mb-2 min-h-5 text-center text-base text-[#ff0000] sm:mt-3 sm:text-lg" role="alert">
		{#if showTermsError}
			*You must accept our Terms of Service
		{:else}
			{error}
		{/if}
	</p>

	<SocialLogin ongoogle={handleGoogle} />
</form>
