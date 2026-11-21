<script lang="ts">
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { unreadNotificationCount } from '$lib/utils/stores';
	import { onMount } from 'svelte';
	import { outcomeOfError, outcomeOfStatus, pageIsLeaving } from '$lib/utils/background-fetch';

	/**
	 * Unread badge for the app bar. No websockets in this stack, so the count is
	 * polled: on an interval, on navigation, and when the tab regains focus. The last
	 * two are what keep it from sitting stale for a minute after you read something.
	 */
	const POLL_INTERVAL_MS = 60_000;
	// Navigation and tab focus are signals that the count *might* be stale, not that it
	// is. Without a floor, clicking through ten pages fires ten requests for an answer
	// the timer would have given anyway.
	const MIN_REFRESH_GAP_MS = 30_000;
	// Past this the exact number is noise, and the badge would grow into the toolbar.
	const MAX_DISPLAYED = 99;

	// In a store so a mutation elsewhere can set it without a round trip; the poll is
	// the safety net for changes this tab did not make.
	const count = $derived($unreadNotificationCount);
	let failed = $state(false);

	const label = $derived(count > MAX_DISPLAYED ? `${MAX_DISPLAYED}+` : String(count));
	const title = $derived(count > 0 ? m.unreadNotifications({ count }) : m.noUnreadNotifications());

	let lastRefresh = 0;
	// Goldline (goldline.10, FND-283): signed out or not allowed means stop polling quietly; a request cut by
	// navigation or unload says nothing; other failures are a console warning, never an error.
	let stopped = false;
	let inFlight: AbortController | null = null;

	async function refresh({ force = false } = {}) {
		if (stopped) return;
		const now = Date.now();
		if (!force && now - lastRefresh < MIN_REFRESH_GAP_MS) return;
		lastRefresh = now;
		inFlight?.abort();
		const controller = new AbortController();
		inFlight = controller;
		try {
			const res = await fetch('/fe-api/notifications/unread-count', { signal: controller.signal });
			const outcome = outcomeOfStatus(res.status);
			if (outcome === 'stop') {
				stopped = true;
				return;
			}
			if (outcome !== 'ok') throw new Error(`HTTP ${res.status}`);
			const data = await res.json();
			unreadNotificationCount.set(Number(data?.count ?? 0));
			failed = false;
		} catch (error) {
			// A failed poll must never break the app bar; keep the last known count.
			if (outcomeOfError(error, pageIsLeaving()) === 'interrupted') return;
			failed = true;
			console.warn('Could not refresh the unread notification count:', error);
		} finally {
			if (inFlight === controller) inFlight = null;
		}
	}

	onMount(() => {
		// No initial refresh here: the $effect below already fires on mount.
		const interval = setInterval(() => refresh({ force: true }), POLL_INTERVAL_MS);
		const onFocus = () => {
			if (document.visibilityState === 'visible') refresh();
		};
		const onLeave = () => inFlight?.abort();
		document.addEventListener('visibilitychange', onFocus);
		window.addEventListener('pagehide', onLeave);
		return () => {
			clearInterval(interval);
			document.removeEventListener('visibilitychange', onFocus);
			window.removeEventListener('pagehide', onLeave);
			inFlight?.abort();
		};
	});

	// Re-poll on navigation, subject to the floor above. Mutations already push their
	// own count into the store, so this only has to catch what other tabs did.
	$effect(() => {
		page.url.pathname;
		refresh();
	});
</script>

<a
	href="/notifications"
	class="relative flex items-center justify-center w-9 h-9 rounded-lg text-surface-600-400
	hover:bg-surface-200-800 hover:text-surface-900-100 transition-colors duration-150"
	aria-label={title}
	{title}
	data-testid="notification-bell"
>
	<i class="fa-regular fa-bell text-lg" class:text-surface-400-600={failed}></i>
	{#if count > 0}
		<span
			class="absolute -top-0.5 -right-0.5 min-w-4 h-4 px-1 flex items-center justify-center
			rounded-full bg-error-500 text-white text-[10px] font-semibold leading-none"
			data-testid="notification-bell-badge"
		>
			{label}
		</span>
	{/if}
</a>
