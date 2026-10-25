<script lang="ts">
    import { page } from '$app/state';

    let { children } = $props();
</script>

<svelte:head>
    <link
        rel="preload"
        href="/fonts/HennyPenny-Regular.ttf"
        as="font"
        type="font/ttf"
        crossorigin="anonymous"
    />

    <link
        rel="preload"
        href="/fonts/Rajdhani-Bold.ttf"
        as="font"
        type="font/ttf"
        crossorigin="anonymous"
    />
</svelte:head>

<div class="min-h-dvh flex flex-col items-center px-4 py-9 sm:px-6 sm:py-12 text-[#f5f3f5] font-bold font-['Rajdhani'] bg-[url('/images/background.png')] bg-cover bg-center bg-no-repeat">
    <header class="auth-header">
        <a href="/login" class="logo">Waurd</a>
    </header>

    <nav class="auth-tabs flex flex-wrap justify-center gap-3 mb-10">
        <a
            href="/login"
            class="relative px-2 sm:px-8 py-1.5 sm:py-1 rounded-md bg-[#ef4637] shadow-[0_10px_12px_rgba(0,0,0,0.45)] text-white text-sm sm:text-2xl no-underline transition-colors"
            class:active={page.url.pathname === '/login'}
            aria-current={page.url.pathname === '/login' ? 'page' : undefined}
        >
            LOGIN
        </a>

        <a
            href="/register"
            class="relative px-2 sm:px-8 py-1.5 sm:py-1 rounded-md bg-[#ef4637] shadow-[0_10px_12px_rgba(0,0,0,0.45)] text-white text-sm sm:text-2xl no-underline transition-colors"
            class:active={page.url.pathname === '/register'}
            aria-current={page.url.pathname === '/register' ? 'page' : undefined}
        >
            REGISTER
        </a>

        <a
            href="/reset-password"
            class="relative px-2 sm:px-8 py-1.5 sm:py-1 rounded-md bg-[#ef4637] shadow-[0_10px_12px_rgba(0,0,0,0.45)] text-white text-sm sm:text-2xl no-underline transition-colors"
            class:active={page.url.pathname === '/reset-password'}
            aria-current={page.url.pathname === '/reset-password' ? 'page' : undefined}
        >
            RESET PASSWORD
        </a>
    </nav>

    <main class="auth-content">
        {@render children()}
    </main>
</div>

<style>
    @font-face {
        font-family: "Henny Penny";
        src: url("/fonts/HennyPenny-Regular.ttf") format("truetype");
        font-weight: 400;
        font-style: normal;
    }

    @font-face {
        font-family: "Rajdhani";
        src: url("/fonts/Rajdhani-Bold.ttf") format("truetype");
        font-weight: 700;
        font-style: normal;
    }

    .auth-header {
        margin-top: clamp(12px, 5vh, 50px);
        margin-bottom: 20px;
    }

    .logo {
        font-family: "Henny Penny", cursive;
        color: #fa8c01;
        font-size: clamp(64px, min(12vw + 40px, 20vh), 190px);
        font-weight: 400;
        letter-spacing: 2px;
        text-decoration: none;
        text-shadow:
            5px 5px 8px rgba(115, 20, 20, 0.8),
            10px 7px 16px rgba(100, 15, 15, 0.55);
    }

    .auth-tabs a.active::before {
        content: "";
        position: absolute;
        left: 50%;
        top: -10px;
        transform: translateX(-50%);
        border-left: 7px solid transparent;
        border-right: 7px solid transparent;
        border-top: 10px solid #ef4637;
    }

    .auth-content {
        width: 100%;
        max-width: 360px;
    }

    @media (max-width: 480px) {
        .auth-header {
            margin-bottom: 44px;
        }
    }

    @media (min-width: 640px) {
        .auth-tabs a.active::before {
            top: -15px;
            border-left-width: 10px;
            border-right-width: 10px;
            border-top-width: 15px;
        }
    }
</style>