<script lang="ts">
	import { page } from '$app/state';
	import type { ActionData, PageData } from './$types';

	let {
		data,
		form
	}: {
		data: PageData;
		form: ActionData | null;
	} = $props();

	let code = $state('');

	let updated = $derived(page.url.searchParams.get('two_factor_updated') === '1');
</script>

<svelte:head>
	<title>Settings</title>
</svelte:head>

<section class="mx-auto w-full max-w-3xl px-4 py-8 text-text-primary sm:px-6">
	<h1 class="text-3xl font-bold">Settings</h1>

	<div class="mt-8 rounded-xl border border-white/15 bg-[#2d353c] p-5 sm:p-6">
		<h2 class="text-xl font-bold">Two-Factor Authentication</h2>

		<p class="mt-3">
			Status:
			<span class={data.twoFactorEnabled ? 'text-green-400' : 'text-red-400'}>
				{data.twoFactorEnabled ? 'Enabled' : 'Disabled'}
			</span>
		</p>

		<p class="mt-3 text-sm text-white/70">
			Protect your account with a verification code sent to your email.
		</p>

		{#if updated}
			<p class="mt-4 text-green-400" role="status">
				Two-factor authentication settings updated successfully!
			</p>
		{/if}

		{#if form?.step === 'code'}
			<p class="mt-5 text-sm text-white/80" role="status">
				A verification code was sent to your email. Enter it below.
			</p>

			<form method="POST" action="?/confirmCode" class="mt-4 flex flex-col gap-4">
				<input type="hidden" name="action" value={form.action ?? ''} />

				<div class="flex flex-col gap-2">
					<label for="two-factor-code" class="font-bold">
						Verification Code
					</label>

					<input
						id="two-factor-code"
						name="code"
						type="text"
						inputmode="numeric"
						autocomplete="one-time-code"
						maxlength="6"
						bind:value={code}
						class="h-11 w-full max-w-xs rounded-xl bg-[#1c232a] px-4 text-center
							text-white outline-none focus-visible:ring-2 focus-visible:ring-orange-400"
					/>
				</div>

				<button
					type="submit"
					class="min-h-11 w-full rounded-lg bg-accent-action px-6 font-bold text-white
						hover:brightness-110 sm:w-fit"
				>
					CONFIRM {form.action === 'enable' ? 'ENABLE' : 'DISABLE'}
				</button>
			</form>
		{:else}
			<form method="POST" action="?/requestCode" class="mt-5">
				<input
					type="hidden"
					name="action"
					value={data.twoFactorEnabled ? 'disable' : 'enable'}
				/>

				<button
					type="submit"
					class="min-h-11 w-full rounded-lg bg-accent-action px-6 font-bold text-white
						hover:brightness-110 sm:w-fit"
				>
					{data.twoFactorEnabled ? 'DISABLE 2FA' : 'ENABLE 2FA'}
				</button>
			</form>
		{/if}

		{#if form?.error}
			<p class="mt-4 text-red-400" role="alert">
				*{form.error}
			</p>
		{/if}
	</div>
</section>
