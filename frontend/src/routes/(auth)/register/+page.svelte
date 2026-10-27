<script lang="ts">
	import FormField from '#lib/components/auth/FormField.svelte';
	import AuthButton from '#lib/components/auth/AuthButton.svelte';
	import SocialLogin from '#lib/components/auth/SocialLogin.svelte';

	let email = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let termsAccepted = $state(false);
	let showTermsError = $state(false);

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();

		if (!termsAccepted) {
			showTermsError = true;
			return;
		}
		showTermsError = false;
		// TODO: register API
	}

	function handleGoogle() {
		// TODO: google sign-in
	}
</script>

<svelte:head>
	<title>Register</title>
</svelte:head>

<form class="flex w-full flex-col" onsubmit={handleSubmit}>
	<FormField label="Email" name="email" type="email" autocomplete="email" bind:value={email} />

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
	<div class="mt-4 flex items-center justify-center gap-2 text-sm sm:mt-6">
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

	<AuthButton class="mt-4 sm:mt-6">REGISTER</AuthButton>

	<p class="mt-2 min-h-5 text-center text-base text-[#ff0000] sm:mt-3 sm:text-lg" role="alert">
		{#if showTermsError}
			*You must accept our Terms of Service
		{/if}
	</p>

	<SocialLogin ongoogle={handleGoogle} />
</form>
