<svelte:head>
    <title>Login — Waurd</title>
</svelte:head>

<script lang="ts">
    import FormField from '#lib/components/auth/FormField.svelte';
    import AuthButton from '#lib/components/auth/AuthButton.svelte';
    import SocialLogin from '#lib/components/auth/SocialLogin.svelte';

    let email = $state('');
    let password = $state('');

    function handleSubmit(event: SubmitEvent) {
        event.preventDefault();
        // TODO: login API
    }

    function handleGoogle() {
        // TODO: google sign-in
    }
</script>

<form class="flex w-full flex-col" onsubmit={handleSubmit}>
    <FormField
        label="Email" 
        name="email" 
        type="email" 
        autocomplete="email" 
        bind:value={email} 
    />

    <FormField
        label="Password"
        name="password"
        type="password"
        autocomplete="current-password"
        bind:value={password}
        class="mt-6"
    />

    <AuthButton class="mt-[clamp(1.5rem,6vh,3.75rem)]">LOGIN</AuthButton>

    <SocialLogin ongoogle={handleGoogle} />
</form>