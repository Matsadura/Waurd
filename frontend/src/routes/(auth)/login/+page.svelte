<script lang="ts">
	import FormField from '#lib/components/auth/FormField.svelte';
	import AuthButton from '#lib/components/auth/AuthButton.svelte';
	import SocialLogin from '#lib/components/auth/SocialLogin.svelte';

	let email = $state('');
	let password = $state('');

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		// TODO: login API
	}

	function handleGoogle() {
		// TODO: google sign-in
	}
</script>

<svelte:head>
	<title>Login</title>
</svelte:head>

<form class="flex w-full flex-col" onsubmit={handleSubmit}>
	<FormField label="Email" name="email" type="email" autocomplete="email" bind:value={email} />

	<FormField
		label="Password"
		name="password"
		type="password"
		autocomplete="current-password"
		bind:value={password}
		class="mt-3 sm:mt-5"
	/>

	<AuthButton class="mt-5 sm:mt-7">LOGIN</AuthButton>

	<SocialLogin ongoogle={handleGoogle} />
</form>
