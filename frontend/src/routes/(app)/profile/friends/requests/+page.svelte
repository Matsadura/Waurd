<script lang="ts">
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Divider from '#lib/components/ui/Divider.svelte';
	import Notice from '#lib/components/ui/Notice.svelte';
	import Row from '#lib/components/ui/Row.svelte';
	import type { ActionData, PageData } from './$types';

	let { data, form }: { data: PageData; form: ActionData | null } = $props();

	let username = $derived(form?.values?.username ?? '');
</script>

<svelte:head>
	<title>Requests · Profile</title>
</svelte:head>

{#if form?.section === 'withdrawRequest'}
	{#if form.error}
		<Notice class="mb-4">{form.error}</Notice>
	{:else if form.message}
		<Notice variant="success" class="mb-4">
			{form.message}
		</Notice>
	{/if}
{/if}

<section aria-labelledby="send-request">
	<h2 id="send-request" class="font-display text-2xl">Send a friend request</h2>

	<form method="POST" action="?/sendRequest" class="mt-3 flex flex-wrap items-end gap-3">
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

	{#if form?.section === 'sendRequest'}
		{#if form.error}
			<Notice class="mt-2">{form.error}</Notice>
		{:else if form.message}
			<Notice variant="success" class="mt-2">
				{form.message}
			</Notice>
		{/if}
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

<Divider class="my-6" />

<section aria-labelledby="pending">
	<h2 id="pending" class="font-display text-2xl">Pending requests</h2>

	{#if data.incoming.length || data.outgoing.length}
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
	{:else}
		<p class="mt-6 text-ash italic">No pending friend requests.</p>
	{/if}
</section>
