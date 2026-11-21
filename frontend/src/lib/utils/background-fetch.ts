/**
 * Goldline (v4.1.1-goldline.10, FND-283): background requests (the unread notification poll, the after-sign-in
 * risk acceptance check) must never put an error in the browser console when the page simply moved on or the
 * user may not see the data. Firefox and Safari reject an interrupted fetch with a TypeError ("NetworkError when
 * attempting to fetch resource", "Load failed"), which was logged as an error on every refused or redirected page.
 */

export type BackgroundOutcome =
	/** the response is usable */
	| 'ok'
	/** the request was cut off (navigation, unload, abort): say nothing */
	| 'interrupted'
	/** signed out or not allowed: say nothing and stop polling */
	| 'stop'
	/** a real failure worth a warning */
	| 'failed';

/** Classifies a finished fetch by its HTTP status. */
export function outcomeOfStatus(status: number): BackgroundOutcome {
	if (status >= 200 && status < 300) return 'ok';
	if (status === 401 || status === 403 || status === 404) return 'stop';
	return 'failed';
}

/** Classifies a rejected fetch. `pageLeaving` is true when the document is hidden or being unloaded. */
export function outcomeOfError(error: unknown, pageLeaving = false): BackgroundOutcome {
	const name = (error as { name?: string } | null)?.name;
	if (name === 'AbortError') return 'interrupted';
	// A TypeError from fetch is a network-level rejection: during navigation or unload that is the browser
	// cutting the request, not a fault. Outside that, it is still only a transient network problem.
	if (error instanceof TypeError) return pageLeaving ? 'interrupted' : 'failed';
	return 'failed';
}

/** True when the document is going away (hidden or unloading), so cut requests are expected. */
export function pageIsLeaving(): boolean {
	if (typeof document === 'undefined') return true;
	return document.visibilityState === 'hidden' || leaving;
}

let leaving = false;
if (typeof window !== 'undefined') {
	window.addEventListener('pagehide', () => {
		leaving = true;
	});
	window.addEventListener('pageshow', () => {
		leaving = false;
	});
}
