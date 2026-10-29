const EXPIRY_SECONDS = 365 * 24 * 60 * 60;
const PDF_PREFIX = "/DownloadFile/";

export async function onRequest(context) {
  const { request, env, next } = context;
  const url = new URL(request.url);
  if (request.method !== "GET" && request.method !== "HEAD") return next();
  if (!url.pathname.startsWith(PDF_PREFIX) || !/\.pdf$/i.test(url.pathname)) return next();

  let relativePath;
  try {
    relativePath = decodeURIComponent(url.pathname.slice(1));
  } catch {
    return next();
  }
  if (relativePath.split("/").some((part) => part === "..")) return next();

  const manifestResponse = await env.ASSETS.fetch(new URL("/pdf-expiry.json", url));
  if (!manifestResponse.ok) return next();

  let manifest;
  try {
    manifest = await manifestResponse.json();
  } catch {
    return next();
  }
  const uploadedAt = Number(manifest[relativePath]);
  if (!Number.isFinite(uploadedAt) || uploadedAt <= 0) return next();

  const expiresAt = uploadedAt + EXPIRY_SECONDS;
  if (Date.now() / 1000 < expiresAt) return next();

  return new Response(null, {
    status: 302,
    headers: {
      Location: new URL("/404.html", url).toString(),
      "Cache-Control": "no-store",
    },
  });
}
