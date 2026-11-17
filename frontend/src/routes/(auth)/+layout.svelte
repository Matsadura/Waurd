<script lang="ts">
	import { page } from '$app/state';
	import WaurdLogo from '#lib/components/WaurdLogo.svelte';

	let { children } = $props();

	const tabs = [
		{ href: '/login', label: 'LOGIN' },
		{ href: '/register', label: 'REGISTER' }
	];

	const isActive = (href: string) => page.url.pathname === href;


</script>

<div
	class="font-serif auth-page relative flex min-h-dvh w-full min-w-0 flex-col items-center overflow-hidden
		px-4 pt-8 font-bold text-text-primary sm:pt-12"
>


	<header class="relative z-10 my-4">
		<WaurdLogo href="/login" size="large" />
	</header>

	<div
		class="auth-column @container relative z-10 mb-10 w-full max-w-2xl border border-white/30
			bg-gray-950/60 p-4 pb-10 shadow-xl shadow-accent/10 backdrop-blur-sm"
	>
		<nav aria-label="Account" class="mb-10 flex sm:px-4">
			{#each tabs as tab (tab.href)}
				<a
					href={tab.href}
					aria-current={isActive(tab.href) ? 'page' : undefined}
					class={[
						'auth-tab min-h-12 w-1/2 border-b-2 px-3 py-4 text-center text-xl font-bold transition-colors',
						isActive(tab.href)
							? 'border-b-accent text-accent'
							: 'border-b-white/20 text-text-primary/50 hover:border-b-accent/60 hover:text-text-primary'
					]}
				>
					{tab.label}
				</a>
			{/each}
		</nav>

		<main class="mx-auto w-full max-w-md">
			{@render children()}
		</main>
	</div>
</div>

<style>
	.auth-page {
		background: linear-gradient(to bottom, var(--color-gray-900), var(--color-gray-950) 306px)
			no-repeat;
		background-color: var(--color-gray-950);
	}

	/* Orange corner brackets give the card a "game panel" feel without clipping its border */
	.auth-column::before,
	.auth-column::after {
		content: '';
		position: absolute;
		width: 18px;
		height: 18px;
		border: 2px solid var(--color-accent);
		pointer-events: none;
	}
	.auth-column::before {
		top: -2px;
		left: -2px;
		border-right: 0;
		border-bottom: 0;
	}
	.auth-column::after {
		right: -2px;
		bottom: -2px;
		border-left: 0;
		border-top: 0;
	}

	.auth-tab:focus-visible {
		outline: 2px solid var(--color-accent);
		outline-offset: -2px;
	}

	
</style>