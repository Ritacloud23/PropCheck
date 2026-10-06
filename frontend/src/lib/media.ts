/**
 * The API returns absolute URLs for locally stored photos (http://<api>/media/...). Serve them
 * through this site's /media rewrite instead, so they work even when the API host is internal.
 * Cloudinary (https) URLs are returned unchanged.
 */
export function localMedia(url: string | null | undefined): string | null {
  if (!url) return null;
  const i = url.indexOf("/media/");
  return i >= 0 && url.startsWith("http://") ? url.slice(i) : url;
}
