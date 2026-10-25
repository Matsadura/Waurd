
<svelte:head>
    <title>Register — Waurd</title>
</svelte:head>

<script lang="ts">
    let email = $state('');
    let password = $state('');
    let confirmPassword = $state('');
    let termsAccepted = $state(false);
    let showTermsError = $state(false);
</script>

<section class="mx-auto w-full max-w-sm">
    <form
        class="flex w-full flex-col"
        onsubmit={(event) => {
            event.preventDefault();

            if (!termsAccepted) {
                showTermsError = true;
                return;
            }
            showTermsError = false;
        }}
    >
        <div class="flex flex-col items-center">
            <label
                for="email"
                class="mb-[0.1rem] text-center text-xl font-bold text-white"
            >
                Email
            </label>

            <input
                id="email"
                name="email"
                type="email"
                autocomplete="email"
                bind:value={email}
                required
                class="h-11 w-full rounded-xl border-0 bg-[#2d353c] px-4 text-center text-[1.1rem] text-white shadow-[0_2px_4px_rgba(0,0,0,0.4)] focus:ring-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ff8a00]"
            />
        </div>


        <div class="mt-6 flex flex-col items-center">
            <label
                for="password"
                class="mb-[0.1rem] text-center text-xl font-bold text-white"
            >
                Password
            </label>

            <input
                id="password"
                name="password"
                type="password"
                autocomplete="new-password"
                bind:value={password}
                required
                class="h-11 w-full rounded-xl border-0 bg-[#2d353c] px-4 text-center text-[1.1rem] text-white shadow-[0_2px_4px_rgba(0,0,0,0.4)] focus:ring-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ff8a00]"
            />
        </div>

        <div class="mt-6 flex flex-col items-center">
            <label
                for="confirm-password"
                class="mb-[0.1rem] text-center text-xl font-bold text-white"
            >
                Confirm Password
            </label>

            <input
                id="confirm-password"
                name="confirm-password"
                type="password"
                autocomplete="new-password"
                bind:value={confirmPassword}
                required
                class="h-11 w-full rounded-xl border-0 bg-[#2d353c] px-4 text-center text-[1.1rem] text-white shadow-[0_2px_4px_rgba(0,0,0,0.4)] focus:ring-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ff8a00]"
            />
        </div>

        <!-- Terms of Service -->
        <div class="mt-8 flex items-center justify-center gap-2 text-sm">
            <input
                id="terms"
                name="terms"
                type="checkbox"
                bind:checked={termsAccepted}
                onchange={() => {
                    if (termsAccepted) {
                        showTermsError = false;
                    }
                }}
                class="size-5 cursor-pointer accent-[#ff8a00]"
            />

            <label for="terms" class="cursor-pointer text-white">
                I agree to all
                <a
                    href="/terms-of-service"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="font-bold underline"
                    onclick={(event) => event.stopPropagation()}
                >
                    Terms of Service
                </a>
            </label>
        </div>

        <!-- Register button -->
        <button
            type="submit"
            class="mx-auto mt-6 h-11 w-[90%] cursor-pointer rounded-[0.4rem] border-0 bg-[#ff8a00] text-[1.2rem] font-bold text-white shadow-[0_2px_4px_rgba(0,0,0,0.4)] transition hover:brightness-[1.08] focus-visible:outline-2 focus-visible:outline-offset-[3px] focus-visible:outline-white"
        >
            REGISTER
        </button>

        <!-- Terms error -->
        {#if showTermsError}
            <p class="mt-4 text-center text-sm text-[#ff0000]" role="alert">
                *You must accept our Terms of Service
            </p>
        {/if}


        <div class="mx-auto mt-6 flex w-3/4 items-center gap-3">
            <div class="h-px flex-1 bg-[#018bf6]"></div>
            <span class="text-[1.2rem] font-light text-[#018bf6]">OR</span>
            <div class="h-px flex-1 bg-[#018bf6]"></div>
        </div>

        <button
            type="button"
            aria-label="Continue with Google"
            class="mx-auto mt-6 flex size-13 cursor-pointer items-center justify-center rounded-full bg-white text-black transition hover:brightness-90 focus-visible:outline-2 focus-visible:outline-offset-[3px] focus-visible:outline-[#ff8a00]"
        >
            <svg
                viewBox="0 0 48 48"
                width="26"
                height="26"
                aria-hidden="true"
            >
                <path
                    fill="#4285F4"
                    d="M43.6 24.5c0-1.4-.1-2.8-.4-4.1H24v7.8h11a9.4 9.4 0 0 1-4.1 6.2v5.1h6.6c3.9-3.6 6.1-8.9 6.1-15Z"
                />
                <path
                    fill="#34A853"
                    d="M24 44c5.5 0 10.1-1.8 13.5-4.9l-6.6-5.1c-1.8 1.2-4.1 1.9-6.9 1.9-5.3 0-9.8-3.6-11.4-8.4H5.8v5.2A20 20 0 0 0 24 44Z"
                />
                <path
                    fill="#FBBC05"
                    d="M12.6 27.5a12 12 0 0 1 0-7.6v-5.2H5.8a20 20 0 0 0 0 18l6.8-5.2Z"
                />
                <path
                    fill="#EA4335"
                    d="M24 11.5c3 0 5.7 1 7.8 3.1l5.8-5.8A19.4 19.4 0 0 0 24 4 20 20 0 0 0 5.8 14.7l6.8 5.2c1.6-4.8 6.1-8.4 11.4-8.4Z"
                />
            </svg>
        </button>
    </form>
</section>
