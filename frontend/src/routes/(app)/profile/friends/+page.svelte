<script lang="ts">
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import Presence from '#lib/components/ui/Presence.svelte';
	import Row from '#lib/components/ui/Row.svelte';
	import type { ActionData, PageData } from './$types';

	let { data, form }: { data: PageData; form: ActionData | null } = $props();

	let username = $derived(form?.values?.username ?? '');

	// Friends who are online come first
	const sorted = $derived([...data.friends].sort((a, b) => Number(b.online) - Number(a.online)));
</script>

<svelte:head>
	<title>Friends · Profile</title>
</svelte:head>

{#if form?.section === 'withdrawRequest' || form?.section === 'removeFriend'}
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

	<form method="POST" action="?/sendRequest" class="mt-3 flex flex-wrap items-end gap-3">
		<div class="w-full max-w-sm">
			<label for="friend-username" class="field-label">Send a friend request</label>
			<input
				id="friend-username"
				name="username"
				bind:value={username}
				class="field mt-1"
				placeholder="Username"
				autocomplete="off"
			/>
		</div>
		<Button type="submit" outline>Send</Button>
	</form>
	{#if form?.section === 'sendRequest'}
		{#if form.error}
			<Notice class="mt-2">{form.error}</Notice>
		{:else if form.message}
			<Notice variant="success" class="mt-2">
				{form.message}
			</Notice>
		{/if}
	{/if}

	{#if sorted.length}
		<ul class="mt-4 divide-y divide-bronze/20">
			{#each sorted as friend (friend.id)}
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
						<span class="flex flex-col gap-2 sm:flex-row">
							<div class="flex flex-col gap-2 sm:flex-row">
								<Button size="sm" outline disabled>Challenge</Button>
								<!-- TODO (when arena is ready) -->

								<form method="POST" action="?/removeFriend">
									<input type="hidden" name="friendId" value={friend.id} />
									<Button type="submit" size="sm" variant="secondary" outline>Remove</Button>
								</form>
							</div>
						</span>
					</Row>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="mt-6 text-ash italic">Your fellowship is empty, send a request to someone.</p>
	{/if}
</section>

{#if form?.section === 'respondRequest'}
	{#if form.error}
		<Notice class="mt-4">{form.error}</Notice>
	{:else if form.message}
		<Notice variant="success" class="mt-4">
			{form.message}
		</Notice>
	{/if}
{/if}

{#if data.incoming.length || data.outgoing.length}
	<Divider class="my-6" />

	<section aria-labelledby="pending">
		<h2 id="pending" class="font-display text-2xl">Pending requests</h2>

		<ul class="mt-3 divide-y divide-bronze/20">
			{#each data.incoming as friend (friend.requestId)}
				<li>
					<Row title={friend.username} subtitle="Wants to join your fellowship">
						{#snippet lead()}
							<Avatar
								name={friend.username}
								src={friend.avatarUrl}
								alt=""
								class="size-12 text-xl"
							/>
						{/snippet}

						<div class="flex flex-col gap-2 sm:flex-row">
							<form method="POST" action="?/respondRequest">
								<input type="hidden" name="requestId" value={friend.requestId} />
								<input type="hidden" name="action" value="ACCEPTED" />
								<Button type="submit" size="sm" variant="success" outline>Accept</Button>
							</form>

							<form method="POST" action="?/respondRequest">
								<input type="hidden" name="requestId" value={friend.requestId} />
								<input type="hidden" name="action" value="DECLINED" />
								<Button type="submit" size="sm" variant="danger" outline>Decline</Button>
							</form>
						</div>
					</Row>
				</li>
			{/each}

			{#each data.outgoing as friend (friend.requestId)}
				<li>
					<Row title={friend.username} subtitle="Awaiting their answer">
						{#snippet lead()}
							<Avatar
								name={friend.username}
								src={friend.avatarUrl}
								alt=""
								class="size-12 text-xl"
							/>
						{/snippet}
						<form method="POST" action="?/withdrawRequest">
							<input type="hidden" name="requestId" value={friend.requestId} />
							<Button type="submit" size="sm" variant="secondary" outline>Withdraw</Button>
						</form>
					</Row>
				</li>
			{/each}
		</ul>
	</section>
{/if}
