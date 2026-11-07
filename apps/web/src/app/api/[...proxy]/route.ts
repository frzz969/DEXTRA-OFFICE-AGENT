import { NextRequest, NextResponse } from 'next/server';

/**
 * Server-side gateway ke FastAPI internal (service "app").
 *
 * DEXTRA_API_URL diinjeksikan Vercel via service binding pada service "web"
 * dan hanya tersedia saat runtime — JANGAN dibaca di module scope / build,
 * dan JANGAN pernah bocor ke browser. Handler ini satu-satunya jalur dari
 * browser (same-origin /api/*) ke FastAPI.
 *
 * Gateway ini dumb pipe: meneruskan method, body, query, cookie, CSRF, dan
 * Authorization apa adanya. Tidak ada business logic / governance di sini.
 */

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

async function proxy(req: NextRequest, { params }: { params: Promise<{ proxy: string[] }> }) {
  const backend = process.env.DEXTRA_API_URL;
  if (!backend) {
    // Gagal dengan jelas tanpa membocorkan URL internal.
    return new NextResponse(JSON.stringify({ detail: 'Backend tidak terkonfigurasi' }), {
      status: 502,
      headers: { 'content-type': 'application/json' },
    });
  }

  const { proxy: segments } = await params;
  const path = segments.join('/');
  const url = new URL(`/api/${path}`, backend);
  req.nextUrl.searchParams.forEach((v, k) => url.searchParams.set(k, v));

  const init: RequestInit = { method: req.method, headers: {} };
  const forward = ['content-type', 'x-csrf-token', 'cookie', 'authorization', 'accept', 'origin'];
  for (const name of forward) {
    const value = req.headers.get(name);
    if (value) (init.headers as Record<string, string>)[name] = value;
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    init.body = await req.text();
  }

  let res: Response;
  try {
    res = await fetch(url.toString(), init);
  } catch {
    // Backend mati / tidak terjangkau: 502 tanpa membocorkan URL.
    return new NextResponse(JSON.stringify({ detail: 'Backend tidak terjangkau' }), {
      status: 502,
      headers: { 'content-type': 'application/json' },
    });
  }

  const body = await res.arrayBuffer();
  const out = new NextResponse(body, { status: res.status });
  res.headers.forEach((v, k) => {
    if (k.toLowerCase() !== 'transfer-encoding' && k.toLowerCase() !== 'content-encoding') {
      out.headers.set(k, v);
    }
  });
  return out;
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
