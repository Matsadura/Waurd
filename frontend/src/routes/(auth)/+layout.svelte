<script lang="ts">
    import { page } from '$app/state';

    let { children } = $props();
</script>

<div class="min-h-screen flex flex-col items-center px-4 py-9 sm:px-6 sm:py-12 text-[#f5f3f5] font-bold font-['Rajdhani'] bg-[url('/images/background.png')] bg-cover bg-center bg-no-repeat">
    <header class="auth-header">
        <a href="/login" class="logo">Waurd</a>
    </header>

    <nav class="auth-tabs flex flex-wrap justify-center gap-4 mb-10">
        <a
            href="/login"
            class="relative px-8 py-1.5 rounded-md bg-[#ef4637] shadow-[0_10px_12px_rgba(0,0,0,0.45)] text-white text-2xl no-underline transition-colors"
            class:active={page.url.pathname === '/login'}
            aria-current={page.url.pathname === '/login' ? 'page' : undefined}
        >
            LOGIN
        </a>

        <a
            href="/register"
            class="relative px-8 py-1.5 rounded-md bg-[#ef4637] shadow-[0_10px_12px_rgba(0,0,0,0.45)] text-white text-2xl no-underline transition-colors"
            class:active={page.url.pathname === '/register'}
            aria-current={page.url.pathname === '/register' ? 'page' : undefined}
        >
            REGISTER
        </a>

        <a
            href="/reset-password"
            class="relative px-8 py-1.5 rounded-md bg-[#ef4637] shadow-[0_10px_12px_rgba(0,0,0,0.45)] text-white text-2xl no-underline transition-colors"
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
        font-display: swap;
    }

    @font-face {
        font-family: "Rajdhani";
        src: url("/fonts/Rajdhani-Bold.ttf") format("truetype");
        font-weight: 700;
        font-style: normal;
        font-display: swap;
    }

    .auth-header {
        margin-bottom: 30px;
    }

    .logo {
        font-family: "Henny Penny", cursive;
        color: #fa8c01;
        font-size: 190px;
        font-weight: 364.6;
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
        top: -15px;
        transform: translateX(-50%);
        border-left: 10px solid transparent;
        border-right: 10px solid transparent;
        border-top: 15px solid #ef4637;
    }

    /* .auth-tabs {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 12px;
        margin-bottom: 40px;
    }

    .auth-tabs a {
        padding: 6px 22px;
        border-radius: 6px;
        background: #252431;
        color: #e4e1e7;
        font-family: "Rajdhani", sans-serif;
        font-size: 14px;
        font-weight: 700;
        text-decoration: none;
        transition: background-color 0.2s, color 0.2s;
    }

    .auth-tabs a:hover {
        background: #383342;
    }

    .auth-tabs a.active {
        background: #f04438;
        color: white;
    }

    .auth-tabs a:focus-visible,
    .logo:focus-visible {
        outline: 2px solid #ff8a00;
        outline-offset: 4px;
    } */

    .auth-content {
        width: 100%;
        max-width: 360px;
    }

    @media (max-width: 480px) {
        .auth-header {
            margin-bottom: 44px;
        }

        .logo {
            font-size: 44px;
        }

        /* .auth-tabs {
            gap: 8px;
            margin-bottom: 32px;
        }

        .auth-tabs a {
            padding: 10px 12px;
            font-size: 12px;
        } */
    }
</style>