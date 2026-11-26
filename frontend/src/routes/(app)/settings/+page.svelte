<script lang="ts">
	import { page } from '$app/state';
	import FormField from '#lib/components/auth/FormField.svelte';
	import SettingsSection from '#lib/components/settings/SettingsSection.svelte';
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Frame from '#lib/components/ui/Frame.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import type { ActionData, PageData } from './$types';

	let { data, form }: { data: PageData; form: ActionData | null } = $props();

	// After a failed save the form shows what was typed, otherwise the saved values
	let username = $derived(form?.values?.username ?? data.user.username);
	let email = $derived(form?.values?.email ?? data.user.email);
	let newPassword = $state('');
	let confirmPassword = $state('');
	let code = $state('');

	let twoFactorUpdated = $derived(page.url.searchParams.get('two_factor_updated') === '1');
</script>

<svelte:head>
	<title>Settings</title>
</svelte:head>

<div class="mx-auto w-full max-w-4xl px-3 py-6 font-body text-bone sm:px-4">
	<Frame class="fade-in">
		<header class="flex flex-wrap items-center justify-between gap-x-8 gap-y-3">
			<div>
				<h1 class="text-3xl sm:text-4xl">Settings</h1>
				<p class="text-lg text-ash italic">Member since {data.user.joined}</p>
			</div>

			<Button href="/profile" outline variant="secondary" size="sm">Back to profile</Button>
		</header>

		<Divider class="my-6" />

		<div class="flex flex-col gap-8">
			<SettingsSection title="Profile" description="How other players see you.">
				<div class="flex items-center gap-4">
					<Avatar
						name={data.user.username}
						src={data.user.avatarUrl ?? undefined}
						alt=""
						class="size-20 text-4xl"
					/>

					<div class="flex min-w-0 flex-col gap-2">
						<form
							method="POST"
							action="?/uploadAvatar"
							enctype="multipart/form-data"
							class="flex flex-wrap items-center gap-2"
						>
							<input
								type="file"
								name="file"
								required
								accept="image/png,image/jpeg,image/webp,image/gif"
								aria-label="Choose an avatar image"
								class="max-w-full min-w-0 text-base text-ash file:mr-3 file:cursor-pointer file:border file:border-bronze/60 file:bg-transparent file:px-3 file:py-0.5 file:text-bone hover:file:border-bone"
							/>
							<Button type="submit" size="sm" outline>Upload</Button>
						</form>

						{#if data.user.avatarUrl}
							<form method="POST" action="?/removeAvatar">
								<Button type="submit" size="sm" outline variant="secondary">Remove avatar</Button>
							</form>
						{/if}

						<p class="text-base text-ash">PNG, JPEG, WebP or GIF, up to 2 MB.</p>
					</div>
				</div>

				{#if form?.section === 'avatar'}
					{#if form.error}
						<Notice class="mt-3">{form.error}</Notice>
					{:else if form.message}
						<Notice variant="success" class="mt-3">{form.message}</Notice>
					{/if}
				{/if}

				<form method="POST" action="?/updateProfile" class="mt-6 flex flex-col gap-5">
					<FormField
						label="Username"
						name="username"
						autocomplete="username"
						bind:value={username}
					/>
					<FormField
						label="Email"
						name="email"
						type="email"
						autocomplete="email"
						bind:value={email}
					/>

					<div>
						<Button type="submit">Save changes</Button>
						<p class="mt-2 text-base text-ash italic">
							Changing your email will require you to log in again.
						</p>
					</div>

					{#if form?.section === 'profile'}
						{#if form.error}
							<Notice>{form.error}</Notice>
						{:else if form.message}
							<Notice variant="success">{form.message}</Notice>
						{/if}
					{/if}
				</form>
			</SettingsSection>

			<Divider />

			<SettingsSection title="Password" description="Choose a new one to keep your account safe.">
				<form method="POST" action="?/changePassword" class="flex flex-col gap-5">
					{#if data.user.hasPassword}
						<FormField
							label="Current password"
							name="current-password"
							type="password"
							autocomplete="current-password"
						/>
					{/if}

					<FormField
						label="New password"
						name="new-password"
						type="password"
						autocomplete="new-password"
						bind:value={newPassword}
					/>
					<FormField
						label="Confirm new password"
						name="confirm-password"
						type="password"
						autocomplete="new-password"
						bind:value={confirmPassword}
					/>

					<div>
						<Button type="submit">Change password</Button>
						<p class="mt-2 text-base text-ash italic">You will be signed out after changing it.</p>
					</div>

					{#if form?.section === 'password' && form.error}
						<Notice>{form.error}</Notice>
					{/if}
				</form>
			</SettingsSection>

			<Divider />

			<SettingsSection title="Two-factor" description="A code sent to your email when you log in.">
				<p class="text-lg">
					Status:
					<span class={data.twoFactorEnabled ? 'text-success-light' : 'text-danger-light'}>
						{data.twoFactorEnabled ? 'Enabled' : 'Disabled'}
					</span>
				</p>

				{#if twoFactorUpdated}
					<Notice variant="success" class="mt-3">
						Two-factor authentication settings updated.
					</Notice>
				{/if}

				{#if form?.section === 'twoFactor' && form.step === 'code'}
					<p class="mt-3 text-ash italic" role="status">
						A verification code was sent to your email. Enter it below.
					</p>

					<form method="POST" action="?/confirmCode" class="mt-4 flex flex-col gap-5">
						<input type="hidden" name="action" value={form.action ?? ''} />

						<div class="flex flex-col gap-1.5">
							<label for="two-factor-code" class="field-label">Verification code</label>
							<input
								id="two-factor-code"
								name="code"
								type="text"
								inputmode="numeric"
								autocomplete="one-time-code"
								maxlength="6"
								bind:value={code}
								class="field max-w-48 text-center tracking-widest"
							/>
						</div>

						<div>
							<Button type="submit" variant={form.action === 'disable' ? 'danger' : 'primary'}>
								Confirm {form.action === 'enable' ? 'enable' : 'disable'}
							</Button>
						</div>
					</form>
				{:else}
					<form method="POST" action="?/requestCode" class="mt-4">
						<input
							type="hidden"
							name="action"
							value={data.twoFactorEnabled ? 'disable' : 'enable'}
						/>
						<Button
							type="submit"
							outline={data.twoFactorEnabled}
							variant={data.twoFactorEnabled ? 'danger' : 'primary'}
						>
							{data.twoFactorEnabled ? 'Disable two-factor' : 'Enable two-factor'}
						</Button>
					</form>
				{/if}

				{#if form?.section === 'twoFactor' && form.error}
					<Notice class="mt-4">{form.error}</Notice>
				{/if}
			</SettingsSection>
		</div>
	</Frame>
</div>
