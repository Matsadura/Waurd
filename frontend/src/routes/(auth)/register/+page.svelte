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
	<title>Register — Waurd</title>
</svelte:head>

<form class="flex w-full flex-col" onsubmit={handleSubmit}>
	<FormField label="Email" name="email" type="email" autocomplete="email" bind:value={email} />

	<FormField
		label="Password"
		name="password"
		type="password"
		autocomplete="new-password"
		bind:value={password}
		class="mt-6"
	/>

	<FormField
		label="Confirm Password"
		name="confirm-password"
		type="password"
		autocomplete="new-password"
		bind:value={confirmPassword}
		class="mt-6"
	/>

	<!-- Terms of Service -->
	<div class="mt-8 flex items-center justify-center gap-2 text-sm">
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
			class="size-5 cursor-pointer accent-[#ff8a00]"
		/>

		<label for="terms" class="cursor-pointer text-white">
			I agree to all
			<a
				href="/terms-of-service"
				target="_blank"
				rel="noopener noreferrer"
				class="font-bold underline"
				onclick={(event) => event.stopPropagation()}
			>
				Terms of Service
			</a>
		</label>
	</div>

	<AuthButton class="mt-6">REGISTER</AuthButton>

	<p
        class="mt-4 min-h-5 text-center text-sm text-[#ff0000]"
        role="alert"
    >
        {#if showTermsError}
            *You must accept our Terms of Service
        {/if}
    </p>

	<!-- {#if showTermsError}
		<p class="mt-4 text-center text-sm text-[#ff0000]" role="alert">
			*You must accept our Terms of Service
		</p>
	{/if} -->

	<SocialLogin ongoogle={handleGoogle} />
</form>
