<script lang="ts">
	import { goto } from '$app/navigation';
	import FormField from '#lib/components/auth/FormField.svelte';
	import AuthButton from '#lib/components/auth/AuthButton.svelte';
	import SocialLogin from '#lib/components/auth/SocialLogin.svelte';
	import { api, ApiError } from '#lib/api.ts';
	import { loadUser } from '#lib/session.svelte.ts';

	let email = $state('');
	let password = $state('');
	let code = $state('');
	let needsCode = $state(false);
	let error = $state('');
	let busy = $state(false);

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		busy = true;
		try {
			if (needsCode) {
				await api('/auth/2fa/verify', { method: 'POST', body: { code } });
			} else {
				const response = await fetch('/api/v1/auth/login', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ email, password })
				});
				const data = await response.json().catch(() => null);
				if (response.status === 202) {
					needsCode = true;
					return;
				}
				if (!response.ok) throw new ApiError(data?.detail ?? 'Login failed.', response.status);
			}
			await loadUser();
			await goto('/play');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Login failed.';
		} finally {
			busy = false;
		}
	}

	function handleGoogle() {
		location.href = '/api/v1/auth/google';
	}
</script>

<svelte:head>
	<title>Login</title>
</svelte:head>

<form class="flex w-full flex-col items-center" onsubmit={handleSubmit}>
	{#if needsCode}
		<p class="mb-4 text-center text-white">We emailed you a 6-digit code.</p>
		<FormField label="Code" name="code" autocomplete="one-time-code" bind:value={code} />
	{:else}
		<FormField label="Email" name="email" type="email" autocomplete="email" bind:value={email} />
		<FormField
			label="Password"
			name="password"
			type="password"
			autocomplete="current-password"
			bind:value={password}
			class="mt-3 sm:mt-5"
		/>
	{/if}

	<AuthButton class="mt-12 mb-2" disabled={busy}>{needsCode ? 'VERIFY' : 'LOGIN'}</AuthButton>

	<p class="mt-2 min-h-5 text-center text-base text-[#ff0000] sm:mt-3 sm:text-lg" role="alert">
		{error}
	</p>

	<SocialLogin ongoogle={handleGoogle} />
</form>
