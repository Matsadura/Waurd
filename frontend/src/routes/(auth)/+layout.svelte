<script lang="ts">
	import { page } from '$app/state';
	import WaurdLogo from '#lib/components/WaurdLogo.svelte';

	let { children } = $props();

	const tabs = [
		{ href: '/login', label: 'LOGIN' },
		{ href: '/register', label: 'REGISTER' },
		{ href: '/reset-password', label: 'RESET PASSWORD' }
	];
</script>

<div
	class="auth-page relative flex min-h-dvh w-full min-w-0 flex-col items-center overflow-hidden bg-background bg-[url('/images/background.png')]
		bg-cover bg-center bg-no-repeat pt-12 font-rajdhani font-bold text-text-primary"
>
	<header class="auth-header my-4">
		<WaurdLogo href="/login" size="large" />
	</header>

	<div class="auth-column @container w-full max-w-2xl">
		<nav class="auth-tabs mb-6 flex flex-wrap justify-center gap-2 px-5 text-lg sm:flex-row">
			{#each tabs as tab (tab.href)}
				<a
					href={tab.href}
					class="relative flex min-h-10 min-w-0 grow items-center justify-center
							rounded-md bg-accent-red
							text-center leading-[1.33] whitespace-nowrap
							text-white no-underline
							shadow-[0_0.42em_0.5em_rgba(0,0,0,0.45)]"
					aria-current={page.url.pathname === tab.href ? 'page' : undefined}
				>
					{tab.label}
				</a>
			{/each}
		</nav>

		<main class="mx-auto w-[max(65%,min(88%,20rem))]">
			{@render children()}
		</main>
	</div>
</div>

<style>
	/* The small triangle above the active tab (sized in em, so it scales with the tab text) */
	.auth-tabs a[aria-current='page']::before {
		content: '';
		position: absolute;
		left: 50%;
		top: -0.62em;
		transform: translateX(-50%);
		border-left: 0.42em solid transparent;
		border-right: 0.42em solid transparent;
		border-top: 0.62em solid var(--color-accent-red);
	}
</style>
