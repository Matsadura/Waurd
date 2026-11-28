<script lang="ts">
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import Presence from '#lib/components/ui/Presence.svelte';
	import Row from '#lib/components/ui/Row.svelte';
	import type { ActionData, PageData } from './$types';

	let { data, form }: { data: PageData; form: ActionData | null } = $props();

	const pageNumbers = $derived.by(() => {
		const count = Math.min(5, data.pages);
		const start = Math.max(1, Math.min(data.page - 2, data.pages - count + 1));

		return Array.from({ length: count }, (_, i) => start + i);
	});

	function pageHref(page: number): string {
		const params = new URLSearchParams({ page: String(page) });

		if (data.query) {
			params.set('q', data.query);
		}

		return `/profile/friends?${params.toString()}`;
	}

	function removeActionHref(): string {
		const params = new URLSearchParams({ page: String(data.page) });

		if (data.query) {
			params.set('q', data.query);
		}

		return `?/removeFriend&${params.toString()}`;
	}
</script>

<svelte:head>
	<title>Friends · Profile</title>
</svelte:head>

{#if form?.section === 'removeFriend'}
	{#if form.error}
		<Notice class="mb-4">{form.error}</Notice>
	{:else if form.message}
		<Notice variant="success" class="mb-4">
			{form.message}
		</Notice>
	{/if}
{/if}

<section aria-labelledby="fellowship">
	<h2 id="fellowship" class="font-display text-2xl">
		Fellowship <span class="text-lg text-ash">({data.friendCount})</span>
	</h2>

	<form method="GET" action="/profile/friends" class="mt-4 flex flex-wrap items-end gap-3">
		<input
			type="search"
			name="q"
			value={data.query}
			maxlength="32"
			aria-label="Search friends by username"
			class="field w-full max-w-sm"
			placeholder="Search your friends..."
			autocomplete="off"
		/>

		<Button type="submit" outline>Search</Button>

		{#if data.query}
			<a href="/profile/friends" class="text-ash underline hover:text-bone"> Clear </a>
		{/if}
	</form>

	{#if data.friends.length}
		<ul class="mt-4 divide-y divide-bronze/20">
			{#each data.friends as friend (friend.id)}
				<li>
					<Row title={friend.username}>
						{#snippet lead()}
							<Avatar
								name={friend.username}
								src={friend.avatarUrl}
								alt=""
								class="size-12 text-xl"
							/>
						{/snippet}

						{#snippet subtitle()}
							<Presence online={friend.online} lastSeen={friend.lastSeen} />
						{/snippet}

						<div class="flex flex-col gap-2 sm:flex-row">
							<Button size="sm" outline disabled>Challenge</Button>

							<form method="POST" action={removeActionHref()}>
								<input type="hidden" name="friendId" value={friend.id} />

								<Button type="submit" size="sm" variant="secondary" outline>Remove</Button>
							</form>
						</div>
					</Row>
				</li>
			{/each}
		</ul>
	{:else if data.query}
		<p class="mt-6 text-ash italic">
			No friends found matching "{data.query}".
		</p>
	{:else}
		<p class="mt-6 text-ash italic">
			Your fellowship is empty. Visit Requests to send a friend request.
		</p>
	{/if}

	{#if data.pages > 1}
		<nav
			aria-label="Friends pagination"
			class="mt-6 flex flex-wrap items-center justify-center gap-2 text-sm"
		>
			{#if data.page > 1}
				<a href={pageHref(1)} class="text-ash hover:text-bone">First</a>
				<a href={pageHref(data.page - 1)} class="text-ash hover:text-bone"> Previous </a>
			{:else}
				<span class="text-ash/40">First</span>
				<span class="text-ash/40">Previous</span>
			{/if}

			{#each pageNumbers as number}
				<a
					href={pageHref(number)}
					aria-current={number === data.page ? 'page' : undefined}
					class={[
						'rounded border px-3 py-1',
						number === data.page
							? 'border-bronze text-bone'
							: 'border-bronze/20 text-ash hover:border-bronze hover:text-bone'
					]}
				>
					{number}
				</a>
			{/each}

			{#if data.page < data.pages}
				<a href={pageHref(data.page + 1)} class="text-ash hover:text-bone">Next</a>
				<a href={pageHref(data.pages)} class="text-ash hover:text-bone">Last</a>
			{:else}
				<span class="text-ash/40">Next</span>
				<span class="text-ash/40">Last</span>
			{/if}
		</nav>
	{/if}
</section>
