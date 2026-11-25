<script lang="ts">
	import AuthTitle from '#lib/components/auth/AuthTitle.svelte';
	import FormField from '#lib/components/auth/FormField.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import type { ActionData } from './$types';

	let { form }: { form: ActionData | null } = $props();

	let code = $state('');
</script>

<svelte:head>
	<title>Verify Two-Factor Authentication</title>
</svelte:head>

<AuthTitle>Two-Factor Verification</AuthTitle>

<form method="POST" class="flex flex-col gap-5">
	<p class="text-center text-lg text-ash">
		Enter the six-digit verification code sent to your email to complete your login.
	</p>

	<FormField
		label="Verification Code"
		name="code"
		type="text"
		autocomplete="one-time-code"
		bind:value={code}
	/>

	<Button type="submit" size="lg" class="w-full">Verify Code</Button>

	{#if form?.error}
		<Notice>{form.error}</Notice>
	{/if}

	<p class="text-center text-base text-ash">The code expires after 10 minutes.</p>

	<a href="/login" class="text-center text-lg text-ash hover:text-bone hover:underline">
		Back to Login
	</a>
</form>
