<script lang="ts">
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import Row from '#lib/components/ui/Row.svelte';
	import type { ActionData, PageData } from './$types';

	let { data, form }: { data: PageData; form: ActionData | null } = $props();

	let username = $derived(form?.values?.username ?? '');

	const pageNumbers = $derived.by(() => {
		const count = Math.min(5, data.pages);
		const start = Math.max(1, Math.min(data.page - 2, data.pages - count + 1));

		return Array.from({ length: count }, (_, i) => start + i);
	});

	function pageHref(page: number): string {
		return `/profile/friends/requests?tab=${data.tab}&page=${page}`;
	}

	function actionHref(action: string): string {
		return `?/${action}&tab=${data.tab}&page=${data.page}`;
	}
</script>

<svelte:head>
	<title>Requests · Profile</title>
</svelte:head>

<h2 class="font-display text-2xl">Friend requests</h2>

<nav aria-label="Request type" class="mt-4 flex gap-6 border-b border-bronze/20">
	<a
		href="/profile/friends/requests?tab=received"
		class="tab"
		aria-current={data.tab === 'received' ? 'page' : undefined}
	>
		Received
	</a>

	<a
		href="/profile/friends/requests?tab=sent"
		class="tab"
		aria-current={data.tab === 'sent' ? 'page' : undefined}
	>
		Sent
	</a>
</nav>

{#if form?.error}
	<Notice class="mt-4">{form.error}</Notice>
{:else if form?.message}
	<Notice variant="success" class="mt-4">
		{form.message}
	</Notice>
{/if}

{#if data.tab === 'sent'}
	<section aria-labelledby="send-request" class="mt-6">
		<h3 id="send-request" class="font-display text-xl">Send a friend request</h3>

		<form
			method="POST"
			action={actionHref('sendRequest')}
			class="mt-3 flex flex-wrap items-end gap-3"
		>
			<div class="w-full max-w-sm">
				<input
					id="friend-username"
					name="username"
					aria-label="Username to send a friend request to"
					bind:value={username}
					class="field mt-1"
					placeholder="Username"
					autocomplete="off"
				/>
			</div>

			<Button type="submit" outline>Send</Button>
		</form>
	</section>

	<Divider class="my-6" />
{/if}

<section aria-labelledby="requests-list" class="mt-5">
	<h3 id="requests-list" class="font-display text-xl">
		{data.tab === 'received' ? 'Incoming' : 'Outgoing'}
		<span class="text-base text-ash">({data.total})</span>
	</h3>

	{#if data.requests.length}
		<ul class="mt-3 divide-y divide-bronze/20">
			{#each data.requests as friend (friend.requestId)}
				<li>
					<Row
						title={friend.username}
						subtitle={data.tab === 'received'
							? 'Wants to join your fellowship'
							: 'Awaiting their answer'}
					>
						{#snippet lead()}
							<Avatar
								name={friend.username}
								src={friend.avatarUrl}
								alt=""
								class="size-12 text-xl"
							/>
						{/snippet}

						{#if data.tab === 'received'}
							<div class="flex flex-col gap-2 sm:flex-row">
								<form method="POST" action={actionHref('respondRequest')}>
									<input type="hidden" name="requestId" value={friend.requestId} />
									<input type="hidden" name="action" value="ACCEPTED" />

									<Button type="submit" size="sm" variant="success" outline>Accept</Button>
								</form>

								<form method="POST" action={actionHref('respondRequest')}>
									<input type="hidden" name="requestId" value={friend.requestId} />
									<input type="hidden" name="action" value="DECLINED" />

									<Button type="submit" size="sm" variant="danger" outline>Decline</Button>
								</form>
							</div>
						{:else}
							<form method="POST" action={actionHref('withdrawRequest')}>
								<input type="hidden" name="requestId" value={friend.requestId} />

								<Button type="submit" size="sm" variant="secondary" outline>Withdraw</Button>
							</form>
						{/if}
					</Row>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="mt-4 text-ash italic">
			{data.tab === 'received' ? 'No incoming friend requests.' : 'No outgoing friend requests.'}
		</p>
	{/if}

	{#if data.pages > 1}
		<nav
			aria-label="Requests pagination"
			class="mt-6 flex flex-wrap items-center justify-center gap-2 text-sm"
		>
			{#if data.page > 1}
				<a href={pageHref(1)} class="text-ash hover:text-bone">First</a>
				<a href={pageHref(data.page - 1)} class="text-ash hover:text-bone"> Previous </a>
			{:else}
				<span class="text-ash/40">First</span>
				<span class="text-ash/40">Previous</span>
			{/if}

			{#each pageNumbers as number (number)}
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
				<a href={pageHref(data.page + 1)} class="text-ash hover:text-bone"> Next </a>
				<a href={pageHref(data.pages)} class="text-ash hover:text-bone">Last</a>
			{:else}
				<span class="text-ash/40">Next</span>
				<span class="text-ash/40">Last</span>
			{/if}
		</nav>
	{/if}
</section>
