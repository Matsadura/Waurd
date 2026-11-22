<script lang="ts">
	import FormField from '#lib/components/auth/FormField.svelte';
	import AuthButton from '#lib/components/auth/AuthButton.svelte';
	import type { ActionData } from './$types';

	let { form }: { form: ActionData | null } = $props();

	let code = $state('');
</script>

<svelte:head>
	<title>Verify Two-Factor Authentication</title>
</svelte:head>

<form method="POST" class="flex w-full flex-col items-center">
	<p class="mb-8 text-center text-base text-white sm:text-lg">
		We've sent a 6-digit verification code to your email address.
		Enter it below to complete your login.
	</p>

	<FormField
		label="Verification Code"
		name="code"
		type="text"
		autocomplete="one-time-code"
		bind:value={code}
	/>

	<AuthButton class="mt-10 mb-2">VERIFY CODE</AuthButton>

	<p
		class="mt-2 min-h-5 text-center text-base text-[#ff0000] sm:mt-3 sm:text-lg"
		role="alert"
	>
		{#if form?.error}
			*{form.error}
		{/if}
	</p>

	<p class="mt-4 text-center text-sm text-white/70">
		The code expires after 10 minutes.
	</p>

	<a
		href="/login"
		class="mt-4 text-base font-bold text-accent-action hover:underline"
	>
		BACK TO LOGIN
	</a>
</form>